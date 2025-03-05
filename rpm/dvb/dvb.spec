%global debug_package %{nil}

# Define the rootfs macros
%global rootfs_qm %{_prefix}/lib/qm/rootfs/

Name: qm-mount-bind-dvb
Version: 0
Release: 1%{?dist}
Summary: Drop-in configuration for QM containers to mount bind /dev/dvb
License: GPL-2.0-only
URL: https://github.com/containers/qm
Source0: %{url}/archive/qm-dvb-%{version}.tar.gz

BuildArch: noarch
Requires: qm >= %{version}

%description
This subpackage installs a drop-in configuration for QM containers to mount bind `/dev/dvb`.

%prep
%autosetup -Sgit -n qm-dvb-%{version}

%install
# Create the directory for drop-in configurations
install -d %{buildroot}%{_sysconfdir}/containers/systemd/qm.container.d

# Install the dvb drop-in configuration file
install -m 644 %{_builddir}/qm-video-%{version}/etc/containers/systemd/qm.container.d/qm_dropin_mount_bind_dvb.conf \
    %{buildroot}%{_sysconfdir}/containers/systemd/qm.container.d/qm_dropin_mount_bind_dvb.conf


%files
%license LICENSE
%doc README.md SECURITY.md
%{_sysconfdir}/containers/systemd/qm.container.d/qm_dropin_mount_bind_dvb.conf

%changelog
* Fri Jul 21 2023 RH Container Bot <rhcontainerbot@fedoraproject.org>
- Added dvb mount bind drop-in configuration.

