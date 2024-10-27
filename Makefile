TARGETS ?= qm
MODULES ?= ${TARGETS:=.pp.bz2}
DESTDIR ?=
PREFIX ?= /usr
DATADIR ?= $(PREFIX)/share
LIBDIR ?= $(PREFIX)/lib
SYSCONFDIR?=/etc
QMDIR=/usr/lib/qm
SPECFILE=rpm/qm.spec
RPM_TOPDIR ?= $(PWD)/rpmbuild
VERSION ?= $(shell cat VERSION)

###########################################
# subpackage QM - img_tempdir             #
###########################################
# use img temp dir as /var/tmp            #
###########################################
# export EN_QM_DROP_IMG_TMPDIR=1
EN_QM_DROP_IMG_TMPDIR ?= 0

#######################################################################
# subpackage QM - mount bind /dev/tty7                                #
#######################################################################
# mount bind /dev/tty7 from host to nested containers as /dev/tty7:rw #
# Please note: /dev/tty7 is typically the virtual terminal associated #
# with the graphical user interface (GUI) on Linux systems.           #
# It is where the X server or the Wayland display server usually runs,#
# handling the graphical display, input, and windowing environment.   #
# When you start a graphical session (such as GNOME, KDE, etc.),      #
# it usually runs on this virtual console.                            #
#######################################################################
# export EN_QM_MNT_BIND_TTY7=1
EN_QM_MNT_BIND_TTY7 ?= 0

############################################
# subpackage QM - mount bind audio device  #
# from host to container and nested        #
# container enabling sound                 #
############################################
# export EN_QM_MNT_BIND_SOUND=1
EN_QM_MNT_BIND_SOUND ?= 0

############################################
# subpackage QM - ros2-rolling             #
############################################
# export EN_QM_ROS2_ROLLING=1
EN_QM_ROS2_ROLLING ?= 0

###########################################
# subpackage QM - Enable Window Manager   #
###########################################
# export EN_QM_WINDOW_MGR=1
EN_QM_WINDOW_MGR ?= 0

###########################################
# subpackage QM - mount bind /dev/ttyUSB0 #
###########################################
# export EN_QM_MNT_BIND_TTY_USB=1
EN_QM_MNT_BIND_TTY_USB ?= 0

###########################################
# subpackage QM - mount bind /dev/kvm #
###########################################
# export EN_QM_MNT_BIND_KVM=1
EN_QM_MNT_BIND_KVM ?= 0

###########################################
# subpackage QM - input devices           #
###########################################
# export EN_QM_MNT_BIND_INPUT=1
EN_QM_MNT_BIND_INPUT ?= 0

###########################################
# subpackage QM - input video             #
###########################################
# export EN_QM_MNT_BIND_VIDEO=1
EN_QM_MNT_BIND_VIDEO ?= 0

# Default help target
.PHONY: help
help:
	@echo "Available targets:"
	@grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@grep -E '^##@ .*$$' $(MAKEFILE_LIST) | sed 's/##@/\n\033[1;32m/' | sed 's/$$/\033[0m/'

.PHONY: file_contexts
file_contexts: qm.fc ##             - Generates the qm_file_contexts
	sed \
	-e "s|${QMDIR}/rootfs||" \
	 -e "s/gen_context(//g" \
	 -e "s/,s0)/:s0/g" \
	 -e "s|${QMDIR}||g" qm.fc > qm_file_contexts

all: selinux file_contexts  man

.PHONY: selinux
selinux: qm.pp ##             - Compresses the QM SELinux policy file (qm.pp)
	@echo Compressing $^ -\> $@
	bzip2 -f -9 $^

%.pp: %.te
	mkdir -p tmp; cp qm.* tmp/
	@if ./build-aux/validations ; then \
		sed -i /user_namespace/d tmp/qm.if; \
	fi
	$(MAKE) -C tmp -f ${DATADIR}/selinux/devel/Makefile $@
	cp tmp/qm.pp .; rm -rf tmp

