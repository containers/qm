%global debug_package %{nil}

Name: qm-mount-bind-tty7
Version: 0
Release: 1%{?dist}
Summary: Drop-in configuration for QM containers to mount bind /dev/tty7
License: GPL-2.0-only
URL: https://github.com/containers/qm
Source0: %{url}/archive/qm-tty7-%{version}.tar.gz

BuildArch: noarch
Requires: qm >= %{version}

%description
This subpackage installs a drop-in configuration for QM containers to mount bind `/dev/tty7`.
`/dev/tty7` is typically associated with the virtual terminal running the GUI session on Linux systems.
This configuration is useful when graphical applications require access to the host’s GUI display server.

%prep
%autosetup -Sgit -n qm-tty7-%{version}

%build
# No build required for configuration files

%install
# Create the directory for drop-in configurations
install -d %{buildroot}%{_sysconfdir}/containers/systemd/qm.container.d

# Install the KVM drop-in configuration file
install -m 644 %{_builddir}/qm-tty7-%{version}/etc/containers/systemd/qm.container.d/qm_dropin_mount_bind_tty7.conf \
    %{buildroot}%{_sysconfdir}/containers/systemd/qm.container.d/qm_dropin_mount_bind_tty7.conf

%files
%license LICENSE
%doc README.md SECURITY.md
%{_sysconfdir}/containers/systemd/qm.container.d/qm_dropin_mount_bind_tty7.conf

%changelog
* Fri Jul 21 2023 RH Container Bot <rhcontainerbot@fedoraproject.org>
- Added drop-in configuration to mount bind /dev/tty7.
