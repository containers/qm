SPECFILE_SUBPACKAGE_KVM=rpm/kvm/qm-kvm.spec

.PHONY: dist
dist: ##             - Creates the QM kvm package
	cd $(ROOTDIR) && tar cvz \
		--exclude-from=build-aux/exclude_from_tar_gz_subpackage_kvm.txt \
		--dereference \
		--transform s/qm/qm-kvm-${VERSION}/ \
		-f /tmp/qm-kvm-${VERSION}.tar.gz \
		../qm/README.md \
		../qm/SECURITY.md \
		../qm/LICENSE \
		../qm/ \
		../qm/etc/containers/systemd/qm.container.d/qm_dropin_mount_bind_kvm.conf
	cd $(ROOTDIR) && mv /tmp/qm-kvm-${VERSION}.tar.gz ./rpm

.PHONY: rpm
rpm: dist ##             - Creates a local RPM windowmanager package, useful for development
	cd $(ROOTDIR) && mkdir -p ${RPM_TOPDIR}/{RPMS,SRPMS,BUILD,SOURCES}
	cd $(ROOTDIR) && tools/version-update -v ${VERSION}
	cd $(ROOTDIR) && cp ./rpm/v${VERSION}.tar.gz ${RPM_TOPDIR}/SOURCES
	cd $(ROOTDIR) && rpmbuild -ba \
	       	--define="_topdir ${RPM_TOPDIR}" \
		--define="version ${VERSION}" \
		${SPECFILE_SUBPACKAGE_IMG_WINDOWMANAGER}

