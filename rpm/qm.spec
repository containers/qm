%global debug_package %{nil}

# rootfs macros
%global rootfs_qm %{_prefix}/lib/qm/rootfs/
%global rootfs_qm_window_manager %{_prefix}/lib/qm/rootfs/qm_windowmanager

# Define the feature flag: 1 to enable, 0 to disable
# By default it's disabled: 0

###########################################
# subpackage QM - img_tempdir             #
###########################################
# use img temp dir as /var/tmp
%define enable_qm_dropin_img_tempdir 0

####################################################################
# subpackage QM - mount bind /dev/tty7                             #
####################################################################
# mount bind /dev/tty7 from host to nested containers              #
# as /dev/tty7:rw                                                  #
# Please note:                                                     #
# /dev/tty7 is typically the virtual terminal                      #
# associated with the graphical user interface (GUI)               #
# on Linux systems.                                                #
# It is where the X server or the Wayland display server           #
# usually runs, handling the graphical display, input              #
# and windowing environment.                                       #
# When you start a graphical session (ex. GNOME, KDE, etc.),       #
# it usually runs on this virtual console.                         #
####################################################################
%define enable_qm_mount_bind_tty7 0

###########################################
# subpackage QM - Enable Window Manager   #
###########################################
%define enable_qm_window_manager 0

###########################################
# subpackage QM - mount bind /dev/ttyUSB0 #
###########################################
%define enable_qm_mount_bind_ttyUSB0 0

###########################################
# subpackage QM - mount bind /dev/video   #
###########################################
%define enable_qm_mount_bind_video 0

###########################################
# subpackage QM - input devices           #
###########################################
%define enable_qm_mount_bind_input 0

# Some bits borrowed from the openstack-selinux package
%global selinuxtype targeted
%global moduletype services
%global modulenames qm
%global seccomp_json /usr/share/%{modulenames}/seccomp.json
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
Version: 0.6.8
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

Requires: parted
Requires: containers-common
Requires: selinux-policy >= %_selinux_policy_version
Requires(post): selinux-policy-base >= %_selinux_policy_version
Requires(post): selinux-policy-targeted >= %_selinux_policy_version
Requires(post): policycoreutils
Requires(post): libselinux-utils
Requires: podman >= %{podman_epoch}:4.5
Requires: bluechi-agent
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

