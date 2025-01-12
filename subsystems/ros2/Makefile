SPECFILE_SUBPACKAGE_ROS2_ROLLING=rpm/ros2/rolling/ros2_rolling.spec

.PHONY: dist
dist: ##             - Creates the QM ros2 package
	cd $(ROOTDIR) && tar cvz \
		--exclude-from=build-aux/exclude_from_tar_gz_subpackage_kvm.txt \
		--dereference \
		--transform s/qm/qm-ros2-${VERSION}/ \
		-f /tmp/qm-ros2-${VERSION}.tar.gz \
		../qm/README.md \
		../qm/SECURITY.md \
		../qm/LICENSE \
		../qm/ \
		../qm/subsystems/ros2/etc/containers/systemd/ros2-rolling.container
	cd $(ROOTDIR) && mv /tmp/qm-ros2-${VERSION}.tar.gz ./rpm


.PHONY: rpm
rpm: dist ##          - Creates a local RPM package, useful for development
	cd $(ROOTDIR) && mkdir -p ${RPM_TOPDIR}/{RPMS,SRPMS,BUILD,SOURCES}
	cd $(ROOTDIR) && tools/version-update -v ${VERSION}
	cd $(ROOTDIR) && cp ./rpm/v${VERSION}.tar.gz ${RPM_TOPDIR}/SOURCES
	cd $(ROOTDIR) && rpmbuild -ba \
		--define="_topdir ${RPM_TOPDIR}" \
		--define="version ${VERSION}" \
		${SPECFILE_SUBPACKAGE_ROS2_ROLLING}

