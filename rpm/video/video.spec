Name: qm-mount-bind-video
Version: 0
Release: 1%{?dist}
Summary: Drop-in configuration for QM containers to mount bind /dev/video
License: GPL-2.0-only
URL: https://github.com/containers/qm
Source0: %{url}/archive/v%{version}.tar.gz

BuildArch: noarch
Requires: qm = %{version}-%{release}

%description
This subpackage installs a drop-in configuration for QM containers to mount bind `/dev/video`.

%prep
%autosetup -Sgit -n qm-%{version}

%build
# No build required for configuration files

%install
install -d %{buildroot}%{_sysconfdir}/qm/containers/containers.conf.d
install -d %{buildroot}%{_sysconfdir}/containers/systemd/
install -m 644 etc/qm/containers/containers.conf.d/qm_dropin_mount_bind_video.conf \
    %{buildroot}%{_sysconfdir}/qm/containers/containers.conf.d/qm_dropin_mount_bind_video.conf
install -m 644 etc/containers/systemd/rear-camera.container \
    %{buildroot}%{_sysconfdir}/containers/systemd/rear-camera.container

%files
%{_sysconfdir}/qm/containers/containers.conf.d/qm_dropin_mount_bind_video.conf
%{_sysconfdir}/containers/systemd/rear-camera.container

%changelog
* Fri Jul 21 2023 RH Container Bot <rhcontainerbot@fedoraproject.org>
- Added video mount bind drop-in configuration.

