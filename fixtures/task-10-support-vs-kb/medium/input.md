# Cartographa Help Center

Cartographa is a route-optimization and delivery-scheduling platform for fleet operators. It ingests your stops, vehicles, drivers, and time windows, builds optimized routes against your business rules, and dispatches them to drivers through the Cartographa Driver app. This Help Center collects the articles our support team references most often. Each article is self-contained; use the section headings to find the topic you need.

Throughout this guide, "workspace" refers to your organization's top-level account, "depot" refers to a physical origin location from which routes begin and end, "plan" refers to a single day's set of optimized routes, and "the Optimizer" refers to the engine that turns stops into routes. Feature names, error codes, and limits are consistent across every article below.

---

## Article 1: Getting Started — Your First Optimized Plan

Welcome to Cartographa. This article walks a brand-new workspace from sign-up to a first dispatched plan in about thirty minutes.

When you create a workspace, Cartographa provisions a single default depot at the address you supplied during sign-up. Before you can build a plan, the depot needs at least one vehicle and one driver attached to it. Open **Settings → Depots**, select the default depot, and confirm its address resolves to a map pin; if the pin lands in the wrong place, click **Adjust Pin** and drag it, because the Optimizer routes from the pin, not from the typed address.

Next, add a vehicle under **Fleet → Vehicles**. A vehicle needs a name, a capacity (expressed in your chosen unit — see Article 12 on units and limits), and a home depot. Then add a driver under **Fleet → Drivers** and assign the driver a default vehicle and a shift window. The shift window is the span during which the driver is available; the Optimizer will not schedule stops outside it.

With one depot, one vehicle, and one driver in place, you can build your first plan. Go to **Plans → New Plan**, choose a service date, and import stops. For a first run, use **Add Stop Manually** to create three or four stops with addresses near your depot. Click **Optimize**. Within a few seconds the Optimizer returns a route, drawn on the map, with an estimated start time, sequence, and arrival time per stop.

To send the plan to the road, click **Dispatch**. The assigned driver receives the route in the Cartographa Driver app on their phone. Once dispatched, the plan moves from **Draft** to **Dispatched** status and stops accepting structural edits; see Article 9 on plan states for how to make changes after dispatch.

A first plan that returns zero routed stops almost always means the stops fell outside every driver's shift window or exceeded vehicle capacity. Article 6 on troubleshooting unrouted stops covers this in detail.

A few habits make the difference between a first plan that "just works" and an hour of confusion. Set the depot time zone correctly before importing anything, because time windows are interpreted in the depot's local time and a wrong zone shifts every window by hours, producing a plan full of unroutable stops for no obvious reason. Give your first driver a generously wide shift while you are learning — an eight-to-six window, say — so that early experiments are not silently constrained by a narrow shift you forgot you set. And keep your first few plans small. The Optimizer is just as happy with three stops as three thousand, but a small plan lets you read the result, click the **Why?** link on each stop, and build an intuition for how time windows, capacity, and skills interact before you trust it with a full day. Once the small plan behaves the way you expect, scaling up is a matter of importing more stops and adding the vehicles and drivers to carry them; the mechanics do not change.

---

## Article 2: Inviting Your Team and Understanding Roles

Cartographa uses four built-in roles, and every workspace member holds exactly one. Choosing the right role keeps planning safe without blocking the people who need to act.

The **Owner** is the single billing-responsible member of the workspace. The Owner can do everything an Admin can, plus change the subscription plan, update payment details, and transfer ownership. There is always exactly one Owner; transferring ownership is the only way to change who holds it, under **Settings → Workspace → Transfer Ownership**.

An **Admin** can manage depots, fleet, integrations, and members, and can build, optimize, and dispatch plans. Admins cannot touch billing. Most operations managers should be Admins.

A **Planner** can build, optimize, and dispatch plans and manage stops, but cannot change depots, fleet configuration, integrations, or members. Planners are your day-to-day dispatchers.

A **Viewer** has read-only access to plans, routes, and live tracking, and is the correct role for warehouse staff, customer-service agents who answer "where is my delivery" questions, or external stakeholders. Viewers cannot dispatch.

To invite a member, go to **Settings → Members → Invite**, enter the email address, and select a role. The invitee receives an email with a link valid for seven days. If the link expires, an Admin can resend it from the same screen. A pending invitation does not count against your seat limit until accepted.

Drivers are not workspace members and do not hold a role. Drivers are created under **Fleet → Drivers** and sign in only to the Driver app using a one-time code sent to their phone. A driver never sees the planning console.

