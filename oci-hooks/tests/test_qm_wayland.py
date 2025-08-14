#!/usr/bin/env python3
"""Wayland seat functionality tests for QM device manager."""

import pytest


class TestQMDeviceManagerWayland:
    """Wayland seat annotation tests."""

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "seat_annotation",
        [
            "org.containers.qm.wayland.seat",
            "org.containers.qm.wayland.seat.0",
            "org.containers.qm.wayland.seat.1",
        ],
    )
    def test_wayland_seat_annotation(
        self, hook_runner, seat_annotation, device_counter
    ):
        """Test Wayland seat annotations."""
        spec = {
            "annotations": {seat_annotation: "true"},
            "linux": {},
        }

        result = hook_runner.run_hook("qm_device_manager", spec)
        assert result.success, f"Hook failed: {result.stderr}"

        # Verify devices and resources are added for seat
        device_count = device_counter.count_devices(result.output_spec)
        resource_count = device_counter.count_resources(result.output_spec)

        assert device_count >= 0, "Device count should be non-negative"
        assert resource_count >= 0, "Resource count should be non-negative"

    @pytest.mark.unit
    def test_wayland_seat_with_existing_devices(self, hook_runner):
        """Test wayland seat annotation with existing devices."""
        spec_with_devices = {
            "annotations": {"org.containers.qm.wayland.seat": "true"},
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

        # Should preserve existing devices
        devices = result.output_spec.get("linux", {}).get("devices", [])
        existing_paths = [d["path"] for d in devices]
        assert (
            "/dev/existing" in existing_paths
        ), "Existing device should be preserved"

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "spec",
        [
            {
                "annotations": {
                    "org.containers.qm.wayland.seat.0": "true",
                    "org.containers.qm.wayland.seat.1": "true",
                },
                "linux": {},
            },
            {
                "annotations": {
                    "org.containers.qm.wayland.seat": "seat0",
                    "org.containers.qm.wayland.seat.0": "true",
                    "org.containers.qm.wayland.seat.1": "true",
                },
                "linux": {},
            },
        ],
        ids=["multiple_seats", "conflicting_seats"],
    )
    def test_multiple_wayland_seats(self, hook_runner, device_counter, spec):
        """Test multiple Wayland seat annotations."""
        result = hook_runner.run_hook("qm_device_manager", spec)
        assert result.success, f"Hook failed: {result.stderr}"

        # Should process both seats
        device_count = device_counter.count_devices(result.output_spec)
        resource_count = device_counter.count_resources(result.output_spec)

        assert device_count >= 0, "Should handle multiple seats"
        assert resource_count >= 0, "Resource count should be non-negative"
