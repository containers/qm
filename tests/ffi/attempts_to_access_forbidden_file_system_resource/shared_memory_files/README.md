# FFI - attempts_to_access_forbidden_file_system_resource/shared_memory_files

This test is intended to confirm that resources (devices, networks, shared memory, etc) present in the file system match the expectations based on the QM partition configuration.

## This Test Set includes these tests

1. Confirm that the file created in /dev/shm/ outside the QM partition that are not visible in /dev/shm inside the QM partition.
