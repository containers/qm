#!/bin/sh

#Kill ping and remove the containers
pkill ping
podman exec -it confusion sh -c "tc qdisc del dev eth0 root" #removing the injected fault#
modprobe -rv sch_netem
echo "removing containers"
podman rm -f partner
podman rm -f orderly
podman rm -f confusion
echo "End Test"
