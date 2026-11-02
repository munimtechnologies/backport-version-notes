#!/usr/bin/env python3
# Copyright 2026 Munim, Inc. (MV2, mv2@munimtech.com)
# Licensed under the Apache License, Version 2.0 (Apache-2.0). See LICENSE.
# Made with AI agents working in MV2's name.
"""Future version notes on maintenance branches.

For Django (stable/X.Y.x) and NumPy (maintenance/X.Y.x), find every Sphinx version
note (versionadded, versionchanged, deprecated, deprecated-removed, versionremoved,
soft-deprecated) at each branch head and at every final release tag, and flag notes
whose version (major, minor) is LATER than the branch's own. Such a note tells readers
of the X.Y docs about a release they are not reading about; on a maintenance branch it
usually arrives with a backport. CPython v3.14.10 is scanned as a control.

Usage: python scan.py --data-dir /data --out-dir /out
"""
import argparse
import csv
import json
import os
import re
import subprocess
import sys
import tarfile
import time
import urllib.request

NOTE_RE = re.compile(
    r"^[\s#]*\.\.\s+(versionadded|versionchanged|deprecated-removed|soft-deprecated|"
    r"versionremoved|deprecated)::[ \t]*(.*?)\s*$"
)
VERSION_RE = re.compile(r"^(?:[A-Za-z]+\s+)?v?(\d+)\.(\d+)(?:\.(\d+))?")
GREP_PATTERN = (
    r"^[[:space:]#]*\.\.[[:space:]]+(versionadded|versionchanged|deprecated|"
    r"versionremoved|deprecated-removed|soft-deprecated)::"
)
OWNER_RE = re.compile(
    r"^\s*(?:\.\.\s+(?!(?:versionadded|versionchanged|deprecated|deprecated-removed|"
    r"versionremoved|soft-deprecated|note|warning|admonition|seealso|code-block|"
    r"sourcecode|code|tip|important|attention|caution|hint|include|toctree|"
    r"literalinclude|testcode|doctest|plot|rubric|only)::)[\w:.-]+::\s*\S"
    r"|def\s+\w|class\s+\w|add_newdoc\(|add_newdoc_ufunc\()"
)

PROJECTS = {
    "django": {
        "url": "https://github.com/django/django.git",
        "branch_re": r"^stable/(\d+)\.(\d+)\.x$",
        "tag_re": r"^(\d+)\.(\d+)(?:\.(\d+))?$",
        "min_branch": (4, 0),
        "pathspecs": ["docs/*.txt"],
    },
    "numpy": {
        "url": "https://github.com/numpy/numpy.git",
        "branch_re": r"^maintenance/(\d+)\.(\d+)\.x$",
        "tag_re": r"^v(\d+)\.(\d+)\.(\d+)$",
        "min_branch": (1, 24),
        "pathspecs": ["*.rst", "*.py", "*.pyi", "*.txt", "*.c", "*.h", "*.src"],
    },
}

# Known case, read on 2026-11-02 before any data: Django stable/5.2.x
# docs/topics/cache.txt carries ".. versionchanged:: 6.0.6" (CVE-2026-35193 backport).
KNOWN = {("django", "stable/5.2.x", "docs/topics/cache.txt", "versionchanged", "6.0.6")}

CPYTHON_CONTROL_URL = "https://github.com/python/cpython/archive/refs/tags/v3.14.10.tar.gz"


def parse_note(line):
    """Return {'directive', 'args', 'ver'} for a version-note line, else None."""
    m = NOTE_RE.match(line)
    if not m:
        return None
    directive, args = m.group(1), m.group(2)
    v = VERSION_RE.match(args)
    ver = (int(v.group(1)), int(v.group(2))) if v else None
    return {"directive": directive, "args": args, "ver": ver}


def branch_version(project, name):
    m = re.match(PROJECTS[project]["branch_re"], name)
    return (int(m.group(1)), int(m.group(2))) if m else None


def tag_version(project, name):
    m = re.match(PROJECTS[project]["tag_re"], name)
    if not m:
        return None
    return (int(m.group(1)), int(m.group(2)), int(m.group(3) or 0))


def is_future(note_ver, branch_ver):
    return note_ver is not None and note_ver > branch_ver


def parse_grep_output(text, ref):
    """Parse `git grep -n <ref>` output into (path, lineno, content) tuples."""
    out = []
    prefix = ref + ":"
    for line in text.splitlines():
        if not line.startswith(prefix):
            continue
        parts = line[len(prefix):].split(":", 2)
        if len(parts) != 3 or not parts[1].isdigit():
            continue
        out.append((parts[0], int(parts[1]), parts[2]))
    return out


def next_lines(lines, lineno, n=3, limit=300):
    """Join the next n non-empty lines after 1-based line `lineno`."""
    got = []
    for l in lines[lineno:]:
        s = l.strip()
        if s:
            got.append(s)
        if len(got) >= n:
            break
    return " / ".join(got)[:limit]


def owner_of(lines, lineno, reach=300):
    """Nearest preceding object directive, def/class or add_newdoc line."""
    for i in range(lineno - 2, max(-1, lineno - 2 - reach), -1):
        if OWNER_RE.match(lines[i]):
            return lines[i].strip()[:160]
    return ""


