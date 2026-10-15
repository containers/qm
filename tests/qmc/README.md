# qmc regression tests

Run `meson setup build --prefix=/usr`, then `meson test -C build --print-errorlogs`.
The tests use Python unittest and C fixtures. They exercise configuration,
OCI preparation, inspection, command errors, signals and utility failures without
a running QM instance or host network changes. Meson and RPM builds enable them
by default; use `-Dtests=false` for a build without test fixtures.

Some preparation and exec cases need private mounts or privileges. unittest
reports these cases as skipped when their prerequisites are unavailable. Passing
this suite does not establish that the installed service runs with SELinux or
that networking works; those checks require a disposable integration machine.
