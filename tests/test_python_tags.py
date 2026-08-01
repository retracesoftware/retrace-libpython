#!/usr/bin/env python3
"""Tests for exact final CPython tag validation."""

from pathlib import Path
import subprocess
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "python-tags"


class PythonTagsTests(unittest.TestCase):
    def run_tags(self, *arguments):
        return subprocess.run(
            [SCRIPT, *arguments], text=True, capture_output=True
        )

    def test_exact_tag_is_normalized(self):
        result = self.run_tags("exact", "v3.14.2")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "3.14.2")

    def test_rejects_non_final_tag(self):
        self.assertNotEqual(
            self.run_tags("exact", "v3.14.0rc1").returncode, 0
        )


if __name__ == "__main__":
    unittest.main()