A practical consequence of the seat model is that giving someone read-only visibility is free. If a colleague keeps asking a Planner "where is delivery 482," the right answer is almost never to read it out from Tracking each time — it is to invite them as a Viewer so they can watch the board themselves at no cost to your bill. Reserve the paid Planner and Admin seats for people who actually build, change, or dispatch. When someone leaves your organization, remove their membership under **Settings → Members → (member) → Remove** rather than merely changing their password; removal revokes their access immediately and frees the seat at the next billing cycle. Removing a member does not delete the plans they created — those belong to the workspace, not the individual — so there is no risk of losing work by removing a departed colleague.

Role changes take effect immediately and are recorded in the audit log on the Scale tier (Article 15). If a Planner reports that an action they could perform yesterday now returns **CART-403**, the first thing to check is whether their role was changed; the audit log will show who changed it and when.

---

## Article 3: Importing Stops in Bulk

Most workspaces do not enter stops by hand. Cartographa imports stops from a CSV file or directly from a connected order system (see Article 5 on integrations).

To import a CSV, open **Plans → New Plan → Import → Upload CSV**. Your file must contain a header row. The required columns are `address` (or, alternatively, a `latitude` and `longitude` pair), and `service_date`. Optional columns the Optimizer understands include `time_window_start`, `time_window_end`, `service_duration_minutes`, `size`, `required_skill`, and `priority`. Any column whose header Cartographa does not recognize is preserved as a custom note on the stop and shown to the driver, but is ignored by the Optimizer.

Addresses are geocoded on import. A stop whose address cannot be geocoded with confidence is flagged with a yellow warning triangle and placed in the **Needs Review** tray rather than silently dropped. You can correct it by clicking the stop and either editing the address or dropping a manual pin. The Optimizer will not route a stop that is still in Needs Review.

The time-window columns accept 24-hour `HH:MM` local to the depot's time zone. If `time_window_end` is earlier than `time_window_start`, the import rejects that row and reports the row number. The `size` column is matched against vehicle capacity in the same unit configured for the workspace.

A single CSV import is capped at 5,000 rows. Files above the cap are rejected with error **CART-413** (see Article 11). To plan more than 5,000 stops in a day, split them across multiple plans or contact support about high-volume planning.

Two import behaviors surprise new users often enough to call out here. First, import is additive, not replacing: uploading a second CSV into a plan that already has stops adds the new rows rather than overwriting the existing ones. If you re-upload a corrected file expecting it to replace the first, you will instead have every stop twice. To start over, clear the plan's stops first (**Plan → Clear Stops**) and then import. Second, Cartographa does not deduplicate across imports — two rows with the same address are treated as two genuine stops, because a route legitimately may visit one address twice (a morning drop and an afternoon pickup, say). If your source data contains accidental duplicates, remove them before import.

A row that fails to import for a structural reason — an inverted time window, a missing required column, a malformed coordinate — does not abort the whole file. Cartographa imports every valid row and reports the rejected rows by number in an import summary, so a single bad row never costs you the other 4,999. Download the summary, fix the named rows, and import just those in a follow-up file.

---

## Article 4: Setting Time Windows, Service Durations, and Skills

The quality of an optimized plan depends on the constraints you give the Optimizer. Three constraints do most of the work: time windows, service durations, and skills.

A **time window** is the span during which a stop may be serviced. If a customer must receive a delivery between 9:00 and 11:00, set `time_window_start` to 09:00 and `time_window_end` to 11:00. The Optimizer treats time windows as hard constraints by default: it will leave a stop unrouted rather than arrive outside its window. You can soften this behavior per plan under **Plan Settings → Constraints → Allow Late Arrival**, which lets the Optimizer schedule a late arrival but records a penalty that pushes it to avoid doing so.

A **service duration** is how long the driver spends at the stop once arrived — unloading, collecting a signature, and so on. It defaults to the workspace's standard service duration (five minutes unless changed under **Settings → Workspace → Defaults**) and can be overridden per stop via the `service_duration_minutes` column. Service durations are added to travel time when the Optimizer computes whether a route fits inside a driver's shift.

A **skill** is a tag that matches a stop's requirement to a driver's capability. If a stop carries `required_skill: refrigerated`, only drivers whose profile lists the `refrigerated` skill can be assigned to it. Skills are free-text tags you define; the Optimizer matches them literally and is case-insensitive. A stop requiring a skill that no driver on the plan possesses cannot be routed and lands in the unrouted tray with the reason "no eligible driver." Manage driver skills under **Fleet → Drivers → (driver) → Skills**.

