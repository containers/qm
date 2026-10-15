TMPDIR ?= /var/tmp
RPM_TOPDIR ?= $(PWD)/rpmbuild
VERSION ?= $(shell cat VERSION)
ROOTDIR ?= $(PWD)
SPECFILE_SUBPACKAGE_VIDEO ?= ${ROOTDIR}/rpm/video/video.spec
PACKAGE_NAME = qm-mount-bind-video

.PHONY: dist
dist: ##             - Creates the QM video package
	cd $(ROOTDIR) && tar -czf $(TMPDIR)/qm-video-$(VERSION).tar.gz \
		--transform 's|^|qm-video-$(VERSION)/|' \
		rpm/video/video.spec \
		subsystems/video/Makefile \
		VERSION \
		README.md \
		SECURITY.md \
		LICENSE \
		data/qmc.conf.d/60-qm-video.conf \
		subsystems/video/etc/containers/systemd/rear-camera.container
	mv $(TMPDIR)/qm-video-$(VERSION).tar.gz $(ROOTDIR)/rpm

.PHONY: video
video: dist ##             - Creates a local RPM package, useful for development
	cd $(ROOTDIR) && mkdir -p ${RPM_TOPDIR}/{RPMS,SRPMS,BUILD,SOURCES}
	cd $(ROOTDIR) && cp ./rpm/qm-video-${VERSION}.tar.gz ${RPM_TOPDIR}/SOURCES
	rpmbuild -ba \
		--define="_topdir ${RPM_TOPDIR}" \
		--define="version ${VERSION}" \
		${SPECFILE_SUBPACKAGE_VIDEO}
	if [ ! -f ${RPM_TOPDIR}/RPMS/noarch/${PACKAGE_NAME}-${VERSION}*.noarch.rpm ]; then \
		echo "rpmbuild failed to build: ${PACKAGE_NAME}"; \
		exit 1; \
	fi
