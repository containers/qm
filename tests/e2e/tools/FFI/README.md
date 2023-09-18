# Free-From-Interference

Free-From-Interference (FFI) means applications within the QM environment do not interfere with applications in the ASIL environment.

## Memory
QM environment will allocates 90% or greater of memory of the system. 
Launch application in the ASIL environment that requires > 10% of memory.
Make sure swap is turned off.
Make sure OOM Killer kills QM applications.

Example:
- memory/ASIL/20_percent_cpu_eat.c 
- memory/QM/90_percent_cpu_eat.c 

## Disk
Try to allocate as maximum possible disk space.
