#!/usr/bin/env python3
"""Small unit tests for artifact identity and path safety."""

import importlib.machinery
import importlib.util
from pathlib import Path
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "artifact"
loader = importlib.machinery.SourceFileLoader("artifact", str(SCRIPT))
spec = importlib.util.spec_from_loader(loader.name, loader)
artifact = importlib.util.module_from_spec(spec)
loader.exec_module(artifact)


class ArtifactTests(unittest.TestCase):
    def test_platform_tag_has_system_and_machine(self):
        self.assertRegex(artifact.platform_tag(), r"^[a-z0-9]+-[a-z0-9_]+$")

    def test_inventory_is_relative_and_deterministic(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "b").write_text("second")
            (root / "a").write_text("first")
            inventory = artifact.file_inventory(root)
            self.assertEqual(list(inventory), ["a", "b"])
            self.assertEqual(inventory["a"]["size"], 5)


if __name__ == "__main__":
    unittest.main()
