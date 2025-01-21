RPM_TOPDIR ?= $(PWD)/rpmbuild
VERSION ?= $(shell cat VERSION)
ROOTDIR ?= $(PWD)
SPECFILE_SUBPACKAGE_IMG_WINDOWMANAGER ?= ${ROOTDIR}/rpm/windowmanager/windowmanager.spec

.PHONY: dist
dist: ##             - Creates the QM windowmanager package
	cd $(ROOTDIR) && tar cvz \
		--dereference \
		--transform 's|subsystems/windowmanager/Makefile|Makefile|' \
		--transform 's|rpm/windowmanager/windowmanager.spec|windowmanager.spec|' \
		--transform s/qm/qm-windowmanager-${VERSION}/ \
		-f /tmp/qm-windowmanager-${VERSION}.tar.gz \
		../qm/README.md \
		../qm/SECURITY.md \
		../qm/LICENSE \
		../qm/subsystems/windowmanager/etc/containers/systemd/ \
		../qm/subsystems/windowmanager/etc/pam.d/wayland \
		../qm/etc/containers/systemd/qm.container.d/qm_dropin_mount_bind_window_manager.conf
	cd $(ROOTDIR) && mv /tmp/qm-windowmanager-${VERSION}.tar.gz ./rpm

.PHONY: windowmanager
windowmanager: dist ##         - Creates a local windowmanager package, useful for development
	cd $(ROOTDIR) && mkdir -p ${RPM_TOPDIR}/{RPMS,SRPMS,BUILD,SOURCES}
	cd $(ROOTDIR) && tools/version-update -v ${VERSION}
	cp ./rpm/qm-windowmanager-${VERSION}.tar.gz ${RPM_TOPDIR}/SOURCES
	rpmbuild -ba \
		--define="_topdir ${RPM_TOPDIR}" \
		--define="version ${VERSION}" \
		${SPECFILE_SUBPACKAGE_IMG_WINDOWMANAGER}

