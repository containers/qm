# FFI - attempts_to_access_forbidden_file_system_resource/devices

This test is intended to confirm that resources (devices, networks, shared memory, etc) present in the file system match the expectations based on the QM partition configuration.

## This Test Set includes these tests

1. Confirm that the device /dev/console is not available in the QM partition.
2. Confirm that the device /dev/disk is not available in the QM partition.
3. Confirm that the device /dev/kmsg is not available in the QM partition.
