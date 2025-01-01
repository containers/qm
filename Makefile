TARGETS ?= qm
MODULES ?= ${TARGETS:=.pp.bz2}
DESTDIR ?=
PREFIX ?= /usr
DATADIR ?= $(PREFIX)/share
LIBDIR ?= $(PREFIX)/lib
SYSCONFDIR?=/etc
QMDIR=/usr/lib/qm
SPECFILE=rpm/qm.spec
SPECFILE_SUBPACKAGE_KVM=rpm/kvm/qm-kvm.spec
SPECFILE_SUBPACKAGE_SOUND=rpm/sound/sound.spec
SPECFILE_SUBPACKAGE_VIDEO=rpm/video/video.spec
SPECFILE_SUBPACKAGE_RADIO=rpm/radio/radio.spec
SPECFILE_SUBPACKAGE_DVB=rpm/dvb/dvb.spec
SPECFILE_SUBPACKAGE_TTY7=rpm/tty7/tty7.spec
SPECFILE_SUBPACKAGE_INPUT=rpm/input/input.spec
SPECFILE_SUBPACKAGE_IMG_WINDOWMANAGER=rpm/windowmanager/windowmanager.spec
SPECFILE_SUBPACKAGE_TTYUSB0=rpm/ttyUSB0/ttyUSB0.spec
SPECFILE_SUBPACKAGE_IMG_TEMPDIR=rpm/img_tempdir/img_tempdir.spec
SPECFILE_SUBPACKAGE_ROS2_ROLLING=rpm/ros2/rolling/ros2_rolling.spec
RPM_TOPDIR ?= $(PWD)/rpmbuild
VERSION ?= $(shell cat VERSION)

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
	tar cvz \
		--exclude-from=build-aux/exclude_from_tar_gz_subpackage_kvm.txt \
		--dereference \
		--transform s/qm/qm-kvm-${VERSION}/ \
		-f /tmp/qm-kvm-${VERSION}.tar.gz \
		../qm/README.md \
		../qm/SECURITY.md \
		../qm/LICENSE \
		../qm/ \
		../qm/etc/containers/systemd/qm.container.d/qm_dropin_mount_bind_kvm.conf
	mv /tmp/qm-kvm-${VERSION}.tar.gz ./rpm

.PHONY: rpm
rpm: clean dist ##             - Creates a local RPM package, useful for development
	mkdir -p ${RPM_TOPDIR}/{RPMS,SRPMS,BUILD,SOURCES}
	tools/version-update -v ${VERSION}
	cp ./rpm/v${VERSION}.tar.gz ${RPM_TOPDIR}/SOURCES
	rpmbuild -ba \
		--define="_topdir ${RPM_TOPDIR}" \
		--define="version ${VERSION}" \
		${SPECFILE}

.PHONY: kvm_subpackage
kvm_subpackage: clean dist ##             - Creates a local RPM package, useful for development
	mkdir -p ${RPM_TOPDIR}/{RPMS,SRPMS,BUILD,SOURCES}
	tools/version-update -v ${VERSION}
	cp ./rpm/v${VERSION}.tar.gz ${RPM_TOPDIR}/SOURCES
	rpmbuild -ba \
		--define="_topdir ${RPM_TOPDIR}" \
		--define="version ${VERSION}" \
		${SPECFILE_SUBPACKAGE_KVM}

.PHONY: ros2_rolling_subpackage
ros2_rolling_subpackage: clean dist ##          - Creates a local RPM package, useful for development
	mkdir -p ${RPM_TOPDIR}/{RPMS,SRPMS,BUILD,SOURCES}
	tools/version-update -v ${VERSION}
	cp ./rpm/v${VERSION}.tar.gz ${RPM_TOPDIR}/SOURCES
	rpmbuild -ba \
		--define="_topdir ${RPM_TOPDIR}" \
		--define="version ${VERSION}" \
		${SPECFILE_SUBPACKAGE_ROS2_ROLLING}

.PHONY: sound_subpackage
sound_subpackage: clean dist ##             - Creates a local RPM package, useful for development
	mkdir -p ${RPM_TOPDIR}/{RPMS,SRPMS,BUILD,SOURCES}
	tools/version-update -v ${VERSION}
	cp ./rpm/v${VERSION}.tar.gz ${RPM_TOPDIR}/SOURCES
	rpmbuild -ba \
		--define="_topdir ${RPM_TOPDIR}" \
		--define="version ${VERSION}" \
		${SPECFILE_SUBPACKAGE_SOUND}

