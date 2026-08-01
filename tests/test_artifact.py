#!/usr/bin/env python3
"""Small unit tests for artifact identity and path safety."""

import importlib.machinery
import importlib.util
import argparse
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
    def make_synthetic_build(self, root, version):
        version_root = root / f"v{version}"
        (version_root / "source" / "Lib").mkdir(parents=True)
        (version_root / "source" / "Lib" / "os.py").write_text("pass\n")
        for mode in artifact.MODES:
            mode_root = version_root / mode
            (mode_root / "build").mkdir(parents=True)
            (mode_root / "retrace-libpython.json").write_text(json.dumps({
                "cpython": {"version": version, "commit": "a" * 40},
                "profile": "retrace-static-v1",
                "mode": mode,
            }))

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

    def test_xz_archive_has_build_directory_roots(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            payload = root / "payload"
            (payload / "v3.11.13").mkdir(parents=True)
            (payload / "v3.12.8").mkdir()
            (payload / "retrace-libpython-manifest.json").write_text(
                json.dumps({"schema": artifact.SCHEMA})
            )
            archive_path = root / "matrix.tar.xz"
            artifact.create_archive(payload, archive_path)
            with tarfile.open(archive_path, "r:xz") as archive:
                roots = {member.name.split("/", 1)[0]
                         for member in archive.getmembers()}
            self.assertEqual(
                roots,
                {"v3.11.13", "v3.12.8", "retrace-libpython-manifest.json"},
            )

    def test_verify_rejects_incomplete_version_matrix(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "retrace-libpython-manifest.json").write_text(json.dumps({
                "schema": artifact.SCHEMA,
                "kind": "exact",
                "platform": artifact.platform_tag(),
                "versions": {"3.12.8": {}},
                "files": {},
            }))
            with self.assertRaisesRegex(SystemExit, "version matrix mismatch"):
                artifact.verify_tree(
                    root, expected_versions=["3.12.8", "3.13.14"]
                )

    def test_version_range_must_be_sequential_in_one_minor(self):
        artifact.validate_requested_versions(["3.14.0", "3.14.1", "3.14.2"])
        for versions in (
            ["3.14.0", "3.14.2"],
            ["3.13.9", "3.14.0"],
            ["3.14.1", "3.14.0"],
        ):
            with self.subTest(versions=versions):
                with self.assertRaisesRegex(SystemExit, "sequential patch series"):
                    artifact.validate_requested_versions(versions)

    def test_verify_rejects_wrong_range_endpoints(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "retrace-libpython-manifest.json").write_text(json.dumps({
                "schema": artifact.SCHEMA,
                "kind": "range",
                "range": {"first": "3.14.0", "last": "3.14.9"},
                "platform": artifact.platform_tag(),
                "versions": {"3.14.0": {}, "3.14.10": {}},
                "sources": [{}, {}],
                "files": {},
            }))
            with self.assertRaisesRegex(SystemExit, "range artifact identity"):
                artifact.verify_tree(root)

    def test_compose_exact_artifacts_into_range_with_provenance(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            build = root / "build"
            archives = []
            fake_git_output = lambda repository, *args: (
                "" if args == ("status", "--porcelain") else "b" * 40
            )
            with mock.patch.object(artifact, "git_output", fake_git_output):
                for version in ("3.14.0", "3.14.1"):
                    self.make_synthetic_build(build, version)
                    archive_path = root / f"exact-{version}.tar.xz"
                    artifact.command_pack(argparse.Namespace(
                        root=build,
                        versions=[version],
                        output=archive_path,
                        producer_version="test",
                        sources=None,
                    ))
                    archives.append(archive_path)

                range_archive = root / "range.tar.xz"
                artifact.command_compose(argparse.Namespace(
                    versions=["3.14.0", "3.14.1"],
                    sources=[
                        [f"registry:exact-{version}", "sha256:" + "c" * 64, path]
                        for version, path in zip(("3.14.0", "3.14.1"), archives)
                    ],
                    output=range_archive,
                    producer_version="test",
                ))

            with tempfile.TemporaryDirectory() as extracted:
                extracted_root = Path(extracted)
                artifact.safe_extract(range_archive, extracted_root)
                manifest = artifact.verify_tree(
                    extracted_root, expected_versions=["3.14.0", "3.14.1"]
                )
            self.assertEqual(manifest["kind"], "range")
            self.assertEqual(manifest["range"], {
                "first": "3.14.0", "last": "3.14.1"
            })
            self.assertEqual(
                [source["digest"] for source in manifest["sources"]],
                ["sha256:" + "c" * 64] * 2,
            )


if __name__ == "__main__":
    unittest.main()