####################################################################
################# QM Window Manager ################################
####################################################################
%if %{enable_qm_window_manager}
    # Create the necessary directory structure in the BUILDROOT
    mkdir -p %{buildroot}/%{rootfs_qm}/etc/pam.d
    mkdir -p %{buildroot}/%{rootfs_qm}/etc/systemd/system
    mkdir -p %{buildroot}/etc/systemd/system
    mkdir -p %{buildroot}/etc/containers/systemd/
    mkdir -p %{buildroot}/%{rootfs_qm}/etc/containers/systemd
    mkdir -p %{buildroot}/%{rootfs_qm}/%{_prefix}/lib/tmpfiles.d/etc/containers/systemd/
    mkdir -p %{buildroot}/%{rootfs_qm}/%{_prefix}/lib/tmpfiles.d/etc/containers/systemd/qm.container.d
    mkdir -p %{buildroot}/%{rootfs_qm_window_manager}/mutter
    mkdir -p %{buildroot}/%{rootfs_qm_window_manager}/session-activate

    # Install the pam.d file for wayland
    install -m 644 ./qm-windowmanager/etc/pam.d/wayland %{buildroot}/%{rootfs_qm}/etc/pam.d/wayland

    # Install the systemd service files
    install -m 644 ./qm-windowmanager/etc/systemd/system/wayland-session.service %{buildroot}/%{rootfs_qm}/etc/systemd/system/wayland-session.service
    install -m 644 ./qm-windowmanager/etc/systemd/system/qm-dbus.socket %{buildroot}/%{rootfs_qm}/etc/systemd/system/qm-dbus.socket
    install -m 644 ./qm-windowmanager/etc/containers/systemd/session-activate.container %{buildroot}/%{rootfs_qm}/etc/containers/systemd/session-activate.container

    install -m 755 ./qm-windowmanager/usr/share/qm/mutter/ContainerFile %{buildroot}/%{rootfs_qm_window_manager}/mutter/ContainerFile
    install -m 755 ./qm-windowmanager/usr/share/qm/manage-pam-selinux-systemd-user-config %{buildroot}/%{rootfs_qm_window_manager}/manage-pam-selinux-systemd-user-config
    install -m 755 ./qm-windowmanager/usr/share/qm/session-activate/ContainerFile %{buildroot}/%{rootfs_qm_window_manager}/session-activate/ContainerFile
    install -m 755 ./qm-windowmanager/usr/share/qm/session-activate/qm_windowmanager_activate_session %{buildroot}/%{rootfs_qm_window_manager}/session-activate/qm_windowmanager_activate_session

    # Install the tmpfiles.d configuration for mutter and weston
    install -m 644 ./qm-windowmanager/etc/containers/systemd/gnome_mutter.container %{buildroot}/%{rootfs_qm}/etc/containers/systemd/gnome_mutter.container
    install -m 644 ./qm-windowmanager/etc/containers/systemd/weston_terminal.container %{buildroot}/%{rootfs_qm}/etc/containers/systemd/weston_terminal.container
    install -m 644 ./qm-windowmanager/etc/containers/systemd/session-activate.container %{buildroot}/%{rootfs_qm}/etc/containers/systemd/session-activate.container

    # Install additional tmpfiles.d configurations
    install -m 644 ./qm-windowmanager/usr/lib/tmpfiles.d/wayland-xdg-directory.conf %{buildroot}/%{rootfs_qm}%{_prefix}/lib/tmpfiles.d/wayland-xdg-directory.conf
    install -m 644 ./qm-windowmanager/etc/containers/systemd/wayland-extra-devices.conf %{buildroot}/etc/containers/systemd/wayland-extra-devices.conf

    # first step - add drop-in file in /etc/containers/containers.d.conf/qm_dropin_mount_bind_window_manager.conf
    install -m 644 ./qm-windowmanager/etc/qm/containers/containers.conf.d/qm_dropin_mount_bind_window_manager.conf %{buildroot}%{_sysconfdir}/containers/containers.conf.d/qm_dropin_mount_bind_window_manager.conf

    # second step - add drop-in file in /etc/qm/containers/containers.d.conf/qm_dropin/mount_bind_window_manager.conf
    install -m 644 ./qm-windowmanager/etc/qm/containers/containers.conf.d/qm_dropin_mount_bind_window_manager.conf %{buildroot}%{_sysconfdir}/qm/containers/containers.conf.d/qm_dropin_mount_bind_window_manager.conf
%endif
####################################################################
################# END QM Window Manager ############################
####################################################################

########################################################
# START - qm dropin sub-package - img tempdir          #
########################################################
%if %{enable_qm_dropin_img_tempdir}
    install -m 644 %{_builddir}/qm-%{version}/etc/qm/containers/containers.conf.d/qm_dropin_img_tempdir.conf \
        %{buildroot}%{_sysconfdir}/qm/containers/containers.conf.d/qm_dropin_img_tempdir.conf
%endif
########################################################
# END - qm dropin sub-package - img tempdir            #
########################################################

########################################################
# START - qm dropin sub-package - mount ttyUSB0        #
########################################################
%if %{enable_qm_mount_bind_ttyUSB0}
    # first step - add drop-in file in /etc/containers/containers.d.conf/qm_dropin_mount_bind_ttyUSB0.conf
    # to QM container mount ttyUSB0
    install -m 644 %{_builddir}/qm-%{version}/etc/qm/containers/containers.conf.d/qm_dropin_mount_bind_ttyUSB0.conf %{buildroot}%{_sysconfdir}/containers/containers.conf.d/qm_dropin_mount_bind_ttyUSB0.conf

    # second step - add drop-in file in /etc/qm/containers/containers.d.conf/qm_dropin/mount_bind_ttyUSB0.conf
    # to nested containers in QM env mount bind ttyUSB0
    install -m 644 %{_builddir}/qm-%{version}/etc/qm/containers/containers.conf.d/qm_dropin_mount_bind_ttyUSB0.conf %{buildroot}%{_sysconfdir}/qm/containers/containers.conf.d/qm_dropin_mount_bind_ttyUSB0.conf
