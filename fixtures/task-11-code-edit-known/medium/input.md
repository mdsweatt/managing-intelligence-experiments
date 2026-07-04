File: inventory/reservations.py

```python
"""Inventory reservation service.

This module implements a soft-reservation system for a warehouse inventory
platform. Reservations place a temporary hold on physical stock so that a
checkout flow can complete payment without the items being sold out from
underneath it. Holds expire automatically after a TTL unless they are
committed (converted into a fulfilled order) or explicitly released.

The service is designed to be backend-agnostic: it talks to a small set of
storage and clock protocols rather than concrete database classes, which keeps
the reservation logic unit-testable without a live database.

Concurrency model
-----------------
All mutating operations on a single SKU are serialized through a per-SKU lock
obtained from the injected ``LockProvider``. Reads of aggregate availability
are lock-free and may be momentarily stale; callers that need a consistent
view across multiple SKUs should acquire a batch lock via
``ReservationManager.lock_skus``.

Units
-----
All quantities are integers measured in the SKU's base unit. The service never
deals in fractional stock; callers must convert before entering this layer.
"""

from __future__ import annotations

import logging
import threading
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import (
    Callable,
    Dict,
    Iterable,
    Iterator,
    List,
    Mapping,
    MutableMapping,
    Optional,
    Protocol,
    Sequence,
    Tuple,
)

logger = logging.getLogger("inventory.reservations")

# Default time-to-live for a hold before it is eligible for reaping.
DEFAULT_TTL = timedelta(minutes=15)

# Hard upper bound on how long any single reservation may live, even if a
# caller requests a longer TTL. Protects against holds that never expire.
MAX_TTL = timedelta(hours=4)

# Maximum number of distinct line items permitted in a single reservation.
MAX_LINES_PER_RESERVATION = 100

# Sentinel used by the reaper to batch-expire in chunks.
REAP_BATCH_SIZE = 500


class ReservationState(str, Enum):
    """Lifecycle states for a reservation.

    The legal transitions are::

        PENDING -> CONFIRMED -> COMMITTED
        PENDING -> CONFIRMED -> RELEASED
        PENDING -> RELEASED
        PENDING -> EXPIRED
        CONFIRMED -> EXPIRED

    Any other transition is rejected by ``_assert_transition``.
    """

    PENDING = "pending"
    CONFIRMED = "confirmed"
    COMMITTED = "committed"
    RELEASED = "released"
    EXPIRED = "expired"

    @property
    def is_terminal(self) -> bool:
        """Return True if no further transition is permitted from this state."""
        return self in (
            ReservationState.COMMITTED,
            ReservationState.RELEASED,
            ReservationState.EXPIRED,
        )

    @property
    def holds_stock(self) -> bool:
        """Return True if a reservation in this state is consuming availability."""
        return self in (ReservationState.PENDING, ReservationState.CONFIRMED)


_LEGAL_TRANSITIONS: Mapping[ReservationState, Tuple[ReservationState, ...]] = {
    ReservationState.PENDING: (
        ReservationState.CONFIRMED,
        ReservationState.RELEASED,
        ReservationState.EXPIRED,
    ),
    ReservationState.CONFIRMED: (
        ReservationState.COMMITTED,
        ReservationState.RELEASED,
        ReservationState.EXPIRED,
    ),
    ReservationState.COMMITTED: (),
    ReservationState.RELEASED: (),
    ReservationState.EXPIRED: (),
}


class ReservationError(Exception):
    """Base class for all reservation-related errors."""


class InsufficientStockError(ReservationError):
    """Raised when a reservation cannot be satisfied from available stock."""

    def __init__(self, sku: str, requested: int, available: int) -> None:
        self.sku = sku
        self.requested = requested
        self.available = available
        super().__init__(
            f"insufficient stock for {sku!r}: requested {requested}, "
            f"available {available}"
        )


class UnknownSkuError(ReservationError):
    """Raised when an operation references a SKU the catalog does not know."""

    def __init__(self, sku: str) -> None:
        self.sku = sku
        super().__init__(f"unknown sku: {sku!r}")


class ReservationNotFoundError(ReservationError):
    """Raised when a reservation id cannot be located in the store."""

    def __init__(self, reservation_id: str) -> None:
        self.reservation_id = reservation_id
        super().__init__(f"no reservation with id {reservation_id!r}")


class IllegalTransitionError(ReservationError):
    """Raised when a state transition is not permitted by the lifecycle."""

    def __init__(self, current: ReservationState, target: ReservationState) -> None:
        self.current = current
        self.target = target
        super().__init__(
            f"illegal transition {current.value!r} -> {target.value!r}"
        )


class ReservationExpiredError(ReservationError):
    """Raised when an operation is attempted on a hold past its TTL."""

    def __init__(self, reservation_id: str, expires_at: datetime) -> None:
        self.reservation_id = reservation_id
        self.expires_at = expires_at
        super().__init__(
            f"reservation {reservation_id!r} expired at {expires_at.isoformat()}"
        )


class LineQuantityError(ReservationError):
    """Raised when a requested line quantity is non-positive or too large."""


@dataclass(frozen=True)
class ReservationLine:
    """A single SKU-and-quantity pair within a reservation."""

    sku: str
    quantity: int

    def __post_init__(self) -> None:
        if not self.sku:
            raise LineQuantityError("line sku must be non-empty")
        if self.quantity <= 0:
            raise LineQuantityError(
                f"line quantity must be positive, got {self.quantity}"
            )


@dataclass
class Reservation:
    """An active hold on one or more SKUs.

    Reservations are mutable only through the ``ReservationManager``; callers
    should treat the fields here as read-only snapshots.
    """

    reservation_id: str
    customer_id: str
    lines: Tuple[ReservationLine, ...]
    state: ReservationState
    created_at: datetime
    expires_at: datetime
    updated_at: datetime
    confirmed_at: Optional[datetime] = None
    committed_at: Optional[datetime] = None
    released_at: Optional[datetime] = None
    order_id: Optional[str] = None
    metadata: Mapping[str, str] = field(default_factory=dict)

    @property
    def skus(self) -> Tuple[str, ...]:
        """Return the distinct SKUs covered by this reservation."""
        return tuple(line.sku for line in self.lines)

    def quantity_for(self, sku: str) -> int:
        """Return the held quantity for ``sku``, or 0 if not in this hold."""
        return sum(line.quantity for line in self.lines if line.sku == sku)

    def is_expired(self, now: datetime) -> bool:
        """Return True if this hold has passed its TTL as of ``now``."""
        return not self.state.is_terminal and now >= self.expires_at

    def total_units(self) -> int:
        """Return the sum of all line quantities in the reservation."""
        return sum(line.quantity for line in self.lines)


@dataclass(frozen=True)
class StockSnapshot:
    """An immutable view of stock for a single SKU at a point in time."""

    sku: str
    on_hand: int
    held: int

    @property
    def available(self) -> int:
        """Return the sellable quantity (on hand minus active holds)."""
        return max(0, self.on_hand - self.held)


class Clock(Protocol):
    """A source of the current time, injectable for testing."""

    def now(self) -> datetime:  # pragma: no cover - protocol
        ...


class SystemClock:
    """A ``Clock`` backed by the system wall clock in UTC."""

    def now(self) -> datetime:
        return datetime.now(timezone.utc)


class FixedClock:
    """A ``Clock`` that returns a fixed instant, advanceable by tests."""

    def __init__(self, instant: datetime) -> None:
        self._instant = instant

    def now(self) -> datetime:
        return self._instant

    def advance(self, delta: timedelta) -> None:
        """Move the fixed clock forward by ``delta``."""
        self._instant = self._instant + delta


class LockProvider(Protocol):
    """Supplies context-managed locks keyed by an arbitrary string."""

    def lock(self, key: str) -> "ContextLock":  # pragma: no cover - protocol
        ...


class ContextLock(Protocol):
    """A re-entrant lock usable as a context manager."""

    def __enter__(self) -> "ContextLock":  # pragma: no cover - protocol
        ...

    def __exit__(self, *exc: object) -> None:  # pragma: no cover - protocol
        ...


class InMemoryLockProvider:
    """A ``LockProvider`` backed by per-key ``threading.RLock`` instances.

    Suitable for single-process deployments and tests. A distributed
    deployment should swap in a Redis- or database-backed implementation that
    honors the same protocol.
    """

    def __init__(self) -> None:
        self._locks: MutableMapping[str, threading.RLock] = {}
        self._guard = threading.Lock()

    def lock(self, key: str) -> threading.RLock:
        with self._guard:
            existing = self._locks.get(key)
            if existing is None:
                existing = threading.RLock()
                self._locks[key] = existing
            return existing


class CatalogProvider(Protocol):
    """Supplies on-hand stock counts and validates SKU existence."""

    def on_hand(self, sku: str) -> int:  # pragma: no cover - protocol
        ...

    def exists(self, sku: str) -> bool:  # pragma: no cover - protocol
        ...


class InMemoryCatalog:
    """A simple in-memory catalog of SKU -> on-hand quantity."""

    def __init__(self, stock: Optional[Mapping[str, int]] = None) -> None:
        self._stock: Dict[str, int] = dict(stock or {})

    def on_hand(self, sku: str) -> int:
        if sku not in self._stock:
            raise UnknownSkuError(sku)
        return self._stock[sku]

    def exists(self, sku: str) -> bool:
        return sku in self._stock

    def set_on_hand(self, sku: str, quantity: int) -> None:
        """Set the on-hand quantity for a SKU, creating it if necessary."""
        if quantity < 0:
            raise ValueError(f"on-hand quantity cannot be negative: {quantity}")
        self._stock[sku] = quantity

    def adjust_on_hand(self, sku: str, delta: int) -> int:
        """Apply a signed delta to on-hand stock and return the new value."""
        current = self.on_hand(sku)
        updated = current + delta
        if updated < 0:
            raise ValueError(
                f"adjustment would drive {sku!r} negative: {current} + {delta}"
            )
        self._stock[sku] = updated
        return updated


class ReservationStore(Protocol):
    """Persistence boundary for reservation records."""

    def get(self, reservation_id: str) -> Optional[Reservation]:  # pragma: no cover
        ...

    def put(self, reservation: Reservation) -> None:  # pragma: no cover
        ...

    def delete(self, reservation_id: str) -> None:  # pragma: no cover
        ...

    def all_active(self) -> Iterable[Reservation]:  # pragma: no cover
        ...

    def for_sku(self, sku: str) -> Iterable[Reservation]:  # pragma: no cover
        ...


class InMemoryReservationStore:
    """A dict-backed ``ReservationStore`` for tests and single-node use."""

    def __init__(self) -> None:
        self._records: Dict[str, Reservation] = {}

    def get(self, reservation_id: str) -> Optional[Reservation]:
        return self._records.get(reservation_id)

    def put(self, reservation: Reservation) -> None:
        self._records[reservation.reservation_id] = reservation

    def delete(self, reservation_id: str) -> None:
        self._records.pop(reservation_id, None)

    def all_active(self) -> Iterator[Reservation]:
        for record in list(self._records.values()):
            if record.state.holds_stock:
                yield record

    def for_sku(self, sku: str) -> Iterator[Reservation]:
        for record in list(self._records.values()):
            if sku in record.skus and record.state.holds_stock:
                yield record

    def count(self) -> int:
        """Return the total number of stored records (any state)."""
        return len(self._records)


@dataclass
class ReservationMetrics:
    """Counters describing reservation activity since process start."""

    created: int = 0
    confirmed: int = 0
    committed: int = 0
    released: int = 0
    expired: int = 0
    rejected_insufficient: int = 0

    def as_dict(self) -> Dict[str, int]:
        """Return the metrics as a plain dict for emission to a sink."""
        return {
            "created": self.created,
            "confirmed": self.confirmed,
            "committed": self.committed,
            "released": self.released,
            "expired": self.expired,
            "rejected_insufficient": self.rejected_insufficient,
        }


def _normalize_lines(lines: Sequence[ReservationLine]) -> Tuple[ReservationLine, ...]:
    """Collapse duplicate SKUs into a single line and validate the request.

    Lines for the same SKU are summed. The result is sorted by SKU so that
    two logically equivalent requests produce identical reservation records,
    which keeps hashing and equality checks stable.
    """
    if not lines:
        raise LineQuantityError("a reservation must contain at least one line")
    merged: Dict[str, int] = {}
    for line in lines:
        merged[line.sku] = merged.get(line.sku, 0) + line.quantity
    if len(merged) > MAX_LINES_PER_RESERVATION:
        raise LineQuantityError(
            f"reservation has {len(merged)} lines, exceeds "
            f"{MAX_LINES_PER_RESERVATION}"
        )
    return tuple(
        ReservationLine(sku=sku, quantity=qty)
        for sku, qty in sorted(merged.items())
    )


def _clamp_ttl(ttl: timedelta) -> timedelta:
    """Clamp a requested TTL into the legal ``(0, MAX_TTL]`` range."""
    if ttl <= timedelta(0):
        raise ValueError(f"ttl must be positive, got {ttl}")
    if ttl > MAX_TTL:
        logger.warning("requested ttl %s exceeds MAX_TTL %s; clamping", ttl, MAX_TTL)
        return MAX_TTL
    return ttl


def _assert_transition(current: ReservationState, target: ReservationState) -> None:
    """Raise ``IllegalTransitionError`` if ``current -> target`` is not legal."""
    if target not in _LEGAL_TRANSITIONS.get(current, ()):
        raise IllegalTransitionError(current, target)


def _new_reservation_id() -> str:
    """Generate a unique, prefixed reservation identifier."""
    return f"rsv_{uuid.uuid4().hex}"


class ReservationManager:
    """Coordinates reservation lifecycle against stock, locks, and storage.

    A single manager instance is safe to share across threads. All operations
    that change availability acquire the relevant per-SKU locks first, in a
    deterministic (sorted) order, to avoid deadlocks between concurrent
    multi-SKU reservations.
    """

    def __init__(
        self,
        store: ReservationStore,
        catalog: CatalogProvider,
        locks: LockProvider,
        clock: Optional[Clock] = None,
        default_ttl: timedelta = DEFAULT_TTL,
        metrics: Optional[ReservationMetrics] = None,
    ) -> None:
        self._store = store
        self._catalog = catalog
        self._locks = locks
        self._clock = clock or SystemClock()
        self._default_ttl = _clamp_ttl(default_ttl)
        self._metrics = metrics or ReservationMetrics()

    # -- public API ----------------------------------------------------------

    @property
    def metrics(self) -> ReservationMetrics:
        """Return the live metrics object for this manager."""
        return self._metrics

    @contextmanager
    def lock_skus(self, skus: Iterable[str]) -> Iterator[None]:
        """Acquire per-SKU locks for ``skus`` in a deadlock-safe order.

        Locks are taken in sorted order so that two callers requesting an
        overlapping set always acquire shared locks in the same sequence.
        """
        ordered = sorted(set(skus))
        acquired: List[ContextLock] = []
        try:
            for sku in ordered:
                lock = self._locks.lock(sku)
                lock.__enter__()
                acquired.append(lock)
            yield
        finally:
            for lock in reversed(acquired):
                lock.__exit__(None, None, None)

    def reserve(
        self,
        customer_id: str,
        lines: Sequence[ReservationLine],
        ttl: Optional[timedelta] = None,
        metadata: Optional[Mapping[str, str]] = None,
    ) -> Reservation:
        """Create a PENDING hold for ``customer_id`` covering ``lines``.

        Validates SKU existence and availability under lock, then persists the
        new reservation. Raises ``InsufficientStockError`` if any line cannot
        be satisfied; the entire reservation is all-or-nothing.
        """
        if not customer_id:
            raise ReservationError("customer_id must be non-empty")
        normalized = _normalize_lines(lines)
        effective_ttl = _clamp_ttl(ttl) if ttl is not None else self._default_ttl
        skus = [line.sku for line in normalized]

        with self.lock_skus(skus):
            for line in normalized:
                self._check_available(line.sku, line.quantity)
            now = self._clock.now()
            reservation = Reservation(
                reservation_id=_new_reservation_id(),
                customer_id=customer_id,
                lines=normalized,
                state=ReservationState.PENDING,
                created_at=now,
                expires_at=now + effective_ttl,
                updated_at=now,
                metadata=dict(metadata or {}),
            )
            self._store.put(reservation)
            self._metrics.created += 1
            logger.info(
                "reserved %s for customer %s (%d units across %d skus)",
                reservation.reservation_id,
                customer_id,
                reservation.total_units(),
                len(normalized),
            )
            return reservation

    def confirm(self, reservation_id: str) -> Reservation:
        """Move a PENDING hold to CONFIRMED (e.g. payment authorized).

        Confirming does not change availability but signals that the hold is
        committed-intent and should be prioritized by the reaper last.
        """
        with self._with_reservation(reservation_id) as reservation:
            self._reject_if_expired(reservation)
            _assert_transition(reservation.state, ReservationState.CONFIRMED)
            now = self._clock.now()
            updated = replace(
                reservation,
                state=ReservationState.CONFIRMED,
                confirmed_at=now,
                updated_at=now,
            )
            self._store.put(updated)
            self._metrics.confirmed += 1
            logger.info("confirmed reservation %s", reservation_id)
            return updated

    def commit(self, reservation_id: str, order_id: str) -> Reservation:
        """Convert a CONFIRMED hold into a fulfilled order.

        Decrements on-hand stock by the held quantities and marks the
        reservation COMMITTED, attaching ``order_id``. After this the hold no
        longer counts toward availability because the stock is physically gone.
        """
        if not order_id:
            raise ReservationError("order_id must be non-empty")
        with self._with_reservation(reservation_id) as reservation:
            self._reject_if_expired(reservation)
            _assert_transition(reservation.state, ReservationState.COMMITTED)
            with self.lock_skus(reservation.skus):
                for line in reservation.lines:
                    self._decrement_on_hand(line.sku, line.quantity)
                now = self._clock.now()
                updated = replace(
                    reservation,
                    state=ReservationState.COMMITTED,
                    committed_at=now,
                    updated_at=now,
                    order_id=order_id,
                )
                self._store.put(updated)
                self._metrics.committed += 1
                logger.info(
                    "committed reservation %s as order %s", reservation_id, order_id
                )
                return updated

    def release(self, reservation_id: str) -> Reservation:
        """Release a hold, returning its stock to availability.

        Legal from PENDING or CONFIRMED. The freed stock becomes immediately
        available to other callers once the per-SKU locks are dropped.
        """
        with self._with_reservation(reservation_id) as reservation:
            _assert_transition(reservation.state, ReservationState.RELEASED)
            now = self._clock.now()
            updated = replace(
                reservation,
                state=ReservationState.RELEASED,
                released_at=now,
                updated_at=now,
            )
            self._store.put(updated)
            self._metrics.released += 1
            logger.info("released reservation %s", reservation_id)
            return updated

    def extend(self, reservation_id: str, ttl: timedelta) -> Reservation:
        """Extend a hold's TTL, measured from now, clamped to ``MAX_TTL``.

        Only non-terminal holds may be extended; an expired hold must be
        recreated rather than revived.
        """
        clamped = _clamp_ttl(ttl)
        with self._with_reservation(reservation_id) as reservation:
            if reservation.state.is_terminal:
                raise IllegalTransitionError(reservation.state, reservation.state)
            self._reject_if_expired(reservation)
            now = self._clock.now()
            updated = replace(
                reservation,
                expires_at=now + clamped,
                updated_at=now,
            )
            self._store.put(updated)
            logger.info(
                "extended reservation %s to %s",
                reservation_id,
                updated.expires_at.isoformat(),
            )
            return updated

    def get(self, reservation_id: str) -> Reservation:
        """Fetch a reservation by id or raise ``ReservationNotFoundError``."""
        reservation = self._store.get(reservation_id)
        if reservation is None:
            raise ReservationNotFoundError(reservation_id)
        return reservation

    def availability(self, sku: str) -> StockSnapshot:
        """Return a point-in-time stock snapshot for ``sku``.

        This is a lock-free read and may briefly disagree with a concurrent
        ``reserve`` that has acquired the SKU lock but not yet persisted.
        """
        on_hand = self._catalog.on_hand(sku)
        held = self._held_quantity(sku)
        return StockSnapshot(sku=sku, on_hand=on_hand, held=held)

    def availability_for(self, skus: Iterable[str]) -> Dict[str, StockSnapshot]:
        """Return availability snapshots for several SKUs at once."""
        return {sku: self.availability(sku) for sku in skus}

    def can_reserve(self, lines: Sequence[ReservationLine]) -> bool:
        """Return True if ``lines`` could be reserved right now.

        This is a non-binding pre-check: it takes the relevant SKU locks, sums
        the requested quantities per SKU, and compares against current
        availability. Because the locks are dropped on return, a later
        ``reserve`` may still fail under contention. Callers should treat a
        True result as a hint, not a guarantee.
        """
        normalized = _normalize_lines(lines)
        with self.lock_skus([line.sku for line in normalized]):
            for line in normalized:
                if not self._catalog.exists(line.sku):
                    return False
                if line.quantity > self.availability(line.sku).available:
                    return False
            return True

    def holds_for_customer(self, customer_id: str) -> List[Reservation]:
        """Return all active holds belonging to ``customer_id``.

        Useful for surfacing a customer's in-flight carts and for enforcing
        per-customer hold limits at the application layer.
        """
        return [
            reservation
            for reservation in self._store.all_active()
            if reservation.customer_id == customer_id
        ]

    def release_all_for_customer(self, customer_id: str) -> int:
        """Release every active hold for ``customer_id`` and return the count.

        Best-effort: a hold that transitions out from under us (e.g. expires
        concurrently) is skipped rather than raising.
        """
        released = 0
        for reservation in self.holds_for_customer(customer_id):
            try:
                self.release(reservation.reservation_id)
                released += 1
            except (IllegalTransitionError, ReservationNotFoundError):
                logger.debug(
                    "skipping release for %s during bulk customer release",
                    reservation.reservation_id,
                )
        return released

    def rebalance_metadata(
        self, reservation_id: str, metadata: Mapping[str, str]
    ) -> Reservation:
        """Merge ``metadata`` into a non-terminal hold and persist it.

        Metadata is advisory (e.g. cart source, promo code) and never affects
        availability, so this does not re-validate stock.
        """
        with self._with_reservation(reservation_id) as reservation:
            if reservation.state.is_terminal:
                raise IllegalTransitionError(reservation.state, reservation.state)
            merged = dict(reservation.metadata)
            merged.update(metadata)
            now = self._clock.now()
            updated = replace(reservation, metadata=merged, updated_at=now)
            self._store.put(updated)
            return updated

    def reap_expired(self, now: Optional[datetime] = None) -> int:
        """Expire all holds past their TTL and return the count expired.

        Processed in batches of ``REAP_BATCH_SIZE`` to bound the work done
        while holding locks. Returns the number of reservations transitioned
        to EXPIRED.
        """
        moment = now or self._clock.now()
        expired_count = 0
        batch: List[Reservation] = []
        for reservation in self._store.all_active():
            if reservation.is_expired(moment):
                batch.append(reservation)
            if len(batch) >= REAP_BATCH_SIZE:
                expired_count += self._expire_batch(batch, moment)
                batch = []
        if batch:
            expired_count += self._expire_batch(batch, moment)
        if expired_count:
            logger.info("reaped %d expired reservations", expired_count)
        return expired_count

    def purge_terminal(self, older_than: timedelta) -> int:
        """Delete terminal records last updated before ``older_than`` ago.

        Keeps the store from growing unbounded with COMMITTED/RELEASED/EXPIRED
        records. Returns the number of records purged.
        """
        cutoff = self._clock.now() - older_than
        purged = 0
        for reservation in list(self._iter_all()):
            if reservation.state.is_terminal and reservation.updated_at < cutoff:
                self._store.delete(reservation.reservation_id)
                purged += 1
        if purged:
            logger.info("purged %d terminal reservations", purged)
        return purged

    # -- internal helpers ----------------------------------------------------

    @contextmanager
    def _with_reservation(self, reservation_id: str) -> Iterator[Reservation]:
        """Yield a reservation under its SKU locks, raising if missing."""
        reservation = self._store.get(reservation_id)
        if reservation is None:
            raise ReservationNotFoundError(reservation_id)
        with self.lock_skus(reservation.skus):
            current = self._store.get(reservation_id)
            if current is None:
                raise ReservationNotFoundError(reservation_id)
            yield current

    def _check_available(self, sku: str, requested: int) -> None:
        """Raise ``InsufficientStockError`` if ``requested`` exceeds available."""
        if not self._catalog.exists(sku):
            raise UnknownSkuError(sku)
        snapshot = self.availability(sku)
        if requested > snapshot.available:
            self._metrics.rejected_insufficient += 1
            raise InsufficientStockError(sku, requested, snapshot.available)

    def _held_quantity(self, sku: str) -> int:
        """Sum the held quantity for ``sku`` across active reservations."""
        return sum(
            reservation.quantity_for(sku)
            for reservation in self._store.for_sku(sku)
        )

    def _decrement_on_hand(self, sku: str, quantity: int) -> None:
        """Reduce physical on-hand stock when a hold is committed."""
        adjust = getattr(self._catalog, "adjust_on_hand", None)
        if callable(adjust):
            adjust(sku, -quantity)
        else:  # pragma: no cover - defensive for read-only catalogs
            logger.warning(
                "catalog for %s does not support adjustment; on-hand not decremented",
                sku,
            )

    def _reject_if_expired(self, reservation: Reservation) -> None:
        """Raise ``ReservationExpiredError`` if the hold has passed its TTL."""
        if reservation.is_expired(self._clock.now()):
            raise ReservationExpiredError(
                reservation.reservation_id, reservation.expires_at
            )

    def _expire_batch(self, batch: Sequence[Reservation], now: datetime) -> int:
        """Transition a batch of holds to EXPIRED under their SKU locks."""
        count = 0
        for reservation in batch:
            try:
                with self.lock_skus(reservation.skus):
                    current = self._store.get(reservation.reservation_id)
                    if current is None or not current.is_expired(now):
                        continue
                    _assert_transition(current.state, ReservationState.EXPIRED)
                    updated = replace(
                        current,
                        state=ReservationState.EXPIRED,
                        updated_at=now,
                    )
                    self._store.put(updated)
                    self._metrics.expired += 1
                    count += 1
            except IllegalTransitionError:
                logger.debug(
                    "skipping expire for %s in state %s",
                    reservation.reservation_id,
                    reservation.state,
                )
        return count

    def _iter_all(self) -> Iterator[Reservation]:
        """Best-effort iteration over every stored record, active or not."""
        all_records = getattr(self._store, "_records", None)
        if isinstance(all_records, dict):
            yield from list(all_records.values())
        else:  # pragma: no cover - fallback for opaque stores
            yield from self._store.all_active()


class ReservationReaper:
    """A small driver that periodically calls ``reap_expired`` on a manager.

    Intended to be run on a background thread or invoked by a scheduler. It
    tracks a simple run count and the last sweep size for observability.
    """

    def __init__(
        self,
        manager: ReservationManager,
        interval: timedelta = timedelta(seconds=30),
    ) -> None:
        self._manager = manager
        self._interval = interval
        self._runs = 0
        self._last_swept = 0
        self._stop = threading.Event()

    @property
    def runs(self) -> int:
        """Return how many sweeps have completed."""
        return self._runs

    @property
    def last_swept(self) -> int:
        """Return how many holds were expired in the most recent sweep."""
        return self._last_swept

    def sweep_once(self) -> int:
        """Run a single reap pass and record its result."""
        swept = self._manager.reap_expired()
        self._runs += 1
        self._last_swept = swept
        return swept

    def run_forever(self, sleep: Callable[[float], None]) -> None:
        """Loop until ``stop`` is set, sweeping every ``interval`` seconds.

        ``sleep`` is injected so tests can drive the loop without real time.
        """
        seconds = self._interval.total_seconds()
        while not self._stop.is_set():
            self.sweep_once()
            sleep(seconds)

    def stop(self) -> None:
        """Signal ``run_forever`` to exit after its current iteration."""
        self._stop.set()


def build_default_manager(
    initial_stock: Optional[Mapping[str, int]] = None,
    clock: Optional[Clock] = None,
) -> ReservationManager:
    """Construct a manager wired with in-memory components.

    Convenience for tests, demos, and single-process deployments. Production
    callers should inject durable store/catalog/lock implementations directly.
    """
    catalog = InMemoryCatalog(initial_stock or {})
    store = InMemoryReservationStore()
    locks = InMemoryLockProvider()
    return ReservationManager(
        store=store,
        catalog=catalog,
        locks=locks,
        clock=clock or SystemClock(),
    )


def summarize_holds(manager: ReservationManager, sku: str) -> Dict[str, int]:
    """Return a small summary dict of stock posture for one SKU."""
    snapshot = manager.availability(sku)
    return {
        "on_hand": snapshot.on_hand,
        "held": snapshot.held,
        "available": snapshot.available,
    }
```
