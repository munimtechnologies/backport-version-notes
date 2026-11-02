# Pre-registration: version notes from later releases on Django and NumPy maintenance branches

MV2, Munim, Inc. (mv2@munimtech.com). Written 2026-11-02, before any data was collected.
Made with AI agents working in MV2's name; not checked by a human. Code Apache-2.0; text
and data CC BY 4.0.

## Question

When a project backports a change to an older maintenance branch, does the backport carry
a version note (`versionadded`, `versionchanged`, `deprecated`, `deprecated-removed`,
`versionremoved`, `soft-deprecated`) that names a LATER release than the branch's own? On
the X.Y branch, a note naming X.(Y+1) or later tells readers of the X.Y docs about a
release they are not reading about. Usually that is a mistake, though some are deliberate
(a deprecation schedule, for example).

## Why this study

MV2's CPython audit (munimtechnologies/branch-version-notes-audit, graded 2026-11-02) found
three such notes on CPython 3.13 and 3.14. All three came with backports, and runtime checks
confirmed two of them describe behaviour the branch does not have. This study asks whether
the same failure exists in two other large Python projects that backport docs to
maintenance branches.

One example was seen before this pre-registration and is the gate's known case: Django's
`stable/5.2.x` `docs/topics/cache.txt` has `.. versionchanged:: 6.0.6`. It came with the
5.2.x backport of the CVE-2026-35193 fix (commit 050a3dc). Django 5.2.15 has the same fix.

## Prior art (searched 2026-11-02)

- CPython's `next` placeholder (gh-121277), which the release tools replace with the real
  version at release time. It lets main notes avoid guessing a number. It does not check
  maintenance branches.
- Review rules like PyPCAPKit #2530 (one `versionadded` per version per block), checked by
  reviewers, not by a tool.
- Django's release checklist removes `versionadded`/`versionchanged` notes from two
  releases ago before each feature release. That is about old notes, not future ones.
- MV2's own CPython audit (above).
No tool or study was found that checks Django's or NumPy's maintenance branches for notes
naming a later release.

## Data

- Django: bare clone of github.com/django/django. Heads of every `stable/X.Y.x` with X.Y
  >= 4.0, and every final tag (`X.Y` or `X.Y.Z`, with no a/b/rc) of those branches.
  Scanned files: `docs/*.txt`.
- NumPy: bare clone of github.com/numpy/numpy. Heads of every `maintenance/X.Y.x` with X.Y
  >= 1.24, and every final tag `vX.Y.Z` of those branches. Scanned files: `*.rst`, `*.py`,
  `*.pyi`, `*.txt`, `*.c`, `*.h`, `*.src` (docstrings carry notes too).
- Control: CPython tag v3.14.10 (`Doc/**/*.rst`), from the GitHub tag archive.
- A note's version is the first `X.Y[.Z]` in its arguments (an optional leading word such
  as "NumPy" is allowed). A note is FUTURE when (X, Y) is later than the branch's (X, Y).
  Notes with no parseable version (such as `next`) are counted, not graded.

## Gate (all must hold, or nothing below is graded)

- G1: the control scan finds `versionchanged:: 3.15` in CPython v3.14.10
  `Doc/library/datetime.rst` (the utcfromtimestamp note).
- G2: the known Django case is found as a future note on `stable/5.2.x`.
- G3: the newest head of each project has >= 100 version notes (a floor to catch a broken
  parser; Django deletes old notes before each feature release, so its count is low).
- G4: >= 90% of the listed final tags of each project are scanned without error.

## Predictions

- **P1** (Django): >= 2 future notes at the `stable/*` heads, beyond the known case.
- **P2** (NumPy): >= 1 future note at the `maintenance/*` heads.
- **P3** (hand review): >= 2 future notes across both projects, beyond the known case, are
  real problems under label L1 or L2 below.
- **P4** (when they arrive): of the future notes (beyond the known case) on branches that
  have an X.Y.0 tag, >= 50% are absent at X.Y.0. That is, they arrived after the feature
  release, through bugfix-era backports, not before the release.

How blind these are: P1 is half-blind, because one Django case had been seen. P2 and P4
are blind. P3 depends on our own reading, so every label will be shown with its evidence.

## Hand-review labels (fixed now; the CPython lesson was to have a label for L2)

- **L1, wrong version on this branch:** the behaviour exists in this branch's releases, but
  the note names a later branch's version (for example a fix released in 5.2.15 labelled
  6.0.6 on the 5.2 branch).
- **L2, behaviour the branch lacks:** the note describes a change that this branch's
  releases do not have.
- **L3, intended forward reference:** a deprecation or removal schedule, soft-deprecation
  advice, or wording that is true on this branch as written.
- **L4, unclear:** say why.

Each future note is read in the file at the branch head, and its arrival is traced to a
commit where possible. When there are more than 40 future notes, every note on a branch
that is still supported will be reviewed (Django 5.2, 6.0 and 6.1; NumPy's two newest
maintenance branches), plus the first 20 others in `future_notes.csv` order. Counts for P3
are per branch, and the number of distinct upstream changes behind them is reported too.

## Outputs

`summary.json` (gate, P1, P2, P4, per-head counts, control), `future_notes.csv` (every
future note with owner, context, first tag and whether it was present at X.Y.0),
`heads.csv`.

## Limits known in advance

- A note's version is matched as text, and its key is (path, directive, args). A note that
  moved files counts as new in the tag where it moved.
- Old NumPy branches' docs are not rebuilt or published any more, so notes on them may
  never reach readers. Branch support status is recorded in the grading.
- Nothing will be filed upstream by AI agents. Any report would follow each project's
  contribution and AI policy, which will be read first.
