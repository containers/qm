RPM_TOPDIR ?= $(PWD)/rpmbuild
VERSION ?= $(shell cat VERSION)
ROOTDIR ?= $(PWD)
SPECFILE_SUBPACKAGE_IMG_KVM ?= ${ROOTDIR}/rpm/kvm/qm-kvm.spec
PACKAGE_NAME = qm-kvm

.PHONY: dist
dist: ##             - Creates the QM kvm package
	cd ${ROOTDIR} && tar cvz \
		--dereference \
		--transform 's|subsystems/kvm/Makefile|Makefile|' \
		--transform 's|rpm/kvm/qm-kvm.spec|qm-kvm.spec|' \
		--transform 's|qm|qm-kvm-${VERSION}|' \
		-f /tmp/qm-kvm-${VERSION}.tar.gz \
		../qm/rpm/kvm/qm-kvm.spec \
		../qm/subsystems/kvm/Makefile \
		../qm/tools/version-update \
		../qm/VERSION \
		../qm/README.md \
		../qm/SECURITY.md \
		../qm/LICENSE \
		../qm/etc/containers/systemd/qm.container.d/qm_dropin_mount_bind_kvm.conf \
		../qm/subsystems/kvm/etc/containers/systemd/kvm.container

	cd ${ROOTDIR} && mv /tmp/qm-kvm-${VERSION}.tar.gz ./rpm

.PHONY: kvm
kvm: dist ##             - Creates a local RPM kvm package, useful for development
	@echo ${VERSION}
	cd ${ROOTDIR} && mkdir -p ${RPM_TOPDIR}/{RPMS,SRPMS,BUILD,SOURCES}
	cd ${ROOTDIR} && cp ./rpm/qm-kvm-${VERSION}.tar.gz ${RPM_TOPDIR}/SOURCES
	rpmbuild -ba \
		--define="_topdir ${RPM_TOPDIR}" \
		--define="version ${VERSION}" \
		${SPECFILE_SUBPACKAGE_IMG_KVM}
	if [ ! -f ${RPM_TOPDIR}/RPMS/noarch/${PACKAGE_NAME}-${VERSION}*.noarch.rpm ]; then \
		echo "rpmbuild failed to build: ${PACKAGE_NAME}"; \
		exit 1; \
	fi