%endif
########################################################
# END - qm dropin sub-package - mount ttyUSB0          #
########################################################

########################################################
# START - qm dropin sub-package - mount video          #
########################################################
%if %{enable_qm_mount_bind_video}
    mkdir -p %{buildroot}/%{rootfs_qm}/%{_sysconfdir}/containers/systemd/
    # first step - add drop-in file in /etc/containers/containers.d.conf/qm_dropin_mount_bind_video.conf
    # to QM container mount video
    install -m 644 %{_builddir}/qm-%{version}/etc/qm/containers/containers.conf.d/qm_dropin_mount_bind_video.conf %{buildroot}%{_sysconfdir}/containers/containers.conf.d/qm_dropin_mount_bind_video.conf

    # second step - add drop-in file in /etc/qm/containers/containers.d.conf/qm_dropin/mount_bind_video.conf
    # to nested containers in QM env mount bind video
    install -m 644 %{_builddir}/qm-%{version}/etc/qm/containers/containers.conf.d/qm_dropin_mount_bind_video.conf %{buildroot}%{_sysconfdir}/qm/containers/containers.conf.d/qm_dropin_mount_bind_video.conf

    install -m 644 %{_builddir}/qm-%{version}/etc/containers/systemd/rear-camera.container %{buildroot}/%{rootfs_qm}/%{_sysconfdir}/containers/systemd/rear-camera.container
%endif
########################################################
# END - qm dropin sub-package - mount video            #
########################################################

########################################################
# START - qm dropin sub-package - mount input          #
########################################################
%if %{enable_qm_mount_bind_input}
    # first step - add drop-in file in /etc/containers/containers.d.conf/qm_dropin_mount_bind_input.conf
    # to QM container mount input
    install -m 644 %{_builddir}/qm-%{version}/etc/qm/containers/containers.conf.d/qm_dropin_mount_bind_input.conf %{buildroot}%{_sysconfdir}/containers/containers.conf.d/qm_dropin_mount_bind_input.conf

    # second step - add drop-in file in /etc/qm/containers/containers.d.conf/qm_dropin/mount_bind_input.conf
    # to nested containers in QM env mount bind input
    install -m 644 %{_builddir}/qm-%{version}/etc/qm/containers/containers.conf.d/qm_dropin_mount_bind_input.conf %{buildroot}%{_sysconfdir}/qm/containers/containers.conf.d/qm_dropin_mount_bind_input.conf
%endif
########################################################
# END - qm dropin sub-package - mount input            #
########################################################

########################################################
# START - qm dropin sub-package - mount bind /dev/tty7 #
########################################################
%if %{enable_qm_mount_bind_tty7}
    # first step - add drop-in file in /etc/containers/containers.d.conf/qm_dropin_mount_bind_tty.conf
    # to QM container mount bind /dev/tty7
    install -m 644 %{_builddir}/qm-%{version}/etc/qm/containers/containers.conf.d/qm_dropin_mount_bind_tty7.conf %{buildroot}%{_sysconfdir}/containers/containers.conf.d/qm_dropin_mount_bind_tty7.conf

    # second step - add drop-in file in /etc/qm/containers/containers.d.conf/qm_dropin/mount_bind_tty.conf
    # to nested containers in QM env mount bind it in /dev/tty7
    install -m 644 %{_builddir}/qm-%{version}/etc/qm/containers/containers.conf.d/qm_dropin_mount_bind_tty7.conf %{buildroot}%{_sysconfdir}/qm/containers/containers.conf.d/qm_dropin_mount_bind_tty7.conf
