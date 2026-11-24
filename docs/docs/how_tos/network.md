# Networking with QM

QM has a private IPv4 network. Its defaults are `10.90.0.2/24` inside QM and
`10.90.0.1` on the host. Outbound traffic is masqueraded through the host.
Choose a subnet that does not overlap host routes or other container networks:

```json
{
  "ip": "172.30.20.2",
  "gateway": "172.30.20.1",
  "prefix-length": 28
}
```

Save this as `/etc/qmc.conf.d/50-network.conf`, inspect it with `qmc inspect`,
and restart `qm.service`. The address and gateway must be distinct usable
addresses in the same subnet. Only IPv4 is supported by the outer launcher;
outer host networking and port-publishing options are unavailable.

Host firewall rules must permit forwarding for the selected QM subnet. QM's
rules do not override a drop policy in another firewall. The host can reach
services bound to QM's address; use the host gateway address to reach host
services from QM. Inspect the running service and test connectivity after
changing the host firewall or network configuration.

QM copies the host resolver configuration and watches it and `/etc/hosts` for
updates. With systemd-resolved, the upstream resolver file is preferred when
available. An explicit `resolv-conf` path requires a matching administrator
path watcher if it is outside the supplied watched paths.

Applications inside QM still use Podman networking. The supplied QM
`containers.conf` defaults nested containers to `netns="host"`, which shares
QM's network namespace. An application Quadlet can use `Network=private` for
an additional private network, or `Network=host` to share QM's namespace.
These application settings do not select the outer host's network namespace.
Place application Quadlets in `/etc/qm/containers/systemd/` on the host,
then run `qmc exec systemctl daemon-reload` and start the application service.

## Waiting for host networking

Host network readiness can be forwarded to QM for applications that need it at
startup. Install `qm-integration` inside QM's rootfs.

On the host, enable network integration:

```sh
sudo systemctl enable --now qm-network-integration.service
```

This sends a readiness signal to QM once host networking is online. The host's
appropriate wait-online provider must be enabled, such as
`NetworkManager-wait-online.service` or `systemd-networkd-wait-online.service`.

Inside QM, enable the wait service:

```sh
sudo qmc exec systemctl enable qm-wait-for-host-network.service
```

This delays `network-online.target` inside QM until the host readiness signal
arrives.

The service waits up to 120 seconds; override
`TimeoutStartSec=` in a guest service drop-in to change that limit. As with other
wait-online services, a timeout fails the wait service and permits the target's
startup to continue.

Guest services that require the milestone should have:

```ini
[Unit]
Wants=network-online.target
After=network-online.target
```
