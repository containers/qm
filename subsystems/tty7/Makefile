SPECFILE_SUBPACKAGE_TTY7=rpm/tty7/tty7.spec

.PHONY: dist
dist: ##             - Creates the QM tty7 package
	cd $(ROOTDIR) && tar cvz \
		--dereference \
		--transform s/qm/qm-tty7-${VERSION}/ \
		-f /tmp/qm-tty7-${VERSION}.tar.gz \
		../qm/README.md \
		../qm/SECURITY.md \
		../qm/LICENSE \
		../qm/etc/containers/systemd/qm.container.d/qm_dropin_mount_bind_tty7.conf
	cd $(ROOTDIR) && mv /tmp/qm-tty7-${VERSION}.tar.gz ./rpm

.PHONY: tty7
tty7: dist ##             - Creates a local RPM package, useful for development
	cd $(ROOTDIR) && mkdir -p ${RPM_TOPDIR}/{RPMS,SRPMS,BUILD,SOURCES}
	cd $(ROOTDIR) && tools/version-update -v ${VERSION}
	cd $(ROOTDIR) && cp ./rpm/qm-tty7-${VERSION}.tar.gz ${RPM_TOPDIR}/SOURCES
	cd $(ROOTDIR) && rpmbuild -ba \
		--define="_topdir ${RPM_TOPDIR}" \
		--define="version ${VERSION}" \
		${SPECFILE_SUBPACKAGE_TTY7}