---

## Article 5: Integrations — Connecting Your Order System

Cartographa connects to external order, e-commerce, and warehouse systems so stops flow in automatically rather than through manual CSV uploads. Integrations are managed under **Settings → Integrations** and require Admin or Owner role.

A connection is established through OAuth where the partner system supports it; otherwise you supply an API key from the partner system. Once connected, you configure a **sync rule**: which orders become stops, how often the sync runs, and which plan they land in. For example, a rule might say "every order tagged `delivery` with a ship date of tomorrow becomes a stop in tomorrow's plan, synced every fifteen minutes." Synced stops appear in the target plan's Draft state and are optimized on your normal schedule.

Field mapping happens once per integration. You map the partner system's fields to Cartographa's stop fields — their "deliver-by date" to our `time_window_end`, their "item count" to our `size`, and so on. Unmapped partner fields are attached as custom notes, exactly as with CSV custom columns.

If a sync fails, the integration shows a red status badge and the most recent error on the Integrations page. The most common cause is an expired or revoked credential, which surfaces as error **CART-401**; reauthorize the connection to clear it. A sync that succeeds but returns zero orders is shown as a green status with a "0 orders" note and is not an error — it usually means your sync rule's filter matched nothing.

Synced stops can be edited in Cartographa, but edits are not written back to the partner system. Cartographa is a one-way consumer of order data unless you have enabled the optional **status writeback** feature, which sends delivery completion events back to the partner system after a driver marks a stop delivered.

Status writeback deserves a word of caution because it is the one integration feature that changes data in your other system. When enabled (Growth tier and above), each time a driver marks a stop **Delivered**, **Failed**, or **Partial**, Cartographa posts that outcome to the mapped status field in the partner system. This is what lets your order or e-commerce platform show "delivered" without a human copying it across. Writeback fires once per terminal status change and is idempotent on our side, so a retried event does not double-post. If writeback itself fails — because the partner credential expired, for example — it surfaces the same **CART-401** on the Integrations page and queues the event for retry rather than dropping it; a delivery is never lost just because the writeback hiccupped.

A sync rule can target any plan, including a plan for a future date, which is the normal pattern: tomorrow's orders flow into tomorrow's plan throughout today, and you optimize and dispatch in the morning. Be deliberate about the sync frequency. A fifteen-minute sync keeps a plan current without hammering the partner API; a one-minute sync rarely buys anything and is more likely to brush against the partner system's own rate limits. If a sync that used to work suddenly returns nothing, check whether the partner system changed the tag or status your filter depends on before assuming a Cartographa fault.

---

## Article 6: Troubleshooting Unrouted Stops

When the Optimizer cannot place a stop on any route, it does not guess — it leaves the stop in the **unrouted tray** with a specific reason. Reading that reason is the fastest way to fix the plan. The reasons are:

**"Outside all shift windows."** No driver's shift overlaps the stop's time window enough to reach it, service it, and return. Either widen the relevant driver's shift, relax the stop's time window, or add a driver whose shift covers it.

**"Exceeds vehicle capacity."** Adding the stop's `size` to a route would push the vehicle over its capacity. Increase capacity, split the load across vehicles, or reduce the stop size if it was entered incorrectly.

**"No eligible driver."** The stop requires a skill no scheduled driver holds (see Article 4). Add the skill to a driver or assign a driver who has it.

**"Unreachable location."** The geocoded pin cannot be reached by road from the depot — commonly a pin dropped in water, on a pedestrian-only zone, or across an uncrossable boundary. Correct the pin in Needs Review.

**"Time window infeasible."** The stop's window is too narrow to be reached from the depot even on a dedicated route — for instance, a 30-minute window two hours of driving away that opens before any shift starts. Widen the window or enable Allow Late Arrival.

A plan that returns many unrouted stops at once, all with the same reason, usually points to a single misconfiguration — a depot pin in the wrong place, a shift window left blank, or a capacity unit mismatch — rather than a problem with each stop. Fix the shared cause first.

If stops are unrouted with no reason shown and the plan simply spins on **Optimize** without completing, see Article 7 on optimization failures.

---

## Article 7: When Optimization Fails or Times Out

A normal optimization completes in seconds for small plans and up to a minute or two for large ones. When it does not complete, Cartographa returns one of three outcomes, each with a distinct remedy.

