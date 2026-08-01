#!/usr/bin/env python3
"""Tests for exact CPython tag and patch-range validation."""

from pathlib import Path
import subprocess
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "python-tags"


class PythonTagsTests(unittest.TestCase):
    def run_tags(self, *arguments):
        return subprocess.run(
            [SCRIPT, *arguments], text=True, capture_output=True
        )

    def test_range_is_inclusive(self):
        result = self.run_tags("range", "v3.14.0", "v3.14.2")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "v3.14.0 v3.14.1 v3.14.2")

    def test_rejects_invalid_ranges(self):
        for arguments in (
            ("range", "v3.13.9", "v3.14.0"),
            ("range", "v3.14.2", "v3.14.0"),
            ("range", "v3.14.0", "v3.14.0"),
            ("range", "v3.14.0rc1", "v3.14.0"),
        ):
            with self.subTest(arguments=arguments):
                self.assertNotEqual(self.run_tags(*arguments).returncode, 0)


if __name__ == "__main__":
    unittest.main()