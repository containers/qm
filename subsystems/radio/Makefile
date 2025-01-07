SPECFILE_SUBPACKAGE_RADIO=rpm/radio/radio.spec

.PHONY: dist
dist: ##             - Creates the QM radio package
	cd $(ROOTDIR) && tar cvz \
		--exclude-from=build-aux/exclude_from_tar_gz_subpackage_kvm.txt \
		--dereference \
		--transform s/qm/qm-radio-${VERSION}/ \
		-f /tmp/qm-radio-${VERSION}.tar.gz \
		../qm/README.md \
		../qm/SECURITY.md \
		../qm/LICENSE \
		../qm/ \
                ../qm/etc/containers/systemd/qm.container.d/qm_dropin_mount_bind_radio.conf
	cd $(ROOTDIR) && mv /tmp/qm-radio-${VERSION}.tar.gz ./rpm


.PHONY: rpm
	rpm: dist ##             - Creates a local RPM package, useful for development
	mkdir -p ${RPM_TOPDIR}/{RPMS,SRPMS,BUILD,SOURCES}
	tools/version-update -v ${VERSION}
	cp ./rpm/v${VERSION}.tar.gz ${RPM_TOPDIR}/SOURCES
	rpmbuild -ba \
		--define="_topdir ${RPM_TOPDIR}" \
		--define="version ${VERSION}" \
		${SPECFILE_SUBPACKAGE_RADIO}

