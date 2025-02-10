Name: qm-dropin-img-tempdir
Version: 0
Release: 1%{?dist}
Summary: Drop-in configuration for QM nested containers using img tempdir
License: GPL-2.0-only
URL: https://github.com/containers/qm
Source0: %{url}/archive/qm-img_tmpdir-%{version}.tar.gz
BuildArch: noarch

Requires: qm = %{version}-%{release}

%description
This sub-package installs drop-in configurations for QM nested containers that use img tempdir.

%prep
%autosetup -Sgit -n qm-img_tmpdir-%{version}

%install
install -d %{buildroot}%{_sysconfdir}/qm/containers/containers.conf.d
install -m 644 %{_builddir}/qm-video-%{version}/etc/qm/containers/containers.conf.d/qm_dropin_img_tempdir.conf \
    %{buildroot}%{_sysconfdir}/qm/containers/containers.conf.d/

%files
%license LICENSE
%doc README.md
%{_sysconfdir}/qm/containers/containers.conf.d/qm_dropin_img_tempdir.conf

%changelog
* Fri Jul 21 2023 RH Container Bot <rhcontainerbot@fedoraproject.org>
- Added img_tempdir mount bind drop-in configuration.