**Optimization timed out (CART-504).** The Optimizer has a hard ceiling of three minutes per plan. A plan that hits the ceiling is almost always too large or too tightly constrained — thousands of stops with narrow, conflicting time windows and too few vehicles. The remedy is to relax constraints (widen windows, add vehicles) or split the plan. The timeout protects you from a runaway computation; it never partially dispatches.

**Optimization failed — invalid input (CART-422).** One or more stops or vehicles contains data the Optimizer cannot use: a stop with no geocode, a vehicle with zero or negative capacity, or a shift window that ends before it starts. The error message names the offending record. Fix it and re-optimize.

**Optimization failed — internal error (CART-500).** This is a problem on our side, not your data. Retry once; if it recurs on the same plan, contact support with the plan ID. Do not keep retrying, as a genuine CART-500 will not clear on its own.

Of these three, **CART-504 (timeout)** is by far the most common on real operations, and it is worth understanding why a plan times out rather than simply reacting to it. The Optimizer searches for a good assignment of stops to vehicles and a good sequence within each route. That search space grows explosively with the number of stops, and it grows worse when constraints conflict — many narrow time windows competing for too few vehicles force the search to explore a great many near-misses before finding a feasible arrangement, or before proving none exists within the ceiling. So a plan times out for one of two reasons: it is genuinely large (thousands of stops), or it is small but cruelly constrained (tight, overlapping windows with insufficient capacity). The remedies map to the cause. For a large plan, split it into two or more plans, or add vehicles so the search has more room to place stops. For an over-constrained plan, widen the tightest time windows, enable **Allow Late Arrival** so the Optimizer can trade a small penalty for feasibility instead of searching for a perfect on-time fit, or add a vehicle. A useful diagnostic habit: if a plan that optimized fine yesterday times out today after you tightened windows or removed a vehicle, the change you just made is the cause, and reversing it is the fastest fix.

Optimization never silently changes your inputs. If a result looks wrong but the run succeeded, the cause is the constraints you supplied, not a Cartographa modification — review the time windows, capacities, and skills on the affected stops. A frequent surprise is a stop that routed to a distant driver because a nearer driver lacked a required skill; the **Why?** link beside each routed stop explains the assignment.

---

## Article 8: Live Tracking and Driver App Basics

Once a plan is dispatched, the assigned drivers see their route in the Cartographa Driver app, and planners see live progress on the **Tracking** board.

A driver opens the app, signs in with the one-time code, and sees the day's stops in optimized sequence. Tapping a stop shows the address, time window, customer notes, and any custom fields carried over from import. The driver taps **Navigate** to hand off to their phone's map app, and **Arrived** on reaching the stop, which starts the service timer. On completing the stop the driver taps **Delivered**, **Failed**, or **Partial**, optionally capturing a photo or signature if the plan requires proof of delivery.

On the planning side, the Tracking board shows each driver's position, the stops completed, and an updated estimated time of arrival for remaining stops based on actual progress. A driver running behind shows in amber; a driver who has missed a time window shows in red. The position updates while the Driver app is open and location permission is granted; if a driver's position stops updating, the most common causes are a backgrounded app or revoked location permission on the phone, not a Cartographa fault.

If a driver marks a stop **Failed**, it returns to an unassigned state and a planner can reschedule it into a later plan. Failed stops do not automatically re-optimize into the current plan, because doing so mid-route would disrupt every subsequent arrival estimate; rescheduling is a deliberate planner action.

The Driver app caches the route on dispatch, so a driver who loses signal mid-route keeps the sequence and addresses. Status taps made offline sync when signal returns.

Two driver-app questions reach support constantly. The first is "the driver can't see today's route." In order, the causes are: the plan was never dispatched (it is still in Draft, so nothing reached the phone); the route was assigned to a different driver; the driver is signed in to the wrong workspace; or the app needs a pull-to-refresh after a late dispatch. The Tracking board confirms whether the plan is dispatched and to whom, which resolves most of these in seconds. The second is "the driver's location stopped updating." This is almost always a phone-side permission or power setting — location permission downgraded to "while using the app" and then the app backgrounded, or aggressive battery optimization suspending the app — rather than a Cartographa fault. The fix lives in the phone's settings, not the console: grant the Driver app "always" location permission and exempt it from battery optimization. A driver whose position is stale still has their cached route and can complete the day; only the live position on your board is affected.

Proof of delivery, when a plan requires it, is configured per plan under **Plan Settings → Proof of Delivery**. You can require a photo, a signature, or both, and the captured proof is attached to the stop and visible in the plan export and analytics. A driver cannot mark a stop **Delivered** without supplying the required proof, which prevents the common dispute of a delivery marked complete with nothing to show for it. Proof captured offline uploads with the rest of the status sync when signal returns.

