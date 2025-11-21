#!/usr/bin/env bash

# Packit script for qm-oci-hooks package
# This script handles custom processing of the qm-oci-hooks spec file

set -eo pipefail

# Set path to rpm spec file
SPEC_FILE=rpm/oci-hooks/qm-oci-hooks.spec

# Get Version from oci-hooks spec file (independent versioning)
OCI_HOOKS_VERSION=$(grep '^Version:' ${SPEC_FILE} | awk '{print $2}')

echo "Building qm-oci-hooks package version: ${OCI_HOOKS_VERSION}"

# Generate source tarball using git archive
git archive --prefix="qm-oci-hooks-${OCI_HOOKS_VERSION}/" -o "rpm/oci-hooks/qm-oci-hooks-${OCI_HOOKS_VERSION}.tar.gz" HEAD \
    oci-hooks/ \
    SECURITY.md \
    LICENSE \
    CODE-OF-CONDUCT.md \
    README.md

echo "Source tarball created: rpm/oci-hooks/qm-oci-hooks-${OCI_HOOKS_VERSION}.tar.gz"

# RPM Spec modifications

# Update Release in spec with Packit's release envvar (only the first occurrence)
sed -i "0,/^Release:.*/{s/^Release:.*/Release: ${PACKIT_RPMSPEC_RELEASE}%{?dist}/}" ${SPEC_FILE}

# Update Source tarball name in spec to match what Packit expects
sed -i "s/^Source0:.*/Source0: %{name}-${OCI_HOOKS_VERSION}.tar.gz/" ${SPEC_FILE}

echo "qm-oci-hooks package preparation completed"
