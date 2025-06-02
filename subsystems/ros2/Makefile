RPM_TOPDIR ?= $(PWD)/rpmbuild
VERSION ?= $(shell cat VERSION)
ROOTDIR ?= $(PWD)
SPECFILE_SUBPACKAGE_ROS2_ROLLING ?= ${ROOTDIR}/rpm/ros2/ros2_rolling.spec
PACKAGE_NAME = qm-ros2

.PHONY: dist
dist: ##             - Creates the QM ros2 package
	cd $(ROOTDIR) && tar cvz \
		--dereference \
                --transform 's|subsystems/ros2/Makefile|Makefile|' \
                --transform 's|rpm/ros2/ros2_rolling.spec|ros2_rolling.spec|' \
		--transform s/qm/qm-ros2-${VERSION}/ \
		-f /tmp/qm-ros2-${VERSION}.tar.gz \
                ../qm/rpm/ros2/ros2_rolling.spec \
                ../qm/subsystems/ros2/Makefile \
                ../qm/tools/version-update \
                ../qm/VERSION \
		../qm/README.md \
		../qm/SECURITY.md \
		../qm/LICENSE \
		../qm/subsystems/ros2/etc/containers/systemd/ros2.container
	cd $(ROOTDIR) && mv /tmp/qm-ros2-${VERSION}.tar.gz ./rpm


.PHONY: ros2
ros2: dist ##          - Creates a local RPM package, useful for development
	cd $(ROOTDIR) && mkdir -p ${RPM_TOPDIR}/{RPMS,SRPMS,BUILD,SOURCES}
	cd $(ROOTDIR) && tools/version-update -v ${VERSION}
	cd $(ROOTDIR) && cp ./rpm/qm-ros2-${VERSION}.tar.gz ${RPM_TOPDIR}/SOURCES
	rpmbuild -ba \
		--define="_topdir ${RPM_TOPDIR}" \
		--define="version ${VERSION}" \
		${SPECFILE_SUBPACKAGE_ROS2_ROLLING}
	if [ ! -f ${RPM_TOPDIR}/RPMS/noarch/${PACKAGE_NAME}-${VERSION}*.noarch.rpm ]; then \
		echo "rpmbuild failed to build: ${PACKAGE_NAME}"; \
		exit 1; \
	fi