---

## Article 9: Plan States and Editing After Dispatch

Every plan moves through a defined set of states, and what you can edit depends on the state. Understanding this prevents the common frustration of "why can't I change this stop."

A plan is born in **Draft**. In Draft you can add, remove, and edit stops freely, change plan settings and constraints, and run **Optimize** as many times as you like. Nothing has been sent to drivers.

Clicking **Dispatch** moves the plan to **Dispatched**. The route is now on drivers' phones. In Dispatched state you cannot change the structure of a route — you cannot reorder stops or move a stop between drivers through a normal edit — because the driver is already executing it. You can, however, **cancel an individual stop** (which notifies the driver to skip it) and **add an urgent stop** to a driver's remaining route through **Tracking → (driver) → Add Stop**, which inserts it without re-optimizing the whole plan.

When all stops on a plan are completed, failed, or cancelled, the plan moves to **Completed** automatically. Completed plans are read-only and feed the analytics and export described in Articles 13 and 14.

A Draft plan that is never dispatched and whose service date passes moves to **Expired** at midnight in the depot's time zone. Expired plans are read-only but can be **cloned** into a new Draft for a future date, which copies the stops and settings so you do not rebuild from scratch.

To make a structural change after dispatch — say you must completely re-sequence a driver's day — the supported path is to **recall** the plan (**Tracking → Recall Plan**), which pulls it back to Draft and removes it from drivers' phones, edit and re-optimize, then dispatch again. Recall is intentionally a heavier action than canceling a single stop, because it disrupts every driver on the plan.

---

## Article 10: Account, Billing, and Subscription Plans

Cartographa bills per **active seat** per month, where a seat is any Owner, Admin, or Planner. Viewers are free and unlimited. Drivers are not seats and never count toward billing; you can have any number of drivers on any subscription.

There are three subscription tiers. **Starter** supports one depot, up to 25 drivers, and CSV import only. **Growth** supports up to five depots, up to 150 drivers, integrations, and status writeback. **Scale** removes the depot and driver caps, adds priority support and the audit log, and is required for SSO (see Article 15). The current tier is shown under **Settings → Billing**, where the Owner can upgrade or downgrade.

Billing is monthly by default, charged on the calendar day you first subscribed. Annual billing is available at a discount and is configured by contacting support. When you add a seat mid-cycle, Cartographa prorates the charge for the remainder of the cycle. When you remove a seat, the credit applies to your next invoice rather than as an immediate refund.

A failed payment puts the workspace into a **grace period** of fourteen days, during which everything continues to work and a banner reminds the Owner to update payment details under **Settings → Billing → Payment Method**. If payment is not resolved by the end of the grace period, the workspace moves to **read-only**: existing plans and data remain fully visible and exportable, but you cannot dispatch new plans until billing is restored. Data is never deleted for non-payment; a read-only workspace can be reactivated at any time by settling the balance.

Invoices and receipts are available under **Settings → Billing → Invoices** and can be downloaded as PDF. To change the billing email or add a VAT/tax identifier that appears on invoices, use **Settings → Billing → Billing Details**.

---

## Article 11: Error Code Reference

Cartographa surfaces a stable set of numeric error codes prefixed with `CART-`. Use this reference to interpret any code you encounter; the in-product message will also include a short description and, where relevant, the offending record.

**CART-400 — Malformed request.** The data sent was structurally invalid, usually from a hand-edited API call or a corrupted CSV. Re-export or correct the file and retry.

**CART-401 — Authentication failed.** Your API key or integration credential is missing, expired, or revoked. Reauthorize the integration (Article 5) or regenerate the API key (Article 16).

**CART-403 — Permission denied.** Your role does not permit this action — for example, a Planner attempting to change fleet configuration, or an Admin attempting a billing change. Ask an Admin or the Owner, or have your role changed (Article 2).

**CART-409 — Conflict.** The resource changed underneath you, typically two planners editing the same plan at once, or dispatching a plan that another user already dispatched. Refresh and retry.

**CART-413 — Payload too large.** A CSV import exceeded the 5,000-row cap, or a single API request exceeded its size limit. Split the file or batch the request (Article 3).

**CART-422 — Unprocessable input.** The request was well-formed but contains data the Optimizer cannot use — an ungeocodable stop, a non-positive vehicle capacity, or an inverted shift window. The message names the record (Article 7).

