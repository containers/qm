%global debug_package %{nil}

# rootfs macros for QM ROS2 Rolling
%global rootfs_qm %{_prefix}/lib/qm/rootfs/
%global ros2_container %{rootfs_qm}/%{_sysconfdir}/containers/systemd/

Name: qm-ros2-rolling
Version: 0.6.8
Release: 1%{?dist}
Summary: Subpackage container for quadlet container to ROS2 Rolling environment
License: GPL-2.0-only
URL: https://github.com/containers/qm
Source0: %{url}/archive/v%{version}.tar.gz
BuildArch: noarch

BuildRequires: make
BuildRequires: git-core
BuildRequires: pkgconfig(systemd)
Requires: qm = %{version}-%{release}
Requires: podman

%description
This subpackage provides a containerized ROS2 Rolling environment within the
Quality Management (QM) system. It enables ROS2 applications to run in isolated
containers managed by Podman and systemd within the QM environment.

%prep
%autosetup -Sgit -n qm-%{version}

%build
# No special build requirements for ROS2 Rolling container
%{__make} all

%install
# Create the necessary directory structure
mkdir -p %{buildroot}%{ros2_container}

# Install the ROS2 Rolling container file
install -m 644 subsystems/ros2/ros2-rolling.container %{buildroot}%{ros2_container}

%files
%license LICENSE
%doc README.md
%{ros2_container}ros2-rolling.container

%changelog
* Fri Jul 21 2023 RH Container Bot <rhcontainerbot@fedoraproject.org> - 0.6.8-1
- Initial release of qm-ros2-rolling
