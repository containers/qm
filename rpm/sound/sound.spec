%global debug_package %{nil}

# Define the rootfs macros
%global rootfs_qm %{_prefix}/lib/qm/rootfs/

Name: qm-sound
Version: 0
Release: 1%{?dist}
Summary: Drop-in configuration for QM containers to mount bind /dev/snd
License: GPL-2.0-only
URL: https://github.com/containers/qm
Source0: %{url}/archive/qm-sound-%{version}.tar.gz
BuildArch: noarch

Requires: qm = %{version}-%{release}

%description
This subpackage installs a drop-in configuration for QM containers,
enabling the mount bind of the audio device `/dev/snd` from the host to
the container and nested containers.

%prep
%autosetup -Sgit -n qm-sound-%{version}

%build
# No build necessary for this configuration package

%install
# Install drop-in configuration for /dev/snd
# Create the directory for drop-in configurations
install -d %{buildroot}%{_sysconfdir}/containers/systemd/qm.container.d
install -d %{buildroot}%{rootfs_qm}%{_sysconfdir}/containers/systemd

install -m 644 %{_builddir}/qm-sound-%{version}/subsystems/sound/etc/containers/systemd/audio.container %{buildroot}%{rootfs_qm}%{_sysconfdir}/containers/systemd/audio.container
# Install the sound drop-in configuration file
install -m 644 %{_builddir}/qm-sound-%{version}/etc/containers/systemd/qm.container.d/qm_dropin_mount_bind_snd.conf \
    %{buildroot}%{_sysconfdir}/containers/systemd/qm.container.d/qm_dropin_mount_bind_snd.conf

%files
%license LICENSE
%doc README.md SECURITY.md
%{_sysconfdir}/containers/systemd/qm.container.d/qm_dropin_mount_bind_snd.conf
%{rootfs_qm}%{_sysconfdir}/containers/systemd/audio.container

%changelog
* Fri Jul 21 2023 RH Container Bot <rhcontainerbot@fedoraproject.org>
- Initial release focused on enabling mount bind for /dev/snd in QM environments.
