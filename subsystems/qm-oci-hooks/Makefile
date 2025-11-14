RPM_TOPDIR ?= $(PWD)/rpmbuild
VERSION ?= $(shell grep '^Version:' ${ROOTDIR}/rpm/oci-hooks/qm-oci-hooks.spec | awk '{print $$2}')
ROOTDIR ?= $(PWD)
SPECFILE_SUBPACKAGE_OCI_HOOKS ?= ${ROOTDIR}/rpm/oci-hooks/qm-oci-hooks.spec
PACKAGE_NAME = qm-oci-hooks

.PHONY: dist
dist: ##             - Creates the QM OCI hooks package
	cd $(ROOTDIR) && tar cvz \
		--dereference \
		--transform 's|subsystems/qm-oci-hooks/Makefile|Makefile|' \
		--transform 's|rpm/oci-hooks/qm-oci-hooks.spec|qm-oci-hooks.spec|' \
		--transform 's|qm|qm-oci-hooks-${VERSION}|' \
		-f /tmp/qm-oci-hooks-${VERSION}.tar.gz \
		../qm/rpm/oci-hooks/qm-oci-hooks.spec \
		../qm/subsystems/qm-oci-hooks/Makefile \
		../qm/tools/version-update \
		../qm/VERSION \
		../qm/README.md \
		../qm/SECURITY.md \
		../qm/LICENSE \
		../qm/CODE-OF-CONDUCT.md \
		../qm/oci-hooks/qm-device-manager/oci-qm-device-manager \
		../qm/oci-hooks/qm-device-manager/oci-qm-device-manager.json \
		../qm/oci-hooks/qm-seat-manager/oci-qm-seat-manager.json \
		../qm/oci-hooks/qm-device-manager/README.md \
		../qm/oci-hooks/wayland-client-devices/oci-qm-wayland-client-devices \
		../qm/oci-hooks/wayland-client-devices/oci-qm-wayland-client-devices.json \
		../qm/oci-hooks/wayland-client-devices/README.md \
		../qm/oci-hooks/lib/common.sh \
		../qm/oci-hooks/lib/device-support.sh
	cd $(ROOTDIR) && mv /tmp/qm-oci-hooks-${VERSION}.tar.gz ./rpm

.PHONY: qm-oci-hooks
qm-oci-hooks: dist ##     - Creates a local RPM package, useful for development
	@echo ${VERSION}
	cd $(ROOTDIR) && mkdir -p ${RPM_TOPDIR}/{RPMS,SRPMS,BUILD,SOURCES}
	cd $(ROOTDIR) && tools/version-update -v ${VERSION}
	cd $(ROOTDIR) && cp ./rpm/qm-oci-hooks-${VERSION}.tar.gz ${RPM_TOPDIR}/SOURCES
	rpmbuild -ba \
		--define="_topdir ${RPM_TOPDIR}" \
		--define="version ${VERSION}" \
		${SPECFILE_SUBPACKAGE_OCI_HOOKS}
	if [ ! -f ${RPM_TOPDIR}/RPMS/noarch/${PACKAGE_NAME}-${VERSION}*.noarch.rpm ]; then \
		echo "rpmbuild failed to build: ${PACKAGE_NAME}"; \
		exit 1; \
	fi
