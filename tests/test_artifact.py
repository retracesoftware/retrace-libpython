#!/usr/bin/env python3
"""Small unit tests for artifact identity and path safety."""

import importlib.machinery
import importlib.util
import argparse
import json
from pathlib import Path
import subprocess
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

    def test_series_uses_512_mib_dictionary(self):
        filters = artifact.series_compression_filters()
        self.assertEqual(len(filters), 1)
        self.assertEqual(filters[0]["id"], artifact.lzma.FILTER_LZMA2)
        self.assertEqual(filters[0]["dict_size"], 512 * 1024 * 1024)

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
                with self.assertRaisesRegex(SystemExit, "sequential patches"):
                    artifact.validate_requested_versions(versions)

    def test_compose_exact_artifacts_into_series_with_provenance(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            build = root / "build"
            archives = []

            def fake_git_output(repository, *args):
                if args == ("status", "--porcelain"):
                    raise subprocess.CalledProcessError(128, "git")
                return "b" * 40

            with mock.patch.object(artifact, "git_output", fake_git_output):
                for version in ("3.14.0", "3.14.1"):
                    self.make_synthetic_build(build, version)
                    archive_path = root / f"exact-{version}.tar.xz"
                    artifact.command_pack(argparse.Namespace(
                        root=build,
                        versions=[version],
                        output=archive_path,
                        producer_version="test",
                        producer_commit="b" * 40,
                        sources=None,
                    ))
                    archives.append(archive_path)

                series_archive = root / "series.tar.xz"
                artifact.command_compose(argparse.Namespace(
                    versions=["3.14.0", "3.14.1"],
                    sources=[
                        [f"registry:exact-{version}", "sha256:" + "c" * 64, path]
                        for version, path in zip(("3.14.0", "3.14.1"), archives)
                    ],
                    output=series_archive,
                    producer_version="test",
                    producer_commit="b" * 40,
                ))

            with tempfile.TemporaryDirectory() as extracted:
                extracted_root = Path(extracted)
                artifact.safe_extract(series_archive, extracted_root)
                manifest = artifact.verify_tree(
                    extracted_root, expected_versions=["3.14.0", "3.14.1"]
                )
            self.assertEqual(manifest["kind"], "series")
            self.assertEqual(manifest["series"], {
                "first": "3.14.0", "last": "3.14.1"
            })
            self.assertEqual(
                [source["digest"] for source in manifest["sources"]],
                ["sha256:" + "c" * 64] * 2,
            )

if __name__ == "__main__":
    unittest.main()
