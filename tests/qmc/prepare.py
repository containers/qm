# SPDX-License-Identifier: GPL-2.0-only
# Copyright (C) 2026 Alexander Larsson
# See LICENSE for the full license text.

import json
import os
import pathlib
import stat
import subprocess
import sys
import tempfile
import unittest

LAUNCHER = pathlib.Path(sys.argv[1]).resolve()
SOURCE = pathlib.Path(sys.argv[2]).resolve()
EXPECTED_CGROUP = sys.argv[3] if len(sys.argv) > 3 else None
PRIVATE_PATHS = os.environ.get("QM_TEST_PRIVATE_PATHS") == "1"
HOST_MACHINE_ID = "d2c79cc3388a48e494c8cd22cce8f499"
sys.argv = sys.argv[:1]


class PrepareTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="qm-prepare-")
        self.addCleanup(self.temp.cleanup)
        self.directory = pathlib.Path(self.temp.name)
        self.runtime = self.directory / "runtime"
        self.resolv = self.directory / "resolv.conf"
        self.resolv.write_text("nameserver 192.0.2.53\n")
        self.subids = pathlib.Path("/etc")
        self.devices = pathlib.Path("/dev")
        self.hosts = pathlib.Path("/etc/hosts")
        if PRIVATE_PATHS:
            self.hosts.write_text("127.0.0.1\tlocalhost\n")
            pathlib.Path("/etc/machine-id").write_text(HOST_MACHINE_ID + "\n")
            for name in ("subuid", "subgid"):
                (self.subids / name).write_text("")
            for name in ("kvm", "fuse"):
                (self.devices / name).unlink(missing_ok=True)
        self.base = json.loads((SOURCE / "data/qm.json").read_text())
        self.vendor = json.loads((SOURCE / "data/qmc.conf.in").read_text())
        self.seccomp = json.loads((SOURCE / "tests/qmc/seccomp-no-rt.json").read_text())

    def prepare(self, base=None, seccomp=None, hostname="qm", extra=(), env=None,
                host_resolv=False, settings=None):
        inputs = {
            "base.json": self.base if base is None else base,
            "seccomp.json": self.seccomp if seccomp is None else seccomp,
        }
        for name, value in inputs.items():
            (self.directory / name).write_text(json.dumps(value))
        config = {
            "base-config": str(self.directory / "base.json"),
            "hostname": hostname,
            "userns": "auto" if PRIVATE_PATHS else "off",
            "mounts": self.vendor["mounts"],
            "devices": self.vendor["devices"],
            "capabilities": self.vendor["capabilities"],
        }
        if "path" not in inputs["base.json"]["root"]:
            config["rootfs"] = self.vendor["rootfs"]
        if seccomp is not False:
            config["seccomp"] = str(self.directory / "seccomp.json")
        if not host_resolv:
            config["resolv-conf"] = str(self.resolv)
        config.update(settings or {})
        filename = self.directory / "qmc.conf"
        filename.write_text(json.dumps(config))
        return subprocess.run(
            [str(LAUNCHER), "launch", "--prepare-only", "--runtime-dir", str(self.runtime),
             "--config", str(filename), *extra],
            text=True, capture_output=True, env=env,
        )

    def generated(self):
        return json.loads((self.runtime / "config.json").read_text())

    def assert_device(self, config, destination, source):
        info = os.stat(source)
        expected = {"path": destination, "type": "c" if stat.S_ISCHR(info.st_mode) else "b",
                    "major": os.major(info.st_rdev), "minor": os.minor(info.st_rdev),
                    "fileMode": stat.S_IMODE(info.st_mode), "uid": info.st_uid,
                    "gid": info.st_gid}
        self.assertEqual([d for d in config["linux"]["devices"]
                          if d["path"] == destination], [expected])
        self.assertFalse(any(m["destination"] == destination for m in config["mounts"]))
        self.assertIn({"allow": True, "type": expected["type"], "major": expected["major"],
                       "minor": expected["minor"], "access": "rwm"},
                      config["linux"]["resources"]["devices"])

    def device_glob_fixture(self):
        devices = self.directory / "devices"
        devices.mkdir()
        for name in ("null", "zero"):
            (devices / name).symlink_to(f"/dev/{name}")
        return devices

    def seat_fixture(self):
        """Use real sd-device enumeration against private sysfs/udev fixtures."""
        sysfs = self.directory / "sysfs"
        udev = self.directory / "udev"
        for relative in ("class/input", "class/mem", "dev/char"):
            (sysfs / relative).mkdir(parents=True)
        (udev / "data").mkdir(parents=True)
        (udev / "tags/seat").mkdir(parents=True)

        for name, relative, seat in (("input0", "devices/input0", None),
                                     ("input1", "devices/input0/input1", "seat1")):
            device = sysfs / relative
            device.mkdir(parents=True)
            (device / "uevent").touch()
            (device / "subsystem").symlink_to("/sys/class/input")
            (sysfs / f"class/input/{name}").symlink_to(f"../../{relative}")
            identity = f"+input:{name}"
            (udev / "data" / identity).write_text(
                "V:1\nG:seat\nQ:seat\n" + (f"E:ID_SEAT={seat}\n" if seat else ""))
            (udev / "tags/seat" / identity).touch()

        for name, parent, minor in (("null", "input0", 3), ("zero", "input0/input1", 5)):
            relative = f"devices/{parent}/{name}"
            device = sysfs / relative
            device.mkdir()
            (device / "uevent").write_text(f"MAJOR=1\nMINOR={minor}\nDEVNAME={name}\n")
            (device / "subsystem").symlink_to("/sys/class/mem")
            (sysfs / f"dev/char/1:{minor}").symlink_to(f"../../{relative}")

        for source, destination in ((sysfs, "/sys"), (udev, "/run/udev")):
            pathlib.Path(destination).mkdir(parents=True, exist_ok=True)
            subprocess.run(["mount", "--bind", str(source), destination], check=True)
            self.addCleanup(subprocess.run, ["umount", destination], check=True)

        # sd-device's own test switch permits fixtures outside a sysfs filesystem.
        return {**os.environ, "SYSTEMD_DEVICE_VERIFY_SYSFS": "0"}

    def test_static_config(self):
        result = self.prepare(hostname="qm-test")
        self.assertEqual(result.returncode, 0, result.stderr)
        config = self.generated()
        self.assertEqual(config["hostname"], "qm-test")
        self.assertIn("HOSTNAME=qm-test", config["process"]["env"])
        self.assertFalse(any(e.startswith("container_uuid=") for e in config["process"]["env"]))
        self.assertEqual(config["process"]["args"],
                         [*self.base["process"]["args"], "--machine-id=" + HOST_MACHINE_ID])
        self.assertEqual(config["root"], {**self.base["root"], "path": self.vendor["rootfs"]})
        self.assertNotIn("capabilities", self.base["process"])
        expected_caps = """
            CAP_AUDIT_CONTROL CAP_AUDIT_READ CAP_AUDIT_WRITE CAP_BLOCK_SUSPEND
            CAP_BPF CAP_CHECKPOINT_RESTORE CAP_CHOWN CAP_DAC_OVERRIDE CAP_DAC_READ_SEARCH
            CAP_FOWNER CAP_FSETID CAP_IPC_LOCK CAP_IPC_OWNER CAP_KILL CAP_LEASE
            CAP_LINUX_IMMUTABLE CAP_MAC_ADMIN CAP_MAC_OVERRIDE CAP_MKNOD CAP_NET_ADMIN
            CAP_NET_BIND_SERVICE CAP_NET_BROADCAST CAP_NET_RAW CAP_PERFMON CAP_SETFCAP
            CAP_SETGID CAP_SETPCAP CAP_SETUID CAP_SYSLOG CAP_SYS_ADMIN CAP_SYS_CHROOT
            CAP_SYS_MODULE CAP_SYS_NICE CAP_SYS_PACCT CAP_SYS_PTRACE CAP_SYS_RAWIO
            CAP_SYS_TIME CAP_SYS_TTY_CONFIG CAP_WAKE_ALARM
        """.split()
        caps = config["process"]["capabilities"]
        self.assertEqual(set(caps), {"bounding", "effective", "permitted"})
        for values in caps.values():
            self.assertEqual(sorted(values), sorted(expected_caps))
        self.assertEqual(config["linux"]["mountLabel"], self.base["linux"]["mountLabel"])
        self.assertTrue(config["linux"]["cgroupsPath"].endswith("/payload"))
        if EXPECTED_CGROUP is not None:
            self.assertEqual(config["linux"]["cgroupsPath"], EXPECTED_CGROUP)
        netns = next(n for n in config["linux"]["namespaces"] if n["type"] == "network")
        self.assertEqual(netns["path"], str(self.runtime / "netns"))
        mounts = {m["destination"]: m for m in config["mounts"]}
        self.assertNotIn("/etc/machine-id", mounts)
        self.assertEqual(mounts["/dev/shm"]["type"], "tmpfs")
        self.assertIn("size=65536k", mounts["/dev/shm"]["options"])
        for destination in ("/etc/hosts", "/etc/hostname", "/etc/resolv.conf", "/run/.containerenv", "/run/secrets"):
            self.assertTrue(pathlib.Path(mounts[destination]["source"]).exists())
        signals = mounts["/run/host/qmc-signals"]
        self.assertEqual(signals["source"], str(self.runtime / "signals"))
        self.assertIn("ro", signals["options"])
        self.assertEqual(stat.S_IMODE((self.runtime / "signals").stat().st_mode), 0o755)
        self.assertEqual((self.runtime / "files/hostname").read_text(), "qm-test\n")
        self.assertEqual((self.runtime / "files/resolv.conf").read_text(), self.resolv.read_text())
        self.assertIn("10.90.0.2\tqm-test qm\n", (self.runtime / "files/hosts").read_text())
        self.assertNotIn("overlay-containers", json.dumps(config))
        self.assertEqual(config["annotations"]["run.oci.mount_context_type"], "rootcontext")
        profile = config["linux"]["seccomp"]
        self.assertNotIn("archMap", profile)
        self.assertEqual(profile["defaultErrnoRet"], 38)
        rules = profile["syscalls"]
        self.assertTrue(any(r["names"] == ["sched_setattr"] and r.get("errnoRet") == 1 for r in rules))
        scheduling = [r for r in rules if r["names"] == ["sched_setscheduler"]]
        self.assertEqual([r["args"][0]["value"] for r in scheduling], [0, 3, 5])
        self.assertTrue(all("includes" not in r and "excludes" not in r for r in rules))

    def test_default_mounts_precede_their_children(self):
        destinations = ("/etc", "/var", "/var/tmp")
        self.assertFalse(any(m["destination"] in destinations for m in self.base["mounts"]))
        result = self.prepare()
        self.assertEqual(result.returncode, 0, result.stderr)
        mounts = self.generated()["mounts"]
        order = [m["destination"] for m in mounts]
        for destination, source in (("/etc", "/etc/qm"), ("/var", "/var/qm"),
                                     ("/var/tmp", "/var/qm/tmp")):
            with self.subTest(destination=destination):
                self.assertEqual([m for m in mounts if m["destination"] == destination], [
                    {"type": "bind", "source": source, "destination": destination,
                     "options": ["rbind", "rprivate"]}])
                for child in order:
                    if child.startswith(destination + "/"):
                        self.assertLess(order.index(destination), order.index(child))

    def test_configured_network_hosts_survive_configuration_changes(self):
        settings = {"ip": "172.30.20.2", "gateway": "172.30.20.1", "prefix-length": 28}
        result = self.prepare(hostname="qm-test", settings=settings)
        self.assertEqual(result.returncode, 0, result.stderr)
        target = self.runtime / "files/hosts"
        contents = target.read_text()
        self.assertIn("172.30.20.1\thost.containers.internal host.docker.internal\n", contents)
        self.assertIn("172.30.20.2\tqm-test qm\n", contents)
        inode = target.stat().st_ino
        # update_resolv uses a new configuration with default network settings.
        target.write_text("stale contents\n")
        result = self.update_resolv()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(target.read_text(), contents)
        self.assertEqual(target.stat().st_ino, inode)

    def test_invalid_host_machine_id_preserves_init_arguments(self):
        for extra in ([], ["--machine-id=" + "1" * 32]):
            base = {**self.base, "process": {
                **self.base["process"], "args": [*self.base["process"]["args"], *extra]}}
            for value in ("", "uninitialized\n", "0" * 32, "1" * 31, "1" * 33, "g" * 32):
                with self.subTest(machine_id=value, extra=extra):
                    if PRIVATE_PATHS:
                        pathlib.Path("/etc/machine-id").write_text(value)
                    result = self.prepare(base=base, env={**os.environ, "QM_TEST_MACHINE_ID": value})
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertIn("invalid host machine ID", result.stderr)
                    self.assertEqual(self.generated()["process"]["args"], base["process"]["args"])

    def test_custom_init_arguments(self):
        self.base["process"]["args"] = ["/init", "--custom-argument"]
        result = self.prepare()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.generated()["process"]["args"], self.base["process"]["args"])

    def test_machine_id_overrides_base_argument(self):
        self.base["process"]["args"] += ["--machine-id=" + "1" * 32]
        result = self.prepare()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.generated()["process"]["args"][-1],
                         "--machine-id=" + HOST_MACHINE_ID)

    def test_oci_seccomp_roundtrip(self):
        profile = {"defaultAction": "SCMP_ACT_ERRNO", "defaultErrnoRet": 38,
                   "syscalls": [{"names": ["exit"], "action": "SCMP_ACT_ALLOW"}]}
        result = self.prepare(seccomp=profile)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.generated()["linux"]["seccomp"], profile)

    def test_console_and_verbose_logging(self):
        result = self.prepare(extra=("--verbose",))
        self.assertEqual(result.returncode, 0, result.stderr)
        process = self.generated()["process"]
        self.assertTrue(process["terminal"])
        self.assertFalse(any(e.startswith("SYSTEMD_LOG_") for e in process["env"]))
        self.base["process"]["env"] += ["SYSTEMD_LOG_LEVEL=warning",
                                        "SYSTEMD_LOG_TARGET=journal"]
        result = self.prepare()
        self.assertEqual(result.returncode, 0, result.stderr)
        process = self.generated()["process"]
        self.assertTrue(process["terminal"])
        self.assertIn("SYSTEMD_LOG_LEVEL=warning", process["env"])
        self.assertIn("SYSTEMD_LOG_TARGET=journal", process["env"])
        result = self.prepare(extra=("--verbose",))
        self.assertEqual(result.returncode, 0, result.stderr)
        env = self.generated()["process"]["env"]
        self.assertEqual([e for e in env if e.startswith("SYSTEMD_LOG_LEVEL=")],
                         ["SYSTEMD_LOG_LEVEL=warning"])
        self.assertEqual([e for e in env if e.startswith("SYSTEMD_LOG_TARGET=")],
                         ["SYSTEMD_LOG_TARGET=journal"])
        self.assertIn("HOME=/root", env)

    def test_configuration_verbosity_and_cli_override(self):
        result = self.prepare(settings={"verbose": False})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("Loading OCI configuration", result.stderr)
        result = self.prepare(settings={"verbose": True})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Loading OCI configuration", result.stderr)
        result = self.prepare(settings={"verbose": False}, extra=("--verbose",))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Loading OCI configuration", result.stderr)

    def test_removed_options_and_positional_config(self):
        for option in ("--hostname", "--rootfs", "--etc-dir", "--var-dir",
                       "--seccomp", "--resolv-conf", "--userns"):
            with self.subTest(option=option):
                result = self.prepare(extra=(option, "value"))
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertIn("unrecognized option", result.stderr)
        result = self.prepare(extra=(str(self.directory / "base.json"),))
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("launch takes no positional arguments", result.stderr)

    def test_seccomp_required(self):
        result = self.prepare(seccomp=False)
        self.assertGreater(result.returncode, 0)
        self.assertIn("set seccomp in qmc.conf", result.stderr)

    def test_inline_seccomp(self):
        profile = {"defaultAction": "SCMP_ACT_ERRNO", "defaultErrnoRet": 38, "syscalls": []}
        self.base["linux"]["seccomp"] = profile
        result = self.prepare(seccomp=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.generated()["linux"]["seccomp"], profile)

    def test_paths_and_timezone(self):
        result = self.prepare(settings={
            "rootfs": "/test/rootfs",
            "mounts": [*self.vendor["mounts"],
                       {"source": "/test/etc", "destination": "/etc"},
                       {"source": "/test/var", "destination": "/var"}],
        }, env={**os.environ, "TZ": "Europe/Stockholm"})
        self.assertEqual(result.returncode, 0, result.stderr)
        config = self.generated()
        self.assertEqual(config["root"]["path"], "/test/rootfs")
        self.assertEqual(config["root"]["readonly"], self.base["root"]["readonly"])
        mounts = {m["destination"]: m["source"] for m in config["mounts"]}
        self.assertEqual(mounts["/etc"], "/test/etc")
        self.assertEqual(mounts["/var"], "/test/var")
        self.assertEqual(mounts["/var/tmp"], "/var/qm/tmp")
        self.assertIn("TZ=Europe/Stockholm", config["process"]["env"])

    def test_default_mounts_can_be_removed(self):
        result = self.prepare(settings={"mounts": [
            *self.vendor["mounts"],
            *[{"destination": path, "remove": True} for path in ("/etc", "/var", "/var/tmp")],
        ]})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(any(m["destination"] in ("/etc", "/var", "/var/tmp")
                             for m in self.generated()["mounts"]))

    def test_localtime_mount(self):
        result = self.prepare()
        self.assertEqual(result.returncode, 0, result.stderr)
        mounts = {m["destination"]: m for m in self.generated()["mounts"]}
        if pathlib.Path("/etc/localtime").exists():
            self.assertEqual(mounts["/etc/localtime"]["source"], "/etc/localtime")
            self.assertEqual(mounts["/etc/localtime"]["options"],
                             ["ro", "nosuid", "noexec", "nodev", "rbind", "rprivate"])
        else:
            self.assertNotIn("/etc/localtime", mounts)

    def test_missing_localtime_mount(self):
        result = self.prepare(settings={"mounts": [{
            "source": str(self.directory / "missing-localtime"),
            "destination": "/etc/localtime", "optional": True}]})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(any(m["destination"] == "/etc/localtime"
                             for m in self.generated()["mounts"]))

    def test_mount_operations_and_optional_sources(self):
        source = self.directory / "shared"
        source.mkdir()
        self.base["mounts"].append({"type": "tmpfs", "source": "tmpfs",
                                    "destination": "/shared", "options": ["ro", "nodev"]})
        missing = str(self.directory / "missing")
        result = self.prepare(settings={"mounts": [
            {"destination": "/etc/localtime", "remove": True},
            {"source": missing, "destination": "/shared", "optional": True},
            {"source": str(source) + "/missing/..", "destination": "/shared/./",
             "options": ["ro"]},
            {"source": missing, "destination": "/absent", "optional": True},
            {"source": missing, "destination": "/removed"},
            {"destination": "/removed/child/..", "remove": True}]})
        self.assertEqual(result.returncode, 0, result.stderr)
        mounts = self.generated()["mounts"]
        self.assertEqual([m for m in mounts if m["destination"] == "/shared"], [
            {"source": str(source), "destination": "/shared", "type": "bind",
             "options": ["ro", "rbind", "rprivate"]}])
        self.assertFalse(any(m["destination"] in ("/etc/localtime", "/absent", "/removed")
                             for m in mounts))

    def test_mount_replacement_preserves_order_and_empty_options(self):
        source = str(self.directory)
        destinations = ["/shared-tree", *[f"/shared-tree/child-{i}" for i in range(20)]]
        result = self.prepare(settings={"mounts": [
            *[{"source": source, "destination": dest} for dest in destinations],
            {"source": source, "destination": "/shared-tree", "options": []}]})
        self.assertEqual(result.returncode, 0, result.stderr)
        mounts = [m for m in self.generated()["mounts"]
                  if m["destination"] in destinations]
        self.assertEqual([m["destination"] for m in mounts], destinations)
        self.assertTrue(all(m["options"] == ["rbind", "rprivate"] for m in mounts))

    def test_device_operations_resolve_before_granting_access(self):
        missing = str(self.directory / "missing")
        result = self.prepare(settings={"devices": [
            {"source": "/dev/null", "destination": "/dev/test"},
            {"source": "/dev/zero", "destination": "/dev/test"},
            {"source": "/dev/null", "destination": "/dev/removed"},
            {"destination": "/dev/removed", "remove": True},
            {"source": missing, "destination": "/dev/skipped"},
            {"destination": "/dev/skipped", "remove": True},
            {"source": missing, "destination": "/dev/absent", "optional": True}]})
        self.assertEqual(result.returncode, 0, result.stderr)
        config = self.generated()
        self.assert_device(config, "/dev/test", "/dev/zero")
        self.assertEqual([d["path"] for d in config["linux"]["devices"]], ["/dev/test"])
        self.assertEqual(config["linux"]["resources"]["devices"], [
            *self.base["linux"]["resources"]["devices"],
            {"allow": True, "type": "c", "major": 1, "minor": 5, "access": "rwm"}])

    def test_device_removal_preserves_shared_base_access(self):
        self.base["linux"]["devices"] = [
            {"path": path, "type": "c", "major": 1, "minor": 3}
            for path in ("/dev/a", "/dev/b")]
        rule = {"allow": True, "type": "c", "major": 1, "minor": 3, "access": "rwm"}
        self.base["linux"]["resources"]["devices"].append(rule)
        result = self.prepare(settings={"devices": [{"destination": "/dev/a", "remove": True}]})
        self.assertEqual(result.returncode, 0, result.stderr)
        config = self.generated()["linux"]
        self.assertEqual([d["path"] for d in config["devices"]], ["/dev/b"])
        self.assertIn(rule, config["resources"]["devices"])
        result = self.prepare(settings={"devices": [
            {"source": "/dev/null", "destination": "/dev/c"},
            {"destination": "/dev/a", "remove": True},
            {"destination": "/dev/b", "remove": True}]})
        self.assertEqual(result.returncode, 0, result.stderr)
        config = self.generated()["linux"]
        self.assertEqual([d["path"] for d in config["devices"]], ["/dev/c"])
        self.assertEqual(config["resources"]["devices"].count(rule), 1)

    def test_device_globs_and_remapping(self):
        devices = self.device_glob_fixture()
        for pattern, destination in [("nul?", None), ("[nz]*", "/dev/test")]:
            source = str(devices / pattern)
            with self.subTest(source=source):
                operation = {"source": source}
                if destination:
                    operation["destination"] = destination
                result = self.prepare(settings={"devices": [operation]})
                self.assertEqual(result.returncode, 0, result.stderr)
                config = self.generated()
                names = ["null", "zero"] if destination else ["null"]
                prefix = destination or str(devices)
                self.assertEqual([d["path"] for d in config["linux"]["devices"]],
                                 [f"{prefix}/{name}" for name in names])
                for name in names:
                    self.assert_device(config, f"{prefix}/{name}", f"/dev/{name}")

    def test_device_glob_overrides_and_removals(self):
        devices = self.device_glob_fixture()
        result = self.prepare(settings={"devices": [
            {"source": str(devices / "[nz]*"), "destination": "/dev/test"},
            {"source": "/dev/zero", "destination": "/dev/test/null"},
            {"destination": "/dev/test/zero", "remove": True}]})
        self.assertEqual(result.returncode, 0, result.stderr)
        config = self.generated()
        self.assertEqual([d["path"] for d in config["linux"]["devices"]], ["/dev/test/null"])
        self.assert_device(config, "/dev/test/null", "/dev/zero")
        self.assertFalse(any(r.get("allow") and r.get("minor") == 3
                             for r in config["linux"]["resources"]["devices"]))

    def test_device_replaces_mount_and_preserves_metadata(self):
        source = "/dev/null" if PRIVATE_PATHS else "/dev/tty"
        self.base["mounts"].append({"destination": "/dev/test", "source": "tmpfs",
                                    "type": "tmpfs", "options": []})
        result = self.prepare(settings={"devices": [
            {"source": source, "destination": "/dev/test"}]})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assert_device(self.generated(), "/dev/test", source)

    def test_later_device_glob_restores_an_earlier_removed_match(self):
        devices = self.device_glob_fixture()
        for earlier in ({"destination": "/dev/test/null", "remove": True},
                        {"source": str(self.directory / "missing"),
                         "destination": "/dev/test/null"}):
            with self.subTest(earlier=earlier):
                result = self.prepare(settings={"devices": [
                    {"source": str(devices / "nu*"), "destination": "/dev/test"},
                    earlier,
                    {"source": str(devices / "[nz]*"), "destination": "/dev/test"}]})
                self.assertEqual(result.returncode, 0, result.stderr)
                config = self.generated()
                self.assert_device(config, "/dev/test/null", "/dev/null")
                self.assert_device(config, "/dev/test/zero", "/dev/zero")

    def test_empty_device_selections(self):
        empty = self.directory / "empty"
        empty.mkdir()
        (empty / "file").touch()
        (empty / "link").symlink_to("/dev/null")
        (empty / "loop").symlink_to(empty)
        for source in (str(empty), str(empty / "missing*"), str(empty / "fil*")):
            for optional in (False, True):
                with self.subTest(source=source, optional=optional):
                    result = self.prepare(settings={"devices": [
                        {"source": source, "destination": "/dev/test", "optional": optional}]})
                    if optional:
                        self.assertEqual(result.returncode, 0, result.stderr)
                        self.assertFalse(self.generated()["linux"].get("devices"))
                    else:
                        self.assertNotEqual(result.returncode, 0)
                        self.assertIn(source, result.stderr)

    def test_absent_and_cancelled_seat_selections(self):
        seat = "seat-qmc-test-absent"
        result = self.prepare(settings={"devices": [{"seat": seat}]})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(f"no devices found for seat {seat}", result.stderr)

        for devices in ([{"seat": seat, "optional": True}],
                        [{"seat": seat}, {"seat": seat, "remove": True}]):
            result = self.prepare(settings={"devices": devices})
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(self.generated()["linux"].get("devices"))
            self.assertEqual(self.generated()["linux"]["resources"]["devices"],
                             self.base["linux"]["resources"]["devices"])

    @unittest.skipUnless(PRIVATE_PATHS, "requires private sysfs and udev database mounts")
    def test_seat_devices_follow_parent_membership(self):
        env = self.seat_fixture()
        for seats, names in ((["seat0"], ["null"]), (["seat1"], ["zero"]),
                             (["seat0", "seat1"], ["null", "zero"])):
            with self.subTest(seats=seats):
                result = self.prepare(settings={"devices": [{"seat": seat} for seat in seats]},
                                      env=env)
                self.assertEqual(result.returncode, 0, result.stderr)
                config = self.generated()
                self.assertEqual([d["path"] for d in config["linux"]["devices"]],
                                 [f"/dev/{name}" for name in names])
                for name in names:
                    self.assert_device(config, f"/dev/{name}", f"/dev/{name}")

        # Both tagged ancestors select zero, but it must only appear once.
        (self.directory / "udev/data/+input:input1").write_text("V:1\nG:seat\nQ:seat\n")
        result = self.prepare(settings={"devices": [{"seat": "seat0"}]}, env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        config = self.generated()
        self.assertEqual(sorted(d["path"] for d in config["linux"]["devices"]),
                         ["/dev/null", "/dev/zero"])
        self.assertEqual(len(config["linux"]["resources"]["devices"]),
                         len(self.base["linux"]["resources"]["devices"]) + 2)

    @unittest.skipUnless(PRIVATE_PATHS, "requires private sysfs and udev database mounts")
    def test_seat_operations_and_individual_overrides(self):
        env = self.seat_fixture()
        cases = [
            ([{"seat": "seat0"}, {"seat": "seat0", "remove": True}], []),
            ([{"seat": "seat0"}, {"destination": "/dev/null", "remove": True}], []),
            ([{"seat": "seat0"}, {"seat": "seat0", "remove": True}, {"seat": "seat1"}],
             ["zero"]),
            ([{"seat": "seat0"}, {"destination": "/dev/null", "remove": True},
              {"seat": "seat0"}], ["null"]),
            ([{"source": str(self.directory / "missing"), "destination": "/dev/null"},
              {"seat": "seat0"}], ["null"]),
        ]
        for devices, names in cases:
            with self.subTest(devices=devices):
                result = self.prepare(settings={"devices": devices}, env=env)
                self.assertEqual(result.returncode, 0, result.stderr)
                config = self.generated()
                self.assertEqual([d["path"] for d in config["linux"].get("devices", [])],
                                 [f"/dev/{name}" for name in names])
                self.assertEqual(len(config["linux"]["resources"]["devices"]),
                                 len(self.base["linux"]["resources"]["devices"]) + len(names))

        result = self.prepare(settings={"devices": [
            {"seat": "seat0"}, {"source": "/dev/zero", "destination": "/dev/null"}]}, env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assert_device(self.generated(), "/dev/null", "/dev/zero")
        self.assertFalse(any(r.get("allow") and r.get("minor") == 3
                             for r in self.generated()["linux"]["resources"]["devices"]))

    def test_devices_and_mounts_share_destination_identity(self):
        self.base["mounts"].append({"destination": "/shared", "source": "tmpfs",
                                    "type": "tmpfs", "options": []})
        result = self.prepare(settings={
            "mounts": [{"source": "/dev/null", "destination": "/shared"}],
            "devices": [{"destination": "/shared", "remove": True}]})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(any(m["destination"] == "/shared"
                             for m in self.generated()["mounts"]))

    def test_required_or_invalid_device_fails(self):
        ordinary_file = self.directory / "file"
        ordinary_file.touch()
        for source, optional in [(str(self.directory / "missing"), False),
                                 (str(ordinary_file), True)]:
            with self.subTest(source=source):
                result = self.prepare(settings={"devices": [
                    {"source": source, "destination": "/dev/test", "optional": optional}]})
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(source, result.stderr)

    def test_optional_mount_does_not_hide_other_stat_errors(self):
        loop = self.directory / "loop"
        loop.symlink_to(loop)
        result = self.prepare(settings={"mounts": [
            {"source": str(loop), "destination": "/shared", "optional": True}]})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(str(loop), result.stderr)

    def test_optional_devices_do_not_hide_other_lookup_errors(self):
        loop = self.directory / "loop"
        loop.symlink_to(loop)
        for source in (str(loop), str(loop) + "*"):
            with self.subTest(source=source):
                result = self.prepare(settings={"devices": [
                    {"source": source, "destination": "/dev/test", "optional": True}]})
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(str(loop), result.stderr)

    @unittest.skipUnless(PRIVATE_PATHS, "requires a private mount namespace")
    def test_device_directories_and_directory_globs(self):
        tree = self.directory / "device-tree"
        for name, source in (("adapter0/null", "/dev/null"), ("adapter1/zero", "/dev/zero")):
            target = tree / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.touch()
            subprocess.run(["mount", "--bind", source, str(target)], check=True)
            self.addCleanup(subprocess.run, ["umount", str(target)], check=True)
        (tree / "ordinary-file").touch()
        (tree / "device-link").symlink_to("/dev/null")
        (tree / "directory-link").symlink_to(tree)
        self.base["mounts"].append({"destination": "/dev/test", "source": "old",
                                    "type": "bind", "options": []})

        for source in (str(tree), str(tree / "adapter*")):
            with self.subTest(source=source):
                result = self.prepare(settings={"devices": [
                    {"source": source, "destination": "/dev/test"},
                    {"source": "/dev/zero", "destination": "/dev/test/adapter0/null"},
                    {"destination": "/dev/test/adapter1/zero", "remove": True}]})
                self.assertEqual(result.returncode, 0, result.stderr)
                config = self.generated()
                self.assertEqual([d["path"] for d in config["linux"]["devices"]],
                                 ["/dev/test/adapter0/null"])
                self.assert_device(config, "/dev/test/adapter0/null", "/dev/zero")
                self.assertFalse(any(m["destination"] == "/dev/test"
                                     for m in config["mounts"]))

        result = self.prepare(settings={"devices": [{"source": str(tree)}]})
        self.assertEqual(result.returncode, 0, result.stderr)
        config = self.generated()
        self.assert_device(config, str(tree / "adapter0/null"), "/dev/null")
        self.assert_device(config, str(tree / "adapter1/zero"), "/dev/zero")

        alias = self.directory / "tree-alias"
        alias.symlink_to(tree)
        result = self.prepare(settings={"devices": [{"source": str(alias)}]})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assert_device(self.generated(), str(alias / "adapter0/null"), "/dev/null")

        target = tree / "hostname"
        target.touch()
        subprocess.run(["mount", "--bind", "/dev/null", str(target)], check=True)
        self.addCleanup(subprocess.run, ["umount", str(target)], check=True)
        result = self.prepare(settings={"devices": [
            {"source": str(tree / "host*"), "destination": "/etc"}]})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("reserved mount destination: /etc/hostname", result.stderr)

    def test_payload_memory_limit_preserves_other_resources(self):
        self.base["linux"]["resources"]["memory"] = {"limit": 123, "swap": 456}
        for value, expected in [(None, 123), ("5G", 5 * 1024 ** 3), ("infinity", -1)]:
            with self.subTest(value=value):
                result = self.prepare(settings={"memory-max": value} if value else {})
                self.assertEqual(result.returncode, 0, result.stderr)
                config = self.generated()["linux"]
                self.assertEqual(config["resources"]["memory"], {"limit": expected, "swap": 456})
                self.assertTrue(config["cgroupsPath"].endswith("/payload"))
                self.assertEqual(config["resources"]["pids"], {"limit": -1})

    def test_capability_changes_precede_seccomp_resolution(self):
        self.base["process"]["capabilities"] = {
            "ambient": ["CAP_NET_RAW"], "inheritable": ["CAP_NET_RAW"]}
        profile = {"defaultAction": "SCMP_ACT_ERRNO", "syscalls": [
            {"names": ["getpid"], "action": "SCMP_ACT_ALLOW",
             "includes": {"caps": ["CAP_SYS_RESOURCE"]}},
            {"names": ["getppid"], "action": "SCMP_ACT_ALLOW",
             "includes": {"caps": ["CAP_NET_RAW"]}}]}
        result = self.prepare(seccomp=profile, settings={
            "capabilities": [*self.vendor["capabilities"],
                             {"name": "sys_resource"}, {"name": "CAP_SYS_RESOURCE"},
                             {"name": "net_raw", "remove": True}]})
        self.assertEqual(result.returncode, 0, result.stderr)
        config = self.generated()
        caps = config["process"]["capabilities"]
        for name in ("bounding", "effective", "permitted"):
            self.assertEqual(caps[name].count("CAP_SYS_RESOURCE"), 1)
            self.assertNotIn("CAP_NET_RAW", caps[name])
        self.assertEqual(caps["ambient"], [])
        self.assertEqual(caps["inheritable"], [])
        self.assertEqual(config["linux"]["seccomp"]["syscalls"], [
            {"names": ["getpid"], "action": "SCMP_ACT_ALLOW"}])

    def test_capabilities_apply_in_list_order(self):
        for capabilities, expected in (
            ([{"name": "all", "remove": True}, {"name": "CAP_CHOWN"}], ["CAP_CHOWN"]),
            ([{"name": "chown"}, {"name": "ALL", "remove": True}], []),
            ([{"name": "all", "remove": True}, {"name": "chown", "remove": False}],
             ["CAP_CHOWN"]),
            ([{"name": "ALL"}, {"name": "all", "remove": True}], []),
        ):
            with self.subTest(capabilities=capabilities):
                result = self.prepare(settings={"capabilities": capabilities})
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(self.generated()["process"]["capabilities"], {
                    name: expected for name in ("bounding", "effective", "permitted")})

    def test_unmask_specific_paths_and_all(self):
        result = self.prepare(settings={"unmask": ["/proc/./keys/", "/proc/unused/../sys", "/absent"]})
        self.assertEqual(result.returncode, 0, result.stderr)
        linux = self.generated()["linux"]
        self.assertEqual(linux["maskedPaths"], [p for p in self.base["linux"]["maskedPaths"]
                                                 if p != "/proc/keys"])
        self.assertEqual(linux["readonlyPaths"], [p for p in self.base["linux"]["readonlyPaths"]
                                                   if p != "/proc/sys"])
        result = self.prepare(settings={"unmask": ["ALL"]})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.generated()["linux"]["maskedPaths"], [])
        self.assertEqual(self.generated()["linux"]["readonlyPaths"], [])

    def test_missing_resolver(self):
        self.resolv.unlink()
        result = self.prepare()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.runtime / "files/resolv.conf").read_text(), "")
        self.resolv.symlink_to(self.directory / "missing/resolv.conf")
        result = self.prepare()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.runtime / "files/resolv.conf").read_text(), "")

    def test_resolver_read_error(self):
        self.resolv.unlink()
        self.resolv.mkdir()
        result = self.prepare()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(f"read {self.resolv}", result.stderr)

    def update_resolv(self, *extra, env=None):
        filename = self.directory / "update.conf"
        filename.write_text(json.dumps({"resolv-conf": str(self.resolv)}))
        return subprocess.run(
            [str(LAUNCHER), "update-resolv-conf", "--config", str(filename),
             *extra], text=True, capture_output=True,
            env={**os.environ, "RUNTIME_DIRECTORY": str(self.runtime), **(env or {})})

    @unittest.skipUnless(EXPECTED_CGROUP is not None, "requires the preparation test's truncate fixture")
    def test_update_resolver_before_truncate(self):
        result = self.prepare()
        self.assertEqual(result.returncode, 0, result.stderr)
        target = self.runtime / "files/resolv.conf"
        snapshot = self.directory / "before-truncate"
        snapshot.mkdir()
        for contents in ("nameserver 1.1.1.1\n", "", "search example.test\nnameserver 192.0.2.54\n"):
            with self.subTest(contents=contents):
                old_size = target.stat().st_size
                self.resolv.write_text(contents)
                result = self.update_resolv(env={"QM_TEST_BEFORE_TRUNCATE_DIR": str(snapshot)})
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual((snapshot / "resolv.conf").read_bytes(), contents.encode().ljust(old_size, b" "))
                self.assertEqual(target.read_text(), contents)

    def test_update_resolver_in_place(self):
        result = self.prepare()
        self.assertEqual(result.returncode, 0, result.stderr)
        target = self.runtime / "files/resolv.conf"
        alias = self.directory / "bound-resolv.conf"
        os.link(target, alias)
        original = target.stat()
        for contents in ("search example.test\nnameserver 192.0.2.54\n",
                         "nameserver 192.0.2.55\n", ""):
            with self.subTest(contents=contents):
                self.resolv.write_text(contents)
                result = self.update_resolv()
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(target.stat().st_ino, original.st_ino)
                self.assertEqual(target.stat().st_mode, original.st_mode)
                self.assertEqual(alias.read_text(), contents)

    def test_update_resolver_missing_files(self):
        result = self.update_resolv()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        self.assertFalse(self.runtime.exists())
        result = self.prepare()
        self.assertEqual(result.returncode, 0, result.stderr)
        contents = self.resolv.read_text()
        self.resolv.unlink()
        result = self.update_resolv()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.runtime / "files/resolv.conf").read_text(), contents)

    def test_update_resolver_missing_destination(self):
        result = self.prepare()
        self.assertEqual(result.returncode, 0, result.stderr)
        target = self.runtime / "files/resolv.conf"
        target.unlink()
        self.resolv.write_text("nameserver 192.0.2.55\n")
        result = self.update_resolv()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        self.assertFalse(target.exists())

    def test_update_resolver_read_error(self):
        result = self.prepare()
        self.assertEqual(result.returncode, 0, result.stderr)
        contents = self.resolv.read_text()
        self.resolv.unlink()
        self.resolv.mkdir()
        result = self.update_resolv()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(f"read {self.resolv}", result.stderr)
        self.assertEqual((self.runtime / "files/resolv.conf").read_text(), contents)

    def test_update_resolver_arguments(self):
        for extra in (("cleanup",), ("--prepare-only",),
                      ("exec", "/bin/true"), (str(SOURCE / "data/qm.json"),)):
            with self.subTest(extra=extra):
                result = self.update_resolv(*extra)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("update-resolv-conf", result.stderr)

    def test_update_hosts_in_place(self):
        snapshot = self.directory / "before-truncate"
        snapshot.mkdir()
        for hostname in ("qm", "qm-test"):
            with self.subTest(hostname=hostname):
                result = self.prepare(hostname=hostname)
                self.assertEqual(result.returncode, 0, result.stderr)
                target = self.runtime / "files/hosts"
                contents = target.read_text()
                self.assertIn("10.90.0.1\thost.containers.internal host.docker.internal\n", contents)
                self.assertIn(f"10.90.0.2\t{hostname}" + (" qm" if hostname != "qm" else "") + "\n", contents)
                alias = self.directory / "bound-hosts"
                alias.unlink(missing_ok=True)
                os.link(target, alias)
                original = target.stat()
                for previous in ("", contents + "192.0.2.100\tstale-host\n"):
                    target.write_text(previous)
                    result = self.update_resolv(env={"QM_TEST_BEFORE_TRUNCATE_DIR": str(snapshot)})
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(target.stat().st_ino, original.st_ino)
                    self.assertEqual(target.stat().st_mode, original.st_mode)
                    self.assertEqual(alias.read_text(), contents)
                    if EXPECTED_CGROUP is not None:
                        self.assertEqual((snapshot / "hosts").read_bytes(),
                                         contents.encode().ljust(len(previous.encode()), b" "))
                target.unlink()
                result = self.update_resolv()
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertFalse(target.exists())

    @unittest.skipUnless(PRIVATE_PATHS, "requires the smoke test's private /etc")
    def test_update_hosts_without_resolver(self):
        result = self.prepare(hostname="qm-test")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.resolv.unlink()
        target = self.runtime / "files/hosts"
        for contents in ("127.0.0.1\tlocalhost\n192.0.2.100\tnew-host\n", ""):
            self.hosts.write_text(contents)
            result = self.update_resolv()
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(target.read_text().startswith(contents + "\n"))
            self.assertIn("10.90.0.2\tqm-test qm\n", target.read_text())
            self.assertNotIn("stale-host", target.read_text())
            if not contents:
                self.assertNotIn("new-host", target.read_text())
        previous = target.read_text()
        self.hosts.unlink()
        result = self.update_resolv()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(target.read_text(), previous)

    @unittest.skipUnless(PRIVATE_PATHS, "requires the smoke test's private /etc")
    def test_update_hosts_read_error(self):
        result = self.prepare()
        self.assertEqual(result.returncode, 0, result.stderr)
        target = self.runtime / "files/hosts"
        previous = target.read_text()
        self.hosts.unlink()
        self.hosts.mkdir()
        try:
            result = self.update_resolv()
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("read /etc/hosts", result.stderr)
            self.assertEqual(target.read_text(), previous)
        finally:
            self.hosts.rmdir()

    @unittest.skipUnless(PRIVATE_PATHS, "requires the smoke test's private /etc and /run")
    def test_missing_default_resolver(self):
        result = self.prepare(host_resolv=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.runtime / "files/resolv.conf").read_text(), "")

    def test_static_mount_settings_are_preserved(self):
        localtime = self.directory / "localtime"
        localtime.touch()
        self.base["mounts"].append({"destination": "/etc/localtime", "type": "bind",
                                    "source": str(localtime), "options": ["bind", "ro"]})
        for mount in self.base["mounts"]:
            if mount["destination"] == "/dev/shm":
                mount["options"] = ["rw", "nosuid", "nodev", "size=128m"]
            elif mount["destination"] == "/etc/localtime":
                mount["source"] = str(localtime)
        result = self.prepare(settings={"mounts": []})
        self.assertEqual(result.returncode, 0, result.stderr)
        expected = [m for m in self.base["mounts"]
                    if m["destination"] in ("/dev/shm", "/etc/localtime")]
        actual = [m for m in self.generated()["mounts"]
                  if m["destination"] in ("/dev/shm", "/etc/localtime")]
        self.assertEqual(actual, expected)

    def test_missing_annotations(self):
        self.base.pop("annotations")
        result = self.prepare()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.generated()["annotations"],
                         {"io.container.manager": "qmc"})

    @unittest.skipUnless(PRIVATE_PATHS, "requires the smoke test's private /etc and /dev")
    def test_existing_device_mount(self):
        self.base["mounts"].append({"destination": "/dev/kvm", "type": "tmpfs",
                                    "source": "old", "options": ["ro", "nodev"]})
        (self.devices / "kvm").symlink_to("/dev/null")
        result = self.prepare()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assert_device(self.generated(), "/dev/kvm", "/dev/null")

    @unittest.skipUnless(PRIVATE_PATHS, "requires the smoke test's private /etc and /dev")
    def test_optional_devices(self):
        result = self.prepare()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(any(m["destination"] in ("/dev/kvm", "/dev/fuse")
                             for m in self.generated()["mounts"]))
        self.assertFalse(any(d["path"] in ("/dev/kvm", "/dev/fuse")
                             for d in self.generated()["linux"].get("devices", [])))
        (self.devices / "kvm").symlink_to("/dev/null")
        (self.devices / "fuse").symlink_to("/dev/zero")
        result = self.prepare()
        self.assertEqual(result.returncode, 0, result.stderr)
        config = self.generated()
        self.assert_device(config, "/dev/kvm", "/dev/null")
        self.assert_device(config, "/dev/fuse", "/dev/zero")
        rules = config["linux"]["resources"]["devices"]
        self.assertTrue(any(r.get("allow") is True and r.get("major") == 1 and
                            r.get("minor") == 3 for r in rules))
        self.assertTrue(any(r.get("allow") is True and r.get("major") == 1 and
                            r.get("minor") == 5 for r in rules))

    @unittest.skipUnless(PRIVATE_PATHS, "requires the smoke test's private /etc and /dev")
    def test_auto_userns(self):
        (self.subids / "subuid").write_text("other:100000:65536\nqm_root:1000000000:1500000000\n")
        (self.subids / "subgid").write_text("qm_root:2000000000:500000000\n")
        result = self.prepare()
        self.assertEqual(result.returncode, 0, result.stderr)
        linux = self.generated()["linux"]
        self.assertIn({"type": "user"}, linux["namespaces"])
        self.assertEqual(linux["uidMappings"],
                         [{"containerID": 0, "hostID": 1000000000, "size": 1500000000}])
        self.assertEqual(linux["gidMappings"],
                         [{"containerID": 0, "hostID": 2000000000, "size": 500000000}])
        result = self.prepare(settings={"userns": "off"})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("uidMappings", self.generated()["linux"])

    @unittest.skipUnless(PRIVATE_PATHS, "requires the smoke test's private /etc and /dev")
    def test_userns_invalid_or_incomplete(self):
        result = self.prepare(settings={"userns": "required"})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("required", result.stderr)
        (self.subids / "subuid").write_text("qm_root:1000000000:1000\n")
        result = self.prepare()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("both subuid and subgid", result.stderr)
        (self.subids / "subgid").write_text("qm_root:4294967290:10\n")
        result = self.prepare()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("invalid qm_root size", result.stderr)

    def test_capability_filter(self):
        removals = [{"name": name, "remove": True}
                    for name in ("CAP_SYS_ADMIN", "CAP_BPF", "CAP_PERFMON", "CAP_AUDIT_WRITE")]
        result = self.prepare(settings={"capabilities": [*self.vendor["capabilities"], *removals]})
        self.assertEqual(result.returncode, 0, result.stderr)
        rules = self.generated()["linux"]["seccomp"]["syscalls"]
        for syscall in ("bpf", "perf_event_open"):
            self.assertTrue(any(syscall in r["names"] and r["action"] == "SCMP_ACT_ERRNO" for r in rules))
            self.assertFalse(any(syscall in r["names"] and r["action"] == "SCMP_ACT_ALLOW" for r in rules))
        self.assertTrue(any(r["names"] == ["socket"] and r.get("errnoRet") == 22 for r in rules))

    def test_invalid_inputs(self):
        cases = [
            ({"hostname": "bad\nhost"}, "invalid hostname"),
            ({"settings": {"userns": "invalid"}}, "invalid userns mode"),
            ({"base": {**self.base, "annotations": []}}, "invalid annotations"),
            ({"base": {**self.base, "process": {**self.base["process"], "env": [None]}}}, "JSON string"),
            ({"seccomp": {"syscalls": [{"includes": {"minKernel": "6.0"}}]}}, "unsupported seccomp condition"),
        ]
        for arguments, error in cases:
            with self.subTest(error=error):
                result = self.prepare(**arguments)
                self.assertGreater(result.returncode, 0)
                self.assertIn(error, result.stderr)

    def test_absolute_path_errors(self):
        for option in ("--runtime-dir", "rootfs", "base-config", "seccomp", "resolv-conf"):
            with self.subTest(option=option):
                result = self.prepare(**({"extra": (option, "relative")} if option.startswith("--")
                                         else {"settings": {option: "relative"}}))
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(f"{option} must be an absolute path", result.stderr)

    def test_cleanup_after_delete_failure(self):
        result = self.prepare()
        self.assertEqual(result.returncode, 0, result.stderr)
        state = self.runtime / "crun/qm"
        state.mkdir()
        (state / "status").touch()
        (self.runtime / "netns").touch()
        saved = {"version": 1, "netns": str(self.runtime / "netns"),
                 "crun": {"executable": "/bin/false", "root": str(self.runtime / "crun"), "id": "qm"}}
        (self.runtime / "state.json").write_text(json.dumps(saved))
        result = subprocess.run(
            [str(LAUNCHER), "cleanup", "--runtime-dir", str(self.runtime)],
            text=True, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.runtime / "netns").exists())
        self.assertEqual(json.loads((self.runtime / "state.json").read_text()), saved)
        (state / "status").unlink()
        result = subprocess.run(
            [str(LAUNCHER), "cleanup", "--runtime-dir", str(self.runtime)],
            text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.runtime / "state.json").exists())

    def test_cleanup_without_namespace(self):
        result = self.prepare()
        self.assertEqual(result.returncode, 0, result.stderr)
        (self.runtime / "netns").touch()
        (self.runtime / "state.json").write_text(json.dumps(
            {"version": 1, "netns": str(self.runtime / "netns")}))
        result = subprocess.run([str(LAUNCHER), "cleanup", "--runtime-dir", str(self.runtime)])
        self.assertEqual(result.returncode, 0)
        self.assertFalse((self.runtime / "netns").exists())
        self.assertFalse((self.runtime / "state.json").exists())

    def test_cleanup_without_state_preserves_unrecorded_files(self):
        result = self.prepare()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.runtime / "state.json").exists())
        (self.runtime / "netns").touch()
        result = subprocess.run([str(LAUNCHER), "cleanup", "--runtime-dir", str(self.runtime)],
                                text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.runtime / "netns").exists())

    def test_cleanup_without_state_preserves_empty_runtime_directory(self):
        self.runtime.mkdir(mode=0o1700)
        original = self.runtime.stat()
        command = [str(LAUNCHER), "cleanup", "--runtime-dir", str(self.runtime)]
        result = subprocess.run(command, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.runtime.stat().st_ino, original.st_ino)
        self.assertEqual(self.runtime.stat().st_mode, original.st_mode)
        self.assertEqual(list(self.runtime.iterdir()), [])

    def test_cleanup_uses_recorded_crun_and_namespace(self):
        result = self.prepare()
        self.assertEqual(result.returncode, 0, result.stderr)
        pin = self.directory / "recorded-pin"
        pin.touch()
        (self.runtime / "netns").touch()
        root = self.directory / "recorded-crun-root"
        status = root / "recorded-id/status"
        status.parent.mkdir(parents=True)
        status.touch()
        default_status = self.runtime / "crun/qm/status"
        default_status.parent.mkdir()
        default_status.touch()
        arguments = self.directory / "delete-arguments.json"
        executable = self.directory / "recorded-crun"
        executable.write_text(
            f"#!{sys.executable}\nimport json, pathlib, sys\n"
            f"pathlib.Path({str(arguments)!r}).write_text(json.dumps(sys.argv[1:]))\n"
            f"pathlib.Path({str(status)!r}).unlink()\n")
        executable.chmod(0o755)
        (self.runtime / "state.json").write_text(json.dumps({
            "version": 1, "netns": str(pin),
            "crun": {"executable": str(executable), "root": str(root), "id": "recorded-id"}}))
        result = subprocess.run([str(LAUNCHER), "cleanup", "--runtime-dir", str(self.runtime)],
                                text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(arguments.read_text()),
                         ["--root", str(root), "delete", "--force", "recorded-id"])
        self.assertFalse(pin.exists())
        self.assertFalse(status.exists())
        self.assertFalse((self.runtime / "state.json").exists())
        self.assertTrue(default_status.exists())
        self.assertTrue((self.runtime / "netns").exists())

    def test_invalid_cleanup_state_is_preserved(self):
        result = self.prepare()
        self.assertEqual(result.returncode, 0, result.stderr)
        pin = self.runtime / "netns"
        pin.touch()
        state = self.runtime / "state.json"
        invalid_network = json.dumps({"version": 1, "netns": str(pin),
                                      "network": {"owner": "qm-launch:/saved",
                                                  "veth": "a" * 16, "nft_table": "saved"}})
        for contents in ("{", '{"version":2}', '{"version":1,"netns":false}', invalid_network):
            with self.subTest(contents=contents):
                state.write_text(contents)
                result = subprocess.run([str(LAUNCHER), "cleanup", "--runtime-dir", str(self.runtime)],
                                        text=True, capture_output=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(state.read_text(), contents)
                self.assertTrue(pin.exists())

    @unittest.skipUnless(os.geteuid() == 0, "startup requires root")
    def test_startup_warns_and_retries_partial_cleanup(self):
        result = self.prepare()
        self.assertEqual(result.returncode, 0, result.stderr)
        bundle = (self.runtime / "config.json").read_bytes()
        status = self.runtime / "crun/qm/status"
        status.parent.mkdir()
        status.touch()
        pin = self.runtime / "netns"
        pin.touch()
        saved = json.dumps({"version": 1, "bundle": str(self.runtime), "netns": str(pin),
                            "crun": {"executable": "/bin/false",
                                     "root": str(self.runtime / "crun"), "id": "qm"}})
        state = self.runtime / "state.json"
        state.write_text(saved)
        missing_config = self.directory / "missing.json"
        filename = self.directory / "qmc.conf"
        filename.write_text(json.dumps({"base-config": str(missing_config)}))
        command = [str(LAUNCHER), "launch", "--runtime-dir", str(self.runtime),
                   "--config", str(filename)]
        result = subprocess.run(command, text=True, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("cleanup incomplete; continuing startup", result.stderr)
        self.assertIn(f"read {missing_config}", result.stderr)
        self.assertEqual(state.read_text(), saved)
        self.assertEqual((self.runtime / "config.json").read_bytes(), bundle)
        self.assertFalse(pin.exists())
        status.unlink()
        result = subprocess.run(command, text=True, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(f"read {missing_config}", result.stderr)
        self.assertFalse(state.exists())
        self.assertTrue(self.runtime.is_dir())
        self.assertEqual(list(self.runtime.iterdir()), [self.runtime / "signals"])

    def test_successful_cleanup_preserves_runtime_directory_metadata(self):
        result = self.prepare()
        self.assertEqual(result.returncode, 0, result.stderr)
        (self.runtime / "netns").touch()
        (self.runtime / "state.json").write_text(json.dumps({
            "version": 1, "bundle": str(self.runtime), "netns": str(self.runtime / "netns")}))
        self.runtime.chmod(0o1700)
        original = self.runtime.stat()
        command = [str(LAUNCHER), "cleanup", "--runtime-dir", str(self.runtime)]
        for _ in range(2):
            result = subprocess.run(command, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(self.runtime.stat().st_ino, original.st_ino)
            self.assertEqual(self.runtime.stat().st_mode, original.st_mode)
            self.assertEqual(list(self.runtime.iterdir()), [self.runtime / "signals"])

    def test_cleanup_removes_bundle_without_following_symlinks(self):
        result = self.prepare()
        self.assertEqual(result.returncode, 0, result.stderr)
        (self.runtime / "extra-file").write_text("another runtime file\n")
        target = self.directory / "symlink-target"
        target.write_text("outside the bundle\n")
        hostname = self.runtime / "files/hostname"
        hostname.unlink()
        hostname.symlink_to(target)
        crun = self.runtime / "crun"
        cache = crun / ".cache/seccomp"
        cache.mkdir(parents=True)
        (cache / "filter").write_text("cached filter\n")
        (cache / "link").symlink_to(target)
        (crun / ".empty-directory").mkdir(mode=0o555)
        (self.runtime / "state.json").write_text(json.dumps({
            "version": 1, "bundle": str(self.runtime),
            "crun": {"executable": "/bin/false", "root": str(crun), "id": "qm"}}))
        result = subprocess.run(
            [str(LAUNCHER), "cleanup", "--runtime-dir", str(self.runtime)],
            text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(self.runtime.is_dir())
        self.assertEqual(list(self.runtime.iterdir()), [self.runtime / "signals"])
        self.assertEqual(target.read_text(), "outside the bundle\n")

    def test_signals_survive_preparation_cleanup_and_restart(self):
        command = [str(LAUNCHER), "signal", "--runtime-dir", str(self.runtime)]
        result = subprocess.run([*command, "network-ready"], text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        signal = self.runtime / "signals/network-ready"
        original = signal.stat()
        for _ in range(2):
            result = self.prepare()
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(signal.stat().st_ino, original.st_ino)
            (self.runtime / "state.json").write_text(json.dumps({
                "version": 1, "bundle": str(self.runtime)}))
            result = subprocess.run([str(LAUNCHER), "cleanup", "--runtime-dir", str(self.runtime)],
                                    text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(list(self.runtime.iterdir()), [signal.parent])
            self.assertEqual(signal.stat().st_ino, original.st_ino)
        result = subprocess.run([*command, "--clear", "network-ready"],
                                text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(signal.exists())

    def test_prepare_preserves_existing_cleanup_state(self):
        result = self.prepare()
        self.assertEqual(result.returncode, 0, result.stderr)
        saved = '{"version":1}'
        (self.runtime / "state.json").write_text(saved)
        result = self.prepare()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("cleanup state already exists", result.stderr)
        self.assertEqual((self.runtime / "state.json").read_text(), saved)


unittest.main()
