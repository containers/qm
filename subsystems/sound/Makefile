TMPDIR ?= /var/tmp
RPM_TOPDIR ?= $(PWD)/rpmbuild
VERSION ?= $(shell cat VERSION)
ROOTDIR ?= $(PWD)
SPECFILE_SUBPACKAGE_SOUND ?= ${ROOTDIR}/rpm/sound/sound.spec
PACKAGE_NAME = qm-sound

.PHONY: dist
dist: ##             - Creates the QM sound package
	cd $(ROOTDIR) && tar -czf $(TMPDIR)/qm-sound-$(VERSION).tar.gz \
		--transform 's|^|qm-sound-$(VERSION)/|' \
		rpm/sound/sound.spec \
		subsystems/sound/Makefile \
		VERSION \
		README.md \
		SECURITY.md \
		LICENSE \
		data/qmc.conf.d/60-qm-sound.conf \
		subsystems/sound/etc/containers/systemd/audio.container
	mv $(TMPDIR)/qm-sound-$(VERSION).tar.gz $(ROOTDIR)/rpm

.PHONY: sound
sound: dist ##             - Creates a local RPM package, useful for development
	cd $(ROOTDIR) && mkdir -p ${RPM_TOPDIR}/{RPMS,SRPMS,BUILD,SOURCES}
	cd $(ROOTDIR) && cp ./rpm/qm-sound-${VERSION}.tar.gz ${RPM_TOPDIR}/SOURCES
	rpmbuild -ba \
		--define="_topdir ${RPM_TOPDIR}" \
		--define="version ${VERSION}" \
		${SPECFILE_SUBPACKAGE_SOUND}
	if [ ! -f ${RPM_TOPDIR}/RPMS/noarch/${PACKAGE_NAME}-${VERSION}*.noarch.rpm ]; then \
		echo "rpmbuild failed to build: ${PACKAGE_NAME}"; \
		exit 1; \
	fi