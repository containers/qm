# What is `execute_set_scheduler`?

A test tool to validate if `set_scheduler()` syscall can be executed.

## Why?

QM environment deny `set_scheduler()` syscall for safety and must be validated via FFI tests.

## How to deny is made?

During the QM service startup it passes arguments to Podman. One of these arguments is `seccomp=/usr/share/qm/seccomp.json` which contains rules that deny the `set_scheduler()`.

## How to test?

```console
host> gcc -o execute_set_scheduler execute_set_scheduler.c -Wall  # build the bin
host> cp execute_set_scheduler /usr/lib/qm/rootfs/root/  # copy the bin to QM partition

# podman exec -it qm bash  # Execute the test, it must fail in recent versions of QM
bash-5.1# cd /root && ./test_sched_setscheduler
Failed to set scheduler: Operation not permitted
```
