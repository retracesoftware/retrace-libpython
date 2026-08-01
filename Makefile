# Build exact-patch CPython prerequisites for Retrace.

PYTHON_TAG ?= v3.12.8
VERSION := $(shell python3 scripts/python-tags exact $(PYTHON_TAG))
PROFILE ?= retrace-static-v1
BUILD_MODE ?= release
CPYTHON_REPO_URL ?= https://github.com/python/cpython.git
JOBS ?= $(shell getconf _NPROCESSORS_ONLN 2>/dev/null || echo 2)
PRODUCER_VERSION ?= $(shell git describe --tags --exact-match 2>/dev/null | sed 's/^v//' || git rev-parse --short=12 HEAD)
PRODUCER_COMMIT ?= $(shell git rev-parse HEAD)
REGISTRY ?= ghcr.io/retracesoftware/retrace-libpython
MACOSX_DEPLOYMENT_TARGET ?= 11.0

ROOT := $(CURDIR)
VERSION_ROOT := $(ROOT)/build/v$(VERSION)
SOURCE := $(VERSION_ROOT)/source
MODE_ROOT := $(VERSION_ROOT)/$(BUILD_MODE)
CONFIG_STAMP := $(MODE_ROOT)/.configured
PYTHON := $(MODE_ROOT)/python
LIBPYTHON := $(MODE_ROOT)/libpython.a
METADATA := $(MODE_ROOT)/retrace-libpython.json
PYMINOR := $(basename $(VERSION))
PLATFORM := $(shell python3 scripts/artifact platform-tag)
ARTIFACT_NAME := retrace-libpython-$(PRODUCER_VERSION)-cpython-$(VERSION)-$(PLATFORM)-$(PROFILE).tar.xz
ARTIFACT := $(ROOT)/dist/$(ARTIFACT_NAME)
REFERENCE := $(REGISTRY):$(PRODUCER_VERSION)-cpython-$(VERSION)-$(PLATFORM)-$(PROFILE)
HOST_SYSTEM := $(shell uname -s)

ifeq ($(HOST_SYSTEM),Darwin)
PLATFORM_BUILD_ENV := MACOSX_DEPLOYMENT_TARGET=$(MACOSX_DEPLOYMENT_TARGET)
METADATA_PLATFORM_ARGS := --deployment-target=$(MACOSX_DEPLOYMENT_TARGET)
else
PLATFORM_BUILD_ENV :=
METADATA_PLATFORM_ARGS :=
endif

ifeq ($(BUILD_MODE),release)
CPYTHON_CFLAGS := -O3
CONFIGURE_MODE_ARGS :=
else ifeq ($(BUILD_MODE),debug)
CPYTHON_CFLAGS := -Og -g3
CONFIGURE_MODE_ARGS := --with-pydebug
else
$(error BUILD_MODE must be release or debug, not '$(BUILD_MODE)')
endif

.PHONY: all build build-all prune-version pack pack-built verify install push pull print-artifact print-reference test clean

all: build

build: $(METADATA)

build-all:
	$(MAKE) build PYTHON_TAG=$(PYTHON_TAG) BUILD_MODE=release
	$(MAKE) build PYTHON_TAG=$(PYTHON_TAG) BUILD_MODE=debug

prune-version:
	find $(VERSION_ROOT)/release $(VERSION_ROOT)/debug -type f -name '*.o' -delete
	rm -f $(VERSION_ROOT)/release/_bootstrap_python \
	    $(VERSION_ROOT)/debug/_bootstrap_python
	find $(VERSION_ROOT)/release $(VERSION_ROOT)/debug -maxdepth 1 \
	    -type f -name 'libpython*.a' ! -name libpython.a -delete

pack: build-all prune-version
	$(MAKE) pack-built PYTHON_TAG=$(PYTHON_TAG) PRODUCER_VERSION=$(PRODUCER_VERSION)

pack-built:
	python3 scripts/artifact pack --root $(ROOT)/build --versions $(VERSION) \
	    --output $(ARTIFACT) --producer-version $(PRODUCER_VERSION) \
	    --producer-commit $(PRODUCER_COMMIT)

verify: $(ARTIFACT)
	python3 scripts/artifact verify --archive $(ARTIFACT) \
	    --versions $(VERSION) --run

install: $(ARTIFACT)
	test -n "$(DESTINATION)"
	python3 scripts/artifact install --archive $(ARTIFACT) \
	    --destination $(DESTINATION) --versions $(VERSION) \
	    --run $(INSTALL_FLAGS)

push: verify
	scripts/registry push $(REFERENCE) $(ARTIFACT)

pull:
	mkdir -p $(dir $(ARTIFACT))
	scripts/registry pull $(REFERENCE) $(ARTIFACT)
	python3 scripts/artifact verify --archive $(ARTIFACT) \
	    --versions $(VERSION) --run

print-artifact:
	@printf '%s\n' '$(ARTIFACT)'

print-reference:
	@printf '%s\n' '$(REFERENCE)'

test:
	python3 -m unittest discover -s tests -v

$(SOURCE)/configure:
	mkdir -p $(VERSION_ROOT)
	git clone --depth 1 --branch $(PYTHON_TAG) $(CPYTHON_REPO_URL) $(SOURCE)

$(CONFIG_STAMP): $(SOURCE)/configure
	mkdir -p $(MODE_ROOT)
	cd $(MODE_ROOT) && $(PLATFORM_BUILD_ENV) $(SOURCE)/configure --without-ensurepip -q \
	    $(CONFIGURE_MODE_ARGS) CFLAGS="$(CPYTHON_CFLAGS)" \
	    CFLAGS_NODIST="-fPIC -ffunction-sections -fdata-sections"
	touch $@

$(PYTHON): $(CONFIG_STAMP)
	cd $(MODE_ROOT) && env MAKEFLAGS= $(PLATFORM_BUILD_ENV) $(MAKE) -j$(JOBS)

$(LIBPYTHON): $(PYTHON)
	set -- $(MODE_ROOT)/libpython$(PYMINOR)*.a; \
	test "$$#" -eq 1; cp "$$1" $@

$(METADATA): $(LIBPYTHON) scripts/write-metadata
	python3 scripts/write-metadata \
	    --source $(SOURCE) --build $(MODE_ROOT) --output $@ \
	    --version $(VERSION) --mode $(BUILD_MODE) --profile $(PROFILE) \
	    --cflags="$(CPYTHON_CFLAGS)" \
	    --configure-args="--without-ensurepip $(CONFIGURE_MODE_ARGS)" \
	    --cflags-nodist="-fPIC -ffunction-sections -fdata-sections" \
	    $(METADATA_PLATFORM_ARGS)

$(ARTIFACT):
	$(MAKE) pack PYTHON_TAG=$(PYTHON_TAG) PRODUCER_VERSION=$(PRODUCER_VERSION)

clean:
	rm -rf $(VERSION_ROOT)
