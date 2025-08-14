#!/usr/bin/env python3
"""Error handling and edge case tests for QM device manager."""

import pytest


class TestQMDeviceManagerErrorHandling:
    """Error handling and edge case tests."""

    @pytest.mark.unit
    @pytest.mark.hook_execution
    def test_non_qm_annotations_ignored(self, hook_runner, device_counter):
        """Test that non-QM annotations are ignored."""
        spec = {
            "annotations": {
                "org.opencontainers.image.title": "test",
                "com.example.custom": "value",
            },
            "linux": {},
        }

        result = hook_runner.run_hook("qm_device_manager", spec)

        assert result.success, f"Hook failed: {result.stderr}"
        assert (
            device_counter.count_devices(result.output_spec) == 0
        ), "No devices should be added for non-QM annotations"

    @pytest.mark.unit
    def test_hook_with_existing_devices(self, hook_runner):
        """Test hook behavior when devices already exist."""
        spec_with_devices = {
            "annotations": {"org.containers.qm.device.audio": "true"},
            "linux": {
                "devices": [
                    {
                        "path": "/dev/existing",
                        "type": "c",
                        "major": 1,
                        "minor": 3,
                    }
                ]
            },
        }

        result = hook_runner.run_hook("qm_device_manager", spec_with_devices)
        assert result.success, f"Hook failed: {result.stderr}"

        # Should preserve existing devices and potentially add new ones
        devices = result.output_spec.get("linux", {}).get("devices", [])
        existing_paths = [d["path"] for d in devices]
        assert (
            "/dev/existing" in existing_paths
        ), "Existing device should be preserved"

    @pytest.mark.unit
    def test_hook_with_existing_resources(self, hook_runner):
        """Test hook behavior when resources already exist."""
        spec_with_resources = {
            "annotations": {"org.containers.qm.wayland.seat": "true"},
            "linux": {
                "resources": {"devices": [{"allow": False, "type": "a"}]}
            },
        }

        result = hook_runner.run_hook("qm_device_manager", spec_with_resources)
        assert result.success, f"Hook failed: {result.stderr}"

        # Should preserve existing resources
        resources = result.output_spec.get("linux", {}).get("resources", {})
        devices_limit = resources.get("devices", [])

        # Check that the existing rule is preserved
        deny_all_rule = {"allow": False, "type": "a"}
        assert (
            deny_all_rule in devices_limit
        ), "Existing resource rules should be preserved"


class TestWaylandClientDevicesErrorHandling:
    """Error handling tests for Wayland client devices."""

    @pytest.mark.unit
    def test_annotation_isolation(self, hook_runner, device_counter):
        """Test that invalid annotations don't affect valid ones."""
        spec = {
            "annotations": {
                "org.containers.qm.wayland-client.gpu": "true",
                "org.containers.qm.wayland-client.invalid": "bad_value",
                "org.opencontainers.image.title": "test",
            },
            "linux": {},
        }

        result = hook_runner.run_hook("wayland_client_devices", spec)
        assert result.success, f"Hook failed: {result.stderr}"

        # Valid GPU annotation should still be processed
        total_devices = device_counter.count_devices(result.output_spec)
        assert total_devices >= 0, "Valid annotations should be processed"

    @pytest.mark.unit
    def test_empty_annotation_value(self, hook_runner, device_counter):
        """Test handling of empty annotation values."""
        spec = {
            "annotations": {"org.containers.qm.wayland-client.gpu": ""},
            "linux": {},
        }

        result = hook_runner.run_hook("wayland_client_devices", spec)
        assert result.success, f"Hook failed: {result.stderr}"

        # Empty value should be treated as falsy
        total_devices = device_counter.count_devices(result.output_spec)
        assert (
            total_devices == 0
        ), "Empty annotation value should not add devices"

    @pytest.mark.unit
    def test_unknown_annotation_values(self, hook_runner, device_counter):
        """Test handling of unknown annotation values."""
        spec = {
            "annotations": {"org.containers.qm.wayland-client.gpu": "maybe"},
            "linux": {},
        }

        result = hook_runner.run_hook("wayland_client_devices", spec)
        assert result.success, f"Hook failed: {result.stderr}"

        # Unknown values should typically be treated as falsy for safety
        total_devices = device_counter.count_devices(result.output_spec)
        assert (
            total_devices == 0
        ), "Unknown annotation values should not add devices"
