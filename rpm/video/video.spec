%global debug_package %{nil}

# Define the rootfs macros
%define qm_sysconfdir %{_sysconfdir}/qm

Name: qm-mount-bind-video
Version: %{version}
Release: 1%{?dist}
Summary: Drop-in configuration for QM containers to mount bind /dev/video
License: GPL-2.0-only
URL: https://github.com/containers/qm
Source0: %{url}/archive/qm-video-%{version}.tar.gz

BuildArch: noarch
Requires: qm >= %{version}

%description
This subpackage installs a drop-in configuration for QM containers to mount bind `/dev/video`.

%prep
%autosetup -Sgit -n qm-video-%{version}

%build
# No build required for configuration files

%install
# Create the directory for drop-in configurations
install -d %{buildroot}%{_datadir}/qm/qmc.conf.d
install -d %{buildroot}%{qm_sysconfdir}/containers/systemd

install -m 644 %{_builddir}/qm-video-%{version}/subsystems/video/etc/containers/systemd/rear-camera.container \
     %{buildroot}%{qm_sysconfdir}/containers/systemd/rear-camera.container

install -m 644 %{_builddir}/qm-video-%{version}/data/qmc.conf.d/60-qm-video.conf \
    %{buildroot}%{_datadir}/qm/qmc.conf.d/60-qm-video.conf

%files
%license LICENSE
%doc README.md SECURITY.md
%{_datadir}/qm/qmc.conf.d/60-qm-video.conf
%{qm_sysconfdir}/containers/systemd/rear-camera.container

%changelog
* Fri Jul 21 2023 RH Container Bot <rhcontainerbot@fedoraproject.org>
- Added video mount bind drop-in configuration.

