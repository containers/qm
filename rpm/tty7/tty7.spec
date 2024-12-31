Name: qm-mount-bind-tty7
Version: 0.6.8
Release: 1%{?dist}
Summary: Drop-in configuration for QM containers to mount bind /dev/tty7
License: GPL-2.0-only
URL: https://github.com/containers/qm
Source0: %{url}/archive/v%{version}.tar.gz

BuildArch: noarch
Requires: qm = %{version}-%{release}

%description
This subpackage installs a drop-in configuration for QM containers to mount bind `/dev/tty7`.
`/dev/tty7` is typically associated with the virtual terminal running the GUI session on Linux systems.
This configuration is useful when graphical applications require access to the host’s GUI display server.

%prep
%autosetup -Sgit -n qm-%{version}

%build
# No build required for configuration files

%install
# Create the required directory structure
install -d %{buildroot}%{_sysconfdir}/containers/containers.conf.d
install -d %{buildroot}%{_sysconfdir}/qm/containers/containers.conf.d

# Install the configuration files
install -m 644 etc/qm/containers/containers.conf.d/qm_dropin_mount_bind_tty7.conf \
    %{buildroot}%{_sysconfdir}/qm/containers/containers.conf.d/qm_dropin_mount_bind_tty7.conf
install -m 644 etc/qm/containers/containers.conf.d/qm_dropin_mount_bind_tty7.conf \
    %{buildroot}%{_sysconfdir}/containers/containers.conf.d/qm_dropin_mount_bind_tty7.conf

%files
%{_sysconfdir}/containers/containers.conf.d/qm_dropin_mount_bind_tty7.conf
%{_sysconfdir}/qm/containers/containers.conf.d/qm_dropin_mount_bind_tty7.conf

%changelog
* Fri Jul 21 2023 RH Container Bot <rhcontainerbot@fedoraproject.org>
- Added drop-in configuration to mount bind /dev/tty7.
