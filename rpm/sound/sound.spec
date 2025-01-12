%global debug_package %{nil}

# Define the rootfs macros
%global rootfs_qm %{_prefix}/lib/qm/rootfs/

Name: qm-mount-bind-sound
Version: 0
Release: 1%{?dist}
Summary: Drop-in configuration for QM containers to mount bind /dev/snd
License: GPL-2.0-only
URL: https://github.com/containers/qm
Source0: %{url}/archive/v%{version}.tar.gz
BuildArch: noarch

Requires: qm = %{version}-%{release}

%description
This subpackage installs a drop-in configuration for QM containers,
enabling the mount bind of the audio device `/dev/snd` from the host to
the container and nested containers.

%prep
%autosetup -Sgit -n qm-%{version}

%build
# No build necessary for this configuration package

%install
# Install drop-in configuration for /dev/snd
install -d %{buildroot}%{_sysconfdir}/containers/containers.conf.d
install -d %{buildroot}%{_sysconfdir}/qm/containers/containers.conf.d
install -d %{buildroot}%{rootfs_qm}%{_sysconfdir}/containers/systemd

install -m 644 etc/qm/containers/containers.conf.d/qm_dropin_mount_bind_snd.conf %{buildroot}%{_sysconfdir}/containers/containers.conf.d/qm_dropin_mount_bind_snd.conf
install -m 644 etc/qm/containers/containers.conf.d/qm_dropin_mount_bind_snd.conf %{buildroot}%{_sysconfdir}/qm/containers/containers.conf.d/qm_dropin_mount_bind_snd.conf
install -m 644 subsystems/sound/etc/containers/systemd/audio.container %{buildroot}%{rootfs_qm}%{_sysconfdir}/containers/systemd/audio.container

%files
%license LICENSE
%doc CODE-OF-CONDUCT.md README.md SECURITY.md
%{_sysconfdir}/containers/containers.conf.d/qm_dropin_mount_bind_snd.conf
%{_sysconfdir}/qm/containers/containers.conf.d/qm_dropin_mount_bind_snd.conf
%{rootfs_qm}%{_sysconfdir}/containers/systemd/audio.container

%changelog
* Fri Jul 21 2023 RH Container Bot <rhcontainerbot@fedoraproject.org>
- Initial release focused on enabling mount bind for /dev/snd in QM environments.
