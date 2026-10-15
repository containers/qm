# SPDX-License-Identifier: GPL-2.0-only
.DEFAULT_GOAL := help
BUILDDIR ?= build
PREFIX ?= /usr
DATADIR ?= $(PREFIX)/share
SYSCONFDIR ?= /etc
DESTDIR ?=
VERSION ?= $(shell cat VERSION)
RPM_TOPDIR ?= $(CURDIR)/rpmbuild
ROOTDIR ?= $(CURDIR)
TARGETS ?= qm
PACKIT_SUBPACKAGES := wayland qm-oci-hooks
FILTERED_TARGETS := $(filter-out $(PACKIT_SUBPACKAGES),$(TARGETS))

.PHONY: help all install clean man selinux file_contexts dist rpm subpackages install-policy codespell
help:
	@echo 'Build: make all; install: make install DESTDIR=...; packages: make rpm'
	@echo 'Subsystems: make TARGETS=kvm subpackages'

$(BUILDDIR)/build.ninja:
	meson setup $(BUILDDIR) --prefix=$(PREFIX) --datadir=$(DATADIR) --sysconfdir=$(SYSCONFDIR)

all: $(BUILDDIR)/build.ninja
	meson compile -C $(BUILDDIR)

man selinux file_contexts: all

install: all
	DESTDIR=$(DESTDIR) meson install -C $(BUILDDIR)

clean:
	@if test -f $(BUILDDIR)/build.ninja; then meson compile -C $(BUILDDIR) --clean; fi

dist:
	mkdir -p rpm
	@set -e; archive=$$(mktemp); trap 'rm -f "$$archive"' EXIT; \
	  tar --exclude-vcs --exclude='./build' --exclude='./rpmbuild' \
	    --exclude='*.tar.gz' --exclude='__pycache__' \
	    --transform 's|^\./|qm-$(VERSION)/|' -czf "$$archive" .; \
	  mv "$$archive" rpm/qm-$(VERSION).tar.gz

rpm: dist
	mkdir -p $(RPM_TOPDIR)/SOURCES $(BUILDDIR)
	cp rpm/qm-$(VERSION).tar.gz $(RPM_TOPDIR)/SOURCES/
	sed 's/^Version:.*/Version: $(VERSION)/' rpm/qm.spec > $(BUILDDIR)/qm.spec
	rpmbuild -ba --define '_topdir $(abspath $(RPM_TOPDIR))' $(BUILDDIR)/qm.spec

subpackages: $(FILTERED_TARGETS)
$(FILTERED_TARGETS):
	$(MAKE) -f subsystems/$@/Makefile $@

install-policy: all
	semodule -i $(BUILDDIR)/qm.pp.bz2

codespell:
	codespell -S build,tmp,.git -L te -w
