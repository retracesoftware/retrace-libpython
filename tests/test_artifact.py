#!/usr/bin/env python3
"""Small unit tests for artifact identity and path safety."""

import importlib.machinery
import importlib.util
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "artifact"
loader = importlib.machinery.SourceFileLoader("artifact", str(SCRIPT))
spec = importlib.util.spec_from_loader(loader.name, loader)
artifact = importlib.util.module_from_spec(spec)
loader.exec_module(artifact)


class ArtifactTests(unittest.TestCase):
    def test_platform_tag_has_system_and_machine(self):
        self.assertRegex(artifact.platform_tag(), r"^[a-z0-9]+-[a-z0-9_]+$")

    @mock.patch.object(artifact.platform, "machine", return_value="arm64")
    @mock.patch.object(artifact.platform, "system", return_value="Darwin")
    def test_platform_tag_uses_macos_name(self, _system, _machine):
        self.assertEqual(artifact.platform_tag(), "macos-arm64")

    def test_inventory_is_relative_and_deterministic(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "b").write_text("second")
            (root / "a").write_text("first")
            inventory = artifact.file_inventory(root)
            self.assertEqual(list(inventory), ["a", "b"])
            self.assertEqual(inventory["a"]["size"], 5)

    def test_copy_mode_normalizes_macos_python_executable(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            destination = root / "destination"
            (source / "python").mkdir(parents=True)
            (source / "python.exe").write_text("executable")
            (source / "build").mkdir()

            artifact.copy_mode(source, destination)

            self.assertEqual((destination / "python").read_text(), "executable")

    def test_xz_archive_has_exact_version_root(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            payload = root / "payload"
            (payload / "v3.12.8").mkdir(parents=True)
            (payload / "retrace-libpython-manifest.json").write_text(
                json.dumps({"schema": artifact.SCHEMA})
            )
            archive_path = root / "exact.tar.xz"
            artifact.create_archive(payload, archive_path)
            with tarfile.open(archive_path, "r:xz") as archive:
                roots = {member.name.split("/", 1)[0]
                         for member in archive.getmembers()}
            self.assertEqual(
                roots,
                {"v3.12.8", "retrace-libpython-manifest.json"},
            )

    def test_verify_rejects_wrong_exact_version(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "retrace-libpython-manifest.json").write_text(json.dumps({
                "schema": artifact.SCHEMA,
                "kind": "exact",
                "platform": artifact.platform_tag(),
                "versions": {"3.12.8": {}},
                "files": {},
            }))
            with self.assertRaisesRegex(SystemExit, "version mismatch"):
                artifact.verify_tree(
                    root, expected_versions=["3.12.8", "3.13.14"]
                )

if __name__ == "__main__":
    unittest.main()
