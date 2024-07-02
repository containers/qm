# The `execute_sched_setattr` command

## What is `execute_sched_setattr` ?

A test tool to validate if `SCHED_DEADLINE` can be set via `sched_setattr()` syscall.

## Why?

QM environment should not allow `SCHED_DEADLINE` be set via `sched_setattr()` syscall
and must validated via FFI tests.

## How to deny is made?

During the QM service startup it passes arguments to Podman. One of these arguments is `seccomp=/usr/share/qm/seccomp.json` which contains rules that deny the `sched_setattr()`.

## How to test?

```console
host> gcc -o execute_sched_setattr execute_sched_setattr.c -Wall  # build the bin
host> cp execute_sched_setattr /usr/lib/qm/rootfs/root/  # copy the bin to QM partition

# podman exec -it qm bash  # Execute the test, it must fail in recent versions of QM
bash-5.1# cd /root && ./execute_sched_setattr
Current Scheduling Policy: SCHED_OTHER
Current Priority: 0
sched_setattr failed: Operation not permitted
```
