#!/usr/bin/env python3
"""Validation tests for QM device manager."""

import pytest


class TestQMDeviceManagerValidation:
    """JSON and structure validation tests."""

    @pytest.mark.unit
    def test_output_json_structure(
        self, hook_runner, sample_specs, oci_spec_validator
    ):
        """Test that hook output follows OCI specification structure."""
        result = hook_runner.run_hook(
            "qm_device_manager", sample_specs["audio_device"]
        )

        assert result.success, f"Hook failed: {result.stderr}"
        assert oci_spec_validator(result.output_spec), "Output spec is invalid"

    @pytest.mark.unit
    def test_device_structure_validation(self, hook_runner, sample_specs):
        """Test that device entries have correct structure."""
        result = hook_runner.run_hook(
            "qm_device_manager", sample_specs["multiple_devices"]
        )

        assert result.success, f"Hook failed: {result.stderr}"

        devices = result.output_spec.get("linux", {}).get("devices", [])

        # Check that all devices have required fields
        required_fields = ["path", "type", "major", "minor"]
        assert all(
            field in device for device in devices for field in required_fields
        ), "All devices must have required fields: path, type, major, minor"

        # Check path types
        assert all(
            isinstance(d["path"], str) for d in devices
        ), "Path must be str"
        # Check type values
        assert all(
            d["type"] in ["c", "b"] for d in devices
        ), "Type must be c or b"
        # Check major/minor are integers
        assert all(
            isinstance(d["major"], int) for d in devices
        ), "Major must be int"
        assert all(
            isinstance(d["minor"], int) for d in devices
        ), "Minor must be int"

    @pytest.mark.unit
    def test_resource_structure_validation(self, hook_runner):
        """Test that resource entries have correct structure."""
        spec = {
            "annotations": {"org.containers.qm.wayland.seat": "true"},
            "linux": {},
        }

        result = hook_runner.run_hook("qm_device_manager", spec)
        assert result.success, f"Hook failed: {result.stderr}"

        # Check devices limit structure
        devices_limit = (
            result.output_spec.get("linux", {})
            .get("resources", {})
            .get("devices", [])
        )

        # Validate all device rules have required fields
        assert all(
            "allow" in device_rule for device_rule in devices_limit
        ), "All device rules must have 'allow' field"

        assert all(
            "type" in device_rule for device_rule in devices_limit
        ), "All device rules must have 'type' field"

        assert all(
            isinstance(device_rule["allow"], bool)
            for device_rule in devices_limit
        ), "All 'allow' fields must be bool"

        assert all(
            device_rule["type"] in ["c", "b", "a"]
            for device_rule in devices_limit
        ), "All device types must be 'c', 'b', or 'a'"

    @pytest.mark.unit
    def test_empty_annotations_validation(
        self, hook_runner, oci_spec_validator
    ):
        """Test validation with empty annotations."""
        empty_spec = {"annotations": {}, "linux": {}}

        result = hook_runner.run_hook("qm_device_manager", empty_spec)
        assert result.success, f"Hook failed: {result.stderr}"
        assert oci_spec_validator(result.output_spec), "Output should be valid"

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "malformed_spec",
        [
            # Non-string annotation values should be handled gracefully
            {
                "annotations": {"org.containers.qm.device.audio": True},
                "linux": {},
            },
            {
                "annotations": {"org.containers.qm.device.audio": 123},
                "linux": {},
            },
            {
                "annotations": {"org.containers.qm.device.audio": []},
                "linux": {},
            },
        ],
        ids=["boolean_value", "integer_value", "list_value"],
    )
    def test_malformed_annotation_values(self, hook_runner, malformed_spec):
        """Test handling of malformed annotation values."""
        result = hook_runner.run_hook("qm_device_manager", malformed_spec)
        # Hook should not crash, but may not process the annotation
        assert (
            result.success
        ), f"Hook should handle malformed values: {result.stderr}"
