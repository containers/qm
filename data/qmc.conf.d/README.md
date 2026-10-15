# Outer QM device configuration

The KVM, sound and video packages install their respective JSON defaults into
`/usr/share/qm/qmc.conf.d`. Application Quadlets remain inside QM.

`60-qm-window-manager.conf` is an optional TTY example. Copy it to
`/etc/qmc.conf.d` on the host when QM needs virtual terminals. To select a
Wayland seat as well, add a `devices` entry with `"seat": "seat0"` and
`"optional": true`. The old seat hook also granted common input and render
nodes regardless of seat. Add these explicitly if required:

```json
{
  "devices": [
    {"seat": "seat0", "optional": true},
    {"source": "/dev/input/event[0-9]*", "optional": true},
    {"source": "/dev/input/mice*", "optional": true},
    {"source": "/dev/input/mouse[0-9]*", "optional": true},
    {"source": "/dev/dri/render*", "optional": true}
  ]
}
```

Selections are expanded at QM startup. Restart `qm.service` after changing
configuration or the host device set.
