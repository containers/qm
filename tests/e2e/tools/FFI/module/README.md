# The `modprobe_module` command

## What is `modprobe_module`?

`modprobe_module` is a simple script that validates it won't be possible to access `/lib/modules` to load any module via modprobe inside the QM partition.

## How to use it?

It must be executed inside the QM partition to validate it won't be possible to modprobe any module under `/lib/modules`.

Example:

```console
my-host# podman exec -it qm bash

bash-5.1# ./modprobe_module
modprobe: FATAL: Module ext4 not found in directory /lib/modules/5.14.0-447.400.el9iv.x86_64
ls: cannot access '/lib/modules/5.14.0-447.400.el9iv.x86_64': No such file or directory
done

```
