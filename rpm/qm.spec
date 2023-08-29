%global debug_package %{nil}

# Some bits borrowed from the openstack-selinux package
%global selinuxtype targeted
%global moduletype services
%global modulenames qm

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

%if 0%{?rhel} && 0%{?centos} == 0
# podman 4.5 is not available in RHEL 9 but it's available in CentOS Stream 9.
# bluechi-agent is available in EPEL 9.
%bcond_with podman_45
%else
%bcond_without podman_45
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
Requires: selinux-policy >= %_selinux_policy_version
Requires(post): selinux-policy-base >= %_selinux_policy_version
Requires(post): selinux-policy-targeted >= %_selinux_policy_version
Requires(post): policycoreutils
Requires(post): libselinux-utils
%if %{with podman_45}
Requires: podman >= %{podman_epoch}:4.5
%endif
Requires: hirte-agent

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
# install policy modules
%_format MODULES $x.pp.bz2
%{__make} DESTDIR=%{buildroot} DATADIR=%{_datadir} install

%post
# Install all modules in a single transaction
%_format MODULES %{_datadir}/selinux/packages/$x.pp.bz2
%selinux_modules_install -s %{selinuxtype} $MODULES

# Set AllowedCPUs in quadlet file
NPROC=$(nproc)
if [[ $NPROC == 1 ]]; then
    ALLOWED_CPUS=0
elif [[ $NPROC == 2 ]]; then
    ALLOWED_CPUS=1
else
    ALLOWED_CPUS=$(expr $NPROC / 2)"-"$(expr $NPROC - 1)
fi
sed "s/^AllowedCPUs=.*/AllowedCPUs=$ALLOWED_CPUS/" %{_datadir}/containers/systemd/%{name}.container > %{_sysconfdir}/containers/systemd/%{name}.container

%postun
if [ $1 -eq 0 ]; then
   %selinux_modules_uninstall -s %{selinuxtype} %{modulenames}
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
%ghost %dir %{_datadir}/containers
%ghost %dir %{_datadir}/containers/systemd
%{_datadir}/containers/systemd/qm.container
%ghost %{_sysconfdir}/containers/systemd/qm.container
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
