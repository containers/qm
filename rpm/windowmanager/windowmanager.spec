Name: qm-windowmanager
Version: 0.6.8
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
install -d  %{buildroot}/%{_sysconfdir}/pam.d/
install -d %{buildroot}%{_sysconfdir}/containers/containers.conf.d
install -m 644 ./qm-windowmanager/etc/qm/containers/containers.conf.d/qm_dropin_mount_bind_window_manager.conf \
			%{buildroot}/%{_sysconfdir}/containers/containers.conf.d/
install -m 644 ./qm-windowmanager/etc/pam.d/wayland %{buildroot}/%{_sysconfdir}/pam.d/

%files
%license LICENSE
%doc README.md
%{_sysconfdir}/pam.d/wayland
%{_sysconfdir}/containers/containers.conf.d/qm_dropin_mount_bind_window_manager.conf

%changelog
* Fri Jul 21 2023 RH Container Bot <rhcontainerbot@fedoraproject.org>
- Added windowmanager mount bind drop-in configuration.
