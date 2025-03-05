%global debug_package %{nil}

# Define rootfs macro for QM environment
%global rootfs_qm %{_prefix}/lib/qm/rootfs/

Name: qm-kvm
Version: 0
Release: 1%{?dist}
Summary: Drop-in configuration for QM containers to mount bind /dev/kvm
License: GPL-2.0-only
URL: https://github.com/containers/qm
Source0: %{url}/archive/qm-kvm-%{version}.tar.gz
BuildArch: noarch

Requires: qm >= %{version}

%description -n qm-kvm
This subpackage provides a drop-in configuration for the QM environment to enable mount binding of `/dev/kvm` from the host system to containers. This configuration is essential for supporting KVM-based virtualization within QM containers.

%prep
%autosetup -Sgit -n qm-kvm-%{version}

%install
# Create the directory for drop-in configurations
install -d %{buildroot}%{_sysconfdir}/containers/systemd/qm.container.d

# Install the KVM drop-in configuration file
install -m 644 %{_builddir}/qm-kvm-%{version}/etc/containers/systemd/qm.container.d/qm_dropin_mount_bind_kvm.conf \
    %{buildroot}%{_sysconfdir}/containers/systemd/qm.container.d/qm_dropin_mount_bind_kvm.conf

%files -n qm-kvm
%license LICENSE
%doc README.md SECURITY.md
%{_sysconfdir}/containers/systemd/qm.container.d/qm_dropin_mount_bind_kvm.conf

%changelog
* Fri Jul 21 2023 RH Container Bot <rhcontainerbot@fedoraproject.org>
- Initial standalone spec for the QM KVM subpackage.
