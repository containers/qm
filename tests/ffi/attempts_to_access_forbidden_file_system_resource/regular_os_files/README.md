# FFI - attempts_to_access_forbidden_file_system_resource/regular_os_files

This test is intended to confirm that resources (devices, networks, shared memory, etc) present in the file system match the expectations based on the QM partition configuration.

## This Test Set includes these tests

1. Confirm that the directory /etc/qm cannot be accessed in the QM partition.
2. Confirm that the directory /usr/lib/qm cannot be accessed in the QM partition.
3. Confirm that the directory /usr/share/qm cannot be accessed in the QM partition.
