# What is setsysctl?
setsysctl is simple script that uses sysctl tool to try to change several parameters in the host OS.

# How to use it?
It must be executed inside QM environment as a container (nested) to make sure attemps to change OS level are denied.

Example:
```
my-host# podman exec -it qm bash

bash-5.1# podman run -it fedora bash

[root@d0c4f92289b0 ~]# ./setsysctl
Setting sysctl parameters...
sysctl: permission denied on key "net.ipv4.ip_forward"
sysctl: permission denied on key "net.ipv4.conf.all.rp_filter"
sysctl: permission denied on key "net.ipv4.tcp_max_syn_backlog"
sysctl: permission denied on key "vm.swappiness"
sysctl: permission denied on key "vm.overcommit_memory"
done
```
