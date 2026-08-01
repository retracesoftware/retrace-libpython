# retrace-libpython

Builds exact-patch CPython prerequisite bundles for Retrace. The producer owns
the CPython compiler/configuration profile; it does not contain Retrace overlay
sources or build `_retrace`.

`versions.txt` is the authoritative supported patch matrix. One artifact is
published per producer release, build profile, platform, and architecture; it
contains every listed patch release in both release and debug modes.

## Build

```bash
make build VERSION=3.12.8 BUILD_MODE=release \
  CPYTHON_REPO_URL=file:///opt/cpython.git
make build VERSION=3.12.8 BUILD_MODE=debug \
  CPYTHON_REPO_URL=file:///opt/cpython.git
make build-all VERSION=3.12.8 \
  CPYTHON_REPO_URL=file:///opt/cpython.git
make matrix CPYTHON_REPO_URL=file:///opt/cpython.git
```

Each mode has an independent out-of-tree build under
`build/v<version>/<mode>/`. The pristine exact-tag checkout is shared at
`build/v<version>/source/`.

## Artifacts

Create and verify one deterministic, maximum-compression XZ bundle containing
pristine source and both build modes for every version in `versions.txt`:

```bash
make pack verify PRODUCER_VERSION=0.2.0
```

The archive has no `build/` wrapper. Its entries are directly rooted at patch
directories:

```text
v3.11.0/source/
v3.11.0/release/
v3.11.0/debug/
...
v3.14.6/source/
v3.14.6/release/
v3.14.6/debug/
retrace-libpython-manifest.json
```

It can therefore be extracted directly into a consumer's `build/` directory.

Install the bundle into a different root and validate its relocated
interpreters:

```bash
make install PRODUCER_VERSION=0.2.0 DESTINATION=/path/to/retrace-eval/build
```

Each installed mode provides:

- `python`: the raw CPython executable, suitable for symbol inspection;
- `python-relocatable`: a launcher that resolves the bundled standard library
  and native modules relative to the installed artifact;
- `libpython.a`, `pyconfig.h`, generated build metadata, and native standard
  library modules.

The bundle deliberately excludes CPython object files and all Retrace overlay,
transformation, filtering, and extension outputs.

## GHCR

Install `oras`, authenticate to GHCR, and publish or fetch the immutable
identity derived from the producer version, platform, architecture, and
profile. The identity does not contain a CPython patch because the single
bundle contains the complete checked-in matrix:

```bash
make push PRODUCER_VERSION=0.2.0
make pull PRODUCER_VERSION=0.2.0
```

An existing concrete tag is never replaced. Registry transport is optional;
all build, pack, verify, and install operations work locally.
