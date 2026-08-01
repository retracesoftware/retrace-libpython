# AGENTS.md

## Project

`retrace-libpython` produces reproducible, exact-patch CPython prerequisite
bundles for Retrace. It owns CPython source acquisition, release/debug build
profiles, artifact manifests, packaging, verification, and optional GHCR
transport. It must not contain Retrace overlay sources or build `_retrace`.

## Principles

- Local source builds are authoritative; remote artifacts are optional.
- Release and debug outputs must use separate build roots.
- Exact artifacts are immutable and keyed by producer/profile revision, exact
  CPython tag, platform ABI, and architecture.
- The producer contains no supported-version list. Callers supply exact tags;
  series workflows discover strict final tags for a requested minor release.
- Archives contain `vX.Y.Z/{source,release,debug}` at their root.
- Keep build, pack, verify, and install independent of GHCR transport.
- Do not commit generated CPython source or build outputs.

## Build

```bash
make build PYTHON_TAG=v3.12.8 BUILD_MODE=release CPYTHON_REPO_URL=file:///opt/cpython.git
make build PYTHON_TAG=v3.12.8 BUILD_MODE=debug CPYTHON_REPO_URL=file:///opt/cpython.git
make build-all PYTHON_TAG=v3.12.8 CPYTHON_REPO_URL=file:///opt/cpython.git
make pack verify PYTHON_TAG=v3.12.8 PRODUCER_VERSION=0.2.0
```

The exact workflow accepts one `python_tag`. The series workflow accepts a
minor release, OS, and architecture, discovers CPython's final GitHub tags,
matrix-builds only missing exact artifacts, and composes an OS/architecture-
specific archive with a 512 MiB XZ dictionary. Support policy remains with the
consumer.