.PHONY: codespell
codespell: ##             - Runs codespell to check for spelling errors
	@codespell -S tmp,.git -L te -w

clean: ##             - Removes generated files and dirs
	rm -f *~  *.tc *.pp *.pp.bz2
	rm -rf tmp *.tar.gz ${RPM_TOPDIR}

man: qm.8.md ##             - Generates the QM man page
	go-md2man --in qm.8.md --out qm.8

.PHONY: dist
dist: ##             - Creates the QM distribution package
	tar cvz \
		--exclude='.git' \
		--dereference \
		--exclude='.gitignore' \
		--exclude='demos' \
		--exclude='.github' \
		--transform s/qm/qm-${VERSION}/ \
		-f /tmp/v${VERSION}.tar.gz ../qm
	mv /tmp/v${VERSION}.tar.gz ./rpm

.PHONY: rpm
rpm: clean dist ##             - Creates a local RPM package, useful for development
	mkdir -p ${RPM_TOPDIR}/{RPMS,SRPMS,BUILD,SOURCES}
	tools/version-update -v ${VERSION}
	cp ./rpm/v${VERSION}.tar.gz ${RPM_TOPDIR}/SOURCES
	rpmbuild -ba \
		--define="u_enable_qm_dropin_img_tempdir ${EN_QM_DROP_IMG_TMPDIR}" \
		--define="u_enable_qm_window_manager ${EN_QM_WINDOW_MGR}" \
		--define="u_enable_qm_mount_bind_tty7 ${EN_QM_MNT_BIND_TTY7}" \
		--define="u_enable_qm_mount_bind_ttyUSB0 ${EN_QM_MNT_BIND_TTY_USB}" \
		--define="u_enable_qm_mount_bind_sound ${EN_QM_MNT_BIND_SOUND}" \
		--define="u_enable_qm_mount_bind_kvm ${EN_QM_MNT_BIND_KVM}" \
		--define="u_enable_qm_mount_bind_input ${EN_QM_MNT_BIND_INPUT}" \
		--define="u_enable_qm_mount_bind_video ${EN_QM_MNT_BIND_VIDEO}" \
		--define="u_enable_qm_dropin_ros2_rolling ${EN_QM_ROS2_ROLLING}" \
		--define="_topdir ${RPM_TOPDIR}" \
		--define="version ${VERSION}" \
		${SPECFILE}

# ostree target is a helper for everything required for ostree
.PHONY: ostree
ostree: qm_dropin_img_tempdir ##             - A helper for creating QM packages for ostree based distros

.PHONY: qm_dropin_window_manager
qm_dropin_window_manager: qm_dropin_mount_bind_kvm qm_dropin_mount_bind_sound qm_dropin_mount_bind_tty7 qm_dropin_mount_bind_input ##         - QM RPM sub-package qm_dropin_window_manager
	sed -i 's/%define enable_qm_window_manager 0/%define enable_qm_window_manager 1/' ${SPECFILE}
	$(MAKE) VERSION=${VERSION} rpm

.PHONY: qm_dropin_img_tempdir
qm_dropin_img_tempdir: ##            - QM RPM sub-package qm_dropin_img_tempdir
	sed -i 's/%define enable_qm_dropin_img_tempdir 0/%define enable_qm_dropin_img_tempdir 1/' ${SPECFILE}
	$(MAKE) VERSION=${VERSION} rpm

.PHONY: qm_dropin_ros2_rolling
qm_dropin_ros2_rolling: ##           - QM RPM sub-package to creating a quadlet container with ROS2 rolling env
	sed -i 's/%define enable_qm_ros2_rolling 0/%define enable_qm_ros2_rolling 1/' ${SPECFILE}
	$(MAKE) VERSION=${VERSION} rpm

.PHONY: qm_dropin_mount_bind_ttyUSB0
qm_dropin_mount_bind_ttyUSB0: ##     - QM RPM sub-package to mount bind /dev/ttyUSB0 in the nested containers
	sed -i 's/%define enable_qm_mount_bind_ttyUSB0 0/%define enable_qm_mount_bind_ttyUSB0 1/' ${SPECFILE}
	$(MAKE) VERSION=${VERSION} rpm

