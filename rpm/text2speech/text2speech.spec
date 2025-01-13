%global debug_package %{nil}

# Define rootfs macro for QM environment
%global rootfs_qm %{_prefix}/lib/qm/rootfs/

Name: qm-text2speech
Version: 0.6.8
Release: 1%{?dist}
Summary: Drop-in configuration for QM containers to mount bind
License: GPL-2.0-only
URL: https://github.com/containers/qm
Source0: %{url}/archive/v%{version}.tar.gz
BuildArch: noarch

# Build requirements
BuildRequires: make
BuildRequires: podman
BuildRequires: selinux-policy
BuildRequires: selinux-policy-devel

# Runtime dependencies
Requires: qm = %{version}-%{release}
Requires: qm-mount-bind-sound
Requires: selinux-policy >= %{_selinux_policy_version}
Requires: selinux-policy-base >= %{_selinux_policy_version}
Requires: podman
Requires: espeak

%description -n qm-text2speech
This subpackage provides a drop-in configuration for the QM environment to enable espeak

%prep
%autosetup -n qm-%{version}

%build

%install

%post
dnf --installroot /usr/lib/qm/rootfs/ install espeak -y

%files
%license LICENSE
%doc CODE-OF-CONDUCT.md README.md SECURITY.md

%changelog
* Fri Jul 21 2023 RH Container Bot <rhcontainerbot@fedoraproject.org>
- Initial standalone spec for the QM KVM subpackage.
