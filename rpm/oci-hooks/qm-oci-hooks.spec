%global debug_package %{nil}

# Define path macro for QM rootfs
%global qm_rootfs_prefix /usr/lib/qm/rootfs

Name: qm-oci-hooks
Version: %{version}
Release: 1%{?dist}
Summary: OCI hooks for QM containers
License: GPL-2.0-only
URL: https://github.com/containers/qm
Source0: %{url}/archive/qm-oci-hooks-%{version}.tar.gz
BuildArch: noarch

# Runtime dependencies
Requires: qm >= %{version}
Requires: jq

%description
This subpackage provides OCI hooks for QM containers that enable dynamic
device access and Wayland display server integration. The hooks are installed
both on the host system and inside the QM rootfs to support nested containers.

Included hooks:
- qm-device-manager: Dynamic device mounting based on container annotations
- wayland-client-devices: GPU hardware acceleration for Wayland clients

The hooks are available in two locations:
- Host system: /usr/libexec/oci/hooks.d/ and /usr/share/containers/oci/hooks.d/
- QM rootfs: /usr/lib/qm/rootfs/usr/libexec/oci/hooks.d/ and /usr/lib/qm/rootfs/usr/share/containers/oci/hooks.d/

%prep
%autosetup -Sgit -n qm-oci-hooks-%{version}

%build
# No build required for OCI hooks

%install
# Create OCI hook directories
install -d %{buildroot}%{_libexecdir}/oci/hooks.d
install -d %{buildroot}%{_libexecdir}/oci/lib
install -d %{buildroot}%{_datadir}/containers/oci/hooks.d

# Note: QM rootfs directories (/usr/lib/qm/rootfs/*) are handled by ghost directories in main qm package
# We only need to create the specific directories we're installing into
install -d %{buildroot}%{qm_rootfs_prefix}%{_libexecdir}/oci/hooks.d
install -d %{buildroot}%{qm_rootfs_prefix}%{_libexecdir}/oci/lib
install -d %{buildroot}%{qm_rootfs_prefix}%{_datadir}/containers/oci/hooks.d

# Install QM Device Manager hook
install -m 755 %{_builddir}/qm-oci-hooks-%{version}/oci-hooks/qm-device-manager/oci-qm-device-manager \
    %{buildroot}%{_libexecdir}/oci/hooks.d/oci-qm-device-manager
install -m 644 %{_builddir}/qm-oci-hooks-%{version}/oci-hooks/qm-device-manager/oci-qm-device-manager.json \
    %{buildroot}%{_datadir}/containers/oci/hooks.d/oci-qm-device-manager.json
install -m 755 %{_builddir}/qm-oci-hooks-%{version}/oci-hooks/qm-device-manager/oci-qm-device-manager \
    %{buildroot}%{qm_rootfs_prefix}%{_libexecdir}/oci/hooks.d/oci-qm-device-manager
install -m 644 %{_builddir}/qm-oci-hooks-%{version}/oci-hooks/qm-device-manager/oci-qm-device-manager.json \
    %{buildroot}%{qm_rootfs_prefix}%{_datadir}/containers/oci/hooks.d/oci-qm-device-manager.json

# Install Wayland Client Devices hook
install -m 755 %{_builddir}/qm-oci-hooks-%{version}/oci-hooks/wayland-client-devices/oci-qm-wayland-client-devices \
    %{buildroot}%{_libexecdir}/oci/hooks.d/oci-qm-wayland-client-devices
install -m 644 %{_builddir}/qm-oci-hooks-%{version}/oci-hooks/wayland-client-devices/oci-qm-wayland-client-devices.json \
    %{buildroot}%{_datadir}/containers/oci/hooks.d/oci-qm-wayland-client-devices.json
install -m 755 %{_builddir}/qm-oci-hooks-%{version}/oci-hooks/wayland-client-devices/oci-qm-wayland-client-devices \
    %{buildroot}%{qm_rootfs_prefix}%{_libexecdir}/oci/hooks.d/oci-qm-wayland-client-devices
install -m 644 %{_builddir}/qm-oci-hooks-%{version}/oci-hooks/wayland-client-devices/oci-qm-wayland-client-devices.json \
    %{buildroot}%{qm_rootfs_prefix}%{_datadir}/containers/oci/hooks.d/oci-qm-wayland-client-devices.json

# Install common libraries
install -m 644 %{_builddir}/qm-oci-hooks-%{version}/oci-hooks/lib/common.sh \
    %{buildroot}%{_libexecdir}/oci/lib/common.sh
install -m 644 %{_builddir}/qm-oci-hooks-%{version}/oci-hooks/lib/device-support.sh \
    %{buildroot}%{_libexecdir}/oci/lib/device-support.sh
install -m 644 %{_builddir}/qm-oci-hooks-%{version}/oci-hooks/lib/common.sh \
    %{buildroot}%{qm_rootfs_prefix}%{_libexecdir}/oci/lib/common.sh
install -m 644 %{_builddir}/qm-oci-hooks-%{version}/oci-hooks/lib/device-support.sh \
    %{buildroot}%{qm_rootfs_prefix}%{_libexecdir}/oci/lib/device-support.sh

# Create documentation directory and install component-specific README files with unique names
install -d %{buildroot}%{_docdir}/qm-oci-hooks
install -m 644 %{_builddir}/qm-oci-hooks-%{version}/oci-hooks/qm-device-manager/README.md \
    %{buildroot}%{_docdir}/qm-oci-hooks/README-qm-device-manager.md
install -m 644 %{_builddir}/qm-oci-hooks-%{version}/oci-hooks/wayland-client-devices/README.md \
    %{buildroot}%{_docdir}/qm-oci-hooks/README-wayland-client-devices.md

%files
%license LICENSE
%doc CODE-OF-CONDUCT.md README.md SECURITY.md
%{_docdir}/qm-oci-hooks/README-qm-device-manager.md
%{_docdir}/qm-oci-hooks/README-wayland-client-devices.md

# OCI hook executables and libraries (host system)
%dir %{_libexecdir}/oci
%dir %{_libexecdir}/oci/hooks.d
%dir %{_libexecdir}/oci/lib
%{_libexecdir}/oci/hooks.d/oci-qm-device-manager
%{_libexecdir}/oci/hooks.d/oci-qm-wayland-client-devices
%{_libexecdir}/oci/lib/common.sh
%{_libexecdir}/oci/lib/device-support.sh

# OCI hook configurations (host system)
%dir %{_datadir}/containers/oci
%dir %{_datadir}/containers/oci/hooks.d
%{_datadir}/containers/oci/hooks.d/oci-qm-device-manager.json
%{_datadir}/containers/oci/hooks.d/oci-qm-wayland-client-devices.json

# OCI hook executables and libraries (QM rootfs for nested containers)
%{qm_rootfs_prefix}%{_libexecdir}/oci/hooks.d/oci-qm-device-manager
%{qm_rootfs_prefix}%{_libexecdir}/oci/hooks.d/oci-qm-wayland-client-devices
%{qm_rootfs_prefix}%{_libexecdir}/oci/lib/common.sh
%{qm_rootfs_prefix}%{_libexecdir}/oci/lib/device-support.sh

# OCI hook configurations (QM rootfs for nested containers)
%{qm_rootfs_prefix}%{_datadir}/containers/oci/hooks.d/oci-qm-device-manager.json
%{qm_rootfs_prefix}%{_datadir}/containers/oci/hooks.d/oci-qm-wayland-client-devices.json

%changelog
* Fri Jul 21 2023 RH Container Bot <rhcontainerbot@fedoraproject.org>
- Initial release of consolidated QM OCI hooks package
