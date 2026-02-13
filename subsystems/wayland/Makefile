ROOTDIR ?= $(PWD)
RPM_TOPDIR ?= $(ROOTDIR)/rpmbuild
VERSION ?= $(shell grep '^Version:' $(ROOTDIR)/rpm/wayland/qm-wayland.spec | awk '{print $$2}')
SPECFILE_SUBPACKAGE_WAYLAND ?= ${ROOTDIR}/rpm/wayland/qm-wayland.spec
PACKAGE_NAME = qm-wayland

WAYLAND_FILES = \
	rpm/wayland/qm-wayland.spec \
	subsystems/wayland/Makefile \
	subsystems/wayland/README.md \
	SECURITY.md \
	LICENSE \
	subsystems/wayland/50-qm-wayland.preset \
	subsystems/wayland/etc/containers/systemd/qm-dbus-broker.container \
	subsystems/wayland/etc/containers/systemd/wayland-compositor.container \
	subsystems/wayland/etc/pam.d/systemd-user \
	subsystems/wayland/etc/pam.d/wayland-autologin \
	subsystems/wayland/etc/systemd/system/qm-dbus.socket \
	subsystems/wayland/etc/systemd/system/wayland-session.service \
	subsystems/wayland/etc/systemd/system/wayland.socket \
	subsystems/wayland/etc/weston/weston.ini \
	subsystems/wayland/usr/bin/wayland-session

.PHONY: dist
dist: ##             - Creates the QM wayland package
	cd $(ROOTDIR) && tar cvz \
		--dereference \
		--transform 's|subsystems/wayland/Makefile|Makefile|' \
		--transform 's|rpm/wayland/qm-wayland.spec|qm-wayland.spec|' \
		--transform 's|^|qm-wayland-${VERSION}/|' \
		-f /tmp/qm-wayland-${VERSION}.tar.gz \
		${WAYLAND_FILES}

	mv /tmp/qm-wayland-${VERSION}.tar.gz $(ROOTDIR)/rpm

.PHONY: wayland
wayland: dist ##             - Creates a local RPM package, useful for development
	mkdir -p ${RPM_TOPDIR}/{RPMS,SRPMS,BUILD,SOURCES}
	cp $(ROOTDIR)/rpm/qm-wayland-${VERSION}.tar.gz ${RPM_TOPDIR}/SOURCES
	rpmbuild -ba \
		--define="_topdir ${RPM_TOPDIR}" \
		--define="version ${VERSION}" \
		${SPECFILE_SUBPACKAGE_WAYLAND}
	if ! compgen -G "${RPM_TOPDIR}/RPMS/noarch/${PACKAGE_NAME}-${VERSION}*.noarch.rpm" > /dev/null; then \
		echo "rpmbuild failed to build: ${PACKAGE_NAME}"; \
		exit 1; \
	fi