%endif

########################################################
# END - qm dropin sub-package - mount bind /dev/tty7   #
########################################################

# install policy modules
%_format MODULES $x.pp.bz2
%{__make} DESTDIR=%{buildroot} DATADIR=%{_datadir} install

%post
# Install all modules in a single transaction
%_format MODULES %{_datadir}/selinux/packages/$x.pp.bz2
%selinux_modules_install -s %{selinuxtype} $MODULES
# Execute the script to create seccomp rules after the package is installed
/usr/share/qm/create-seccomp-rules
/usr/share/qm/comment-tz-local # FIX-ME GH-issue: 367
/usr/share/qm/qm-is-ostree

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
   %selinux_modules_uninstall -s %{selinuxtype} %{modulenames}
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

#######################################
# sub-package QM Img TempDir          #
#######################################
%if %{enable_qm_dropin_img_tempdir}
%package -n qm-dropin-img-tempdir
Summary: Drop-in configuration for QM nested containers to img tempdir
Requires: %{name} = %{version}-%{release}
BuildArch: noarch

%description -n qm-dropin-img-tempdir
This sub-package installs a drop-in configurations for the QM.
It creates the `/etc/qm/containers/containers.conf.d/` directory for adding
additional drop-in configurations.

%files -n qm-dropin-img-tempdir
%{_sysconfdir}/qm/containers/containers.conf.d/qm_dropin_img_tempdir.conf
%endif

#######################################
# sub-package QM Mount Bind /dev/tty7 #
#######################################
%if %{enable_qm_mount_bind_tty7}
%package -n qm_mount_bind_tty7
Summary: Drop-in configuration for QM containers to mount bind /dev/tty7
Requires: %{name} = %{version}-%{release}
BuildArch: noarch

%description -n qm_mount_bind_tty7
This sub-package installs a drop-in configurations for the QM.
It creates the `/etc/qm/containers/containers.conf.d/` directory for adding
additional drop-in configurations.

%files -n qm_mount_bind_tty7
%{_sysconfdir}/containers/containers.conf.d/qm_dropin_mount_bind_tty7.conf
%{_sysconfdir}/qm/containers/containers.conf.d/qm_dropin_mount_bind_tty7.conf
%endif

#######################################
# sub-package QM Mount Input          #
#######################################
%if %{enable_qm_mount_bind_input}
%package -n qm_mount_bind_input
Summary: Drop-in configuration for QM containers to mount bind input
Requires: %{name} = %{version}-%{release}
BuildArch: noarch

%description -n qm_mount_bind_input
This sub-package installs a drop-in configurations for the QM.
It creates the `/etc/qm/containers/containers.conf.d/` directory for adding
additional drop-in configurations.

%files -n qm_mount_bind_input
%{_sysconfdir}/containers/containers.conf.d/qm_dropin_mount_bind_input.conf
%{_sysconfdir}/qm/containers/containers.conf.d/qm_dropin_mount_bind_input.conf
%endif

#######################################
# sub-package QM Mount ttyUSB0        #
#######################################
%if %{enable_qm_mount_bind_ttyUSB0}
%package -n qm_mount_bind_ttyUSB0
Summary: Drop-in configuration for QM containers to mount bind ttyUSB0
Requires: %{name} = %{version}-%{release}
BuildArch: noarch

%description -n qm_mount_bind_ttyUSB0
This sub-package installs a drop-in configurations for the QM.
It creates the `/etc/qm/containers/containers.conf.d/` directory for adding
additional drop-in configurations.

%files -n qm_mount_bind_ttyUSB0
%{_sysconfdir}/containers/containers.conf.d/qm_dropin_mount_bind_ttyUSB0.conf
%{_sysconfdir}/qm/containers/containers.conf.d/qm_dropin_mount_bind_ttyUSB0.conf
%endif

