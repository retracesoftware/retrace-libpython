#!/usr/bin/env python3
"""Tests for exact CPython tag and patch-range validation."""

from pathlib import Path
import json
import subprocess
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "python-tags"


class PythonTagsTests(unittest.TestCase):
    def run_tags(self, *arguments):
        return subprocess.run(
            [SCRIPT, *arguments], text=True, capture_output=True
        )

    def run_tags_with_input(self, input_value, *arguments):
        return subprocess.run(
            [SCRIPT, *arguments], input=input_value, text=True, capture_output=True
        )

    def test_exact_tag_is_normalized(self):
        result = self.run_tags("exact", "v3.14.2")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "3.14.2")

    def test_rejects_non_final_tag(self):
        self.assertNotEqual(
            self.run_tags("exact", "v3.14.0rc1").returncode, 0
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

    def test_series_filters_final_tags_and_sorts_patches(self):
        result = self.run_tags_with_input(
            "\n".join((
                "refs/tags/v3.14.2",
                "refs/tags/v3.14.0",
                "refs/tags/v3.14.1",
                "refs/tags/v3.14.1",
                "refs/tags/v3.14.2rc1",
                "refs/tags/v3.13.9",
                "refs/tags/v3.14.0a1",
                "refs/tags/v3.14.3-not-a-release",
            )),
            "series", "3.14", "--json",
        )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(
            json.loads(result.stdout),
            ["v3.14.0", "v3.14.1", "v3.14.2"],
        )

    def test_series_rejects_nonsequential_tags(self):
        result = self.run_tags_with_input(
            "refs/tags/v3.14.0\nrefs/tags/v3.14.2\n",
            "series", "3.14", "--json",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not sequential", result.stderr)

    def test_series_rejects_invalid_minor_or_no_final_tags(self):
        for input_value, series in (
            ("refs/tags/v3.14.0\n", "v3.14"),
            ("refs/tags/v3.14.0rc1\n", "3.14"),
        ):
            with self.subTest(series=series):
                self.assertNotEqual(
                    self.run_tags_with_input(
                        input_value, "series", series, "--json"
                    ).returncode,
                    0,
                )


if __name__ == "__main__":
    unittest.main()