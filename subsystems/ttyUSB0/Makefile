SPECFILE_SUBPACKAGE_TTYUSB0=rpm/ttyUSB0/ttyUSB0.spec

.PHONY: dist
dist: ##             - Creates the QM ttyUSB0 package
	cd $(ROOTDIR) && tar cvz \
		--exclude-from=build-aux/exclude_from_tar_gz_subpackage_kvm.txt \
		--dereference \
		--transform s/qm/qm-ttyUSB0-${VERSION}/ \
		-f /tmp/qm-ttyUSB0-${VERSION}.tar.gz \
		../qm/README.md \
		../qm/SECURITY.md \
		../qm/LICENSE \
		../qm/ \
		../qm/etc/qm/containers/containers.conf.d/qm_dropin_mount_bind_ttyUSB0.conf
	cd $(ROOTDIR) && mv /tmp/qm-ttyUSB0-${VERSION}.tar.gz ./rpm

.PHONY: rpm
rpm: dist ##             - Creates a local RPM package, useful for development
	cd $(ROOTDIR) && mkdir -p ${RPM_TOPDIR}/{RPMS,SRPMS,BUILD,SOURCES}
	cd $(ROOTDIR) && tools/version-update -v ${VERSION}
	cd $(ROOTDIR) && cp ./rpm/v${VERSION}.tar.gz ${RPM_TOPDIR}/SOURCES
	cd $(ROOTDIR) && rpmbuild -ba \
		--define="_topdir ${RPM_TOPDIR}" \
		--define="version ${VERSION}" \
		${SPECFILE_SUBPACKAGE_TTYUSB0}