#######################################
# sub-package qm window manager       #
#######################################
%if %{enable_qm_window_manager}
%package windowmanager
Summary: Optional Window Manager deployed in QM environment (Experimental)
Requires: qm_mount_bind_input
Requires: qm_mount_bind_sound
%description windowmanager
The optional window manager deployed in QM environment as nested container.

%files windowmanager
%{rootfs_qm}/%{_sysconfdir}/pam.d/wayland
%{rootfs_qm}/%{_sysconfdir}/systemd/system/wayland-session.service
%{rootfs_qm}/%{_sysconfdir}/systemd/system/qm-dbus.socket
%{rootfs_qm}/%{_sysconfdir}/containers/systemd/session-activate.container
%{rootfs_qm}/%{_sysconfdir}/containers/systemd/gnome_mutter.container
%{rootfs_qm}/%{_sysconfdir}/containers/systemd/weston_terminal.container
%{rootfs_qm_window_manager}/session-activate/ContainerFile
%{rootfs_qm_window_manager}/session-activate/qm_windowmanager_activate_session
%{rootfs_qm_window_manager}/mutter/ContainerFile
%{rootfs_qm_window_manager}/manage-pam-selinux-systemd-user-config
%config(noreplace) %{rootfs_qm}/%{_prefix}/lib/tmpfiles.d/wayland-xdg-directory.conf
%config(noreplace) /etc/containers/systemd/wayland-extra-devices.conf
# extra seats tty0-7
%{_sysconfdir}/containers/containers.conf.d/qm_dropin_mount_bind_window_manager.conf
%{_sysconfdir}/qm/containers/containers.conf.d/qm_dropin_mount_bind_window_manager.conf

%post windowmanager
%{rootfs_qm_window_manager}/manage-pam-selinux-systemd-user-config %{rootfs_qm_window_manager}/etc/pam.d/systemd-user --comment
services=("activate-session.service" "qm-dbus.socket" "wayland-session.service")

# Loop to enable and start each service or socket
for service in "${services[@]}"; do
    podman exec qm systemctl enable "$service" >/dev/null 2>&1 || :
    podman exec qm systemctl start "$service" >/dev/null 2>&1 || :
done

%preun windowmanager
# getting back the config from the qm-windowmanager config comments
%{rootfs_qm_window_manager}/manage-pam-selinux-systemd-user-config %{rootfs_qm_window_manager}/etc/pam.d/systemd-user --uncomment
services=("activate-session.service" "qm-dbus.socket" "wayland-session.service")

# Stop and disable the services before uninstalling
for service in "${services[@]}"; do
    podman exec qm systemctl stop "$service" >/dev/null 2>&1 || :
    podman exec qm systemctl disable "$service" >/dev/null 2>&1 || :
done

%postun windowmanager
# Reload systemd daemon after uninstallation
podman exec qm systemctl daemon-reload &> /dev/null
%endif

#######################################
# sub-package QM Mount Bind /dev/video#
#######################################
%if %{enable_qm_mount_bind_video}
%package -n qm_mount_bind_video
Summary: Drop-in configuration for QM containers to mount bind /dev/video
Requires: %{name} = %{version}-%{release}
BuildArch: noarch

%description -n qm_mount_bind_video
This sub-package installs a drop-in configurations for the QM.
It creates the `/etc/qm/containers/containers.conf.d/` directory for adding
additional drop-in configurations.

%files -n qm_mount_bind_video
%{_sysconfdir}/containers/containers.conf.d/qm_dropin_mount_bind_video.conf
%{_sysconfdir}/qm/containers/containers.conf.d/qm_dropin_mount_bind_video.conf
%{rootfs_qm}/%{_sysconfdir}/containers/systemd/rear-camera.container
%endif

%changelog
%if %{defined autochangelog}
%autochangelog
%else
* Fri Jul 21 2023 RH Container Bot <rhcontainerbot@fedoraproject.org>
- Placeholder changelog for envs that are not autochangelog-ready
%endif
