TARGETS ?= qm
MODULES ?= ${TARGETS:=.pp.bz2}
DESTDIR ?=
PREFIX ?= /usr
DATADIR ?= $(PREFIX)/share
LIBDIR ?= $(PREFIX)/lib
SYSCONFDIR?=/etc
QMDIR=/usr/lib/qm

.PHONY: file_contexts
file_contexts: qm.fc
	sed \
	-e "s|${QMDIR}/rootfs||" \
	 -e "s/gen_context(//g" \
	 -e "s/,s0)/:s0/g" \
	 -e "s|${QMDIR}||g" qm.fc > qm_file_contexts

all: selinux file_contexts  man

.PHONY: selinux
selinux: qm.pp
	@echo Compressing $^ -\> $@
	bzip2 -f -9 $^

%.pp: %.te
	mkdir -p tmp; cp qm.* tmp/
	@if ./build-aux/validations ; then \
		sed -i /user_namespace/d tmp/qm.if; \
	fi
	make -C tmp -f ${DATADIR}/selinux/devel/Makefile $@
	cp tmp/qm.pp .; rm -rf tmp

.PHONY: codespell
codespell:
	@codespell -S tmp,.git -L te -w

clean:
	rm -f *~  *.tc *.pp *.pp.bz2
	rm -rf tmp *.tar.gz

man: qm.8.md
	go-md2man --in qm.8.md --out qm.8

install-policy: all
	semodule -i ${TARGETS}.pp.bz2
	sepolicy manpage --path . --domain ${TARGETS}_t

install: man all
	install -D -pm 644 ${TARGETS}.pp.bz2 ${DESTDIR}${DATADIR}/selinux/packages/qm.pp.bz2
	install -D -pm 644 qm.if ${DESTDIR}${DATADIR}/selinux/devel/include/services/qm.if
	install -D -pm 644 qm_selinux.8 ${DESTDIR}${DATADIR}/man/man8/qm_selinux.8
	install -D -pm 644 qm.8 ${DESTDIR}${DATADIR}/man/man8/qm.8
	install -d -m 755 ${DESTDIR}${DATADIR}/qm
	install -D -m 644 qm_contexts  ${DESTDIR}${DATADIR}/qm/contexts
	install -D -m 755 setup ${DESTDIR}${DATADIR}/qm/setup
	install -D -m 755 tools/comment-tz-local ${DESTDIR}${DATADIR}/qm/comment-tz-local
	install -D -m 755 tools/qm-rootfs ${DESTDIR}${DATADIR}/qm/qm-rootfs
	install -D -m 755 create-seccomp-rules ${DESTDIR}${DATADIR}/qm/create-seccomp-rules
	install -D -m 644 qm_file_contexts ${DESTDIR}${DATADIR}/qm/file_contexts
	install -D -m 644 containers.conf ${DESTDIR}${DATADIR}/qm/containers.conf
	install -D -m 644 qm.container ${DESTDIR}${DATADIR}/containers/systemd/qm.container
