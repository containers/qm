%global debug_package %{nil}

Name: qm-text2speech
Version: 0
Release: 1%{?dist}
Summary: Drop-in configuration for QM containers to mount bind
License: GPL-2.0-only
URL: https://github.com/containers/qm
Source0: %{url}/archive/qm-text2speech-%{version}.tar.gz
BuildArch: noarch

# Runtime dependencies
Requires: qm >= %{version}
Requires: qm-mount-bind-sound
Requires: espeak

%description -n qm-text2speech
This subpackage provides a drop-in configuration for the QM environment to enable espeak

%prep
%autosetup -n qm-text2speech-%{version}

%build

%install

%post
dnf install  --setopt=reposdir=/etc/yum.repos.d  --installroot /usr/lib/qm/rootfs/ espeak-ng

%files
%license LICENSE
%doc CODE-OF-CONDUCT.md README.md SECURITY.md

%changelog
* Fri Jul 21 2023 RH Container Bot <rhcontainerbot@fedoraproject.org>
- Initial standalone spec for the QM espeak subpackage.
