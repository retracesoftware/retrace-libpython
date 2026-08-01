# Build exact-patch CPython prerequisites for Retrace.

VERSION ?= 3.12.8
PROFILE ?= retrace-static-v1
BUILD_MODE ?= release
CPYTHON_REPO_URL ?= https://github.com/python/cpython.git
JOBS ?= $(shell getconf _NPROCESSORS_ONLN 2>/dev/null || echo 2)
PRODUCER_VERSION ?= dev
REGISTRY ?= ghcr.io/retracesoftware/retrace-libpython

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
ARTIFACT_NAME := retrace-libpython-$(PRODUCER_VERSION)-cpython-$(VERSION)-$(PLATFORM).tar.gz
ARTIFACT := $(ROOT)/dist/$(ARTIFACT_NAME)
REFERENCE := $(REGISTRY):$(PRODUCER_VERSION)-cpython-$(VERSION)-$(PLATFORM)-$(PROFILE)

ifeq ($(BUILD_MODE),release)
CPYTHON_CFLAGS := -O3
CONFIGURE_MODE_ARGS :=
else ifeq ($(BUILD_MODE),debug)
CPYTHON_CFLAGS := -Og -g3
CONFIGURE_MODE_ARGS := --with-pydebug
else
$(error BUILD_MODE must be release or debug, not '$(BUILD_MODE)')
endif

.PHONY: all build build-all pack verify install push pull test clean

all: build

build: $(METADATA)

build-all:
	$(MAKE) build VERSION=$(VERSION) BUILD_MODE=release
	$(MAKE) build VERSION=$(VERSION) BUILD_MODE=debug

pack: build-all
	python3 scripts/artifact pack --root $(VERSION_ROOT) \
	    --output $(ARTIFACT) --producer-version $(PRODUCER_VERSION)

verify: $(ARTIFACT)
	python3 scripts/artifact verify --archive $(ARTIFACT) --run

install: $(ARTIFACT)
	test -n "$(DESTINATION)"
	python3 scripts/artifact install --archive $(ARTIFACT) \
	    --destination $(DESTINATION) --run $(INSTALL_FLAGS)

push: verify
	scripts/registry push $(REFERENCE) $(ARTIFACT)

pull:
	mkdir -p $(dir $(ARTIFACT))
	scripts/registry pull $(REFERENCE) $(ARTIFACT)
	python3 scripts/artifact verify --archive $(ARTIFACT) --run

test:
	python3 -m unittest discover -s tests -v

$(SOURCE)/configure:
	mkdir -p $(VERSION_ROOT)
	git clone --depth 1 --branch v$(VERSION) $(CPYTHON_REPO_URL) $(SOURCE)

$(CONFIG_STAMP): $(SOURCE)/configure
	mkdir -p $(MODE_ROOT)
	cd $(MODE_ROOT) && $(SOURCE)/configure --without-ensurepip -q \
	    $(CONFIGURE_MODE_ARGS) CFLAGS="$(CPYTHON_CFLAGS)" \
	    CFLAGS_NODIST="-fPIC -ffunction-sections -fdata-sections"
	touch $@

$(PYTHON): $(CONFIG_STAMP)
	cd $(MODE_ROOT) && env MAKEFLAGS= $(MAKE) -j$(JOBS)

$(LIBPYTHON): $(PYTHON)
	set -- $(MODE_ROOT)/libpython$(PYMINOR)*.a; \
	test "$$#" -eq 1; cp "$$1" $@

$(METADATA): $(LIBPYTHON) scripts/write-metadata
	python3 scripts/write-metadata \
	    --source $(SOURCE) --build $(MODE_ROOT) --output $@ \
	    --version $(VERSION) --mode $(BUILD_MODE) --profile $(PROFILE) \
	    --cflags="$(CPYTHON_CFLAGS)" \
	    --configure-args="--without-ensurepip $(CONFIGURE_MODE_ARGS)" \
	    --cflags-nodist="-fPIC -ffunction-sections -fdata-sections"

$(ARTIFACT):
	$(MAKE) pack VERSION=$(VERSION) PRODUCER_VERSION=$(PRODUCER_VERSION)

clean:
	rm -rf $(VERSION_ROOT)