**CART-429 — Rate limited.** You have exceeded the API rate limit. Back off and retry after the interval given in the `Retry-After` response header (Article 16).

**CART-500 — Internal error.** A fault on Cartographa's side. Retry once; if it persists, contact support with the relevant ID (Article 7).

**CART-503 — Service temporarily unavailable.** Cartographa is undergoing brief maintenance or is shedding load. Retry after a short wait; check the status page for active incidents.

**CART-504 — Optimization timed out.** The plan exceeded the three-minute optimization ceiling. Relax constraints or split the plan (Article 7).

---

## Article 12: Units, Limits, and Capacity

Cartographa is unit-agnostic but requires consistency: you choose one capacity unit per workspace, and every vehicle capacity and every stop `size` is interpreted in that unit. Set it under **Settings → Workspace → Capacity Unit**. The common choices are package count, weight (kilograms or pounds), or volume (liters or cubic feet). Changing the unit after stops exist does not convert existing values — it only relabels them — so choose deliberately and avoid changing it mid-operation.

The platform enforces several hard limits, independent of subscription tier:

- A single CSV import is capped at **5,000 rows** (CART-413 above this).
- A single plan may contain at most **5,000 stops**.
- A single optimization run may not exceed **three minutes** of compute (CART-504 above this).
- A driver shift may not exceed **16 hours**; the Optimizer rejects longer shifts as invalid input (CART-422).
- A workspace may hold at most **2,000 plans** in active (non-archived) storage; older plans should be archived or exported.
- The API rate limit is **600 requests per minute** per workspace (CART-429 above this).

Subscription-tier limits (depot count, driver count) are separate from these platform limits and are listed in Article 10. Where a platform limit and a tier limit both apply, the lower one governs — a Starter workspace is capped at 25 drivers by tier even though the platform itself imposes no driver cap.

Capacity is a per-vehicle scalar; Cartographa does not currently model multiple capacity dimensions (for example, weight and volume simultaneously) on one vehicle. If you need to respect two dimensions at once, model the binding one as capacity and the other as a skill-style tag, or contact support about multi-dimensional capacity on the roadmap.

---

## Article 13: Analytics and Reporting

Completed plans feed the **Analytics** section, which summarizes how your operation actually ran versus how it was planned. Analytics are available to all roles including Viewers, and require no configuration.

The core dashboards are **Plan vs. Actual**, which compares estimated and real arrival times, distances, and durations; **On-Time Performance**, which reports the share of stops serviced within their time windows, broken down by driver, depot, and day; and **Utilization**, which shows how full vehicles ran and how much of each driver's shift was productive. A common first insight is that on-time performance dips on plans with many tight time windows, which is the Optimizer trading punctuality risk against route efficiency exactly as configured.

Analytics are computed from completed-plan data and refresh nightly, so today's in-progress plan will not appear in the dashboards until it completes and the overnight refresh runs. For live, intraday numbers use the Tracking board (Article 8) rather than Analytics.

Date ranges and filters (by depot, driver, or service date) apply across all dashboards. Any dashboard view can be exported to CSV for use in your own tools; for raw record-level export rather than aggregated dashboards, see Article 14.

A note on interpretation: Plan vs. Actual differences are expected and healthy in moderation, because the plan is built on estimated travel times and the actual day includes traffic, customer delays, and failed stops. A persistently large gap, however, usually means your service durations or travel-time assumptions need tuning, not that the Optimizer is wrong.

The single most actionable analytics habit is to compare planned versus actual service durations by stop type. Many operations carry a default five-minute service duration inherited from the workspace default (Article 4) while their drivers actually spend twelve minutes per stop unloading and collecting signatures. That seven-minute gap, multiplied across a day's stops, is enough to make every arrival estimate optimistic and to push on-time performance down even when drivers are working efficiently. Analytics surfaces this gap directly; correcting the service duration to match reality makes the next day's plan honest and immediately improves on-time numbers without any change to how drivers work. Travel-time gaps tell a different story — a persistent travel-time overrun usually points to a recurring traffic pattern the plan should be built around, for example by shifting a congested corridor's stops to a different part of the day.

Utilization deserves the same scrutiny from the other direction. A fleet that consistently runs at low utilization — vehicles half-full, shifts half-used — is paying for capacity it is not deploying, and the plan can probably be served by fewer vehicles or the freed capacity used to absorb growth. A fleet pinned near full utilization every day has no slack to absorb a failed stop or a late customer, which is precisely the condition under which a small disruption cascades into a string of missed windows. Analytics will not make the staffing decision for you, but it makes the trade-off visible instead of guessed.

