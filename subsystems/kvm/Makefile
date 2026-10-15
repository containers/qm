TMPDIR ?= /var/tmp
RPM_TOPDIR ?= $(PWD)/rpmbuild
VERSION ?= $(shell cat VERSION)
ROOTDIR ?= $(PWD)
SPECFILE_SUBPACKAGE_IMG_KVM ?= ${ROOTDIR}/rpm/kvm/qm-kvm.spec
PACKAGE_NAME = qm-kvm

.PHONY: dist
dist: ##             - Creates the QM kvm package
	cd $(ROOTDIR) && tar -czf $(TMPDIR)/qm-kvm-$(VERSION).tar.gz \
		--transform 's|^|qm-kvm-$(VERSION)/|' \
		rpm/kvm/qm-kvm.spec \
		subsystems/kvm/Makefile \
		VERSION \
		README.md \
		SECURITY.md \
		LICENSE \
		data/qmc.conf.d/60-qm-kvm.conf \
		subsystems/kvm/etc/containers/systemd/kvm.container
	mv $(TMPDIR)/qm-kvm-$(VERSION).tar.gz $(ROOTDIR)/rpm

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
