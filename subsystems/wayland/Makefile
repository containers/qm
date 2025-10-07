RPM_TOPDIR ?= $(PWD)/rpmbuild
VERSION ?= $(shell grep '^Version:' rpm/wayland/qm-wayland.spec | awk '{print $$2}')
ROOTDIR ?= $(PWD)
SPECFILE_SUBPACKAGE_WAYLAND ?= ${ROOTDIR}/rpm/wayland/qm-wayland.spec
PACKAGE_NAME = qm-wayland

.PHONY: dist
dist: ##             - Creates the QM wayland package
	cd $(ROOTDIR) && tar cvz \
		--dereference \
		--transform 's|subsystems/wayland/Makefile|Makefile|' \
		--transform 's|rpm/wayland/qm-wayland.spec|qm-wayland.spec|' \
		--transform 's|subsystems/wayland/README.md|README.md|' \
		--transform 's|^qm/|qm-wayland-${VERSION}/|' \
		-f /tmp/qm-wayland-${VERSION}.tar.gz \
		../qm/rpm/wayland/qm-wayland.spec \
		../qm/subsystems/wayland/Makefile \
		../qm/subsystems/wayland/README.md \
		../qm/SECURITY.md \
		../qm/LICENSE \
		../qm/subsystems/wayland/50-qm-wayland.preset \
		../qm/subsystems/wayland/etc/containers/systemd/qm-dbus-broker.container \
		../qm/subsystems/wayland/etc/containers/systemd/wayland-compositor.container \
		../qm/subsystems/wayland/etc/pam.d/systemd-user \
		../qm/subsystems/wayland/etc/pam.d/wayland-autologin \
		../qm/subsystems/wayland/etc/systemd/system/qm-dbus.socket \
		../qm/subsystems/wayland/etc/systemd/system/wayland-session.service \
		../qm/subsystems/wayland/etc/systemd/system/wayland.socket \
		../qm/subsystems/wayland/etc/weston/weston.ini \
		../qm/subsystems/wayland/usr/bin/wayland-session

	cd $(ROOTDIR) && mv /tmp/qm-wayland-${VERSION}.tar.gz ./rpm

.PHONY: wayland
wayland: dist ##             - Creates a local RPM package, useful for development
	cd $(ROOTDIR) && mkdir -p ${RPM_TOPDIR}/{RPMS,SRPMS,BUILD,SOURCES}
	cd $(ROOTDIR) && cp ./rpm/qm-wayland-${VERSION}.tar.gz ${RPM_TOPDIR}/SOURCES
	rpmbuild -ba \
		--define="_topdir ${RPM_TOPDIR}" \
		--define="version ${VERSION}" \
		${SPECFILE_SUBPACKAGE_WAYLAND}
	if [ ! -f ${RPM_TOPDIR}/RPMS/noarch/${PACKAGE_NAME}-${VERSION}*.noarch.rpm ]; then \
		echo "rpmbuild failed to build: ${PACKAGE_NAME}"; \
		exit 1; \
	fi