---

## Article 14: Exporting Your Data

Cartographa lets you export your data at any time, on any subscription tier, including a read-only workspace in billing grace. There is no charge to export and no lock-in.

Three export paths exist. **Plan export** (**Plans → (plan) → Export**) produces a CSV or JSON of a single plan: its stops, the optimized sequence, assignments, and, for completed plans, the actual outcomes per stop. **Bulk export** (**Settings → Data → Export**) produces a dated archive of all plans in a date range, plus your fleet, drivers, and depot configuration, delivered as a downloadable ZIP. **API export** (Article 16) lets you pull the same data programmatically for a live integration.

Exports reflect the data at the moment of export; they are point-in-time snapshots, not live feeds. The bulk export of a large workspace is prepared asynchronously — you request it, and Cartographa emails the Owner or requesting Admin a download link when the archive is ready, typically within minutes. The link is valid for 72 hours.

Exported personal data (driver names, customer addresses) is your responsibility to handle in line with your obligations once it leaves Cartographa. If you need a deletion of specific records rather than an export — for example, to honor a data-subject erasure request — use **Settings → Data → Delete Records**, which permanently removes the named records and is not reversible. Deletion of records that belong to a completed plan will leave the plan's aggregate analytics intact but blank the underlying detail.

---

## Article 15: Security, SSO, and Access Control

Cartographa protects access with several layers, and larger workspaces can centralize identity through single sign-on.

All workspace members sign in with email and password by default, and we strongly recommend enabling **two-factor authentication** under **Settings → Security → Two-Factor**, which can be required workspace-wide by an Admin or Owner. Drivers, who are not members, authenticate with a one-time code sent to their phone and never set a password.

**Single sign-on (SSO)** is available on the Scale tier. Cartographa supports SAML 2.0 with major identity providers. An Owner or Admin configures SSO under **Settings → Security → SSO** by exchanging metadata with your identity provider, choosing whether to allow just-in-time provisioning (new members created automatically on first SSO login), and optionally enforcing SSO so that password login is disabled for everyone except the Owner — the Owner always retains a password fallback so a misconfigured SSO setup cannot lock the workspace out entirely. If you enforce SSO and later need that fallback, sign in as the Owner with email and password to repair the configuration.

The **audit log** (Scale tier, **Settings → Security → Audit Log**) records security- and configuration-relevant events: member and role changes, integration credential changes, dispatches and recalls, exports, and record deletions. Each entry stamps who, what, and when. The audit log is read-only and exportable, and is the first place to look when reconciling "who changed this."

Cartographa encrypts data in transit and at rest. API keys are shown in full only once at creation; afterward only the last four characters are displayed, so store the full key securely when you generate it (Article 16).

---

## Article 16: API Basics and Rate Limits

The Cartographa API lets you create stops, build and optimize plans, dispatch, and pull tracking and analytics data programmatically. This article covers authentication, the request model, and limits; full endpoint documentation lives in the developer portal.

**Authentication.** Generate an API key under **Settings → Integrations → API Keys** (Admin or Owner only). The key is shown in full exactly once — copy it immediately and store it securely, because afterward only its last four characters are visible (Article 15). Send the key as a bearer token in the `Authorization` header. A missing, expired, or revoked key returns **CART-401**. Revoke a compromised key from the same screen; revocation is immediate.

**Scopes.** A key carries the permissions of the role you assign it at creation, mirroring the member roles in Article 2. A key scoped as Planner can manage plans and stops but will receive **CART-403** if it attempts a fleet or billing change. Scope keys to the least privilege the integration needs.

**Rate limits.** The API allows **600 requests per minute** per workspace. Exceeding it returns **CART-429** with a `Retry-After` header giving the number of seconds to wait. Well-behaved clients honor `Retry-After` and use exponential backoff; clients that retry immediately and repeatedly will stay rate-limited. Bulk operations (creating many stops) should be batched rather than sent as one request per stop, both to stay under the limit and to avoid the **CART-413** payload cap on oversized single requests.

**Idempotency.** Write requests accept an `Idempotency-Key` header. Sending the same key twice returns the original result rather than performing the action again, which makes retries after a network failure safe — important precisely because retrying is the right response to CART-429 and CART-503. Idempotency keys are remembered for 24 hours.

**Versioning.** The API is versioned by date in the `Cartographa-Version` header. Pin a version in production so a future change cannot alter your integration's behavior unexpectedly; unpinned requests use the latest version.

