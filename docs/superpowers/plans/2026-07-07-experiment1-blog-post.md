# Experiment-1 Blog Post Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish "The Bill Was the Easy Part" on mikescorner.io with four whiteboard panels, every experimental claim resolvable at public-mirror tag v1.1.

**Architecture:** Content-first, tag-last. Panels and draft are produced and Mike-approved on branch `feat/blog-experiment1-post`; only then is the immutable v1.1 tag cut, so the tag is cut exactly once. (This reorders spec §7 steps 2–3: the spec's link-check requirement still holds — it runs after tagging, before publication.)

**Tech Stack:** design-illustration skill (`agy` CLI render — Google-side, no billable Anthropic API calls in this plan), Markdown, `scripts/build_public_mirror.py` (stdlib Python), git/gh.

**Spec:** `docs/superpowers/specs/2026-07-07-experiment1-blog-post-design.md` (approved 2026-07-07). The spec's §2 outline, §3 panel descriptions, and §6 claim→source map are normative inputs; this plan does not restate them.

## Global Constraints (from spec §5 — verbatim where quoted)

- **Never cite ~$103 for Phase 1a.** The publicly verifiable Phase-1a figure is **$149.01**.
- Every stat, quote, date, anecdote in the draft: real, sourced, or flagged `[MIKE: …]`. No invented personal detail, ever.
- Experimental claims link to the mirror **pinned to tag v1.1**, never `main`. URL base: `https://github.com/mdsweatt/managing-intelligence-experiments/blob/v1.1/`
- Personal backstory (token meter, CraftRole tracker, Max 5x $125+tax, Copilot change) presented as backstory, not repo-verifiable evidence. Employer stays generic ("at the day job"); Copilot and CraftRole are named.
- SemiAnalysis figures keep qualifiers: "up to ~$8,000" / "roughly $14,000"; attributed to SemiAnalysis via SmarterX Episode 219.
- Results stamped to Haiku 4.5 / Sonnet 4.6 / Opus 4.8, June–July 2026.
- VOICE.md is a hard constraint on the draft (read in full before drafting; §8 checklist gates delivery).
- All work on branch `feat/blog-experiment1-post` in the private repo (`mdsweatt/Tokenomics`); the public repo is touched only in Task 5.

---

### Task 1: Whiteboard panels

**Files:**
- Create: `docs/images/blog_panel_1_the_machine_whiteboard.png`
- Create: `docs/images/blog_panel_2_variance_ladder_whiteboard.png`
- Create: `docs/images/blog_panel_3_caps_vs_mandates_whiteboard.png`
- Create: `docs/images/blog_panel_4_crisp_ne_calibrated_whiteboard.png`

**Interfaces:**
- Consumes: spec §3 panel descriptions (composition, doodles, headline scrawls — normative).
- Produces: the four exact filenames above; Task 2 embeds them, Task 5 publishes them at `blob/v1.1/docs/images/<name>`.

- [ ] **Step 1:** Invoke the `design-illustration` skill once per panel, passing the spec §3 description verbatim as the content brief plus this style rider: "Match the hand-drawn whiteboard style of docs/images/report_vs_instrument_whiteboard.png and two_lever_bandability_whiteboard.png (marker-on-whiteboard, sparse color, handwritten labels). Landscape. All numbers must be copied exactly from the brief — no invented numbers."
- [ ] **Step 2:** Verify each render: numbers in the image match spec §3 exactly ($211.52 · 8 hypotheses · 3,989 measured runs / 62-67 · 4.5% · 14.6% / −40…−72% · +12…+738% · 24-24 · R ≈ −0.03 / 54.9% · K=3 · 144). A wrong number in a rendered image is a hard fail — re-render that panel.
- [ ] **Step 3:** Send the four PNGs to Mike (SendUserFile) for eyeball approval. **Gate: do not proceed until approved.**
- [ ] **Step 4:** Commit:
```bash
git add docs/images/blog_panel_*_whiteboard.png
git commit -m "docs: four whiteboard panels for the Experiment-1 blog post"
```

### Task 2: Draft the post

**Files:**
- Create: `docs/blog/2026-07-the-bill-was-the-easy-part.md`

**Interfaces:**
- Consumes: spec §1–§2 (frame + outline), §4 (voice bindings), §5 (constraints), §6 (claim→source map); VOICE.md in full; Task 1 panel filenames.
- Produces: complete draft (~1,700–1,900 words) with embedded panel references and v1.1-pinned links; Task 4 adds this exact path to the mirror EXCLUDE list.

- [ ] **Step 1:** Re-read `~/.claude/skills/writing-in-mikes-voice/VOICE.md` in full (it is the hard constraint, not a reference).
- [ ] **Step 2:** Draft in full per spec §2's nine sections. Every experimental number comes from the spec §6 claim map with its inline v1.1 link; every external claim uses the spec §6 external-sources table. Panel images embedded after §3/§4/§5/§6 respectively with one-line captions carrying the headline scrawl. Personal details not already confirmed in the spec get `[MIKE: …]` flags — never filler.
- [ ] **Step 3:** Self-check against VOICE.md §8 (all 11 boxes) and spec §4 bindings. Fix failures before delivery — the checklist gates delivery, it is not advisory.
- [ ] **Step 4:** Verify no banned content: `grep -n '\$103' docs/blog/2026-07-the-bill-was-the-easy-part.md` → expect no matches; `grep -nE 'delve|landscape|game-changer|dive in' …` → no matches; `grep -n 'blob/main' …` → no matches (v1.1 only).
- [ ] **Step 5:** Commit:
```bash
git add docs/blog/2026-07-the-bill-was-the-easy-part.md
git commit -m "docs: full draft — The Bill Was the Easy Part (voice-checked, [MIKE] flags open)"
```

### Task 3: Mike's draft review

**Files:**
- Modify: `docs/blog/2026-07-the-bill-was-the-easy-part.md`

**Interfaces:**
- Consumes: Task 2 draft.
- Produces: Mike-approved final text, zero `[MIKE:` flags remaining, title + aphorism finalized (spec §8 remaining item).

- [ ] **Step 1:** Send draft to Mike. Collect notes.
- [ ] **Step 2:** Revise, don't regenerate — address flagged items only, preserve everything unflagged (VOICE.md §7.5). Resolve final title + closing aphorism (spec §9 candidates a/b).
- [ ] **Step 3:** Verify zero flags remain: `grep -c '\[MIKE' docs/blog/2026-07-the-bill-was-the-easy-part.md` → expect `0`.
- [ ] **Step 4:** Commit each revision round: `git commit -am "docs: draft revision round N (Mike's notes)"`. **Gate: Mike approves final text before Task 5 cuts the tag.**

### Task 4: Mirror builder `--update` mode

**Files:**
- Modify: `scripts/build_public_mirror.py` (main() argv handling, lines 58–76; EXCLUDE list, lines 26–30)

**Interfaces:**
- Consumes: existing `main()` build logic (unchanged transforms 1–4c).
- Produces: CLI `uv run python scripts/build_public_mirror.py --update /path/to/existing-mirror`; EXCLUDE gains `docs/blog/2026-07-the-bill-was-the-easy-part.md` (post text must not pre-publish inside v1.1).

- [ ] **Step 1:** Add the draft to EXCLUDE:
```python
EXCLUDE = [
    "docs/phase1b-ab-budget-internal.md",
    "docs/phase5-run-loop-design.md",
    "docs/phase5-run-loop-implementation-plan.md",
    "docs/blog/2026-07-the-bill-was-the-easy-part.md",  # blog post text publishes on mikescorner.io, not in the mirror
]
```
- [ ] **Step 2:** Refactor: extract the tree-building body of `main()` (steps 1–4c + RELEASE write) into `build_tree(target: Path, root: Path) -> str` returning `head`; `main()` keeps argv handling. Add update mode:
```python
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
    target.mkdir(parents=True)
    head = build_tree(target, root)
    print(f"\nmirror tree ready: {target}  (source HEAD {head[:10]})")
    print("next: review, then git init + commit inside the mirror, add remote, push.")
    return 0
```
Update the module docstring Usage block to show both forms.
- [ ] **Step 3:** Equivalence verification (fresh build and update mode must produce identical trees):
```bash
uv run python scripts/build_public_mirror.py /tmp/mirror-fresh
cp -R /tmp/mirror-fresh /tmp/mirror-upd && (cd /tmp/mirror-upd && git init -q && git add -A && git commit -qm x)
echo "sentinel" > /tmp/mirror-upd/STALE_FILE
uv run python scripts/build_public_mirror.py --update /tmp/mirror-upd
diff -r --exclude=.git /tmp/mirror-fresh /tmp/mirror-upd && echo IDENTICAL
```
Expected: `IDENTICAL` (and no `STALE_FILE` survives — stale content is cleared, not merged).
- [ ] **Step 4:** Confirm the exclusion works: `test ! -f /tmp/mirror-fresh/docs/blog/2026-07-the-bill-was-the-easy-part.md && echo EXCLUDED` → `EXCLUDED`. Then clean up: `rm -rf /tmp/mirror-fresh /tmp/mirror-upd`.
- [ ] **Step 5:** Run the repo's test suite (`uv run pytest -q`) — expect the same green count as before the change (script has no unit tests; suite guards against import/collection breakage).
- [ ] **Step 6:** Commit:
```bash
git add scripts/build_public_mirror.py
git commit -m "feat: --update mode for mirror builder; exclude blog post text from mirror"
```

### Task 5: Cut public release v1.1

**Files:**
- Modify: `~/Pycharm_Projects/tokenomics-public/**` (full refresh via --update)

**Interfaces:**
- Consumes: merged private `main` (Tasks 1–4), builder `--update` mode.
- Produces: public tag `v1.1` containing panels + billing note + spec; every draft link resolves.

- [ ] **Step 1:** **Gate: Mike merges `feat/blog-experiment1-post` → `main`** (his PR flow). Verify: `git checkout main && git pull && git log --oneline -1` shows the merge.
- [ ] **Step 2:** Refresh the mirror working copy:
```bash
uv run python scripts/build_public_mirror.py --update ~/Pycharm_Projects/tokenomics-public
git -C ~/Pycharm_Projects/tokenomics-public status --short
```
Expected new files only: `docs/images/blog_panel_*_whiteboard.png` (4), `docs/superpowers/specs/…blog-post-design.md`, `docs/superpowers/plans/…blog-post.md`, RELEASE (updated HEAD). Expected absent: `docs/blog/…`. Anything else appearing in the diff → stop and review before committing.
- [ ] **Step 3:** Commit + tag + push (after Mike eyeballs the diff — **gate**):
```bash
git -C ~/Pycharm_Projects/tokenomics-public add -A
git -C ~/Pycharm_Projects/tokenomics-public commit -m "Public release v1.1 — blog whiteboard panels; billing export now at a pinned tag"
git -C ~/Pycharm_Projects/tokenomics-public tag -a v1.1 -m "v1.1: blog panels + billing export"
git -C ~/Pycharm_Projects/tokenomics-public push origin main --tags
```
- [ ] **Step 4:** Link-check every pinned URL in the approved draft:
```bash
grep -oE 'https://github.com/mdsweatt/managing-intelligence-experiments/blob/v1.1/[^) ]+' \
  docs/blog/2026-07-the-bill-was-the-easy-part.md | sort -u | \
  while read -r u; do curl -s -o /dev/null -w "%{http_code} $u\n" "$u"; done
```
Expected: every line starts `200`. Any non-200 → fix the link or the mirror before publication.

### Task 6: Publication handoff

**Files:**
- Deliver: final markdown + 4 PNGs to Mike (no repo changes).

**Interfaces:**
- Consumes: Task 3 approved text, Task 5 verified links.
- Produces: publish-ready package; updated session memory.

- [ ] **Step 1:** SendUserFile: the final markdown + the four PNGs, captioned as the publish package for mikescorner.io (images upload to the blog platform; each caption may link its repo copy at v1.1).
- [ ] **Step 2:** Publish-day checklist for Mike (in the message, not a file): paste markdown → upload 4 images in section order → verify the repo links render as inline hyperlinks (2–4 words, VOICE.md rule 10) → confirm CTA mike@mikescorner.io → title/slug final.
- [ ] **Step 3:** Update memory: `blog-post-experiment1-state.md` (published/URL or handed-off status), `publication-mirror-state.md` (v1.1 cut). Reconcile the MEMORY.md index lines.

## Self-review (done at write time)

Spec coverage: §1–2 outline → Task 2; §3 panels → Task 1; §4 voice bindings → Task 2 step 3; §5 constraints → Global Constraints + Task 2 step 4 greps; §6 claim map → Task 2 step 2 + Task 5 step 4 link-check; §7 execution → Tasks 1–6 (order refinement documented in Architecture); §8 remaining item (title/aphorism) → Task 3 step 2. Placeholders: none (the draft's text is Task-2 work product, not a plan placeholder; its inputs are fully specified). Interface consistency: panel filenames, draft path, and tag name are identical across Tasks 1/2/4/5.
