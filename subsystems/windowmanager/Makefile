SPECFILE_SUBPACKAGE_IMG_WINDOWMANAGER=rpm/windowmanager/windowmanager.spec

.PHONY: dist
dist: ##             - Creates the QM windowmanager package
	cd $(ROOTDIR) && tar cvz \
		--exclude-from=build-aux/exclude_from_tar_gz_subpackage_kvm.txt \
		--dereference \
		--transform s/qm/windowmanager-${VERSION}/ \
		-f /tmp/qm-windowmanager-${VERSION}.tar.gz \
		../qm/README.md \
		../qm/SECURITY.md \
		../qm/LICENSE \
		../qm/ \
                ../qm/etc/containers/systemd/qm.container.d/qm_dropin_mount_bind_window_manager.conf
	cd $(ROOTDIR) && mv /tmp/qm-windowmanager-${VERSION}.tar.gz ./rpm

.PHONY: rpm
rpm: dist ##         - Creates a local windowmanager package, useful for development
	mkdir -p ${RPM_TOPDIR}/{RPMS,SRPMS,BUILD,SOURCES}
	tools/version-update -v ${VERSION}
	cp ./rpm/v${VERSION}.tar.gz ${RPM_TOPDIR}/SOURCES
	rpmbuild -ba \
		--define="_topdir ${RPM_TOPDIR}" \
		--define="version ${VERSION}" \
		${SPECFILE_SUBPACKAGE_IMG_WINDOWMANAGER}

