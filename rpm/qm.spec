%global debug_package %{nil}

# rootfs macros
%global rootfs_qm %{_prefix}/lib/qm/rootfs/

# Define the feature flag: 1 to enable, 0 to disable
# By default it's disabled: 0

# Some bits borrowed from the openstack-selinux and container-selinux packages
%global moduletype services
%global modulenames qm
%global seccomp_json /usr/share/%{modulenames}/seccomp-no-rt.json
%global setup_tool %{_prefix}/share/%{modulenames}/setup

%global _installscriptdir %{_prefix}/lib/%{modulenames}

# Usage: _format var format
# Expand 'modulenames' into various formats as needed
# Format must contain '$x' somewhere to do anything useful
%global _format() export %1=""; for x in %{modulenames}; do %1+=%2; %%1+=" "; done;

# copr_username is only set on copr environments, not on others like koji
# Check if copr is owned by rhcontainerbot
%if "%{?copr_username}" != "rhcontainerbot"
%bcond_with copr
%else
%bcond_without copr
%endif

%if 0%{?fedora}
%global podman_epoch 5
%else
%global podman_epoch 2
%endif

Name: qm
# Set different Epochs for copr and koji
%if %{with copr}
Epoch: 101
%endif
# Keep Version in upstream specfile at 0. It will be automatically set
# to the correct value by Packit for copr and koji builds.
# IGNORE this comment if you're looking at it in dist-git.
Version: 0
%if %{defined autorelease}
Release: %autorelease
%else
Release: 1
%endif
License: GPL-2.0-only
URL: https://github.com/containers/qm
Summary: Containerized environment for running Quality Management software
Source0: %{url}/archive/v%{version}.tar.gz
BuildArch: noarch
# golang-github-cpuguy83-md2man on CentOS Stream 9 is available in CRB repository
BuildRequires: golang-github-cpuguy83-md2man
BuildRequires: container-selinux
BuildRequires: make
BuildRequires: git-core
BuildRequires: pkgconfig(systemd)
BuildRequires: selinux-policy >= %_selinux_policy_version
BuildRequires: selinux-policy-devel >= %_selinux_policy_version
BuildRequires: bluechi-selinux

Requires: iptables
Requires: parted
Requires: containers-common
Requires: selinux-policy >= %_selinux_policy_version
Requires(post): selinux-policy-base >= %_selinux_policy_version
Requires(post): selinux-policy-any >= %_selinux_policy_version
Recommends: selinux-policy-targeted >= %_selinux_policy_version
Requires(post): policycoreutils
Requires(post): libselinux-utils
Requires: podman >= %{podman_epoch}:4.5
Requires: jq

%description
This package allow users to setup an environment which prevents applications
and container tools from interfering with other all other processes on the
system.

The QM runs its own version of systemd and Podman to isolate not only the
applications and containers launched by systemd and Podman but systemd and
Podman themselves.

Software install into the QM environment under `/usr/lib/qm/rootfs` is
automatically isolated from the host. If developers need to further
isolate there applications from other processes in the QM they should
use container tools like Podman.

%prep
%autosetup -Sgit -n %{name}-%{version}
sed -i 's/^install: man all/install:/' Makefile

%build
%{__make} all

%install
# Create the directory for drop-in configurations
install -d %{buildroot}%{_sysconfdir}/containers/containers.conf.d

# install policy modules
%_format MODULES $x.pp.bz2
%{__make} DESTDIR=%{buildroot} DATADIR=%{_datadir} install

%post
%_format MODULES %{_datadir}/selinux/packages/$x.pp.bz2
. %{_sysconfdir}/selinux/config
%selinux_modules_install -s ${SELINUXTYPE} $MODULES
# Execute the script to create seccomp rules after the package is installed
/usr/share/qm/create-seccomp-rules
/usr/share/qm/comment-tz-local # FIX-ME GH-issue: 367
modprobe ip_tables # podmand netavark requires at host to load

%preun
if [ $1 = 0 ]; then
   # Commands to run before the package is completely removed
   # remove previous configured qm rootfs
   systemctl stop qm
   %{setup_tool} --remove-qm-rootfs &> /dev/null
fi

%postun
if [ $1 -eq 0 ]; then
   # This section executes only on package removal, not on upgrade
   . %{_sysconfdir}/selinux/config
   %selinux_modules_uninstall -s ${SELINUXTYPE} %{modulenames}
   if [ -f %{seccomp_json} ]; then
     /bin/rm -f %{seccomp_json}
   fi
fi

#define license tag if not already defined
%{!?_licensedir:%global license %doc}

%files
%license LICENSE
%doc CODE-OF-CONDUCT.md NOTICE README.md SECURITY.md
%dir %{_datadir}/selinux
%{_datadir}/selinux/*
%dir %{_datadir}/qm
%{_datadir}/qm/containers.conf
%{_datadir}/qm/contexts
%{_datadir}/qm/file_contexts
%{_datadir}/qm/setup
%{_datadir}/qm/create-seccomp-rules
%{_datadir}/qm/qm-rootfs
%{_datadir}/qm/qm-storage-settings
%{_datadir}/qm/comment-tz-local
%{_datadir}/qm/qm-is-ostree
%ghost %dir %{_datadir}/containers
%ghost %dir %{_datadir}/containers/systemd
%{_datadir}/containers/systemd/qm.container
%{_mandir}/man8/*
%ghost %dir %{_installscriptdir}
%ghost %dir %{_installscriptdir}/rootfs
%ghost %{_installscriptdir}/rootfs/*

%changelog
%if %{defined autochangelog}
%autochangelog
%else
* Fri Jul 21 2023 RH Container Bot <rhcontainerbot@fedoraproject.org>
- Placeholder changelog for envs that are not autochangelog-ready
%endif
