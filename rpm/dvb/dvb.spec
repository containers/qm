Name: qm-mount-bind-dvb
Version: 0
Release: 1%{?dist}
Summary: Drop-in configuration for QM containers to mount bind /dev/dvb
License: GPL-2.0-only
URL: https://github.com/containers/qm
Source0: %{url}/archive/v%{version}.tar.gz

BuildArch: noarch
Requires: qm = %{version}-%{release}

%description
This subpackage installs a drop-in configuration for QM containers to mount bind `/dev/dvb`.

%prep
%autosetup -Sgit -n qm-%{version}

%install
install -d %{buildroot}%{_sysconfdir}/qm/containers/containers.conf.d
install -m 644 etc/qm/containers/containers.conf.d/qm_dropin_mount_bind_dvb.conf \
    %{buildroot}%{_sysconfdir}/qm/containers/containers.conf.d/

%files
%{_sysconfdir}/qm/containers/containers.conf.d/qm_dropin_mount_bind_dvb.conf

%changelog
* Fri Jul 21 2023 RH Container Bot <rhcontainerbot@fedoraproject.org>
- Added dvb mount bind drop-in configuration.

