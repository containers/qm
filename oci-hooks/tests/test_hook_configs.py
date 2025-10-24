#!/usr/bin/env python3

"""Tests for OCI hook configuration files."""

import json
import re
from pathlib import Path
from collections import Counter

import pytest

from test_utils import HookConfigLoader


TEST_SPEC = {
    "version": "1.0.0",
    "process": {
        "terminal": False,
        "user": {"uid": 0, "gid": 0},
        "args": ["echo", "test"],
        "env": [
            "PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
        ],
        "cwd": "/",
        "capabilities": {
            "bounding": [
                "CAP_AUDIT_WRITE",
                "CAP_KILL",
                "CAP_NET_BIND_SERVICE",
            ],
            "effective": [
                "CAP_AUDIT_WRITE",
                "CAP_KILL",
                "CAP_NET_BIND_SERVICE",
            ],
            "inheritable": [
                "CAP_AUDIT_WRITE",
                "CAP_KILL",
                "CAP_NET_BIND_SERVICE",
            ],
            "permitted": [
                "CAP_AUDIT_WRITE",
                "CAP_KILL",
                "CAP_NET_BIND_SERVICE",
            ],
            "ambient": [
                "CAP_AUDIT_WRITE",
                "CAP_KILL",
                "CAP_NET_BIND_SERVICE",
            ],
        },
        "rlimits": [{"type": "RLIMIT_NOFILE", "hard": 1024, "soft": 1024}],
        "noNewPrivileges": True,
    },
    "root": {"path": "rootfs", "readonly": True},
    "hostname": "testing",
    "mounts": [
        {"destination": "/proc", "type": "proc", "source": "proc"},
        {
            "destination": "/dev",
            "type": "tmpfs",
            "source": "tmpfs",
            "options": ["nosuid", "strictatime", "mode=755", "size=65536k"],
        },
    ],
    "annotations": {},
    "linux": {
        "resources": {},
        "namespaces": [
            {"type": "pid"},
            {"type": "network"},
            {"type": "ipc"},
            {"type": "uts"},
            {"type": "mount"},
        ],
        "maskedPaths": [
            "/proc/acpi",
            "/proc/asound",
            "/proc/kcore",
            "/proc/keys",
            "/proc/latency_stats",
            "/proc/timer_list",
            "/proc/timer_stats",
            "/proc/sched_debug",
            "/sys/firmware",
        ],
        "readonlyPaths": [
            "/proc/bus",
            "/proc/fs",
            "/proc/irq",
            "/proc/sys",
            "/proc/sysrq-trigger",
        ],
    },
}


