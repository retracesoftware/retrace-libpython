# retrace-libpython

Builds exact-patch CPython prerequisite bundles for Retrace. The producer owns
the CPython compiler/configuration profile; it does not contain Retrace overlay
sources or build `_retrace`.

The producer contains no supported CPython version list. Exact tags are inputs,
so a new CPython patch release requires no source change here. One immutable
artifact contains one exact patch in both release and debug modes. Consumers
download and extract the exact artifacts they need.

## Build

```bash
make build PYTHON_TAG=v3.12.8 BUILD_MODE=release \
  CPYTHON_REPO_URL=file:///opt/cpython.git
make build PYTHON_TAG=v3.12.8 BUILD_MODE=debug \
  CPYTHON_REPO_URL=file:///opt/cpython.git
make build-all PYTHON_TAG=v3.12.8 \
  CPYTHON_REPO_URL=file:///opt/cpython.git
```

Each mode has an independent out-of-tree build under
`build/v<version>/<mode>/`. The pristine exact-tag checkout is shared at
`build/v<version>/source/`.

## Artifacts

Create and verify a deterministic, maximum-compression XZ bundle containing
pristine source and both build modes for one exact tag:

```bash
make pack verify PYTHON_TAG=v3.12.8 PRODUCER_VERSION=0.2.0
```

The archive has no `build/` wrapper. Its entries are directly rooted at patch
directories:

```text
v3.12.8/source/
v3.12.8/release/
v3.12.8/debug/
retrace-libpython-manifest.json
```

It can therefore be extracted directly into a consumer's `build/` directory.

Install the bundle into a different root and validate its relocated
interpreters:

```bash
make install PYTHON_TAG=v3.12.8 PRODUCER_VERSION=0.2.0 \
  DESTINATION=/path/to/retrace-eval/build
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
identity derived from the producer version, exact CPython tag, platform,
architecture, and profile:

```bash
make push PYTHON_TAG=v3.12.8 PRODUCER_VERSION=0.2.0
make pull PYTHON_TAG=v3.12.8 PRODUCER_VERSION=0.2.0
```

An existing concrete tag is never replaced. Registry transport is optional;
all build, pack, verify, and install operations work locally.

The artifact workflow accepts one exact `python_tag` and an optional target
platform. Exact artifacts remain immutable and are the only bundles this
repository produces.

## Workflows

`artifacts.yml` receives one final tag such as `v3.14.5` and produces one
immutable exact artifact per architecture. Consumers needing multiple patch
releases pull those exact artifacts independently and extract each into the
same `build/` directory.

Publishing requires dispatching from a `retrace-libpython` release tag.
Pushing a producer release tag runs `refresh-series.yml`, which dispatches the
separate `retrace-libpython-series` aggregator for that producer version. The
repository secret `RETRACE_LIBPYTHON_SERIES_TOKEN` must be able to run workflows
in `retracesoftware/retrace-libpython-series`.
