RPM_TOPDIR ?= $(PWD)/rpmbuild
VERSION ?= $(shell cat VERSION)
ROOTDIR ?= $(PWD)
SPECFILE_SUBPACKAGE_VIDEO ?= ${ROOTDIR}/rpm/video/video.spec

.PHONY: dist
dist: ##             - Creates the QM video package
	cd $(ROOTDIR) && tar cvz \
		--dereference \
		--transform s/qm/qm-video-${VERSION}/ \
		-f /tmp/qm-video-${VERSION}.tar.gz \
		../qm/README.md \
		../qm/SECURITY.md \
		../qm/LICENSE \
		../qm/etc/containers/systemd/qm.container.d/qm_dropin_mount_bind_video.conf \
		../qm/subsystems/video/etc/containers/systemd/rear-camera.container
	cd $(ROOTDIR) && mv /tmp/qm-video-${VERSION}.tar.gz ./rpm

.PHONY: video
video: dist ##             - Creates a local RPM package, useful for development
	cd $(ROOTDIR) && mkdir -p ${RPM_TOPDIR}/{RPMS,SRPMS,BUILD,SOURCES}
	cd $(ROOTDIR) && tools/version-update -v ${VERSION}
	cd $(ROOTDIR) && cp ./rpm/qm-video-${VERSION}.tar.gz ${RPM_TOPDIR}/SOURCES
	rpmbuild -ba \
		--define="_topdir ${RPM_TOPDIR}" \
		--define="version ${VERSION}" \
		${SPECFILE_SUBPACKAGE_VIDEO}

