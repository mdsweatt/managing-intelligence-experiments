"""Build the public-release mirror tree from the current main HEAD.

Produces a curated copy of the tracked tree with the publication transforms applied
(README "Provenance & licensing" section documents them):

  1. exclude private docs (phase1b internal budget note, phase5 future-work designs);
  2. replace the two third-party copyrighted fixture inputs with WITHHELD stubs that
     record the withheld file's sha256 (frozen-manifest hashes stay verifiable);
  3. strip account-scoped identifiers from published data: `request_id` in every
     results/*/records.jsonl, batch job names in analysis/output/phase1d/batch/.

Usage:  uv run python scripts/build_public_mirror.py /path/to/mirror-dir
        uv run python scripts/build_public_mirror.py --update /path/to/existing-mirror

Fresh mode: the target must not exist. Update mode: the target must be an existing git
working copy (e.g. the public mirror checkout); its contents are replaced wholesale from a
fresh build, .git preserved. git commit/tag of the mirror is a manual step after review.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tarfile
import io
from pathlib import Path

EXCLUDE = [
    "docs/phase1b-ab-budget-internal.md",
    "docs/phase5-run-loop-design.md",
    "docs/phase5-run-loop-implementation-plan.md",
    "docs/blog/2026-07-the-meter-and-the-judge.md",  # blog post text publishes on mikescorner.io, not in the mirror
]

WITHHELD = {
    "fixtures/task-05-translate/medium/input.md": (
        "the essay 'Europe 2031 — What getting AI wrong means for us' (third-party published "
        "work; used as the frozen ~7k-word translate-M source)"
    ),
    "fixtures/task-07-summarize/large/input.md": (
        "the Google DeepMind report 'From AGI to ASI' (© Google, all rights reserved; used as "
        "the frozen summarize-L source)"
    ),
}

STUB = """# WITHHELD — third-party copyrighted fixture input

This file's original content is {desc}.

It is **withheld from the public release** for copyright reasons and replaced by this stub.
The experiment's frozen-manifest hash for this fixture was computed over the ORIGINAL bytes:

- sha256 of the withheld file: `{sha}`
- byte length: {n}

No published record contains this text (the runs that used it are tokens-only). To verify the
frozen hash, obtain the work from its publisher and check the sha256 above.
"""


def build_tree(target: Path, root: Path) -> str:
    """Build the transformed mirror tree into `target` (created if needed); return source HEAD."""
    # 1. export tracked tree at HEAD (untracked/ignored content can never leak)
    target.mkdir(parents=True, exist_ok=True)
    tar_bytes = subprocess.run(["git", "-C", str(root), "archive", "HEAD"],
                               check=True, capture_output=True).stdout
    with tarfile.open(fileobj=io.BytesIO(tar_bytes)) as tf:
        tf.extractall(target)
    head = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"],
                          check=True, capture_output=True, text=True).stdout.strip()

    # 2. exclusions
    for rel in EXCLUDE:
        p = target / rel
        p.unlink()
        print(f"excluded: {rel}")

    # 3. copyright tombstones (sha256 from the private originals)
    for rel, desc in WITHHELD.items():
        src = root / rel
        data = src.read_bytes()
        (target / rel).write_text(
            STUB.format(desc=desc, sha=hashlib.sha256(data).hexdigest(), n=len(data)),
            encoding="utf-8")
        print(f"tombstoned: {rel}")

    # 4a. strip request_id from every records.jsonl (field is Optional in the schema)
    for rec in sorted(target.glob("results/run-*/records.jsonl")):
        out_lines = []
        n = 0
        for line in rec.read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            n += r.pop("request_id", None) is not None
            if isinstance(r.get("rate_limit"), dict):   # same id, hyphenated, inside the headers
                r["rate_limit"].pop("request-id", None)
            out_lines.append(json.dumps(r))
        rec.write_text("".join(l + "\n" for l in out_lines), encoding="utf-8")
        print(f"redacted request_id: {rec.relative_to(target)} ({n} records)")

    # 4b. redact batch job names (account-scoped resource ids) in the judge batch state/usage
    batch = target / "analysis/output/phase1d/batch"
    st = batch / "state.json"
    state = json.loads(st.read_text(encoding="utf-8"))
    for i, job in enumerate(state.get("jobs", [])):
        job["name"] = f"batches/redacted-{i}"
    st.write_text(json.dumps(state, indent=2), encoding="utf-8")
    us = batch / "usage.jsonl"
    rows = [json.loads(l) for l in us.read_text(encoding="utf-8").splitlines() if l]
    order = list(dict.fromkeys(r["job"] for r in rows))   # stable order of first appearance
    names = {job: f"batches/redacted-{i}" for i, job in enumerate(order)}
    for r in rows:
        r["job"] = names[r["job"]]
    us.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    print(f"redacted batch job names: state.json + usage.jsonl ({len(names)} jobs)")

    # 4c. scrub request ids quoted in the live-verification probe docs
    import re
    for rel in ("docs/live-verification-2026-06-16.raw.json",
                "docs/live-verification-2026-06-16.md"):
        doc = target / rel
        if doc.exists():
            text = doc.read_text(encoding="utf-8")
            text, n = re.subn(r"req_011[A-Za-z0-9]+", "req_REDACTED", text)
            doc.write_text(text, encoding="utf-8")
            print(f"redacted probe request ids: {rel} ({n})")

    (target / "RELEASE").write_text(
        f"Public release mirror of the private lab repo at {head}\n"
        f"built by scripts/build_public_mirror.py — see README 'Provenance & licensing'.\n",
        encoding="utf-8")
    return head


def main() -> int:
    args = sys.argv[1:]
    update = "--update" in args
    if update:
        args.remove("--update")
    if len(args) != 1:
        print(__doc__)
        return 2
    target = Path(args[0])
    root = Path(subprocess.run(["git", "rev-parse", "--show-toplevel"], check=True,
                               capture_output=True, text=True).stdout.strip())
    if update:
        if not (target / ".git").is_dir():
            print(f"refusing --update: {target} is not an existing git working copy")
            return 2
        import tempfile, shutil
        tmp = Path(tempfile.mkdtemp(prefix="mirror-"))
        head = build_tree(tmp, root)
        for child in target.iterdir():           # clear everything except .git
            if child.name == ".git":
                continue
            shutil.rmtree(child) if child.is_dir() else child.unlink()
        for child in tmp.iterdir():              # move new tree in
            shutil.move(str(child), target / child.name)
        tmp.rmdir()
        print(f"\nmirror working copy refreshed from HEAD {head[:10]}")
        print(f"next: review `git -C {target} status`, commit as a release, tag, push.")
        return 0
    if target.exists():
        print(f"refusing: {target} already exists")
        return 2
    head = build_tree(target, root)
    print(f"\nmirror tree ready: {target}  (source HEAD {head[:10]})")
    print("next: review, then git init + commit inside the mirror, add remote, push.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
