Name: qm_mount_bind_ttyUSB0
Version: 0
Release: 1%{?dist}
Summary: Drop-in configuration for QM containers to mount bind ttyUSB0
License: GPL-2.0-only
URL: https://github.com/containers/qm
Source0: %{url}/archive/v%{version}.tar.gz
BuildArch: noarch

Requires: qm = %{version}-%{release}

%description
This sub-package installs drop-in configurations for QM containers to mount bind ttyUSB0.

%prep
%autosetup -Sgit -n qm-%{version}

%install
# Create the directory for drop-in configurations
install -d %{buildroot}%{_sysconfdir}/containers/systemd/qm.container.d

# Install the KVM drop-in configuration file
install -m 644 %{_builddir}/qm-%{version}/etc/containers/systemd/qm.container.d/qm_dropin_mount_bind_ttyUSB0.conf %{buildroot}%{_sysconfdir}/containers/systemd/qm.container.d/qm_dropin_mount_bind_ttyUSB0.conf

%files
%license LICENSE
%doc README.md
%{_sysconfdir}/containers/systemd/qm.container.d/qm_dropin_mount_bind_ttyUSB0.conf

%changelog
* Fri Jul 21 2023 RH Container Bot <rhcontainerbot@fedoraproject.org>
- Added ttyUSB0 mount bind drop-in configuration.
