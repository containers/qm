RPM_TOPDIR ?= $(PWD)/rpmbuild
VERSION ?= $(shell cat VERSION)
ROOTDIR ?= $(PWD)
SPECFILE_SUBPACKAGE_VIDEO ?= ${ROOTDIR}/rpm/video/video.spec
PACKAGE_NAME = qm-mount-bind-video

.PHONY: dist
dist: ##             - Creates the QM video package
	cd $(ROOTDIR) && tar cvz \
		--dereference \
                --transform 's|subsystems/video/Makefile|Makefile|' \
                --transform 's|rpm/video/video.spec|video.spec|' \
		--transform s/qm/qm-video-${VERSION}/ \
		-f /tmp/qm-video-${VERSION}.tar.gz \
		../qm/rpm/video/video.spec \
                ../qm/subsystems/video/Makefile \
                ../qm/tools/version-update \
                ../qm/VERSION \
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
	if [ ! -f ${RPM_TOPDIR}/RPMS/noarch/${PACKAGE_NAME}-${VERSION}*.noarch.rpm ]; then \
		echo "rpmbuild failed to build: ${PACKAGE_NAME}"; \
		exit 1; \
	fi
