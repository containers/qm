#!/usr/bin/env bash

# Packit's default fix-spec-file often doesn't fetch version string correctly.
# This script handles any custom processing of the dist-git spec file and gets used by the
# fix-spec-file action in .packit.yaml

set -eo pipefail

# Set path to rpm spec file
SPEC_FILE=rpm/qm.spec

# Get Version from HEAD
HEAD_VERSION=$(grep '^policy_module' qm.te | sed 's/[^0-9.]//g')

# Check version consistency in qm.te and VERSION before proceeding
if [[ $(cat VERSION) != "${HEAD_VERSION}" ]]; then
    echo "Inconsistent versions mentioned in VERSION and qm.te files. Investigate!"
    echo "Aborting Packit tasks!"
    exit 1
fi

# Generate source tarball
git archive --prefix="qm-${HEAD_VERSION}/" -o "rpm/qm-${HEAD_VERSION}.tar.gz" HEAD

# RPM Spec modifications

# Update Version in spec with Version from qm.te
sed -i "s/^Version:.*/Version: ${HEAD_VERSION}/" ${SPEC_FILE}

# Update Release in spec with Packit's release envvar
sed -i "s/^Release:.*/Release: ${PACKIT_RPMSPEC_RELEASE}%{?dist}/" ${SPEC_FILE}

# Update Source tarball name in spec
sed -i "s/^Source0:.*.tar.gz/Source0: %{name}-${HEAD_VERSION}.tar.gz/" ${SPEC_FILE}

# Add update create additional subpackages in spec
# Please refer `Let automation create/publish PR sub-packages` of docs/devel/README.md
