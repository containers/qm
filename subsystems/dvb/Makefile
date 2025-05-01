RPM_TOPDIR ?= $(PWD)/rpmbuild
VERSION ?= $(shell cat VERSION)
ROOTDIR ?= $(PWD)
SPECFILE_SUBPACKAGE_DVB ?= ${ROOTDIR}/rpm/dvb/dvb.spec

.PHONY: dist
dist: ##             - Creates the QM dvb package
	cd $(ROOTDIR) && tar cvz \
		--dereference \
		--transform s/qm/qm-dvb-${VERSION}/ \
		-f /tmp/qm-dvb-${VERSION}.tar.gz \
		../qm/README.md \
		../qm/SECURITY.md \
		../qm/LICENSE \
		../qm/etc/containers/systemd/qm.container.d/qm_dropin_mount_bind_dvb.conf
	cd $(ROOTDIR) && mv /tmp/qm-dvb-${VERSION}.tar.gz ./rpm

.PHONY: dvb
dvb: dist ##             - Creates a local RPM package, useful for development
	cd $(ROOTDIR) && mkdir -p ${RPM_TOPDIR}/{RPMS,SRPMS,BUILD,SOURCES}
	cd $(ROOTDIR) && tools/version-update -v ${VERSION}
	cd $(ROOTDIR) && cp ./rpm/qm-dvb-${VERSION}.tar.gz ${RPM_TOPDIR}/SOURCES
	rpmbuild -ba \
		--define="_topdir ${RPM_TOPDIR}" \
		--define="version ${VERSION}" \
		${SPECFILE_SUBPACKAGE_DVB}

