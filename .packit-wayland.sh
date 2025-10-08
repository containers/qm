#!/usr/bin/env bash

# Packit script for qm-wayland package
# This script handles custom processing of the qm-wayland spec file

set -eo pipefail

# Set path to rpm spec file
SPEC_FILE=rpm/wayland/qm-wayland.spec

# Get Version from wayland spec file (independent versioning)
WAYLAND_VERSION=$(grep '^Version:' ${SPEC_FILE} | awk '{print $2}')

echo "Building qm-wayland package version: ${WAYLAND_VERSION}"

# Generate source tarball using git archive
# Create a tarball with only the wayland subsystem files
git archive --prefix="qm-wayland-${WAYLAND_VERSION}/" -o "rpm/wayland/qm-wayland-${WAYLAND_VERSION}.tar.gz" HEAD \
    subsystems/wayland/ \
    rpm/wayland/qm-wayland.spec \
    SECURITY.md \
    LICENSE

echo "Source tarball created: rpm/wayland/qm-wayland-${WAYLAND_VERSION}.tar.gz"

# RPM Spec modifications

# Update Release in spec with Packit's release envvar (only the first occurrence)
sed -i "0,/^Release:.*/{s/^Release:.*/Release: ${PACKIT_RPMSPEC_RELEASE}%{?dist}/}" ${SPEC_FILE}

# Update Source tarball name in spec to match what Packit expects
sed -i "s/^Source0:.*/Source0: %{name}-${WAYLAND_VERSION}.tar.gz/" ${SPEC_FILE}

echo "qm-wayland package preparation completed"
