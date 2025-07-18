RPM_TOPDIR ?= $(PWD)/rpmbuild
VERSION ?= $(shell cat VERSION)
ROOTDIR ?= $(PWD)
SPECFILE_SUBPACKAGE_TTY7 ?= ${ROOTDIR}/rpm/tty7/tty7.spec
PACKAGE_NAME = qm-mount-bind-tty7

.PHONY: dist
dist: ##             - Creates the QM tty7 package
	cd $(ROOTDIR) && tar cvz \
		--dereference \
		--transform 's|subsystems/tty7/Makefile|Makefile|' \
		--transform 's|rpm/tty7/tty7.spec|tty7.spec|' \
		--transform s/qm/qm-tty7-${VERSION}/ \
		-f /tmp/qm-tty7-${VERSION}.tar.gz \
                ../qm/rpm/tty7/tty7.spec \
		../qm/subsystems/tty7/Makefile \
		../qm/tools/version-update \
		../qm/VERSION \
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
	rpmbuild -ba \
		--define="_topdir ${RPM_TOPDIR}" \
		--define="version ${VERSION}" \
		${SPECFILE_SUBPACKAGE_TTY7}
	if [ ! -f ${RPM_TOPDIR}/RPMS/noarch/${PACKAGE_NAME}-${VERSION}*.noarch.rpm ]; then \
		echo "rpmbuild failed to build: ${PACKAGE_NAME}"; \
		exit 1; \
	fi
