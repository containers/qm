%global debug_package %{nil}

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
- wayland-session-devices: Wayland display server device access for multi-seat
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
install -d %{buildroot}%{_datadir}/containers/oci/hooks.d

# Note: QM rootfs directories (/usr/lib/qm/rootfs/*) are handled by ghost directories in main qm package
# We only need to create the specific directories we're installing into
install -d %{buildroot}/usr/lib/qm/rootfs%{_libexecdir}/oci/hooks.d
install -d %{buildroot}/usr/lib/qm/rootfs%{_datadir}/containers/oci/hooks.d

# Install QM Device Manager hook
install -m 755 %{_builddir}/qm-oci-hooks-%{version}/oci-hooks/qm-device-manager/oci-qm-device-manager \
    %{buildroot}%{_libexecdir}/oci/hooks.d/oci-qm-device-manager
install -m 644 %{_builddir}/qm-oci-hooks-%{version}/oci-hooks/qm-device-manager/oci-qm-device-manager.json \
    %{buildroot}%{_datadir}/containers/oci/hooks.d/oci-qm-device-manager.json
install -m 755 %{_builddir}/qm-oci-hooks-%{version}/oci-hooks/qm-device-manager/oci-qm-device-manager \
    %{buildroot}/usr/lib/qm/rootfs%{_libexecdir}/oci/hooks.d/oci-qm-device-manager
install -m 644 %{_builddir}/qm-oci-hooks-%{version}/oci-hooks/qm-device-manager/oci-qm-device-manager.json \
    %{buildroot}/usr/lib/qm/rootfs%{_datadir}/containers/oci/hooks.d/oci-qm-device-manager.json

# Install Wayland Session Devices hook
install -m 755 %{_builddir}/qm-oci-hooks-%{version}/oci-hooks/wayland-session-devices/oci-qm-wayland-session-devices \
    %{buildroot}%{_libexecdir}/oci/hooks.d/oci-qm-wayland-session-devices
install -m 644 %{_builddir}/qm-oci-hooks-%{version}/oci-hooks/wayland-session-devices/oci-qm-wayland-session-devices.json \
    %{buildroot}%{_datadir}/containers/oci/hooks.d/oci-qm-wayland-session-devices.json

# Install Wayland Client Devices hook
install -m 755 %{_builddir}/qm-oci-hooks-%{version}/oci-hooks/wayland-client-devices/oci-qm-wayland-client-devices \
    %{buildroot}%{_libexecdir}/oci/hooks.d/oci-qm-wayland-client-devices
install -m 644 %{_builddir}/qm-oci-hooks-%{version}/oci-hooks/wayland-client-devices/oci-qm-wayland-client-devices.json \
    %{buildroot}%{_datadir}/containers/oci/hooks.d/oci-qm-wayland-client-devices.json
install -m 755 %{_builddir}/qm-oci-hooks-%{version}/oci-hooks/wayland-client-devices/oci-qm-wayland-client-devices \
    %{buildroot}/usr/lib/qm/rootfs%{_libexecdir}/oci/hooks.d/oci-qm-wayland-client-devices
install -m 644 %{_builddir}/qm-oci-hooks-%{version}/oci-hooks/wayland-client-devices/oci-qm-wayland-client-devices.json \
    %{buildroot}/usr/lib/qm/rootfs%{_datadir}/containers/oci/hooks.d/oci-qm-wayland-client-devices.json

# Create documentation directory and install component-specific README files with unique names
install -d %{buildroot}%{_docdir}/qm-oci-hooks
install -m 644 %{_builddir}/qm-oci-hooks-%{version}/oci-hooks/qm-device-manager/README.md \
    %{buildroot}%{_docdir}/qm-oci-hooks/README-qm-device-manager.md
install -m 644 %{_builddir}/qm-oci-hooks-%{version}/oci-hooks/wayland-session-devices/README.md \
    %{buildroot}%{_docdir}/qm-oci-hooks/README-wayland-session-devices.md
install -m 644 %{_builddir}/qm-oci-hooks-%{version}/oci-hooks/wayland-client-devices/README.md \
    %{buildroot}%{_docdir}/qm-oci-hooks/README-wayland-client-devices.md

%files
%license LICENSE
%doc CODE-OF-CONDUCT.md README.md SECURITY.md
%{_docdir}/qm-oci-hooks/README-qm-device-manager.md
%{_docdir}/qm-oci-hooks/README-wayland-session-devices.md
%{_docdir}/qm-oci-hooks/README-wayland-client-devices.md

# OCI hook executables (host system)
%dir %{_libexecdir}/oci
%dir %{_libexecdir}/oci/hooks.d
%{_libexecdir}/oci/hooks.d/oci-qm-device-manager
%{_libexecdir}/oci/hooks.d/oci-qm-wayland-session-devices
%{_libexecdir}/oci/hooks.d/oci-qm-wayland-client-devices

# OCI hook configurations (host system)
%dir %{_datadir}/containers/oci
%dir %{_datadir}/containers/oci/hooks.d
%{_datadir}/containers/oci/hooks.d/oci-qm-device-manager.json
%{_datadir}/containers/oci/hooks.d/oci-qm-wayland-session-devices.json
%{_datadir}/containers/oci/hooks.d/oci-qm-wayland-client-devices.json

# OCI hook executables (QM rootfs for nested containers)
/usr/lib/qm/rootfs%{_libexecdir}/oci/hooks.d/oci-qm-device-manager
/usr/lib/qm/rootfs%{_libexecdir}/oci/hooks.d/oci-qm-wayland-client-devices

# OCI hook configurations (QM rootfs for nested containers)
/usr/lib/qm/rootfs%{_datadir}/containers/oci/hooks.d/oci-qm-device-manager.json
/usr/lib/qm/rootfs%{_datadir}/containers/oci/hooks.d/oci-qm-wayland-client-devices.json

%changelog
* Fri Jul 21 2023 RH Container Bot <rhcontainerbot@fedoraproject.org>
- Initial release of consolidated QM OCI hooks package
