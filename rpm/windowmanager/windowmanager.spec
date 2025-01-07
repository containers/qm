Name: qm-windowmanager
Version: 0
Release: 1%{?dist}
Summary: Optional Window Manager for QM environment
License: GPL-2.0-only
URL: https://github.com/containers/qm
Source0: %{url}/archive/v%{version}.tar.gz
BuildArch: noarch

Requires: qm = %{version}-%{release}

%description
This sub-package installs an experimental window manager for the QM environment.

%prep
%autosetup -Sgit -n qm-%{version}

%install
# Create the directory for drop-in configurations
install -d  %{buildroot}/%{_sysconfdir}/pam.d/
install -d %{buildroot}%{_sysconfdir}/containers/systemd/qm.container.d

# Install the Window manager drop-in configuration file
install -m 644 %{_builddir}/qm-%{version}/etc/containers/systemd/qm.container.d/qm_dropin_mount_bind_window_manager.conf \
    %{buildroot}%{_sysconfdir}/containers/systemd/qm.container.d/qm_dropin_mount_bind_window_manager.conf
install -m 644 ./qm-windowmanager/etc/pam.d/wayland %{buildroot}/%{_sysconfdir}/pam.d/

%files
%license LICENSE
%doc README.md
%{_sysconfdir}/pam.d/wayland
%{_sysconfdir}/containers/systemd/qm.container.d/qm_dropin_mount_bind_window_manager.conf


%changelog
* Fri Jul 21 2023 RH Container Bot <rhcontainerbot@fedoraproject.org>
- Added windowmanager mount bind drop-in configuration.
