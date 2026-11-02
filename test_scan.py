# Copyright 2026 Munim, Inc. (MV2, mv2@munimtech.com)
# Licensed under the Apache License, Version 2.0 (Apache-2.0).
# Made with AI agents working in MV2's name.
import unittest

import scan


class ParseNote(unittest.TestCase):
    def test_versionadded(self):
        p = scan.parse_note(".. versionadded:: 6.1")
        self.assertEqual(p["directive"], "versionadded")
        self.assertEqual(p["ver"], (6, 1))

    def test_indented_micro(self):
        p = scan.parse_note("    .. versionchanged:: 6.0.6")
        self.assertEqual(p["directive"], "versionchanged")
        self.assertEqual(p["args"], "6.0.6")
        self.assertEqual(p["ver"], (6, 0))

    def test_deprecated_removed(self):
        p = scan.parse_note(".. deprecated-removed:: 3.15 3.19")
        self.assertEqual(p["directive"], "deprecated-removed")
        self.assertEqual(p["ver"], (3, 15))

    def test_plain_deprecated(self):
        p = scan.parse_note(".. deprecated:: 1.25.0")
        self.assertEqual(p["directive"], "deprecated")
        self.assertEqual(p["ver"], (1, 25))

    def test_word_prefix(self):
        self.assertEqual(scan.parse_note(".. versionadded:: NumPy 2.0")["ver"], (2, 0))

    def test_next_placeholder(self):
        p = scan.parse_note(".. versionadded:: next")
        self.assertIsNotNone(p)
        self.assertIsNone(p["ver"])

    def test_not_notes(self):
        self.assertIsNone(scan.parse_note(".. note::"))
        self.assertIsNone(scan.parse_note("text .. versionadded:: 1.0"))
        self.assertIsNone(scan.parse_note(".. versionadded 1.0"))

    def test_trailing_cr(self):
        self.assertEqual(scan.parse_note(".. versionadded:: 5.2\r")["args"], "5.2")


class Versions(unittest.TestCase):
    def test_branch(self):
        self.assertEqual(scan.branch_version("django", "stable/5.2.x"), (5, 2))
        self.assertIsNone(scan.branch_version("django", "main"))
        self.assertEqual(scan.branch_version("numpy", "maintenance/2.3.x"), (2, 3))

    def test_tag(self):
        self.assertEqual(scan.tag_version("django", "5.2"), (5, 2, 0))
        self.assertEqual(scan.tag_version("django", "5.2.15"), (5, 2, 15))
        self.assertIsNone(scan.tag_version("django", "5.2rc1"))
        self.assertEqual(scan.tag_version("numpy", "v2.3.4"), (2, 3, 4))
        self.assertIsNone(scan.tag_version("numpy", "v2.3.0rc1"))

    def test_future(self):
        self.assertTrue(scan.is_future((6, 0), (5, 2)))
        self.assertFalse(scan.is_future((5, 2), (5, 2)))
        self.assertFalse(scan.is_future((4, 2), (5, 2)))
        self.assertFalse(scan.is_future(None, (5, 2)))


class Helpers(unittest.TestCase):
    def test_grep_output(self):
        ref = "refs/heads/stable/5.2.x"
        text = (ref + ":docs/topics/cache.txt:1409:.. versionchanged:: 6.0.6\n"
                "other:docs/x.txt:1:.. versionadded:: 1.0\n")
        self.assertEqual(scan.parse_grep_output(text, ref),
                         [("docs/topics/cache.txt", 1409, ".. versionchanged:: 6.0.6")])

    def test_next_lines_and_owner(self):
        lines = [".. setting:: CACHES", "", "Some text.", "", ".. versionchanged:: 6.0.6",
                 "", "    Previously, X.", "    Second line.", "", "Third."]
        self.assertEqual(scan.next_lines(lines, 5), "Previously, X. / Second line. / Third.")
        self.assertEqual(scan.owner_of(lines, 5), ".. setting:: CACHES")

    def test_owner_skips_notes(self):
        lines = ["def foo():", "    .. versionadded:: 2.0.0", "    .. note::",
                 "    .. versionchanged:: 2.4.0"]
        self.assertEqual(scan.owner_of(lines, 4), "def foo():")

    def test_first_tag(self):
        k = ("p", "versionadded", "6.1")
        keysets = {"6.0": set(), "6.0.1": {k}, "6.0.2": {k}}
        self.assertEqual(scan.first_tag(k, ["6.0", "6.0.1", "6.0.2"], keysets), "6.0.1")
        self.assertEqual(scan.first_tag(("q", "x", "1"), ["6.0"], keysets), "")


if __name__ == "__main__":
    unittest.main()
