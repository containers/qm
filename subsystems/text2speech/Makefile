SPECFILE_SUBPACKAGE_TEXT2SPEECH=rpm/text2speech/text2speech.spec

.PHONY: dist
dist: ##             - Creates the QM input package
	cd $(ROOTDIR) && tar cvz \
		--exclude-from=build-aux/exclude_from_tar_gz_subpackage_kvm.txt \
		--dereference \
		--transform s/qm/qm-text2speech-${VERSION}/ \
		-f /tmp/qm-text2speech-${VERSION}.tar.gz \
		../qm/README.md \
		../qm/SECURITY.md \
		../qm/LICENSE \
		../qm/
	cd $(ROOTDIR) && mv /tmp/qm-text2speech-${VERSION}.tar.gz ./rpm

.PHONY: rpm
rpm: dist ##            - Creates a local RPM package, useful for development
	cd $(ROOTDIR) && mkdir -p ${RPM_TOPDIR}/{RPMS,SRPMS,BUILD,SOURCES}
	cd $(ROOTDIR) && tools/version-update -v ${VERSION}
	cd $(ROOTDIR) && cp ./rpm/v${VERSION}.tar.gz ${RPM_TOPDIR}/SOURCES
	cd $(ROOTDIR) && rpmbuild -ba \
		--define="_topdir ${RPM_TOPDIR}" \
		--define="version ${VERSION}" \
		${SPECFILE_SUBPACKAGE_TEXT2SPEECH}
