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
%if "%{?copr_username}" != "centos-automotive-sig" && "%{?copr_projectname}" != "qm-next"
%bcond_with copr
%else
%bcond_without copr
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
Source0: %{url}/archive/v%{version}.tar.gz#/%{name}-%{version}.tar.gz
BuildRequires: golang-github-cpuguy83-md2man
BuildRequires: container-selinux
BuildRequires: make
BuildRequires: gcc
BuildRequires: pkgconfig(json-c)
BuildRequires: pkgconfig(libmnl)
BuildRequires: pkgconfig(libnftables)
BuildRequires: pkgconfig(libsystemd) >= 254
BuildRequires: meson
BuildRequires: ninja-build
BuildRequires: git-core
BuildRequires: pkgconfig(systemd)
BuildRequires: selinux-policy >= %_selinux_policy_version
BuildRequires: selinux-policy-devel >= %_selinux_policy_version
BuildRequires: bluechi-selinux
BuildRequires: python3
BuildRequires: systemd-rpm-macros
BuildRequires: jq

Recommends: selinux-policy-targeted >= %_selinux_policy_version

Requires: parted
Requires: containers-common
Requires: selinux-policy >= %_selinux_policy_version
Requires(post): selinux-policy-base >= %_selinux_policy_version
Requires(post): selinux-policy-any >= %_selinux_policy_version
Requires(post): policycoreutils
Requires(post): libselinux-utils
Requires: jq
Requires: crun
Requires: systemd >= 254
Requires: shadow-utils
%{?systemd_requires}
# Retired CLIs and the standalone prototype; no command compatibility implied.
Obsoletes: qmctl < %{?epoch:%{epoch}:}2
Obsoletes: qm-ctl < %{?epoch:%{epoch}:}2
Obsoletes: qm-launch < 1

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

%build
%meson
%meson_build

%install
%meson_install

%check
%meson_test

%pre
# Stop the old generated unit before its Quadlet disappears. Store activation
# outside /run/qm, whose contents belong to runtime cleanup.
if [ -d /run/systemd/system ]; then
    if [ -f /etc/systemd/system/qm.service ]; then
        echo 'QM: move the full /etc/systemd/system/qm.service override aside and migrate its settings to qm.service.d before upgrading.' >&2
        exit 1
    fi
    umask 077
    mkdir -p /run/qm-rpm-upgrade
    : > /run/qm-rpm-upgrade/state
    for unit in qm.service qmc.service; do
        if systemctl is-active --quiet "$unit"; then
            echo active >> /run/qm-rpm-upgrade/state
            systemctl stop "$unit" || exit 1
        fi
        case "$(systemctl is-enabled "$unit" 2>/dev/null)" in
            enabled|enabled-runtime|generated) echo enabled >> /run/qm-rpm-upgrade/state ;;
        esac
    done
    # The old Quadlet normally removes its container on stop. Only remove a
    # stopped leftover explicitly labelled as belonging to that unit.
    if command -v podman >/dev/null &&
       [ "$(podman inspect --format '{{ index .Config.Labels "PODMAN_SYSTEMD_UNIT" }}' qm 2>/dev/null)" = qm.service ]; then
        podman rm qm || exit 1
    fi
fi

%post
%_format MODULES %{_datadir}/selinux/packages/$x.pp.bz2
. %{_sysconfdir}/selinux/config
%selinux_modules_install -s ${SELINUXTYPE} $MODULES
# Execute the script to create seccomp rules after the package is installed
/usr/share/qm/create-seccomp-rules
# The binary was unpacked before its new file-context rule was installed.
/sbin/restorecon %{_bindir}/qmc
%systemd_post qm.service
%sysctl_apply 00-qm-forwarding.conf 90-qm-launch.conf

%preun
%systemd_preun qm.service qm-resolv-conf.path qm-resolv-conf.service
# Preserve the prepared rootfs and application data on package removal. An
# explicit setup --remove-qm-rootfs remains available before uninstalling.

%postun
%systemd_postun qm.service qm-resolv-conf.path qm-resolv-conf.service
if [ $1 -eq 0 ]; then
   # This section executes only on package removal, not on upgrade
   . %{_sysconfdir}/selinux/config
   %selinux_modules_uninstall -s ${SELINUXTYPE} %{modulenames}
   if [ -f %{seccomp_json} ]; then
     /bin/rm -f %{seccomp_json}
   fi
fi

%posttrans
if [ -d /run/systemd/system ]; then
    systemctl daemon-reload
    if [ -f /run/qm-rpm-upgrade/state ]; then
        if grep -q '^enabled$' /run/qm-rpm-upgrade/state; then
            systemctl enable qm.service
        fi
        if grep -q '^active$' /run/qm-rpm-upgrade/state; then
            systemctl start qm.service || echo 'QM: startup failed; see journalctl -u qm.service and the configuration migration guide.' >&2
        fi
        rm -f /run/qm-rpm-upgrade/state
        rmdir /run/qm-rpm-upgrade
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
%{_bindir}/qmc
%{_datadir}/qm/qm.json
%{_datadir}/qm/qmc.conf
%dir %{_datadir}/qm/qmc.conf.d
%dir %{_sysconfdir}/qmc.conf.d
%{_datadir}/qm/containers.conf
%{_datadir}/qm/contexts
%{_datadir}/qm/file_contexts
%{_datadir}/qm/setup
%{_datadir}/qm/userns
%{_datadir}/qm/create-seccomp-rules
%{_datadir}/qm/qm-rootfs
%{_datadir}/qm/qm-storage-settings
%{_datadir}/qm/check-config-migration
%{_datadir}/qm/qm-is-ostree
%{_unitdir}/qm.service
%{_unitdir}/qm-resolv-conf.path
%{_unitdir}/qm-resolv-conf.service
%{_sysctldir}/00-qm-forwarding.conf
%{_sysctldir}/90-qm-launch.conf
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
