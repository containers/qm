RPM_TOPDIR ?= $(PWD)/rpmbuild
VERSION ?= $(shell cat VERSION)
ROOTDIR ?= $(PWD)
SPECFILE_SUBPACKAGE_TEXT2SPEECH ?= ${ROOTDIR}/rpm/text2speech/text2speech.spec
PACKAGE_NAME = qm-text2speech

.PHONY: dist
dist: ##             - Creates the QM input package
	cd $(ROOTDIR) && tar cvz \
		--dereference \
                --transform 's|subsystems/text2speech/Makefile|Makefile|' \
                --transform 's|rpm/text2speech/text2speech.spec|text2speech.spec|' \
		--transform s/qm/qm-text2speech-${VERSION}/ \
		-f /tmp/qm-text2speech-${VERSION}.tar.gz \
                ../qm/rpm/text2speech/text2speech.spec \
                ../qm/subsystems/text2speech/Makefile \
                ../qm/tools/version-update \
                ../qm/VERSION \
		../qm/README.md \
		../qm/CODE-OF-CONDUCT.md \
		../qm/SECURITY.md \
		../qm/LICENSE
	cd $(ROOTDIR) && mv /tmp/qm-text2speech-${VERSION}.tar.gz ./rpm

.PHONY: text2speech
text2speech: dist ##            - Creates a local RPM package, useful for development
	cd $(ROOTDIR) && mkdir -p ${RPM_TOPDIR}/{RPMS,SRPMS,BUILD,SOURCES}
	cd $(ROOTDIR) && tools/version-update -v ${VERSION}
	cd $(ROOTDIR) && cp ./rpm/qm-text2speech-${VERSION}.tar.gz ${RPM_TOPDIR}/SOURCES
	cd $(ROOTDIR) && rpmbuild -ba \
		--define="_topdir ${RPM_TOPDIR}" \
		--define="version ${VERSION}" \
		${SPECFILE_SUBPACKAGE_TEXT2SPEECH}
	if [ ! -f ${RPM_TOPDIR}/RPMS/noarch/${PACKAGE_NAME}-${VERSION}*.noarch.rpm ]; then \
		echo "rpmbuild failed to build: ${PACKAGE_NAME}"; \
		exit 1; \
	fi