.PHONY: video_subpackage
video_subpackage: clean dist ##             - Creates a local RPM package, useful for development
	mkdir -p ${RPM_TOPDIR}/{RPMS,SRPMS,BUILD,SOURCES}
	tools/version-update -v ${VERSION}
	cp ./rpm/v${VERSION}.tar.gz ${RPM_TOPDIR}/SOURCES
	rpmbuild -ba \
		--define="_topdir ${RPM_TOPDIR}" \
		--define="version ${VERSION}" \
		${SPECFILE_SUBPACKAGE_VIDEO}

.PHONY: radio_subpackage
radio_subpackage: clean dist ##             - Creates a local RPM package, useful for development
	mkdir -p ${RPM_TOPDIR}/{RPMS,SRPMS,BUILD,SOURCES}
	tools/version-update -v ${VERSION}
	cp ./rpm/v${VERSION}.tar.gz ${RPM_TOPDIR}/SOURCES
	rpmbuild -ba \
		--define="_topdir ${RPM_TOPDIR}" \
		--define="version ${VERSION}" \
		${SPECFILE_SUBPACKAGE_RADIO}

.PHONY: dvb_subpackage
dvb_subpackage: clean dist ##             - Creates a local RPM package, useful for development
	mkdir -p ${RPM_TOPDIR}/{RPMS,SRPMS,BUILD,SOURCES}
	tools/version-update -v ${VERSION}
	cp ./rpm/v${VERSION}.tar.gz ${RPM_TOPDIR}/SOURCES
	rpmbuild -ba \
		--define="_topdir ${RPM_TOPDIR}" \
		--define="version ${VERSION}" \
		${SPECFILE_SUBPACKAGE_DVB}

.PHONY: tty7_subpackage
tty7_subpackage: clean dist ##             - Creates a local RPM package, useful for development
	mkdir -p ${RPM_TOPDIR}/{RPMS,SRPMS,BUILD,SOURCES}
	tools/version-update -v ${VERSION}
	cp ./rpm/v${VERSION}.tar.gz ${RPM_TOPDIR}/SOURCES
	rpmbuild -ba \
		--define="_topdir ${RPM_TOPDIR}" \
		--define="version ${VERSION}" \
		${SPECFILE_SUBPACKAGE_TTY7}

.PHONY: input_subpackage
input_subpackage: clean dist ##             - Creates a local RPM package, useful for development
	mkdir -p ${RPM_TOPDIR}/{RPMS,SRPMS,BUILD,SOURCES}
	tools/version-update -v ${VERSION}
	cp ./rpm/v${VERSION}.tar.gz ${RPM_TOPDIR}/SOURCES
	rpmbuild -ba \
		--define="_topdir ${RPM_TOPDIR}" \
		--define="version ${VERSION}" \
		${SPECFILE_SUBPACKAGE_INPUT}

.PHONY: ttyUSB0_subpackage
ttyUSB0_subpackage: clean dist ##             - Creates a local RPM package, useful for development
	mkdir -p ${RPM_TOPDIR}/{RPMS,SRPMS,BUILD,SOURCES}
	tools/version-update -v ${VERSION}
	cp ./rpm/v${VERSION}.tar.gz ${RPM_TOPDIR}/SOURCES
	rpmbuild -ba \
		--define="_topdir ${RPM_TOPDIR}" \
		--define="version ${VERSION}" \
		${SPECFILE_SUBPACKAGE_TTYUSB0}

.PHONY: img_tempdir_subpackage
img_tempdir_subpackage: clean dist ##           - Creates a local RPM package, useful for development
	mkdir -p ${RPM_TOPDIR}/{RPMS,SRPMS,BUILD,SOURCES}
	tools/version-update -v ${VERSION}
	cp ./rpm/v${VERSION}.tar.gz ${RPM_TOPDIR}/SOURCES
	rpmbuild -ba \
		--define="_topdir ${RPM_TOPDIR}" \
		--define="version ${VERSION}" \
		${SPECFILE_SUBPACKAGE_IMG_TEMPDIR}

.PHONY: windowmanager_subpackage
windowmanager_subpackage: clean dist ##         - Creates a local RPM package, useful for development
	mkdir -p ${RPM_TOPDIR}/{RPMS,SRPMS,BUILD,SOURCES}
	tools/version-update -v ${VERSION}
	cp ./rpm/v${VERSION}.tar.gz ${RPM_TOPDIR}/SOURCES
	rpmbuild -ba \
		--define="_topdir ${RPM_TOPDIR}" \
		--define="version ${VERSION}" \
		${SPECFILE_SUBPACKAGE_IMG_WINDOWMANAGER}

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
