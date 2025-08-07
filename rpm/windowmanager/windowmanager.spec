# Define the rootfs macros
%define qm_sysconfdir %{_sysconfdir}/qm


Name: qm-windowmanager
Version: %{version}
Release: 1%{?dist}
Summary: Optional Window Manager for QM environment
License: GPL-2.0-only
URL: https://github.com/containers/qm
Source0: %{url}/archive/qm-windowmanager-%{version}.tar.gz
BuildArch: noarch

Requires: qm >= %{version}
Requires: qm-oci-hooks

%description
This sub-package installs an experimental window manager for the QM environment.

%prep
%autosetup -Sgit -n qm-windowmanager-%{version}

%install
# Create the directory for drop-in configurations
install -d  %{buildroot}/%{_sysconfdir}/pam.d/
install -d %{buildroot}%{_sysconfdir}/containers/systemd/qm.container.d
install -d %{buildroot}%{qm_sysconfdir}/containers/systemd

# Install the Window manager drop-in configuration file
install -m 644 %{_builddir}/qm-windowmanager-%{version}/etc/containers/systemd/qm.container.d/qm_dropin_mount_bind_window_manager.conf \
    %{buildroot}%{_sysconfdir}/containers/systemd/qm.container.d/qm_dropin_mount_bind_window_manager.conf
install -m 644 %{_builddir}/qm-windowmanager-%{version}/subsystems/windowmanager/etc/pam.d/wayland %{buildroot}/%{_sysconfdir}/pam.d/
install -m 644 %{_builddir}/qm-windowmanager-%{version}/subsystems/windowmanager/etc/containers/systemd/* %{buildroot}%{qm_sysconfdir}/containers/systemd/

%files
%license LICENSE
%doc README.md
%{_sysconfdir}/pam.d/wayland
%{_sysconfdir}/containers/systemd/qm.container.d/qm_dropin_mount_bind_window_manager.conf
%{qm_sysconfdir}/containers/systemd/gnome_mutter.container
%{qm_sysconfdir}/containers/systemd/session-activate.container
%{qm_sysconfdir}/containers/systemd/wayland-extra-devices.conf
%{qm_sysconfdir}/containers/systemd/weston_terminal.container

%changelog
* Fri Jul 21 2023 RH Container Bot <rhcontainerbot@fedoraproject.org>
- Added windowmanager mount bind drop-in configuration.