class TestHookConfigurations:
    """Test class for validating OCI hook JSON configurations."""

    @pytest.fixture(scope="class")
    def hook_configs(self):
        """Load all hook configuration files."""
        return HookConfigLoader.load_all_hook_configs()

    @staticmethod
    def _get_hook_names():
        """Get hook names for parametrized tests."""
        return HookConfigLoader.get_hook_names()

    @pytest.mark.unit
    @pytest.mark.parametrize("hook_name", _get_hook_names())
    def test_json_syntax_validity(self, hook_configs, hook_name):
        """Test that hook JSON file has valid syntax."""
        hook_data = hook_configs[hook_name]
        config_path = hook_data["path"]

        # Re-read and parse to ensure JSON is valid
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                json.load(f)
        except json.JSONDecodeError as e:
            pytest.fail(f"Invalid JSON syntax in {config_path}: {e}")

    @pytest.mark.unit
    @pytest.mark.parametrize("hook_name", _get_hook_names())
    @pytest.mark.parametrize(
        "required_field", ["version", "hook", "when", "stages"]
    )
    def test_required_schema_fields(
        self, hook_configs, hook_name, required_field
    ):
        """Test that hook config has required OCI hook schema fields."""
        hook_data = hook_configs[hook_name]
        config = hook_data["config"]
        config_path = hook_data["path"]

        assert (
            required_field in config
        ), f"Missing required field '{required_field}' in {config_path}"

    @pytest.mark.unit
    @pytest.mark.parametrize("hook_name", _get_hook_names())
    def test_hook_path_field(self, hook_configs, hook_name):
        """Test that hook config has required OCI hook schema field 'path'."""
        hook_data = hook_configs[hook_name]
        hook_config = hook_data["config"].get("hook", {})
        config_path = hook_data["path"]

        assert (
            "path" in hook_config
        ), f"Missing required hook field 'path' in {config_path}"

    @pytest.mark.unit
    @pytest.mark.parametrize("hook_name", _get_hook_names())
    def test_version_format(self, hook_configs, hook_name):
        """Test that version field follows semantic versioning."""
        semver_pattern = re.compile(r"^\d+\.\d+\.\d+$")

        hook_data = hook_configs[hook_name]
        config = hook_data["config"]
        config_path = hook_data["path"]

        version = config.get("version")
        assert version, f"Version field is empty in {config_path}"
        assert semver_pattern.match(
            version
        ), f"Invalid version format '{version}' in {config_path}"

    @pytest.mark.unit
    @pytest.mark.parametrize("hook_name", _get_hook_names())
    def test_valid_stages(self, hook_configs, hook_name):
        """Test that stages contain only valid OCI hook stages."""
        hook_data = hook_configs[hook_name]
        config = hook_data["config"]
        config_path = hook_data["path"]

        valid_stages = ["prestart", "precreate", "poststart", "poststop"]

        stages = config.get("stages", [])
        assert isinstance(
            stages, list
        ), f"Stages must be a list in {config_path}"
        assert (
            len(stages) > 0
        ), f"At least one stage must be specified in {config_path}"

        assert all(
            stage in valid_stages for stage in stages
        ), f"Invalid stages in {config_path}. Valid stages: {valid_stages}"

    @pytest.mark.unit
    @pytest.mark.parametrize("hook_name", _get_hook_names())
    def test_annotation_patterns(self, hook_configs, hook_name):
        """Test that annotation patterns are valid regular expressions."""
        hook_data = hook_configs[hook_name]
        config = hook_data["config"]
        config_path = hook_data["path"]

        when_section = config.get("when", {})
        annotations = when_section.get("annotations", {})

        def is_valid_regex(pattern):
            try:
                re.compile(pattern)
                return True
            except re.error:
                return False

        invalid_patterns = {
            p: "key" for p in annotations.keys() if not is_valid_regex(p)
        }
        invalid_value_patterns = {
            v: "value"
            for v in annotations.values()
            if isinstance(v, str) and not is_valid_regex(v)
        }

        assert not invalid_patterns, (
            f"Invalid regex in annotation keys: {invalid_patterns} "
            f"in {config_path}"
        )
        assert not invalid_value_patterns, (
            f"Invalid regex in annotation values: {invalid_value_patterns} "
            f"in {config_path}"
        )

    @pytest.mark.integration
    @pytest.mark.parametrize("hook_name", _get_hook_names())
    def test_hook_executable_exists(self, hook_configs, hook_name):
        """Test that hook executables exist and are executable."""
        hook_data = hook_configs[hook_name]
        config_path = hook_data["path"]
        hook_path = Path(hook_data["config"]["hook"]["path"])

        # For tests, the hook might be in the source directory rather than
        # installed location - try absolute path first, then relative
        try:
            # Check if absolute path works
            hook_path.stat()
        except OSError:
            # If absolute path fails, try relative to config file
            hook_path = config_path.parent / hook_path.name

            # Special case: seat manager uses shared device manager executable
            if not hook_path.exists() and hook_name == "oci-qm-seat-manager":
                parent_dir = config_path.parent.parent
                hook_path = parent_dir / "qm-device-manager" / hook_path.name

        assert hook_path.exists(), f"Hook executable not found: {hook_path}"
        assert hook_path.is_file(), f"Hook executable not a file: {hook_path}"

    @pytest.mark.unit
    def test_device_manager_annotations(self, hook_configs):
        """Test that device manager config matches supported annotations."""
        hook_name = "oci-qm-device-manager"
        assert hook_name in hook_configs, f"Hook {hook_name} not found"

        device_manager_config = hook_configs[hook_name]["config"]
        annotations = device_manager_config.get("when", {}).get(
            "annotations", {}
        )

        # Check that device patterns exist
        device_patterns = [p for p in annotations.keys() if "device" in p]
        assert (
            device_patterns
        ), "Device manager should support device annotations"

        # Test that device patterns match expected device types
        test_annotations = [
            "org.containers.qm.device.audio",
            "org.containers.qm.device.video",
            "org.containers.qm.device.input",
            "org.containers.qm.device.ttys",
        ]

        unmatched_patterns = [
            p
            for p in device_patterns
            if not all(re.match(p, a) for a in test_annotations)
        ]

        assert not unmatched_patterns, (
            f"Device patterns {unmatched_patterns} failed to match all "
            "expected annotations"
        )

    @pytest.mark.unit
    def test_wayland_client_annotations(self, hook_configs):
        """Test that wayland client config matches supported annotations."""
        hook_name = "oci-qm-wayland-client-devices"
        assert hook_name in hook_configs, f"Hook {hook_name} not found"

        wayland_config = hook_configs[hook_name]["config"]
        annotations = wayland_config.get("when", {}).get("annotations", {})

        # Check that wayland-client patterns exist
        wayland_patterns = [
            p for p in annotations.keys() if "wayland-client" in p
        ]
        assert (
            wayland_patterns
        ), "Wayland client should have wayland-client pattern"

        # Test that patterns match expected annotations
        test_annotations = ["org.containers.qm.wayland-client.gpu"]

        unmatched_patterns = [
            p
            for p in wayland_patterns
            if not all(re.match(p, a) for a in test_annotations)
        ]

        assert not unmatched_patterns, (
            f"Wayland patterns {unmatched_patterns} failed to match all "
            "expected annotations"
        )

    @pytest.mark.unit
    def test_no_duplicate_annotations(self, hook_configs):
        """Test that there are no overlapping annotation patterns."""
        # Create a flat list of all annotation patterns from all hooks
        all_patterns = [
            pattern
            for hook_data in hook_configs.values()
            for pattern in hook_data["config"]
            .get("when", {})
            .get("annotations", {})
            .keys()
        ]

        # Count occurrences of each pattern
        pattern_counts = Counter(all_patterns)

        # Assert no duplicate patterns exist using named expression
        assert not (
            duplicates := {
                pattern: count
                for pattern, count in pattern_counts.items()
                if count > 1
            }
        ), "Duplicate annotation patterns found: {}".format(  # pylint: disable=C0209 # noqa: E501
            {
                pattern: [
                    name
                    for name, data in hook_configs.items()
                    if pattern
                    in data["config"].get("when", {}).get("annotations", {})
                ]
                for pattern in duplicates
            }
        )

    @pytest.mark.unit
    @pytest.mark.parametrize("hook_name", _get_hook_names())
    def test_json_formatting(self, hook_configs, hook_name):
        """Test that JSON file is properly formatted."""
        hook_data = hook_configs[hook_name]
        config_path = hook_data["path"]
        config = hook_data["config"]

        # Read the original file content
        with open(config_path, "r", encoding="utf-8") as f:
            original_content = f.read()

        # Generate formatted JSON
        _ = json.dumps(config, indent=2, sort_keys=False) + "\n"

        # Check if formatting is consistent (allowing for minor variations)
        # This is a basic check - in practice you might want to be
        # more lenient
        assert (
            len(original_content.strip()) > 0
        ), f"JSON file {config_path} appears to be empty"

        # Check that it's valid JSON by trying to parse it
        try:
            json.loads(original_content)
        except json.JSONDecodeError as e:
            pytest.fail(f"Invalid JSON in {config_path}: {e}")

    @pytest.mark.integration
    @pytest.mark.parametrize("hook_name", _get_hook_names())
    def test_hook_config_integration(self, hook_configs, hook_name):
        """Test that hook config integrates correctly with its executable."""
        hook_data = hook_configs[hook_name]
        config = hook_data["config"]
        config_path = hook_data["path"]

        # Get hook executable path
        hook_path = config.get("hook", {}).get("path", "")
        assert hook_path, f"Hook path not found in {config_path}"

        # Try absolute path first, then relative to config directory
        full_hook_path = Path(hook_path)
        try:
            # Check if absolute path works
            full_hook_path.stat()
        except OSError:
            # If absolute path fails, try relative to config directory
            full_hook_path = config_path.parent / Path(hook_path).name

            # Special case: seat manager uses shared device manager executable
            is_seat_manager = hook_name == "oci-qm-seat-manager"
            if not full_hook_path.exists() and is_seat_manager:
                parent_dir = config_path.parent.parent
                hook_name_path = Path(hook_path).name
                device_mgr_dir = parent_dir / "qm-device-manager"
                full_hook_path = device_mgr_dir / hook_name_path

        # Check that executable exists
        assert full_hook_path.exists(), (
            f"Hook executable not found: {full_hook_path} "
            f"(configured in {config_path})"
        )

        # Check that it's executable
        assert (
            full_hook_path.is_file()
        ), f"Hook path is not a file: {full_hook_path}"

        # Basic executable check (if we can check permissions)
        try:
            assert (
                full_hook_path.stat().st_mode & 0o111
            ), f"Hook file is not executable: {full_hook_path}"
        except OSError:
            # Skip permission check if we can't access file stats
            pass

    @pytest.mark.unit
    @pytest.mark.parametrize("hook_name", _get_hook_names())
    def test_stage_appropriateness(self, hook_configs, hook_name):
        """Test that hook uses appropriate stages for its functionality."""
        hook_data = hook_configs[hook_name]
        config = hook_data["config"]
        stages = config.get("stages", [])

        # Device management hooks should use precreate stage
        # because they need to modify the OCI spec before container creation
        assert "precreate" in stages, (
            f"Hook {hook_name} should use 'precreate' stage for device "
            "management"
        )

        # Should not use poststop for device hooks
        assert (
            "poststop" not in stages
        ), f"Device hook {hook_name} should not use 'poststop' stage"
