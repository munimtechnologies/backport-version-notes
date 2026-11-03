# Grading: version notes naming a later release on Django and NumPy maintenance branches

MV2, Munim, Inc. (mv2@munimtech.com). Graded 2026-11-03 against `PREREG.md`. Made with AI
agents working in MV2's name. The hand labels below were made by those agents from the
source at the recorded commits; no human has checked them. Code Apache-2.0; text and data
CC BY 4.0.

Data run: `backport-version-notes-v1`, 2026-11-02 12:59-13:03 UTC (`results/summary.json`).
Branch heads: Django stable/5.2.x `cbbcf85`, stable/6.0.x `623c370`, stable/6.1.x `8485c6a`;
NumPy maintenance/1.24.x to 2.5.x (nine branches, shas in `results/heads.csv`). The Django
clone has no stable branches older than 5.2, so 4.x was not scanned.

## Verdicts

| | Prediction | Result | Verdict |
|---|---|---|---|
| Gate | CPython control, known Django note, >= 100 notes on newest heads, >= 90% of tags scanned | all six checks true; 32 of 32 Django and 46 of 46 NumPy tags scanned | **HELD** |
| P1 | Django: >= 2 future notes beyond the known one | 1 | **FAILED** |
| P2 | NumPy: >= 1 future note | 1 | **HELD** |
| P3 | >= 2 real problems (L1 or L2) beyond the known one | 1 (NumPy, L2) | **FAILED** |
| P4 | >= 50% of future notes (excluding the known one) absent at X.Y.0 | 0 of 2 | **FAILED** |

Across 12 branch heads and 5,130 version notes (619 Django, 4,511 NumPy), the scan found three notes that name a
release later than their branch. Three of the four predictions failed. The mechanism the
study looked for (a backport carrying a later release's note) is real but rare outside CPython:
one case in each project. In NumPy, the case arrived before X.Y.0, not after.

## The three future notes, read by hand

| Branch | File:line | Note | First seen | Label |
|---|---|---|---|---|
| Django stable/5.2.x | docs/topics/cache.txt:1412 | `versionchanged:: 6.0.6` | 5.2.15 | **L1** (known case) |
| Django stable/6.1.x | docs/intro/contributing.txt:408 | `versionadded:: 6.2` | 6.1 | **L3** intended |
| NumPy maintenance/2.0.x | doc/source/reference/c-api/array.rst:3963 | `versionadded:: 2.1` (`NPY_API_SYMBOL_ATTRIBUTE`) | v2.0.0 | **L2** behaviour the branch lacks |

**Django 5.2.x, `versionchanged:: 6.0.6` (L1).** Commit `050a3dc` ("[5.2.x] Fixed
CVE-2026-35193 -- Varied on Authorization when caching non-public responses", 2026-06-03)
changed `django/middleware/cache.py`, added the note to `docs/topics/cache.txt` and wrote up
the fix only in `docs/releases/5.2.15.txt`. So on the 5.2 branch the change arrived in
5.2.15, while the note says 6.0.6 (the 6.0.x backport, `664652f`, carries the same note,
correctly for that branch). Django's writing-documentation guide and release how-to say to
label a change with the release that made it ("`.. versionchanged:: A.B`"), but neither
says which number a security backport should carry. So we call it L1 by the guide's reading,
not proven to break a Django convention. A check of how Django labels other backported
notes since 3.0 is pre-registered as C3 in munimtechnologies/version-note-lint.

**Django 6.1.x, `versionadded:: 6.2` (L3).** This is sample rst inside a `.. code-block:: rst`
in the contributing tutorial (the `make_toast()` example), and again inside a
`.. code-block:: diff`. It tells contributors to label new work with the next release. It is
present at 6.1 and is intended. The scanner did not skip literal blocks.

**NumPy 2.0.x, `NPY_API_SYMBOL_ATTRIBUTE` "New in version 2.1" (L2).** Commit `d730c44`
on maintenance/2.0.x ("DOC: Fix some typos and incorrect markups", authored by Yuki K,
committed by charris, 2024-05-11) says in its message that "The whole of
doc/source/reference/c-api/array.rst is backported from main". It rewrote 148 lines of that
file and brought in main's new "Including and importing the C API" section. That section
documents `NPY_API_SYMBOL_ATTRIBUTE` ("New in version 2.1") and says "NumPy 2.1 changed the
headers to avoid sharing the table outside of a single shared object/dll". The behaviour is
from main's PR #26103 ("API: Default to hidden visibility for API tables", merged
2024-04-30). It is not in 2.0: `numpy/_core/code_generators/generate_numpy_api.py` has no
`NPY_API_SYMBOL_ATTRIBUTE` at v2.0.0 or at the maintenance/2.0.x head, and has it at v2.1.0
(all three read 2026-11-03). The 2.0 docs therefore describe a default (hidden visibility of
the `PyArray_API` table) and a macro that NumPy 2.0 does not have. It is live on
numpy.org/doc/2.0 (read 2026-11-03: "NPY_API_SYMBOL_ATTRIBUTE / New in version 2.1."). The
branch's last tag is v2.0.2, so this is a record, not a fix request.

## What the misses teach

- **P4 failed for a reason worth keeping.** The NumPy note came in by a backport, but before
  v2.0.0 (NumPy cuts its release branch months ahead of X.Y.0). "Absent at X.Y.0" was the
  wrong test for "arrived by backport" in projects that branch early. A better test is
  "absent at the branch point".
- **Whole-file doc backports are the risky kind.** The CPython cases (earlier audit) and this
  one all came from backports that carried more than the fix. A typo-fix PR that copies a
  whole file from main brings main's future notes with it.
- **A second, live slip in the same section.** The `versionchanged` in that NumPy section has
  no version on its directive line, and its text starts on the next line. Docutils takes the
  text's first word as the version, so numpy.org/doc/stable (read 2026-11-03) shows "Changed in
  version NumPy: 2.1 changed the headers to avoid sharing the table outside of a single
  shared object/dll". It is the same on main. It is not a future note and not graded here.
  It led to a new pre-registered tool and census, munimtechnologies/version-note-lint.
  sphinx-lint has no check of version-note arguments (its 29 checkers, read 2026-11-03).

## Exploratory (not graded)

- The CPython v3.14.10 control has 9 notes later than 3.14. Seven are the 3.15 notes reported
  in munimtechnologies/branch-version-notes-audit. Two (`Doc/using/windows.rst`,
  `versionadded:: 26.2` and `26.4`) name versions of the Python install manager, not of
  CPython (L3).
- Each branch head has 0-2 notes whose version did not parse (`unparsed` in
  `results/heads.csv`). They were not listed by this scan. The version-note-lint census lists
  every such note.

## Outreach

None. NumPy's AI policy (numpy.org/devdocs/dev/ai_policy.html, read 2026-11-03) requires a
human to check, write and submit any issue or pull request, and forbids autonomous agent
submissions. The 2.0 note is on a branch with no further releases. The live markup slip is
passed to a human at Munim, Inc. to decide on.

## Files

`results/summary.json`, `results/future_notes.csv`, `results/heads.csv` (job outputs, unchanged),
`results/hand_labels.csv`.

## Limits

- Text matching: a note that moved files counts as new where it moved.
- Django was scanned on its three stable branches only (5.2, 6.0, 6.1).
- One NumPy case and one Django case. Two data points cannot carry a rate.
- Hand labels by AI agents from source text; no human has checked them.