---

## Article 17: Notifications and Customer Communications

Cartographa can keep both your team and your end customers informed automatically, reducing "where is my delivery" contacts.

**Team notifications** are configured per member under your own **Profile → Notifications**. You can be alerted by email when a plan you own is dispatched, when an integration sync fails (CART-401 and others), when a driver marks a stop failed, or when the workspace enters billing grace. Notifications are advisory; the authoritative state always lives in the console.

**Customer notifications** are configured per workspace under **Settings → Notifications → Customer**. When enabled and a customer contact is present on a stop, Cartographa can send the customer a message when their stop is dispatched (with an estimated arrival window), when the driver is approaching (a configurable number of stops away), and when the stop is completed. Messages are sent by email, or by SMS where you have provisioned SMS, and use templates you can edit. The estimated arrival window narrows as the day progresses and the Tracking board updates from real driver positions.

Customer notifications respect the stop's time window and the live ETA, so a customer is told a realistic window rather than the original plan if the day runs late. If a stop is canceled or fails, the customer receives the corresponding message only if you have enabled those specific templates, because some operations prefer to handle failed-delivery communication by hand.

A frequent question is why a customer did not receive a notification. The usual causes, in order, are: the stop had no customer contact field populated; customer notifications were disabled at the workspace level; the specific template (approaching, completed) was turned off; or, for SMS, no SMS sender was provisioned. The notification log under **Settings → Notifications → Log** shows, per stop, what was sent and what was suppressed and why.

---

## Article 18: Frequently Asked Questions

**Can I run more than one depot in a single plan?**
No. A plan belongs to exactly one depot, and all its routes start and end there. To operate multiple depots, build one plan per depot for the same service date. Multi-depot routing in a single plan is not supported.

**Why did a stop route to a far-away driver when a closer one was free?**
Almost always a skill or capacity constraint. The closer driver likely lacked a `required_skill` the stop needed, or was already at capacity. Click **Why?** beside the stop for the specific reason (Article 7).

**Do failed stops automatically move to the next plan?**
No. A failed stop returns to an unassigned state and a planner reschedules it deliberately (Article 8). Automatic re-optimization mid-route is intentionally disabled to keep arrival estimates stable.

**What happens to my data if I cancel my subscription?**
Your workspace becomes read-only; data is preserved and remains fully exportable, and nothing is deleted for non-payment or cancellation (Articles 10 and 14). Reactivating restores full function.

**Can a Viewer dispatch a plan in an emergency?**
No. Dispatching requires Planner, Admin, or Owner. A Viewer attempting it receives CART-403. Temporarily elevate the member's role if they must dispatch (Article 2).

**Why does changing my capacity unit not convert my numbers?**
Because Cartographa relabels rather than converts (Article 12). Switching from kilograms to pounds leaves the numeric values unchanged, which would silently misstate capacity — so change the unit only when no live stops depend on it, and re-enter values if needed.

**Is there a limit on drivers?**
The platform imposes no driver cap, but your subscription tier does: 25 on Starter, 150 on Growth, unlimited on Scale (Article 10).

**My optimization keeps timing out. What is the fastest fix?**
Split the plan or widen your tightest time windows and add a vehicle. CART-504 means the plan exceeded the three-minute ceiling because it was too large or too tightly constrained (Article 7).

---

## Article 19: Maintenance, Status, and Getting Support

Planned maintenance is announced in advance on the Cartographa status page and, for significant windows, by email to Owners and Admins. During brief maintenance the API may return **CART-503**; clients that honor retries and backoff ride through these windows without manual intervention (Article 16). The status page is the authoritative source for active incidents and historical uptime; if Cartographa behaves unexpectedly, check it before opening a ticket, because an active incident there is faster information than a support reply.

To contact support, use the in-product **Help → Contact Support** widget, which attaches your workspace ID and, if you opened it from a plan, that plan's ID — this context dramatically speeds resolution, especially for CART-500 and other server-side errors where we need the ID to investigate. Scale-tier workspaces receive priority support with a faster response target.

When reporting a problem, include the exact error code, the plan or integration ID, the time it occurred, and the steps that produced it. A report of "optimization is broken" takes far longer to resolve than "CART-504 on plan 48213 at 09:14 after adding 400 stops with 30-minute windows." The articles in this Help Center resolve the large majority of questions without a ticket; the support team's time is best spent on genuine faults and account-specific situations the documentation cannot cover.
