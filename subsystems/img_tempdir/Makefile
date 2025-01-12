SPECFILE_SUBPACKAGE_IMG_TEMPDIR=rpm/img_tempdir/img_tempdir.spec

.PHONY: dist
dist: ##             - Creates the QM img_tempdir package
	cd $(ROOTDIR) && tar cvz \
		--exclude-from=build-aux/exclude_from_tar_gz_subpackage_kvm.txt \
		--dereference \
		--transform s/qm/qm-img_tempdir-${VERSION}/ \
		-f /tmp/qm-img_tempdir-${VERSION}.tar.gz \
		../qm/README.md \
		../qm/SECURITY.md \
		../qm/LICENSE \
		../qm/ \
		../qm/etc/qm/containers/containers.conf.d/qm_dropin_img_tempdir.conf
	cd $(ROOTDIR) && mv /tmp/qm-img_tempdir-${VERSION}.tar.gz ./rpm

.PHONY: rpm
rpm: dist ##           - Creates a local RPM package, useful for development
	mkdir -p ${RPM_TOPDIR}/{RPMS,SRPMS,BUILD,SOURCES}
	tools/version-update -v ${VERSION}
	cp ./rpm/v${VERSION}.tar.gz ${RPM_TOPDIR}/SOURCES
		rpmbuild -ba \
		--define="_topdir ${RPM_TOPDIR}" \
		--define="version ${VERSION}" \
		${SPECFILE_SUBPACKAGE_IMG_TEMPDIR}

