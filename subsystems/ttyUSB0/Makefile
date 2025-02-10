RPM_TOPDIR ?= $(PWD)/rpmbuild
VERSION ?= $(shell cat VERSION)
ROOTDIR ?= $(PWD)
SPECFILE_SUBPACKAGE_TTYUSB0 ?= ${ROOTDIR}/rpm/ttyUSB0/ttyUSB0.spec

.PHONY: dist
dist: ##             - Creates the QM ttyUSB0 package
	cd $(ROOTDIR) && tar cvz \
		--dereference \
		--transform s/qm/qm-ttyUSB0-${VERSION}/ \
		-f /tmp/qm-ttyUSB0-${VERSION}.tar.gz \
		../qm/README.md \
		../qm/SECURITY.md \
		../qm/LICENSE \
		../qm/etc/containers/systemd/qm.container.d/qm_dropin_mount_bind_ttyUSB0.conf
	cd $(ROOTDIR) && mv /tmp/qm-ttyUSB0-${VERSION}.tar.gz ./rpm

.PHONY: ttyusb0
ttyusb0: dist ##             - Creates a local RPM package, useful for development
	cd $(ROOTDIR) && mkdir -p ${RPM_TOPDIR}/{RPMS,SRPMS,BUILD,SOURCES}
	cd $(ROOTDIR) && tools/version-update -v ${VERSION}
	cd $(ROOTDIR) && cp ./rpm/qm-ttyUSB0${VERSION}.tar.gz ${RPM_TOPDIR}/SOURCES
	rpmbuild -ba \
		--define="_topdir ${RPM_TOPDIR}" \
		--define="version ${VERSION}" \
		${SPECFILE_SUBPACKAGE_TTYUSB0}

