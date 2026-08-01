# retrace-libpython

Builds exact-patch CPython prerequisite bundles for Retrace. The producer owns
the CPython compiler/configuration profile; it does not contain Retrace overlay
sources or build `_retrace`.

The producer contains no supported CPython version list. Exact tags are inputs,
so a new CPython patch release requires no source change here. One immutable
artifact contains one exact patch in both release and debug modes; range
artifacts compose existing exact artifacts.

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

The exact-artifact workflow accepts `python_tag`. A separate range workflow
accepts two tags in one minor series and composes the inclusive sequence,
building only exact artifacts that are absent from GHCR.

## Workflows

`artifacts.yml` receives one final tag such as `v3.14.5` and produces one
immutable exact artifact per architecture. `range.yml` receives inclusive
`first_python_tag` and `last_python_tag` endpoints from the same minor series.
It probes every exact artifact in that sequence, builds and publishes only
missing exact artifacts, and then composes one range artifact per architecture.

Publishing requires dispatching from a `retrace-libpython` release tag. Range
manifests record the OCI reference, immutable manifest digest, and archive
checksum of every exact source artifact.
