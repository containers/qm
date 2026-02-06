%global debug_package %{nil}

# copr_username is only set on copr environments, not on others like koji
%if "%{?copr_username}" != "centos-automotive-sig" && "%{?copr_projectname}" != "qm-next"
%bcond_with copr
%else
%bcond_without copr
%endif

Name: qm-wayland
# Set different Epochs for copr and koji
%if %{with copr}
Epoch: 101
%endif
Version: 0.1.0
%if %{defined autorelease}
Release: %autorelease
%else
Release: 1
%endif
License: GPL-2.0-only
URL: https://github.com/containers/qm
Summary: Wayland support for QM containerized environment
Source0: %{url}/archive/qm-wayland-%{version}.tar.gz
BuildArch: noarch
BuildRequires: make
BuildRequires: git-core
BuildRequires: pkgconfig(systemd)
BuildRequires: systemd-rpm-macros

Requires: systemd
Recommends: qm-oci-hooks

%description
This package provides Wayland display server support for the QM (Quality Management)
containerized environment. It includes systemd units, services, sockets, and
configuration files for managing Wayland user sessions within QM containers.

The package is independent of the main qm package and can be installed separately
to provide Wayland functionality.

%prep
%autosetup -Sgit -n qm-wayland-%{version}

%build

%install
# Install wayland script
install -d %{buildroot}%{_bindir}
install -m 755 subsystems/wayland/usr/bin/wayland-session %{buildroot}%{_bindir}/

# Install wayland and user session files
install -d %{buildroot}%{_sysconfdir}/containers/systemd
install -d %{buildroot}%{_sysconfdir}/containers/systemd/qm-dbus-broker.container.d
install -d %{buildroot}%{_sysconfdir}/containers/systemd/wayland-compositor.container.d
install -d %{buildroot}%{_unitdir}
install -d %{buildroot}%{_unitdir}/wayland-session.service.d
install -d %{buildroot}%{_sysconfdir}/pam.d
install -d %{buildroot}%{_sysconfdir}/weston
install -d %{buildroot}%{_presetdir}

install -m 644 subsystems/wayland/etc/containers/systemd/qm-dbus-broker.container %{buildroot}%{_sysconfdir}/containers/systemd/
install -m 644 subsystems/wayland/etc/containers/systemd/wayland-compositor.container %{buildroot}%{_sysconfdir}/containers/systemd/
install -m 644 subsystems/wayland/etc/systemd/system/* %{buildroot}%{_unitdir}/
install -m 644 subsystems/wayland/etc/pam.d/wayland-autologin %{buildroot}%{_sysconfdir}/pam.d/
# Install custom systemd-user PAM config with .qm-wayland suffix
install -m 644 subsystems/wayland/etc/pam.d/systemd-user %{buildroot}%{_sysconfdir}/pam.d/systemd-user.qm-wayland
install -m 644 subsystems/wayland/etc/weston/weston.ini %{buildroot}%{_sysconfdir}/weston/
install -m 644 subsystems/wayland/50-qm-wayland.preset %{buildroot}%{_presetdir}/

%post
# Backup original systemd-user PAM config and replace with our version
if [ "$1" -eq 1 ] || [ "$1" -eq 2 ]; then
    if [ ! -L "%{_sysconfdir}/pam.d/systemd-user" ]; then
        # Backup if it's a regular file and no backup exists yet
        if [ -f "%{_sysconfdir}/pam.d/systemd-user" ] && [ ! -f "%{_sysconfdir}/pam.d/systemd-user.rpmsave" ]; then
            cp -p "%{_sysconfdir}/pam.d/systemd-user" "%{_sysconfdir}/pam.d/systemd-user.rpmsave"
        fi
        cp -f "%{_sysconfdir}/pam.d/systemd-user.qm-wayland" "%{_sysconfdir}/pam.d/systemd-user"
    fi
fi
%systemd_post qm-dbus.socket
%systemd_post wayland.socket
%systemd_post wayland-session.service

%preun
%systemd_preun qm-dbus.socket
%systemd_preun wayland.socket
%systemd_preun wayland-session.service

%postun
# Restore original systemd-user PAM config on uninstall
if [ "$1" -eq 0 ]; then
    if [ -f "%{_sysconfdir}/pam.d/systemd-user.rpmsave" ]; then
        mv -f "%{_sysconfdir}/pam.d/systemd-user.rpmsave" "%{_sysconfdir}/pam.d/systemd-user"
    fi
fi
%systemd_postun qm-dbus.socket
%systemd_postun wayland.socket
%systemd_postun wayland-session.service

#define license tag if not already defined
%{!?_licensedir:%global license %doc}

%files
%license LICENSE
%doc subsystems/wayland/README.md
# Wayland directories
%dir %{_sysconfdir}/containers/systemd
%dir %{_sysconfdir}/containers/systemd/qm-dbus-broker.container.d
%dir %{_sysconfdir}/containers/systemd/wayland-compositor.container.d
%dir %{_sysconfdir}/pam.d
%dir %{_sysconfdir}/weston
%dir %{_unitdir}/wayland-session.service.d

# Wayland session script
%{_bindir}/wayland-session
# Wayland and user session files
%{_sysconfdir}/containers/systemd/qm-dbus-broker.container
%{_sysconfdir}/containers/systemd/wayland-compositor.container
%{_unitdir}/qm-dbus.socket
%{_unitdir}/wayland-session.service
%{_unitdir}/wayland.socket
%config(noreplace) %{_sysconfdir}/pam.d/systemd-user.qm-wayland
%{_sysconfdir}/pam.d/wayland-autologin
# Weston compositor configuration
%{_sysconfdir}/weston/weston.ini
# Preset file for enabling services
%{_presetdir}/50-qm-wayland.preset

%changelog
* Mon Oct 06 2025 RH Container Bot <rhcontainerbot@fedoraproject.org>
- Initial qm-wayland package split from main qm package
