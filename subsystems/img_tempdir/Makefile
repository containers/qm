RPM_TOPDIR ?= $(PWD)/rpmbuild
VERSION ?= $(shell cat VERSION)
ROOTDIR ?= $(PWD)
SPECFILE_SUBPACKAGE_IMG_TEMPDIR ?= ${ROOTDIR}/rpm/img_tempdir/img_tempdir.spec

.PHONY: dist
dist: ##             - Creates the QM img_tempdir package
	cd $(ROOTDIR) && tar cvz \
		--dereference \
		--transform s/qm/qm-img_tempdir-${VERSION}/ \
		-f /tmp/qm-img_tempdir-${VERSION}.tar.gz \
		../qm/README.md \
		../qm/SECURITY.md \
		../qm/LICENSE \
		../qm/etc/qm/containers/containers.conf.d/qm_dropin_img_tempdir.conf
	cd $(ROOTDIR) && mv /tmp/qm-img_tempdir-${VERSION}.tar.gz ./rpm

.PHONY: img_tempdir
img_tempdir: dist ##           - Creates a local RPM package, useful for development
	cd $(ROOTDIR) && mkdir -p ${RPM_TOPDIR}/{RPMS,SRPMS,BUILD,SOURCES}
	cd $(ROOTDIR) && tools/version-update -v ${VERSION}
	cd $(ROOTDIR) && cp ./rpm/qm-img_tempdir-${VERSION}.tar.gz ${RPM_TOPDIR}/SOURCES
	rpmbuild -ba \
		--define="_topdir ${RPM_TOPDIR}" \
		--define="version ${VERSION}" \
		${SPECFILE_SUBPACKAGE_IMG_TEMPDIR}

