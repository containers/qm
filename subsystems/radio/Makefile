RPM_TOPDIR ?= $(PWD)/rpmbuild
VERSION ?= $(shell cat VERSION)
ROOTDIR ?= $(PWD)
SPECFILE_SUBPACKAGE_RADIO ?= ${ROOTDIR}/rpm/radio/radio.spec

.PHONY: dist
dist: ##             - Creates the QM radio package
	cd $(ROOTDIR) && tar cvz \
		--dereference \
		--transform s/qm/qm-radio-${VERSION}/ \
		-f /tmp/qm-radio-${VERSION}.tar.gz \
		../qm/README.md \
		../qm/SECURITY.md \
		../qm/LICENSE \
        ../qm/etc/containers/systemd/qm.container.d/qm_dropin_mount_bind_radio.conf
	cd $(ROOTDIR) && mv /tmp/qm-radio-${VERSION}.tar.gz ./rpm


.PHONY: radio
radio: dist ##             - Creates a local RPM package, useful for development
	cd $(ROOTDIR) && mkdir -p ${RPM_TOPDIR}/{RPMS,SRPMS,BUILD,SOURCES}
	cd $(ROOTDIR) && tools/version-update -v ${VERSION}
	cd $(ROOTDIR) && cp ./rpm/qm-radio-${VERSION}.tar.gz ${RPM_TOPDIR}/SOURCES
	rpmbuild -ba \
		--define="_topdir ${RPM_TOPDIR}" \
		--define="version ${VERSION}" \
		${SPECFILE_SUBPACKAGE_RADIO}

