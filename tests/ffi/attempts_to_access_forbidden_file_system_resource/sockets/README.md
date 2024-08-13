# FFI - attempts_to_access_forbidden_file_system_resource/sockets

This test is intended to confirm that resources (devices, networks, shared memory, etc) present in the file system match the expectations based on the QM partition configuration.

## This Test Set includes these tests

1. Confirm that /run/systemd/journal/socket have different inode number inside and outside of the QM partition.
2. Confirm that the socket /run/udev/control does not exist in the QM partition.
