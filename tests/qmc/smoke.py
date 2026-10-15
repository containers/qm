# SPDX-License-Identifier: GPL-2.0-only
# Copyright (C) 2026 Alexander Larsson
# See LICENSE for the full license text.

import json
import os
import pathlib
import re
import select
import shutil
import signal
import socket
import struct
import subprocess
import sys
import tempfile
import time

SOURCE = pathlib.Path(__file__).resolve().parents[2]
LAUNCHER = pathlib.Path(sys.argv[1]).resolve()
VENDOR = json.loads((SOURCE / "data/qmc.conf.in").read_text())


def run(*args):
    result = subprocess.run(args, text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError(f"{args}: {result.stdout}{result.stderr}")
    return result.stdout


def wait_until(condition):
    deadline = time.monotonic() + 5
    while not condition():
        assert time.monotonic() < deadline, "Timed out waiting for network setup"
        time.sleep(0.01)


INIT = r'''
#include <arpa/inet.h>
#include <errno.h>
#include <fcntl.h>
#include <netinet/tcp.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/socket.h>
#include <sys/time.h>
#include <sys/un.h>
#include <unistd.h>

static void stop(int signum) { (void)signum; _exit(0); }
static int notify_fd = -1;
static void ready(int signum) {
    (void)signum;
    if (notify_fd >= 0 && write(notify_fd, "READY=1", 7) != 7)
        _exit(14);
}

int main(int argc, char **argv)
{
    if (argc == 2 && !strcmp(argv[1], "--check-bindings")) {
        char contents[32] = {0};
        int fd = open("/shared/token", O_RDONLY);
        if (fd < 0 || read(fd, contents, sizeof(contents) - 1) != 13 ||
            strcmp(contents, "shared token\n"))
            return 21;
        close(fd);
        errno = 0;
        fd = open("/shared/token", O_WRONLY);
        if (fd >= 0 || errno != EROFS)
            return 22;
        fd = open("/dev/null", O_RDONLY);
        if (fd < 0 || read(fd, contents, 1) != 0)
            return 24;
        close(fd);
        if (access("/dev/removed", F_OK) == 0 || access("/optional", F_OK) == 0)
            return 25;
        puts("BINDINGS OK");
        return 0;
    }
    if (argc == 2 && !strcmp(argv[1], "--console-fail")) {
        /* Like systemd PID 1, discard inherited stdio and reopen the console. */
        for (int fd = 0; fd < 3; fd++)
            close(fd);
        usleep(100000);
        int console = open("/dev/console", O_WRONLY | O_NOCTTY);
        if (console < 0 || !isatty(console))
            return 15;
        for (int i = 0; i < 2048; i++)
            if (dprintf(console, "Fatal init diagnostic %d\n", i) < 0)
                return 16;
        return 255;
    }
    if (argc == 2 && !strcmp(argv[1], "--notify"))
        return kill(1, SIGUSR1) < 0 ? 13 : 0;
    if (argc == 2 && (!strcmp(argv[1], "--network-check") ||
                      !strcmp(argv[1], "--network-bulk"))) {
        int bulk = !strcmp(argv[1], "--network-bulk");
        int fd = socket(AF_INET, SOCK_STREAM, 0);
        struct timeval timeout = { .tv_sec = 4 };
        setsockopt(fd, SOL_SOCKET, SO_RCVTIMEO, &timeout, sizeof(timeout));
        setsockopt(fd, SOL_SOCKET, SO_SNDTIMEO, &timeout, sizeof(timeout));
        struct sockaddr_in server = { .sin_family = AF_INET, .sin_port = htons(49000) };
        inet_pton(AF_INET, "192.0.2.2", &server.sin_addr);
        const char request[] = "qm-network\n";
        if (fd < 0 || connect(fd, (struct sockaddr *)&server, sizeof(server)))
            return 10;
        if (bulk) {
            int mss;
            socklen_t length = sizeof(mss);
            if (getsockopt(fd, IPPROTO_TCP, TCP_MAXSEG, &mss, &length) || mss > 1260)
                return 18;
            char data[4096];
            memset(data, 'Q', sizeof(data));
            /* Send and receive 256 KiB, checking every byte in each direction. */
            for (int i = 0; i < 64; i++) {
                size_t offset = 0;
                while (offset < sizeof(data)) {
                    ssize_t count = write(fd, data + offset, sizeof(data) - offset);
                    if (count <= 0)
                        return 19;
                    offset += count;
                }
            }
            for (int i = 0; i < 64; i++) {
                size_t offset = 0;
                while (offset < sizeof(data)) {
                    ssize_t count = read(fd, data + offset, sizeof(data) - offset);
                    if (count <= 0)
                        return 20;
                    offset += count;
                }
                for (size_t j = 0; j < sizeof(data); j++)
                    if (data[j] != 'Q')
                        return 21;
            }
            close(fd);
            return 0;
        }
        if (write(fd, request, sizeof(request) - 1) != sizeof(request) - 1)
            return 10;
        char response[sizeof(request) - 1];
        size_t offset = 0;
        while (offset < sizeof(response)) {
            ssize_t count = read(fd, response + offset, sizeof(response) - offset);
            if (count <= 0)
                return 11;
            offset += count;
        }
        close(fd);
        return memcmp(request, response, sizeof(response)) ? 12 : 0;
    }
    if (argc == 2 && (!strcmp(argv[1], "--read-resolv") ||
                      !strcmp(argv[1], "--read-hosts"))) {
        FILE *file = fopen(!strcmp(argv[1], "--read-resolv") ?
                           "/etc/resolv.conf" : "/etc/hosts", "r");
        if (!file)
            return 8;
        char line[4096];
        while (fgets(line, sizeof(line), file))
            fputs(line, stdout);
        int status = ferror(file) ? 9 : 0;
        fclose(file);
        return status;
    }
    if (argc > 1) {
        if (argc != 3 || strcmp(argv[1], "--exec-check") ||
            strcmp(argv[2], "argument with spaces") || getpid() == 1)
            return 7;
        printf("EXEC %s tty=%d\n", argv[2], isatty(STDIN_FILENO));
        return 23;
    }
    char buffer[512];
    FILE *file = fopen("/proc/self/cgroup", "r");
    if (!file || !fgets(buffer, sizeof(buffer), file) || strcmp(buffer, "0::/\n"))
        return 2;
    fclose(file);
    if (mkdir("/sys/fs/cgroup/init.scope", 0755))
        return 3;
    file = fopen("/sys/fs/cgroup/init.scope/cgroup.procs", "w");
    if (!file || fputs("0\n", file) < 0 || fclose(file))
        return 4;
    file = fopen("/sys/fs/cgroup/cgroup.subtree_control", "w");
    if (!file || fputs("+memory +pids\n", file) < 0 || fclose(file))
        return 5;
    file = fopen("/sys/fs/cgroup/init.scope/memory.max", "r");
    if (!file)
        return 6;
    fclose(file);
    const char *notify = getenv("NOTIFY_SOCKET");
    if (notify) {
        /* PID 1 must be able to bind its own service notification socket. */
        mkdir("/run/systemd", 0755);
        struct sockaddr_un own = { .sun_family = AF_UNIX,
                                   .sun_path = "/run/systemd/notify" };
        int own_fd = socket(AF_UNIX, SOCK_DGRAM, 0);
        if (own_fd < 0 || bind(own_fd, (struct sockaddr *)&own, sizeof(own)))
            return 17;
        struct sockaddr_un address = { .sun_family = AF_UNIX };
        if (strlen(notify) >= sizeof(address.sun_path))
            return 12;
        strcpy(address.sun_path, notify);
        notify_fd = socket(AF_UNIX, SOCK_DGRAM, 0);
        if (notify_fd < 0 || connect(notify_fd, (struct sockaddr *)&address, sizeof(address)))
            return 12;
    }
    signal(SIGRTMIN + 3, stop);
    signal(SIGUSR1, ready);
    puts("READY");
    fflush(stdout);
    for (;;) pause();
}
'''

run("mount", "--make-rprivate", "/")
run("mount", "-t", "tmpfs", "tmpfs", "/run")
supervisor = pathlib.Path("/sys/fs/cgroup") / pathlib.Path(
    pathlib.Path("/proc/self/cgroup").read_text().strip().removeprefix("0::")
).relative_to("/")
assert supervisor.name == "supervisor", "run with DelegateSubgroup=supervisor"
service = supervisor.parent

with tempfile.TemporaryDirectory(prefix="qm-launch-smoke-") as temporary:
    directory = pathlib.Path(temporary)
    rootfs = directory / "rootfs"
    rootfs.mkdir()
    init_source = directory / "init.c"
    init_source.write_text(INIT)
    run("/usr/bin/cc", "-o", str(rootfs / "init"), str(init_source))
    for dependency in re.findall(r"(/[^\s()]+)", run("ldd", str(rootfs / "init"))):
        target = rootfs / dependency.lstrip("/")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(dependency, target)
    config = json.loads((SOURCE / "data/qm.json").read_text())
    config["root"]["path"] = str(rootfs)
    config["process"]["args"] = ["/init"]
    config["process"].pop("selinuxLabel")
    config["process"].pop("rlimits")
    config["linux"].pop("mountLabel")
    config["linux"]["resources"] = {"devices": []}
    config["linux"].pop("sysctl")
    config["mounts"] = [m for m in config["mounts"]
                        if m["destination"] != "/sys/fs/selinux"]
    for mount in config["mounts"]:
        if mount["destination"] == "/etc/localtime":
            mount["source"] = str(directory / "missing-localtime")
        if mount.get("type") == "devpts":
            mount["options"] = ["gid=0" if o == "gid=5" else o for o in mount["options"]]
    base = directory / "base.json"
    base.write_text(json.dumps(config))
    resolv = directory / "resolv.conf"

    devices = directory / "devices"
    devices.mkdir()
    etc = directory / "etc"
    etc.mkdir()
    shutil.copy2("/etc/hosts", etc / "hosts")
    for name in ("null", "zero"):
        (devices / name).touch()
    mounts = []
    try:
        for source, target in (("/dev/null", devices / "null"),
                               ("/dev/zero", devices / "zero"),
                               (etc, "/etc"), (devices, "/dev"),
                               (devices / "null", "/dev/null"),
                               (devices / "zero", "/dev/zero")):
            run("mount", "--bind", str(source), str(target))
            mounts.append(str(target))
        subprocess.run([sys.executable, str(SOURCE / "tests/qmc/prepare.py"),
                        str(LAUNCHER), str(SOURCE)], check=True,
                       env={**os.environ, "QM_TEST_PRIVATE_PATHS": "1"})
    finally:
        for target in reversed(mounts):
            run("umount", target)
    subprocess.run([sys.executable, str(SOURCE / "tests/qmc/exec.py"), str(LAUNCHER)],
                   check=True, env={**os.environ, "QM_TEST_PRIVATE_CRUN": "1"})
    # Keep host-file changes within the smoke test's mount namespace.
    run("mount", "--bind", str(etc / "hosts"), "/etc/hosts")

    # An upstream with no route to QM proves that replies require masquerading.
    run("ip", "netns", "add", "qm-upstream")
    run("ip", "link", "add", "qm-uplink", "type", "veth", "peer", "name",
        "router", "netns", "qm-upstream")
    run("ip", "addr", "add", "192.0.2.1/24", "dev", "qm-uplink")
    run("ip", "link", "set", "qm-uplink", "mtu", "1400", "up")
    run("ip", "netns", "exec", "qm-upstream", "ip", "addr", "add", "192.0.2.2/24", "dev", "router")
    run("ip", "netns", "exec", "qm-upstream", "ip", "link", "set", "router", "mtu", "1400", "up")
    run("ip", "netns", "exec", "qm-upstream", "ip", "link", "set", "lo", "up")
    run("ip", "route", "add", "default", "via", "192.0.2.2")
    run("nft", "add", "table", "ip", "unrelated")
    def launch(attempt, extra=(), settings=None, existing_netns=False, notify_socket=None,
               launcher=LAUNCHER, env=None):
        runtime = directory / f"runtime-{attempt}"
        if existing_netns:
            runtime.mkdir(mode=0o700)
            (runtime / "netns").touch()

        environment = {**os.environ, "RUNTIME_DIRECTORY": str(runtime)}
        environment.update(env or {})
        if notify_socket is not None:
            environment["NOTIFY_SOCKET"] = str(notify_socket)
        config = {"base-config": str(base), "userns": "off",
                  "capabilities": VENDOR["capabilities"],
                  "seccomp": str(SOURCE / "tests/qmc/seccomp-no-rt.json"),
                  "resolv-conf": str(resolv), **(settings or {})}
        filename = directory / f"qmc-{attempt}.conf"
        filename.write_text(json.dumps(config))
        process = subprocess.Popen(
            [str(launcher), "launch", "--config", str(filename), *extra],
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, env=environment,
        )
        return process, runtime

    def assert_network_removed(runtime):
        links = json.loads(run("ip", "-j", "link", "show"))
        assert "qm-veth" not in {link["ifname"] for link in links}
        assert "qm_launch" not in run("nft", "list", "tables")
        assert "unrelated" in run("nft", "list", "tables")
        assert not (runtime / "netns").exists()
        assert not (runtime / "state.json").exists()
        assert runtime.is_dir()
        assert set(runtime.iterdir()) <= {runtime / "signals"}
        if (runtime / "signals").exists():
            assert list((runtime / "signals").iterdir()) == []

    def assert_masquerading(*command):
        listener = subprocess.Popen(
            ["ip", "netns", "exec", "qm-upstream", sys.executable, "-u", "-c",
             "import socket\ns = socket.socket()\ns.settimeout(10)\n"
             "s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)\n"
             "s.bind(('192.0.2.2', 49000))\ns.listen()\nprint('LISTENING', flush=True)\n"
             "c, peer = s.accept()\nprint(peer[0], flush=True)\nc.sendall(c.recv(128))\nc.close()\n"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            assert listener.stdout.readline() == "LISTENING\n"
            run(*command)
            stdout, stderr = listener.communicate(timeout=5)
            assert listener.returncode == 0, stderr
            assert stdout == "192.0.2.1\n", stdout
        finally:
            if listener.poll() is None:
                listener.kill()
                listener.wait()

    forwarding_path = pathlib.Path("/proc/sys/net/ipv4/ip_forward")
    forwarding_path.write_text("0\n")
    process, runtime = launch("forwarding-disabled")
    stdout, stderr = process.communicate(timeout=10)
    assert process.returncode == 1, (stdout, stderr)
    assert "host IPv4 forwarding is disabled" in stderr, stderr
    assert forwarding_path.read_text().strip() == "0"
    assert not (runtime / "state.json").exists()
    run(str(LAUNCHER), "cleanup", "--runtime-dir", str(runtime))
    assert_network_removed(runtime)

    # Apply forwarding before host tuning, just as the installed sysctl files do.
    # New links can still default to not forwarding even though the host routes.
    tuning = directory / "50-host-tuning.conf"
    tuning.write_text("net.ipv4.conf.default.forwarding = 0\n"
                      "net.ipv4.conf.qm-uplink.accept_redirects = 1\n")
    run("/usr/lib/systemd/systemd-sysctl", str(SOURCE / "systemd/00-qm-forwarding.conf"),
        str(tuning))
    assert forwarding_path.read_text().strip() == "1"
    host_tuning = pathlib.Path("/proc/sys/net/ipv4/conf/qm-uplink/accept_redirects")
    assert host_tuning.read_text().strip() == "1"

    # A read-only global setting proves that launch never tries to rewrite it.
    forwarding = directory / "read-only-forwarding"
    forwarding.write_text("1\n")
    run("mount", "--bind", str(forwarding), str(forwarding_path))
    run("mount", "-o", "remount,bind,ro", str(forwarding_path))
    # Model systemd's pre-created RuntimeDirectory and pin its original inode.
    runtime = directory / 'runtime-normal with "quotes" and \\slashes'
    runtime.mkdir(mode=0o1700)
    runtime_fd = os.open(runtime, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    original_runtime = os.fstat(runtime_fd)
    shared = directory / "shared-token"
    shared.write_text("shared token\n")
    memory_limits = {path: (path / "memory.max").read_text()
                     if (path / "memory.max").exists() else "max\n"
                     for path in (service, supervisor)}
    process, runtime = launch('normal with "quotes" and \\slashes',
                              settings={"hostname": "qm-test", "memory-max": "256M",
                                        "mounts": [
                                            {"source": str(shared), "destination": "/shared/token",
                                             "options": ["ro"]},
                                            {"source": str(directory / "missing"),
                                             "destination": "/optional", "optional": True}],
                                        "devices": [
                                            # Rootless crun binds OCI devices from their host path.
                                            {"source": "/dev/nul?"},
                                            {"source": "/dev/zero", "destination": "/dev/removed"},
                                            {"destination": "/dev/removed", "remove": True}]})
    try:
        ready = False
        output = b""
        while select.select([process.stdout], [], [], 10)[0]:
            chunk = os.read(process.stdout.fileno(), 4096)
            print(chunk.decode(), end="", flush=True)
            output += chunk
            if b"READY\n" in output.replace(b"\r\n", b"\n"):
                ready = True
                break
            if not chunk:
                break
        if not ready:
            if process.poll() is None:
                process.kill()
            stdout, stderr = process.communicate(timeout=5)
            raise RuntimeError(f"container did not start: {stdout}{stderr}")
        assert str(process.pid) in (supervisor / "cgroup.procs").read_text().splitlines()
        assert runtime.stat().st_ino == original_runtime.st_ino
        assert runtime.stat().st_mode == original_runtime.st_mode
        assert (service / "payload/init.scope").exists()
        assert (service / "payload/memory.max").read_text().strip() == str(256 * 1024 ** 2)
        for path, limit in memory_limits.items():
            assert (path / "memory.max").read_text() == limit
        assert run(str(LAUNCHER), "exec", "--runtime-dir", str(runtime),
                   "/init", "--check-bindings") == "BINDINGS OK\n"
        assert (service / "cgroup.procs").read_text() == ""
        assert (runtime / "files/resolv.conf").read_text() == ""
        for contents in ("search example.test\nnameserver 192.0.2.53\n",
                         "nameserver 192.0.2.54\n"):
            resolv.write_text(contents)
            run(str(LAUNCHER), "update-resolv-conf", "--runtime-dir", str(runtime),
                "--config", str(directory / 'qmc-normal with "quotes" and \\slashes.conf'))
            assert run(str(LAUNCHER), "exec", "--runtime-dir", str(runtime),
                       "/init", "--read-resolv") == contents
        hosts_inode = (runtime / "files/hosts").stat().st_ino
        for contents in ("127.0.0.1\tlocalhost\n192.0.2.100\tnew-host\n",
                         "127.0.0.1\tlocalhost\n"):
            (etc / "hosts").write_text(contents)
            run(str(LAUNCHER), "update-resolv-conf", "--runtime-dir", str(runtime),
                "--config", str(directory / 'qmc-normal with "quotes" and \\slashes.conf'))
            expected = (contents + "\n10.90.0.1\thost.containers.internal host.docker.internal\n"
                        "10.90.0.2\tqm-test qm\n")
            assert (runtime / "files/hosts").stat().st_ino == hosts_inode
            assert run(str(LAUNCHER), "exec", "--runtime-dir", str(runtime),
                       "/init", "--read-hosts") == expected
        container_ip = "10.90.0.2"
        print(run("nsenter", f"--net={runtime / 'netns'}", "ip", "route"), flush=True)
        run("ping", "-c", "1", "-W", "2", container_ip)
        assert "masquerade" in run("nft", "list", "table", "ip", "qm_launch")
        veth = json.loads(run("ip", "-j", "link", "show", "qm-veth"))[0]
        eth = json.loads(run("nsenter", f"--net={runtime / 'netns'}", "ip", "-j", "link", "show", "eth0"))[0]
        assert veth["mtu"] == eth["mtu"] == 1400
        assert veth["address"] == "02:00:0a:5a:00:01"
        assert veth["ifalias"] == f"qm-launch:{runtime}"
        assert host_tuning.read_text().strip() == "1"
        assert pathlib.Path("/proc/sys/net/ipv4/conf/default/forwarding").read_text().strip() == "0"
        assert pathlib.Path("/proc/sys/net/ipv4/conf/qm-veth/forwarding").read_text().strip() == "1"
        assert "master" not in veth
        assert "qm-br0" not in {link["ifname"] for link in json.loads(run("ip", "-j", "link", "show"))}
        gateway = json.loads(run("ip", "-j", "-4", "addr", "show", "qm-veth"))[0]
        assert gateway["addr_info"][0]["local"] == "10.90.0.1"
        assert gateway["addr_info"][0]["prefixlen"] == 24
        rules = run("nft", "list", "table", "ip", "qm_launch")
        assert 'iifname "qm-veth"' in rules and 'oifname "qm-veth"' in rules
        run("nsenter", f"--net={runtime / 'netns'}", "ping", "-c", "1", "-W", "2", "127.0.0.1")
        pathlib.Path("/proc/sys/net/ipv4/conf/qm-veth/rp_filter").write_text("1\n")
        run("/usr/lib/systemd/systemd-sysctl", "--prefix=/net/ipv4/conf/qm-veth",
            str(SOURCE / "systemd/90-qm-launch.conf"))
        assert pathlib.Path("/proc/sys/net/ipv4/conf/qm-veth/rp_filter").read_text().strip() == "2"
        assert_masquerading(str(LAUNCHER), "exec", "--runtime-dir", str(runtime),
                            "/init", "--network-check")
        command = [str(LAUNCHER), "exec", "--runtime-dir", str(runtime),
                   "/init", "--exec-check", "argument with spaces"]
        result = subprocess.run(command, text=True, capture_output=True, timeout=10)
        assert result.returncode == 23, (result.stdout, result.stderr)
        assert result.stdout == "EXEC argument with spaces tty=0\n", result.stdout
        master, slave = os.openpty()
        try:
            result = subprocess.run(command, stdin=slave, stdout=slave,
                                    stderr=subprocess.PIPE, timeout=10)
            assert result.returncode == 23, result.stderr
            assert os.read(master, 4096) == b"EXEC argument with spaces tty=1\r\n"
        finally:
            os.close(slave)
            os.close(master)
        os.kill(process.pid, signal.SIGRTMIN + 3)
        stdout, stderr = process.communicate(timeout=10)
        print(stdout, end="")
        assert process.returncode == 0, stderr
        run(str(LAUNCHER), "cleanup", "--runtime-dir", str(runtime))
        assert_network_removed(runtime)
        assert runtime.stat().st_ino == original_runtime.st_ino
        assert runtime.stat().st_mode == original_runtime.st_mode
        assert forwarding_path.read_text().strip() == "1"
        assert host_tuning.read_text().strip() == "1"
        print("Early forwarding configuration and host tuning survive launch and cleanup", flush=True)
        print("Cgroup delegation, native networking, MTU, NAT, exec, signal forwarding and cleanup passed", flush=True)
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
        run("umount", str(forwarding_path))
        run(str(LAUNCHER), "cleanup", "--runtime-dir", str(runtime))
        os.close(runtime_fd)

    # Start without an uplink route: QM retains its 1500 fallback MTU.
    run("ip", "route", "del", "default")
    run("ip", "link", "set", "qm-uplink", "down")
    process, runtime = launch("late-uplink")
    try:
        assert select.select([process.stdout], [], [], 10)[0]
        assert process.stdout.readline() == "READY\n"
        def late_network_up():
            result = subprocess.run(["ip", "-j", "link", "show", "qm-veth"],
                                    text=True, capture_output=True)
            return result.returncode == 0 and "UP" in json.loads(result.stdout)[0]["flags"]
        wait_until(late_network_up)
        for command in (("ip",), ("nsenter", f"--net={runtime / 'netns'}", "ip")):
            name = "qm-veth" if command == ("ip",) else "eth0"
            assert json.loads(run(*command, "-j", "link", "show", name))[0]["mtu"] == 1500
        # Keep the remote endpoint at 1500 so each clamp direction is necessary.
        run("ip", "netns", "exec", "qm-upstream", "ip", "link", "set", "router", "mtu", "1500")
        run("ip", "link", "set", "qm-uplink", "mtu", "1300", "up")
        run("ip", "route", "add", "default", "via", "192.0.2.2")
        run("nft", "add", "chain", "ip", "unrelated", "output",
            "{ type filter hook output priority filter; policy accept; }")
        run("nft", "add", "rule", "ip", "unrelated", "output",
            "icmp type destination-unreachable icmp code frag-needed drop")

        def bulk_transfer():
            listener = subprocess.Popen(
                ["ip", "netns", "exec", "qm-upstream", sys.executable, "-u", "-c",
                 "import socket\ns = socket.socket()\ns.settimeout(5)\n"
                 "s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)\n"
                 "s.bind(('192.0.2.2', 49000))\ns.listen()\nprint('LISTENING', flush=True)\n"
                 "c, peer = s.accept()\nc.settimeout(5)\n"
                 "assert peer[0] == '192.0.2.1', peer\n"
                 "assert c.getsockopt(socket.IPPROTO_TCP, socket.TCP_MAXSEG) <= 1260\n"
                 "data = bytearray()\n"
                 "while len(data) < 262144:\n"
                 "    chunk = c.recv(262144 - len(data))\n"
                 "    assert chunk, 'premature EOF'\n    data.extend(chunk)\n"
                 "assert data == b'Q' * 262144\nc.sendall(data)\nc.close()\n"],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            try:
                assert select.select([listener.stdout], [], [], 5)[0]
                assert listener.stdout.readline() == "LISTENING\n"
                result = subprocess.run(
                    [str(LAUNCHER), "exec", "--runtime-dir", str(runtime),
                     "/init", "--network-bulk"], text=True, capture_output=True, timeout=10)
                stdout, stderr = listener.communicate(timeout=7)
                return result, listener.returncode, stderr
            finally:
                if listener.poll() is None:
                    listener.kill()
                    listener.wait()

        result, status, stderr = bulk_transfer()
        assert result.returncode == status == 0, (result, stderr)
        # Negative controls prove that neither SYN nor SYN+ACK clamping is redundant.
        for direction in ("iifname", "oifname"):
            run("nft", "flush", "chain", "ip", "qm_launch", "forward_mss")
            run("nft", "add", "rule", "ip", "qm_launch", "forward_mss",
                f'{direction} "qm-veth" tcp flags syn tcp option maxseg size set rt mtu')
            result, status, stderr = bulk_transfer()
            if direction == "iifname":
                assert result.returncode == 18, (result, stderr)
            else:
                assert status != 0 and "AssertionError" in stderr, (result, stderr)
        run("nft", "add", "rule", "ip", "qm_launch", "forward_mss",
            'iifname "qm-veth" tcp flags syn tcp option maxseg size set rt mtu')
        result, status, stderr = bulk_transfer()
        assert result.returncode == status == 0, (result, stderr)

        # A separate host base chain still controls forwarding. Host reloads
        # that replace only their own table leave QM's rules installed.
        run("nft", "add", "chain", "ip", "unrelated", "forward",
            "{ type filter hook forward priority filter + 10; policy drop; }")
        result = subprocess.run(
            ["nsenter", f"--net={runtime / 'netns'}", "ping", "-c", "1", "-W", "1", "192.0.2.2"],
            text=True, capture_output=True, timeout=5)
        assert result.returncode != 0
        run("nft", "add", "rule", "ip", "unrelated", "forward",
            'iifname "qm-veth" ip saddr 10.90.0.0/24 accept')
        run("nft", "add", "rule", "ip", "unrelated", "forward",
            'oifname "qm-veth" ct state established,related accept')
        run("nsenter", f"--net={runtime / 'netns'}", "ping", "-c", "1", "-W", "2", "192.0.2.2")
        subprocess.run(["nft", "-f", "-"], input=
            'delete table ip unrelated\n'
            'add table ip unrelated\n'
            'add chain ip unrelated forward { type filter hook forward priority filter + 10; policy drop; }\n'
            'add rule ip unrelated forward iifname "qm-veth" ip saddr 10.90.0.0/24 accept\n'
            'add rule ip unrelated forward oifname "qm-veth" ct state established,related accept\n',
            text=True, check=True, capture_output=True)
        result, status, stderr = bulk_transfer()
        assert result.returncode == status == 0, (result, stderr)
        os.kill(process.pid, signal.SIGRTMIN + 3)
        stdout, stderr = process.communicate(timeout=10)
        assert process.returncode == 0, stderr
        print("Late uplink MSS clamping in both directions, bulk NAT traffic and host firewall reload passed", flush=True)
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)
        run(str(LAUNCHER), "cleanup", "--runtime-dir", str(runtime))
        run("nft", "delete", "table", "ip", "unrelated")
        run("nft", "add", "table", "ip", "unrelated")
        run("ip", "link", "set", "qm-uplink", "mtu", "1400", "up")
        run("ip", "netns", "exec", "qm-upstream", "ip", "link", "set", "router", "mtu", "1400")
    assert_network_removed(runtime)

    # Crun must wait for payload readiness and forward it as the main process.
    with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as notify:
        notify.setsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED, 1)
        pathlib.Path("/run/systemd").mkdir(exist_ok=True)
        notify.bind("/run/systemd/notify")
        process, runtime = launch("notify", notify_socket="/run/systemd/notify")
        try:
            assert select.select([process.stdout], [], [], 10)[0]
            assert process.stdout.readline() == "READY\n"
            assert (runtime / "notify.sock").readlink() == pathlib.Path("/run/systemd/notify")
            assert not select.select([notify], [], [], 0.1)[0], "premature readiness"
            run(str(LAUNCHER), "exec", "--runtime-dir", str(runtime), "/init", "--notify")
            notify.settimeout(5)
            message, ancillary, flags, address = notify.recvmsg(
                256, socket.CMSG_SPACE(struct.calcsize("3i")))
            assert message == b"READY=1", message
            credentials = next(data for level, kind, data in ancillary
                               if level == socket.SOL_SOCKET and kind == socket.SCM_CREDENTIALS)
            assert struct.unpack("3i", credentials)[0] == process.pid
            # Closing the receiver also releases any queued notification barrier FD.
            notify.close()
            os.kill(process.pid, signal.SIGRTMIN + 3)
            stdout, stderr = process.communicate(timeout=10)
            assert process.returncode == 0, stderr
            run(str(LAUNCHER), "cleanup", "--runtime-dir", str(runtime))
            assert_network_removed(runtime)
            print("Crun proxies payload readiness as the main process for NotifyAccess=main", flush=True)
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()
            run(str(LAUNCHER), "cleanup", "--runtime-dir", str(runtime))
            pathlib.Path("/run/systemd/notify").unlink()

    crun = "/usr/bin/crun"

    # Capture a fatal init error after it has closed all inherited stdio.
    config["process"]["args"] = ["/init", "--console-fail"]
    base.write_text(json.dumps(config))
    process, runtime = launch("console-failure", extra=("--verbose",))
    try:
        stdout, stderr = process.communicate(timeout=10)
        assert process.returncode == 255, (stdout, stderr)
        assert stdout == "".join(f"Fatal init diagnostic {i}\n" for i in range(2048)), stdout
        run(str(LAUNCHER), "cleanup", "--runtime-dir", str(runtime))
        assert_network_removed(runtime)
        print("Console diagnostics reach stdout, drain on exit and preserve exit 255", flush=True)
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
        run(str(LAUNCHER), "cleanup", "--runtime-dir", str(runtime))

    # A runtime failure before sending the console must not orphan the relay.
    config["process"]["args"] = ["/missing-init"]
    base.write_text(json.dumps(config))
    process, runtime = launch("missing-init")
    stdout, stderr = process.communicate(timeout=10)
    assert process.returncode != 0, (stdout, stderr)
    assert "missing-init" in stderr, stderr
    run(str(LAUNCHER), "cleanup", "--runtime-dir", str(runtime))
    assert_network_removed(runtime)
    print("Crun startup failure stops the waiting console relay", flush=True)

    config["process"]["args"] = ["/init"]
    config["process"]["terminal"] = False
    base.write_text(json.dumps(config))
    process, runtime = launch("no-console")
    try:
        assert select.select([process.stdout], [], [], 10)[0]
        assert process.stdout.readline() == "READY\n"
        assert not (runtime / "console.sock").exists()
        os.kill(process.pid, signal.SIGRTMIN + 3)
        stdout, stderr = process.communicate(timeout=10)
        assert process.returncode == 0, stderr
        run(str(LAUNCHER), "cleanup", "--runtime-dir", str(runtime))
        assert_network_removed(runtime)
        print("Custom configurations without a terminal retain ordinary stdio", flush=True)
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
        run(str(LAUNCHER), "cleanup", "--runtime-dir", str(runtime))
    config["process"]["terminal"] = True
    base.write_text(json.dumps(config))

    missing_crun = directory / "missing-crun"
    missing_crun.write_text("#!/missing-interpreter\n")
    missing_crun.chmod(0o755)
    failures = [
        ("exec-failure", f"exec {crun}", str(missing_crun), crun),
    ]
    for attempt, message, replacement, executable in failures:
        run("mount", "--bind", replacement, executable)
        try:
            process, runtime = launch(attempt)
            stdout, stderr = process.communicate(timeout=10)
            assert process.returncode == 1, (stdout, stderr)
            assert message in stderr, stderr
            assert_network_removed(runtime)
            print(f"{attempt}: cleanup passed", flush=True)
        finally:
            run("umount", executable)

    # Fail after veth creation and check that partial setup is rolled back.
    process, runtime = launch("sysctl-failure",
                              launcher=LAUNCHER.parent.parent / "tests/qmc/test-launch-network",
                              env={"QM_TEST_SYSCTL_FAIL": "net/ipv4/conf/qm-veth/forwarding"})
    stdout, stderr = process.communicate(timeout=10)
    assert process.returncode == -signal.SIGKILL, (stdout, stderr)
    assert "set sysctl net/ipv4/conf/qm-veth/forwarding" in stderr, stderr
    assert "QM network setup failed" in stderr, stderr
    run(str(LAUNCHER), "cleanup", "--runtime-dir", str(runtime))
    assert_network_removed(runtime)
    print("Partial network setup rolls back on sysctl failure", flush=True)

    # Existing objects are not ours just because their names match.
    for kind in ("interface", "table"):
        if kind == "interface":
            run("ip", "link", "add", "qm-veth", "type", "dummy")
        else:
            run("nft", "add", "table", "ip", "qm_launch", "{ comment \"foreign\"; }")
        try:
            process, runtime = launch(f"foreign-{kind}")
            stdout, stderr = process.communicate(timeout=10)
            assert process.returncode == 1, (stdout, stderr)
            assert "already exists" in stderr, stderr
            assert not (runtime / "state.json").exists()
            assert not (runtime / "netns").exists()
            run(str(LAUNCHER), "cleanup", "--runtime-dir", str(runtime))
            assert runtime.is_dir() and list(runtime.iterdir()) == []
            if kind == "interface":
                run("ip", "link", "show", "qm-veth")
            else:
                assert "foreign" in run("nft", "list", "table", "ip", "qm_launch")
            assert "unrelated" in run("nft", "list", "tables")
        finally:
            if kind == "interface":
                run("ip", "link", "delete", "qm-veth")
            else:
                run("nft", "delete", "table", "ip", "qm_launch")
    print("Setup preserves interfaces and tables owned by other applications", flush=True)

    # A cleanup error must not block setup when the required resources are free.
    runtime = directory / "runtime-cleanup-warning"
    runtime.mkdir(mode=0o700)
    old_crun = directory / "old-crun"
    (old_crun / "qm").mkdir(parents=True)
    (old_crun / "qm/status").touch()
    (runtime / "state.json").write_text(json.dumps({
        "version": 1, "bundle": str(runtime),
        "crun": {"executable": "/bin/false", "root": str(old_crun), "id": "qm"}}))
    (runtime / "notify.sock").symlink_to("/run/old-notify.sock")
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as stale_console:
        stale_console.bind(str(runtime / "console.sock"))
    process, runtime = launch("cleanup-warning", notify_socket="/run/new-notify.sock")
    try:
        assert select.select([process.stdout], [], [], 10)[0]
        assert process.stdout.readline() == "READY\n"
        assert (runtime / "notify.sock").readlink() == pathlib.Path("/run/new-notify.sock")
        os.kill(process.pid, signal.SIGRTMIN + 3)
        stdout, stderr = process.communicate(timeout=10)
        assert process.returncode == 0, stderr
        assert "cleanup incomplete; continuing startup" in stderr, stderr
        run(str(LAUNCHER), "cleanup", "--runtime-dir", str(runtime))
        assert_network_removed(runtime)
        print("Partial cleanup preserves stale sockets; startup replaces them and launches successfully", flush=True)
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
        run(str(LAUNCHER), "cleanup", "--runtime-dir", str(runtime))

    # Restart after a crash without an intervening cleanup call.
    process, runtime = launch("missed-cleanup")
    try:
        assert select.select([process.stdout], [], [], 10)[0]
        assert process.stdout.readline() == "READY\n"
        process.kill()
        process.wait(timeout=5)
        crashed = process
        assert (runtime / "state.json").exists()
        process, runtime = launch("missed-cleanup")
        assert select.select([process.stdout], [], [], 10)[0]
        assert process.stdout.readline() == "READY\n"
        crashed.communicate(timeout=5)
        os.kill(process.pid, signal.SIGRTMIN + 3)
        stdout, stderr = process.communicate(timeout=10)
        assert process.returncode == 0, stderr
        run(str(LAUNCHER), "cleanup", "--runtime-dir", str(runtime))
        assert_network_removed(runtime)
        print("Startup recovers a crashed container without prior cleanup", flush=True)
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
        run(str(LAUNCHER), "cleanup", "--runtime-dir", str(runtime))

    # Recover a killed launcher even after the namespace pin was removed.
    process, runtime = launch("recovery")
    try:
        assert select.select([process.stdout], [], [], 10)[0]
        assert process.stdout.readline() == "READY\n"
        process.kill()
        process.wait(timeout=5)
        # Keep the peer namespace alive while cleanup kills container init.
        # Otherwise Linux removes the veth before ownership can be checked.
        with (runtime / "netns").open() as namespace_pin:
            run("umount", "--lazy", str(runtime / "netns"))
            (runtime / "netns").unlink()
            run("ip", "link", "set", "qm-veth", "alias", "another owner")
            result = subprocess.run([str(LAUNCHER), "cleanup", "--runtime-dir", str(runtime)],
                                    text=True, capture_output=True)
            assert result.returncode == 1, result.stderr
            assert "another owner" in result.stderr
            assert (runtime / "state.json").exists()
            assert "qm_launch" not in run("nft", "list", "tables")
            run("ip", "link", "show", "qm-veth")
            # An empty alias represents interruption between creation and tagging.
            run("ip", "link", "set", "qm-veth", "alias", "")
            run(str(LAUNCHER), "cleanup", "--runtime-dir", str(runtime))
            assert_network_removed(runtime)
        process.communicate(timeout=5)
        process, runtime = launch("recovery")
        assert select.select([process.stdout], [], [], 10)[0]
        assert process.stdout.readline() == "READY\n"
        os.kill(process.pid, signal.SIGRTMIN + 3)
        stdout, stderr = process.communicate(timeout=10)
        assert process.returncode == 0, stderr
        run(str(LAUNCHER), "cleanup", "--runtime-dir", str(runtime))
        assert_network_removed(runtime)
        print("Crash recovery, ownership checks, cleanup retries and restart passed", flush=True)
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
        run(str(LAUNCHER), "cleanup", "--runtime-dir", str(runtime))

    # Stopping after preparation must leave only saved state and the namespace.
    helper = str(LAUNCHER.parent.parent / "tests/qmc/test-network")
    prepared = directory / "prepared-network"
    prepared.mkdir(mode=0o700)
    run(helper, str(prepared), "--prepare-only")
    state = json.loads((prepared / "state.json").read_text())
    assert "bridge" not in state["network"]
    links = json.loads(run("ip", "-j", "link", "show"))
    assert "test-veth" not in {link["ifname"] for link in links}
    assert "test_network" not in run("nft", "list", "tables")
    run(str(LAUNCHER), "cleanup", "--runtime-dir", str(prepared))
    assert not (prepared / "state.json").exists()
    assert not (prepared / "netns").exists()
    print("Network preparation saves state without changing the host network", flush=True)

    # Pause network setup and prove that crun can still boot PID 1.
    for attempt in ("parallel-boot", "async-host-failure", "async-nft-failure",
                    "job-crash", "parent-crash", "concurrent-cleanup", "async-crun-failure"):
        gates = []
        worker_fds = []
        environment = {}
        kinds = (("LINK", "NFT") if attempt == "parallel-boot" else
                 ("NFT",) if attempt == "async-nft-failure" else ("LINK",))
        for kind in kinds:
            gate = directory / f"gate-{attempt}-{kind}"
            os.mkfifo(gate, 0o600)
            gates.append((gate, os.open(gate, os.O_RDWR | os.O_CLOEXEC)))
            environment[f"QM_TEST_{kind}_GATE"] = str(gate)
        if attempt == "async-nft-failure":
            environment["QM_TEST_NFT_FAIL"] = "1"
        if attempt == "async-host-failure":
            environment["QM_TEST_SYSCTL_FAIL"] = "net/ipv4/conf/qm-veth/forwarding"
        if attempt == "async-crun-failure":
            config["process"]["args"] = ["/missing-init"]
            base.write_text(json.dumps(config))
        process, runtime = launch(attempt, extra=("--verbose",),
                                  launcher=LAUNCHER.parent.parent / "tests/qmc/test-launch-network",
                                  env=environment)
        concurrent_cleanup = None
        try:
            if attempt == "async-crun-failure":
                stdout, stderr = process.communicate(timeout=5)
                assert process.returncode != 0, (stdout, stderr)
                assert "/missing-init" in stderr, stderr
            else:
                gate, fd = gates[0]
                pid_file = pathlib.Path(f"{gate}.pid")
                wait_until(lambda: pid_file.exists() and pid_file.read_text().strip())
                worker_pid = int(pid_file.read_text())
                worker_fds.append(os.pidfd_open(worker_pid))
                assert select.select([process.stdout], [], [], 5)[0]
                assert process.stdout.readline() == "READY\n", "Init waited for network setup"
                loopback = json.loads(run("nsenter", f"--net={runtime / 'netns'}", "ip",
                                          "-j", "link", "show", "lo"))[0]
                assert "UP" in loopback["flags"], loopback
                run("nsenter", f"--net={runtime / 'netns'}", "ping", "-c", "1", "-W", "2", "127.0.0.1")
                assert pathlib.Path(f"/proc/{process.pid}/comm").read_text().strip() == "crun"
                if kinds[0] == "LINK":
                    assert "qm-veth" not in run("ip", "link", "show")
                else:
                    link = json.loads(run("ip", "-j", "link", "show", "qm-veth"))[0]
                    assert "UP" not in link["flags"], link
                assert "qm_launch" not in run("nft", "list", "tables")
                if attempt == "parent-crash":
                    process.kill()
                elif attempt == "job-crash":
                    os.kill(int(pathlib.Path(f"{gates[0][0]}.pid").read_text()), signal.SIGKILL)
                else:
                    if attempt == "concurrent-cleanup":
                        concurrent_cleanup = subprocess.Popen(
                            [str(LAUNCHER), "cleanup", "--runtime-dir", str(runtime)],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                        # Cleanup cannot finish while the setup job is blocked.
                        assert not select.select([concurrent_cleanup.stderr], [], [], 0.1)[0]
                        assert concurrent_cleanup.poll() is None
                    os.write(gates[0][1], b"1")
                if attempt == "parallel-boot":
                    # Interface and firewall setup must use the same job PID.
                    nft_gate, nft_fd = gates[1]
                    nft_pid_file = pathlib.Path(f"{nft_gate}.pid")
                    wait_until(lambda: nft_pid_file.exists() and nft_pid_file.read_text().strip())
                    assert int(nft_pid_file.read_text()) == worker_pid
                    link = json.loads(run("ip", "-j", "link", "show", "qm-veth"))[0]
                    assert "UP" not in link["flags"], link
                    assert "qm_launch" not in run("nft", "list", "tables")
                    os.write(nft_fd, b"1")
                    def network_up():
                        result = subprocess.run(["ip", "-j", "link", "show", "qm-veth"],
                                                text=True, capture_output=True)
                        return result.returncode == 0 and "UP" in json.loads(result.stdout)[0]["flags"]
                    wait_until(network_up)
                    run("ping", "-c", "1", "-W", "2", "10.90.0.2")
                    os.kill(process.pid, signal.SIGRTMIN + 3)
                stdout, stderr = process.communicate(timeout=5)
                if attempt == "parallel-boot":
                    assert process.returncode == 0, (stdout, stderr)
                    assert "Network setup complete" in stderr, stderr
                else:
                    assert process.returncode != 0, (stdout, stderr)
                if attempt in ("async-host-failure", "async-nft-failure", "job-crash"):
                    assert "QM network setup failed" in stderr, stderr
                for fd in worker_fds:
                    assert select.select([fd], [], [], 5)[0], "Setup worker survived startup"
            if concurrent_cleanup is not None:
                stdout, stderr = concurrent_cleanup.communicate(timeout=5)
                assert concurrent_cleanup.returncode == 0, (stdout, stderr)
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=5)
            if concurrent_cleanup is not None and concurrent_cleanup.poll() is None:
                concurrent_cleanup.kill()
                concurrent_cleanup.wait(timeout=5)
            for gate, fd in gates:
                os.close(fd)
            for fd in worker_fds:
                os.close(fd)
            config["process"]["args"] = ["/init"]
            base.write_text(json.dumps(config))
            run(str(LAUNCHER), "cleanup", "--runtime-dir", str(runtime))
        assert_network_removed(runtime)
    print("Loopback is ready before container boot; background setup, job failures, crashes and concurrent cleanup passed", flush=True)

    process, runtime = launch("configured-network", settings={
        "ip": "172.30.20.2", "gateway": "172.30.20.1", "prefix-length": 28,
        "hostname": "qm-net-test"})
    try:
        assert select.select([process.stdout], [], [], 10)[0]
        assert process.stdout.readline() == "READY\n"
        def configured_network_up():
            result = subprocess.run(["ip", "-j", "link", "show", "qm-veth"],
                                    text=True, capture_output=True)
            return result.returncode == 0 and "UP" in json.loads(result.stdout)[0]["flags"]
        wait_until(configured_network_up)
        gateway = json.loads(run("ip", "-j", "-4", "addr", "show", "qm-veth"))[0]
        assert gateway["addr_info"][0]["local"] == "172.30.20.1"
        assert gateway["addr_info"][0]["prefixlen"] == 28
        routes = run("nsenter", f"--net={runtime / 'netns'}", "ip", "route")
        assert "default via 172.30.20.1 dev eth0" in routes, routes
        assert "172.30.20.0/28 dev eth0" in routes, routes
        rules = run("nft", "list", "table", "ip", "qm_launch")
        assert "172.30.20.0/28" in rules, rules
        run("ping", "-c", "1", "-W", "2", "172.30.20.2")
        assert_masquerading(str(LAUNCHER), "exec", "--runtime-dir", str(runtime),
                            "/init", "--network-check")
        contents = run(str(LAUNCHER), "exec", "--runtime-dir", str(runtime),
                       "/init", "--read-hosts")
        assert "172.30.20.2\tqm-net-test qm\n" in contents
        assert "172.30.20.1\thost.containers.internal host.docker.internal\n" in contents
        filename = directory / "qmc-configured-network.conf"
        configuration = json.loads(filename.read_text())
        configuration.update({"ip": "10.90.0.2", "gateway": "10.90.0.1",
                              "prefix-length": 24, "hostname": "next-qm"})
        filename.write_text(json.dumps(configuration))
        run(str(LAUNCHER), "update-resolv-conf", "--runtime-dir", str(runtime),
            "--config", str(filename))
        assert run(str(LAUNCHER), "exec", "--runtime-dir", str(runtime),
                   "/init", "--read-hosts") == contents
        os.kill(process.pid, signal.SIGRTMIN + 3)
        stdout, stderr = process.communicate(timeout=10)
        assert process.returncode == 0, stderr
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)
        run(str(LAUNCHER), "cleanup", "--runtime-dir", str(runtime))
    assert_network_removed(runtime)
    print("Configured network addresses, routes, NAT and startup hosts identity passed", flush=True)

    # Exercise the backend with names, subnet, MAC, MTU and sysctls different from QM.
    custom = directory / "custom-network"
    custom.mkdir(mode=0o700)
    run("ip", "route", "del", "default")
    try:
        run(helper, str(custom))
        veth = json.loads(run("ip", "-j", "link", "show", "test-veth"))[0]
        assert veth["address"] == "02:00:ac:1e:14:01"
        assert veth["mtu"] == 1234
        run("ip", "link", "show", "test-veth")
        address = json.loads(run("nsenter", f"--net={custom / 'netns'}", "ip",
                                 "-j", "-4", "addr", "show", "test0"))[0]
        assert address["mtu"] == 1234
        assert address["addr_info"][0]["local"] == "172.30.20.2"
        assert address["addr_info"][0]["prefixlen"] == 28
        routes = run("nsenter", f"--net={custom / 'netns'}", "ip", "route")
        assert "default via 172.30.20.1 dev test0" in routes, routes
        run("ping", "-c", "1", "-W", "2", "172.30.20.2")
        assert_masquerading("nsenter", f"--net={custom / 'netns'}",
                            str(rootfs / "init"), "--network-check")
        assert pathlib.Path("/proc/sys/net/ipv4/conf/test-veth/rp_filter").read_text().strip() == "1"
        ipv6 = pathlib.Path("/proc/sys/net/ipv6/conf/test-veth/disable_ipv6")
        if ipv6.exists():
            assert ipv6.read_text().strip() == "0"
        state = json.loads((custom / "state.json").read_text())
        assert "bridge" not in state["network"]
        assert state["network"]["veth"] == "test-veth"
        assert state["network"]["nft_table"] == "test_network"
        # The regular launcher cleans up this other configuration using only
        # saved state, including paths and ownership from another directory.
        cleanup_dir = directory / "custom-cleanup"
        cleanup_dir.mkdir(mode=0o700)
        (custom / "state.json").rename(cleanup_dir / "state.json")
        run(str(LAUNCHER), "cleanup", "--runtime-dir", str(cleanup_dir))
        run(str(LAUNCHER), "cleanup", "--runtime-dir", str(cleanup_dir))
        assert not (cleanup_dir / "state.json").exists()
        assert not (custom / "netns").exists()
        links = json.loads(run("ip", "-j", "link", "show"))
        assert "test-veth" not in {link["ifname"] for link in links}
        assert "test_network" not in run("nft", "list", "tables")
        assert "unrelated" in run("nft", "list", "tables")
        print("Non-default network options, NAT, fallback MTU and cleanup from saved state passed", flush=True)
    finally:
        run(str(LAUNCHER), "cleanup", "--runtime-dir", str(custom))
        if (directory / "custom-cleanup").exists():
            run(str(LAUNCHER), "cleanup", "--runtime-dir", str(directory / "custom-cleanup"))
        run("ip", "route", "add", "default", "via", "192.0.2.2")

    process, runtime = launch("loopback-failure", launcher=LAUNCHER.parent.parent / "tests/qmc/test-launch-network",
                              env={"QM_TEST_LOOPBACK_FAIL": "1"})
    stdout, stderr = process.communicate(timeout=10)
    assert process.returncode == 1, (stdout, stderr)
    assert "bring up network namespace loopback" in stderr, stderr
    assert "READY" not in stdout, stdout
    assert_network_removed(runtime)
    print("Loopback setup failure aborts launch and rolls back namespace preparation", flush=True)

    process, runtime = launch("namespace-create-failure", existing_netns=True)
    stdout, stderr = process.communicate(timeout=10)
    assert process.returncode == 1, (stdout, stderr)
    assert f"create {runtime / 'netns'}" in stderr, stderr
    assert (runtime / "netns").exists(), "must preserve a namespace file we did not create"
    print("Namespace creation failure preserves the existing file", flush=True)

for machine_id_state in ("existing", "uninitialized"):
    subprocess.run([sys.executable, str(SOURCE / "tests/qmc/systemd.py"), str(LAUNCHER),
                    machine_id_state], check=True)
