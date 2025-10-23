%global debug_package %{nil}

Name: qm-oci-hooks
Version: 0.1.0
Release: 1%{?dist}
Summary: OCI hooks for QM containers
License: GPL-2.0-only
URL: https://github.com/containers/qm
Source0: %{url}/archive/qm-oci-hooks-%{version}.tar.gz
BuildArch: noarch
BuildRequires: git-core

# Runtime dependencies
Requires: jq
Requires: systemd-udev
Requires: findutils

%description
This package provides OCI hooks for QM containers that enable dynamic
device access and Wayland display server integration. The hooks are installed
in standard OCI hook locations and can be used in any container environment.
This package is independent and can be installed within the qm container.

Included hooks:
- qm-device-manager: Dynamic device mounting based on container annotations
- qm-seat-manager: Wayland seat device management for systemd-logind integration
- wayland-client-devices: GPU hardware acceleration for Wayland clients

The hooks are installed in standard locations:
- Executables: /usr/libexec/oci/hooks.d/
- Configurations: /usr/share/containers/oci/hooks.d/
- Libraries: /usr/libexec/oci/lib/

%prep
%autosetup -Sgit -n %{name}-%{version}

%build
# No build required for OCI hooks

%install
# Create OCI hook directories
install -d %{buildroot}%{_libexecdir}/oci/hooks.d
install -d %{buildroot}%{_libexecdir}/oci/lib
install -d %{buildroot}%{_datadir}/containers/oci/hooks.d

# Install QM Device Manager hook
install -m 755 oci-hooks/qm-device-manager/oci-qm-device-manager \
    %{buildroot}%{_libexecdir}/oci/hooks.d/oci-qm-device-manager
install -m 644 oci-hooks/qm-device-manager/oci-qm-device-manager.json \
    %{buildroot}%{_datadir}/containers/oci/hooks.d/oci-qm-device-manager.json

# Install QM Seat Manager hook
install -m 644 oci-hooks/qm-seat-manager/oci-qm-seat-manager.json \
    %{buildroot}%{_datadir}/containers/oci/hooks.d/oci-qm-seat-manager.json

# Install Wayland Client Devices hook
install -m 755 oci-hooks/wayland-client-devices/oci-qm-wayland-client-devices \
    %{buildroot}%{_libexecdir}/oci/hooks.d/oci-qm-wayland-client-devices
install -m 644 oci-hooks/wayland-client-devices/oci-qm-wayland-client-devices.json \
    %{buildroot}%{_datadir}/containers/oci/hooks.d/oci-qm-wayland-client-devices.json

# Install common libraries
install -m 644 oci-hooks/lib/common.sh \
    %{buildroot}%{_libexecdir}/oci/lib/common.sh
install -m 644 oci-hooks/lib/device-support.sh \
    %{buildroot}%{_libexecdir}/oci/lib/device-support.sh

# Create documentation directory and install component-specific README files with unique names
install -d %{buildroot}%{_docdir}/qm-oci-hooks
install -m 644 oci-hooks/qm-device-manager/README.md \
    %{buildroot}%{_docdir}/qm-oci-hooks/README-qm-device-manager.md
install -m 644 oci-hooks/wayland-client-devices/README.md \
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
%{_datadir}/containers/oci/hooks.d/oci-qm-seat-manager.json
%{_datadir}/containers/oci/hooks.d/oci-qm-wayland-client-devices.json


%changelog
* Fri Jul 21 2023 RH Container Bot <rhcontainerbot@fedoraproject.org>
- Initial release of consolidated QM OCI hooks package
