#!/usr/bin/env python3
"""Basic functionality tests for QM device manager."""

import pytest

from conftest import DeviceCounter


class TestQMOCIHooksBasic:
    """Basic functionality tests for QM device manager."""

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "hook_name", ["qm_device_manager", "wayland_client_devices"]
    )
    @pytest.mark.parametrize(
        "json_spec",
        [
            {"annotations": {}, "linux": {}},
            {
                "annotations": {"org.containers.qm.device.unknown": "true"},
                "linux": {},
            },
            {
                "annotations": {"org.containers.qm.device.audio": "false"},
                "linux": {},
            },
        ],
        ids=["empty_spec", "unknown_spec", "invalid_spec"],
    )
    def test_basic_annotations(
        self, hook_name, json_spec, hook_runner, oci_spec_validator
    ):
        """Test hook with basic annotations returns unchanged spec."""
        result = hook_runner.run_hook(hook_name, json_spec)

        assert result.success, f"Hook failed: {result.stderr}"
        assert oci_spec_validator(result.output_spec), "Output spec is invalid"
        assert (
            DeviceCounter.count_devices(result.output_spec) == 0
        ), "No devices should be added"

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "invalid_spec",
        [
            # Missing required 'linux' property
            {"annotations": {"com.example": "value"}},
            # 'annotations' should be an object, not a string
            {"annotations": "not-an-object", "linux": {}},
            # Add a property not defined in the schema
            {
                "annotations": {"com.example": "value"},
                "linux": {},
                "extra": 123,
            },
        ],
    )
    def test_invalid_annotations(self, oci_spec_validator, invalid_spec):
        """Test invalid annotations are rejected."""
        assert not oci_spec_validator(
            invalid_spec
        ), "Invalid spec should be rejected"

    @pytest.mark.unit
    def test_missing_linux_section(self, hook_runner):
        """Test hook creates linux section if missing."""
        malformed_json = {
            "annotations": {"org.containers.qm.device.audio": "true"}
            # Missing linux section
        }
        result = hook_runner.run_hook("qm_device_manager", malformed_json)

        assert result.success, f"Hook failed: {result.stderr}"
        assert (
            "linux" in result.output_spec
        ), "Hook should create linux section"
        assert isinstance(
            result.output_spec["linux"], dict
        ), "Linux section should be a dict"

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "json_spec",
        [
            # Non-wayland annotations ignored
            {
                "annotations": {"org.containers.qm.device.audio": "true"},
                "linux": {},
            },
            # Unknown wayland annotations ignored
            {
                "annotations": {
                    "org.containers.qm.wayland-client.unknown": "true"
                },
                "linux": {},
            },
        ],
        ids=["non_wayland_ignored", "unknown_wayland_ignored"],
    )
    def test_wayland_annotations(self, hook_runner, json_spec, device_counter):
        """Test wayland annotations are processed correctly."""
        result = hook_runner.run_hook("wayland_client_devices", json_spec)
        assert result.success, f"Hook failed: {result.stderr}"
        assert (
            device_counter.count_devices(result.output_spec) == 0
        ), "No devices should be added"
