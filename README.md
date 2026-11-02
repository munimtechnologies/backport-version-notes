# backport-version-notes

Do Django and NumPy maintenance branches carry version notes that name a later release?

On the X.Y branch, a note such as `.. versionchanged:: 6.0.6` tells readers of the X.Y docs
about a release they are not reading about. MV2's CPython audit
(munimtechnologies/branch-version-notes-audit) found three of these on CPython 3.13 and
3.14, all brought in by backports. This study runs the same check on Django and NumPy, with
CPython v3.14.10 as a control. `scan.py` scans every maintenance-branch head and every final
release tag, then lists each note whose (major, minor) is later than the branch's, with the
first tag that shipped it.

Status: **pre-registered** (`PREREG.md`, 2026-11-02). Results and grading will be added in
`GRADING.md` and `results/`.

Run: `python -m unittest -v` and then `python scan.py --data-dir DATA --out-dir OUT` (needs
`git` and network access; the bare clones of Django and NumPy take about 0.5 GB).

By MV2, Munim, Inc. (mv2@munimtech.com). Made with AI agents working in MV2's name; no
human has checked the results. Code: Apache-2.0. Text and data: CC BY 4.0. Django
(BSD-3-Clause), NumPy (BSD-3-Clause) and CPython (PSF License) keep their own licences;
this repo quotes only short excerpts of their docs.
