RPM_TOPDIR ?= $(PWD)/rpmbuild
VERSION ?= $(shell cat VERSION)
ROOTDIR ?= $(PWD)
SPECFILE_SUBPACKAGE_INPUT ?= ${ROOTDIR}/rpm/input/input.spec
PACKAGE_NAME = qm-mount-bind-input

.PHONY: dist
dist: ##             - Creates the QM input package
	cd $(ROOTDIR) && tar cvz \
		--dereference \
		--transform s/qm/qm-input-${VERSION}/ \
		-f /tmp/qm-input-${VERSION}.tar.gz \
		../qm/README.md \
		../qm/SECURITY.md \
		../qm/LICENSE \
		../qm/etc/containers/systemd/qm.container.d/qm_dropin_mount_bind_input.conf
	cd $(ROOTDIR) && mv /tmp/qm-input-${VERSION}.tar.gz ./rpm

.PHONY: input
input:  dist ##             - Creates a local RPM package, useful for development
	cd $(ROOTDIR) && mkdir -p ${RPM_TOPDIR}/{RPMS,SRPMS,BUILD,SOURCES}
	cd $(ROOTDIR) && tools/version-update -v ${VERSION}
	cd $(ROOTDIR) && cp ./rpm/qm-input-${VERSION}.tar.gz ${RPM_TOPDIR}/SOURCES
	rpmbuild -ba \
		--define="_topdir ${RPM_TOPDIR}" \
		--define="version ${VERSION}" \
		${SPECFILE_SUBPACKAGE_INPUT}
	if [ ! -f ${RPM_TOPDIR}/RPMS/noarch/${PACKAGE_NAME}-${VERSION}*.noarch.rpm ]; then \
		echo "rpmbuild failed to build: ${PACKAGE_NAME}"; \
		exit 1; \
	fi