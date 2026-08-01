# retrace-libpython

Builds exact-patch CPython prerequisite bundles for Retrace. The producer owns
the CPython compiler/configuration profile; it does not contain Retrace overlay
sources or build `_retrace`.

## Build

```bash
make build VERSION=3.12.8 BUILD_MODE=release \
  CPYTHON_REPO_URL=file:///opt/cpython.git
make build VERSION=3.12.8 BUILD_MODE=debug \
  CPYTHON_REPO_URL=file:///opt/cpython.git
make build-all VERSION=3.12.8 \
  CPYTHON_REPO_URL=file:///opt/cpython.git
```

Each mode has an independent out-of-tree build under
`build/v<version>/<mode>/`. The pristine exact-tag checkout is shared at
`build/v<version>/source/`.

## Artifacts

Create and verify a deterministic bundle containing pristine source and both
build modes:

```bash
make pack verify VERSION=3.12.8 PRODUCER_VERSION=0.1.0
```

Install the bundle into a different root and validate its relocated
interpreters:

```bash
make install VERSION=3.12.8 PRODUCER_VERSION=0.1.0 \
  DESTINATION=/tmp/retrace-libpython-3.12.8
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
identity derived from the producer version, CPython patch, platform, and
profile:

```bash
make push VERSION=3.12.8 PRODUCER_VERSION=0.1.0
make pull VERSION=3.12.8 PRODUCER_VERSION=0.1.0
```

An existing concrete tag is never replaced. Registry transport is optional;
all build, pack, verify, and install operations work locally.