.PHONY: qm_dropin_mount_bind_video0
qm_dropin_mount_bind_video0: ##      - QM RPM sub-package to mount bind /dev/video0 in the nested containers
	sed -i 's/%define enable_qm_mount_bind_video 0/%define enable_qm_mount_bind_video 1/' ${SPECFILE}
	$(MAKE) VERSION=${VERSION} rpm

.PHONY: qm_dropin_mount_bind_kvm
qm_dropin_mount_bind_kvm: ##         - QM RPM sub-package to mount bind /dev/kvm in the nested containers
	sed -i 's/%define enable_qm_mount_bind_kvm 0/%define enable_qm_mount_bind_kvm 1/' ${SPECFILE}
	$(MAKE) VERSION=${VERSION} rpm

.PHONY: qm_dropin_mount_bind_sound
qm_dropin_mount_bind_sound: ##       - QM RPM sub-package to mount bind /dev/snd in the nested containers
	sed -i 's/%define enable_qm_mount_bind_sound 0/%define enable_qm_mount_bind_sound 1/' ${SPECFILE}
	$(MAKE) VERSION=${VERSION} rpm

.PHONY: qm_dropin_mount_bind_tty7
qm_dropin_mount_bind_tty7: ##        - QM RPM sub-package to mount bind /dev/tty7 in the nested containers
	sed -i 's/%define enable_qm_mount_bind_tty7 0/%define enable_qm_mount_bind_tty7 1/' ${SPECFILE}
	$(MAKE) VERSION=${VERSION} rpm

.PHONY: qm_dropin_mount_bind_input
qm_dropin_mount_bind_input: ##       - QM RPM sub-package to mount bind /dev/input in the nested containers
	sed -i 's/%define enable_qm_mount_bind_input 0/%define enable_qm_mount_bind_input 1/' ${SPECFILE}
	$(MAKE) VERSION=${VERSION} rpm

install-policy: all ##             - Install selinux policies only
	semodule -i ${TARGETS}.pp.bz2
	sepolicy manpage --path . --domain ${TARGETS}_t

install: man all ##             - Install QM files (including selinux)
	install -D -pm 644 ${TARGETS}.pp.bz2 ${DESTDIR}${DATADIR}/selinux/packages/qm.pp.bz2
	install -D -pm 644 qm.if ${DESTDIR}${DATADIR}/selinux/devel/include/services/qm.if
	install -D -pm 644 qm_selinux.8 ${DESTDIR}${DATADIR}/man/man8/qm_selinux.8
	install -D -pm 644 qm.8 ${DESTDIR}${DATADIR}/man/man8/qm.8
	install -d -m 755 ${DESTDIR}${DATADIR}/qm
	install -D -m 644 qm_contexts  ${DESTDIR}${DATADIR}/qm/contexts
	install -D -m 755 setup ${DESTDIR}${DATADIR}/qm/setup
	install -D -m 755 tools/comment-tz-local ${DESTDIR}${DATADIR}/qm/comment-tz-local
	install -D -m 755 tools/qm-rootfs ${DESTDIR}${DATADIR}/qm/qm-rootfs
	install -D -m 755 tools/qm-storage-settings ${DESTDIR}${DATADIR}/qm/qm-storage-settings
	install -D -m 755 create-seccomp-rules ${DESTDIR}${DATADIR}/qm/create-seccomp-rules
	install -D -m 644 qm_file_contexts ${DESTDIR}${DATADIR}/qm/file_contexts
	install -D -m 644 containers.conf ${DESTDIR}${DATADIR}/qm/containers.conf
	install -D -m 644 qm.container ${DESTDIR}${DATADIR}/containers/systemd/qm.container
	install -D -m 755 tools/qm-is-ostree ${DESTDIR}${DATADIR}/qm/qm-is-ostree
