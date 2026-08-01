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
- The producer contains no supported-version list. Callers supply exact tags
  and download each patch artifact independently.
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

The exact workflow accepts one `python_tag` and an optional platform; support
policy and multi-patch aggregation remain outside this repository. Builds are
started explicitly by callers or people, never by repository event triggers.