def first_tag(key, ordered_tags, keysets):
    for t in ordered_tags:
        if key in keysets.get(t, set()):
            return t
    return ""


# ---------------------------------------------------------------- git helpers

def git(gitdir, args, ok=(0,)):
    r = subprocess.run(["git", "--git-dir", gitdir] + args, capture_output=True,
                       text=True, encoding="utf-8", errors="replace")
    if r.returncode not in ok:
        raise RuntimeError("git %s failed (%d): %s" % (" ".join(args), r.returncode,
                                                       r.stderr[-500:]))
    return r.stdout


def ensure_repo(url, gitdir, log):
    if os.path.isdir(gitdir):
        try:
            git(gitdir, ["fetch", "--prune", "--quiet", "origin",
                         "+refs/heads/*:refs/heads/*", "+refs/tags/*:refs/tags/*"])
            log.append("fetched %s" % url)
        except RuntimeError as e:
            log.append("fetch failed, using cached copy: %s" % e)
    else:
        r = subprocess.run(["git", "clone", "--bare", "--quiet", url, gitdir],
                           capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError("clone failed: " + r.stderr[-500:])
        log.append("cloned %s" % url)


def scan_ref(gitdir, ref, pathspecs):
    text = git(gitdir, ["grep", "-n", "-I", "-E", GREP_PATTERN, ref, "--"] + pathspecs,
               ok=(0, 1))
    notes = []
    for path, lineno, content in parse_grep_output(text, ref):
        p = parse_note(content)
        if p:
            p.update(path=path, line=lineno)
            notes.append(p)
    return notes


def note_key(n):
    return (n["path"], n["directive"], n["args"])


def scan_project(name, cfg, data_dir, log):
    gitdir = os.path.join(data_dir, name + ".git")
    ensure_repo(cfg["url"], gitdir, log)
    refs = git(gitdir, ["for-each-ref", "--format=%(refname)", "refs/heads", "refs/tags"])
    branches, tags = {}, {}
    for full in refs.split():
        if full.startswith("refs/heads/"):
            short = full[len("refs/heads/"):]
            bv = branch_version(name, short)
            if bv and bv >= cfg["min_branch"]:
                branches[short] = bv
        elif full.startswith("refs/tags/"):
            short = full[len("refs/tags/"):]
            tv = tag_version(name, short)
            if tv and tv[:2] >= cfg["min_branch"]:
                tags[short] = tv
    heads, future = [], []
    tags_listed = tags_scanned = 0
    for br in sorted(branches, key=lambda b: branches[b]):
        bv = branches[br]
        ref = "refs/heads/" + br
        sha = git(gitdir, ["rev-parse", ref]).strip()
        notes = scan_ref(gitdir, ref, cfg["pathspecs"])
        fut = [n for n in notes if is_future(n["ver"], bv)]
        unparsed = sum(1 for n in notes if n["ver"] is None)
        # tags of this branch, oldest first
        btags = sorted([t for t, v in tags.items() if v[:2] == bv], key=lambda t: tags[t])
        keysets = {}
        for t in btags:
            tags_listed += 1
            try:
                keysets[t] = {note_key(n) for n in scan_ref(gitdir, "refs/tags/" + t,
                                                              cfg["pathspecs"])}
                tags_scanned += 1
            except RuntimeError as e:
                log.append("tag %s failed: %s" % (t, e))
        x0 = [t for t in btags if tags[t][2] == 0]
        x0 = x0[0] if x0 else ""
        files = {}
        for n in fut:
            if n["path"] not in files:
                files[n["path"]] = git(gitdir, ["show", "%s:%s" % (ref, n["path"])]).splitlines()
            lines = files[n["path"]]
            key = note_key(n)
            ft = first_tag(key, btags, keysets)
            future.append({
                "project": name, "branch": br, "branch_version": "%d.%d" % bv,
                "head_sha": sha, "path": n["path"], "line": n["line"],
                "directive": n["directive"], "args": n["args"],
                "note_version": "%d.%d" % n["ver"],
                "owner": owner_of(lines, n["line"]),
                "context": next_lines(lines, n["line"]),
                "first_tag": ft,
                "x0_tag": x0,
                "present_at_x0": (key in keysets.get(x0, set())) if x0 else None,
                "known": (name, br, n["path"], n["directive"], n["args"]) in KNOWN,
            })
        heads.append({"branch": br, "version": "%d.%d" % bv, "sha": sha,
                      "notes": len(notes), "future": len(fut), "unparsed": unparsed,
                      "tags": len(btags), "x0_tag": x0})
        log.append("%s %s: %d notes, %d future, %d tags" % (name, br, len(notes),
                                                              len(fut), len(btags)))
    return {"heads": heads, "future": future, "tags_listed": tags_listed,
            "tags_scanned": tags_scanned}


def scan_cpython_control(data_dir, log):
    path = os.path.join(data_dir, "cpython-v3.14.10.tar.gz")
    if not os.path.exists(path):
        req = urllib.request.Request(CPYTHON_CONTROL_URL, headers={"User-Agent": "mv2-scan"})
        with urllib.request.urlopen(req, timeout=300) as r, open(path + ".part", "wb") as f:
            while True:
                b = r.read(1 << 20)
                if not b:
                    break
                f.write(b)
        os.replace(path + ".part", path)
        log.append("downloaded cpython v3.14.10")
    notes, fut = 0, []
    with tarfile.open(path, "r:gz") as tf:
        for m in tf:
            if not (m.isfile() and "/Doc/" in m.name and m.name.endswith(".rst")):
                continue
            rel = m.name.split("/", 1)[1]
            text = tf.extractfile(m).read().decode("utf-8", "replace")
            for i, line in enumerate(text.splitlines(), 1):
                p = parse_note(line)
                if not p:
                    continue
                notes += 1
                if is_future(p["ver"], (3, 14)):
                    fut.append({"path": rel, "line": i, "directive": p["directive"],
                                "args": p["args"]})
    return {"notes": notes, "future": fut}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="/data")
    ap.add_argument("--out-dir", default="/out")
    a = ap.parse_args(argv)
    os.makedirs(a.out_dir, exist_ok=True)
    os.makedirs(a.data_dir, exist_ok=True)
    log = []
    t0 = time.time()
    res = {}
    for name, cfg in PROJECTS.items():
        res[name] = scan_project(name, cfg, a.data_dir, log)
    ctl = scan_cpython_control(a.data_dir, log)

    allfut = res["django"]["future"] + res["numpy"]["future"]
    with open(os.path.join(a.out_dir, "future_notes.csv"), "w", newline="",
              encoding="utf-8") as f:
        cols = ["project", "branch", "branch_version", "head_sha", "path", "line",
                "directive", "args", "note_version", "owner", "context", "first_tag",
                "x0_tag", "present_at_x0", "known"]
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in allfut:
            w.writerow(r)
    with open(os.path.join(a.out_dir, "heads.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["project", "branch", "version", "sha", "notes", "future", "unparsed",
                    "tags", "x0_tag"])
        for name in PROJECTS:
            for h in res[name]["heads"]:
                w.writerow([name, h["branch"], h["version"], h["sha"], h["notes"],
                            h["future"], h["unparsed"], h["tags"], h["x0_tag"]])

    # Pre-registered mechanical checks (see PREREG.md).
    def newest_head_notes(name):
        hs = res[name]["heads"]
        return hs[-1]["notes"] if hs else 0

    def tag_share(name):
        r = res[name]
        return r["tags_scanned"] / r["tags_listed"] if r["tags_listed"] else 0.0

    known_found = any(r["known"] for r in allfut)
    ctl_found = any(x["path"] == "Doc/library/datetime.rst" and
                    x["directive"] == "versionchanged" and x["args"].startswith("3.15")
                    for x in ctl["future"])
    gate = {
        "cpython_control_utcfromtimestamp": ctl_found,
        "django_known_cache_note": known_found,
        "django_newest_head_notes_ge_100": newest_head_notes("django") >= 100,
        "numpy_newest_head_notes_ge_100": newest_head_notes("numpy") >= 100,
        "django_tags_ge_90pct": tag_share("django") >= 0.9,
        "numpy_tags_ge_90pct": tag_share("numpy") >= 0.9,
    }
    dj_beyond = [r for r in res["django"]["future"] if not r["known"]]
    np_fut = res["numpy"]["future"]
    p4_pool = [r for r in allfut if not r["known"] and r["present_at_x0"] is not None]
    p4_after = [r for r in p4_pool if r["present_at_x0"] is False]
    summary = {
        "finished_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "seconds": round(time.time() - t0, 1),
        "gate": gate,
        "gate_held": all(gate.values()),
        "P1_django_future_beyond_known": len(dj_beyond),
        "P1_held": len(dj_beyond) >= 2,
        "P2_numpy_future": len(np_fut),
        "P2_held": len(np_fut) >= 1,
        "P4_pool": len(p4_pool),
        "P4_arrived_after_x0": len(p4_after),
        "P4_share": (len(p4_after) / len(p4_pool)) if p4_pool else None,
        "P4_held": (len(p4_after) / len(p4_pool) >= 0.5) if p4_pool else None,
        "P3": "graded by hand (GRADING.md)",
        "projects": {n: {"heads": res[n]["heads"], "tags_listed": res[n]["tags_listed"],
                         "tags_scanned": res[n]["tags_scanned"],
                         "future_count": len(res[n]["future"])} for n in PROJECTS},
        "cpython_control": ctl,
        "log": log,
    }
    with open(os.path.join(a.out_dir, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=1, sort_keys=True)
    for r in allfut:
        print("FUTURE %s %s %s:%s %s:: %s first=%s known=%s" % (
            r["project"], r["branch"], r["path"], r["line"], r["directive"], r["args"],
            r["first_tag"] or "-", r["known"]))
    print("GATE", json.dumps(gate, sort_keys=True))
    print("P1 %d P2 %d P4 %d/%d" % (len(dj_beyond), len(np_fut), len(p4_after),
                                    len(p4_pool)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
