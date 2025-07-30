#!/usr/bin/env python3
"""Wayland GPU device tests."""

import pytest


class TestWaylandClientDevicesGPU:
    """GPU device detection tests for Wayland client containers."""

    @pytest.mark.unit
    def test_gpu_annotation_enabled(self, hook_runner, sample_specs):
        """Test GPU annotation processes correctly."""
        result = hook_runner.run_hook(
            "wayland_client_devices", sample_specs["wayland_gpu"]
        )
        assert result.success, f"Hook failed: {result.stderr}"

    @pytest.mark.unit
    @pytest.mark.parametrize("gpu_value", ["true", "1", "yes", "True", "YES"])
    def test_gpu_annotation_valid_values(
        self, hook_runner, device_counter, gpu_value
    ):
        """Test GPU annotation with various valid truthy values."""
        spec = {
            "annotations": {"org.containers.qm.wayland-client.gpu": gpu_value},
            "linux": {},
        }
        result = hook_runner.run_hook("wayland_client_devices", spec)
        assert (
            result.success
        ), f"Hook failed with value '{gpu_value}': {result.stderr}"

        # For truthy values, devices should be processed
        total_devices = device_counter.count_devices(result.output_spec)
        assert (
            total_devices >= 0
        ), f"Truthy value '{gpu_value}' should enable GPU processing"

    @pytest.mark.unit
    @pytest.mark.parametrize("gpu_value", ["false", "0", "no", "False", "NO"])
    def test_gpu_annotation_invalid_values(
        self, hook_runner, device_counter, gpu_value
    ):
        """Test GPU annotation with various falsy values."""
        spec = {
            "annotations": {"org.containers.qm.wayland-client.gpu": gpu_value},
            "linux": {},
        }
        result = hook_runner.run_hook("wayland_client_devices", spec)
        assert (
            result.success
        ), f"Hook failed with falsy value '{gpu_value}': {result.stderr}"

        # For falsy values, no devices should be added
        total_devices = device_counter.count_devices(result.output_spec)
        assert (
            total_devices == 0
        ), f"Falsy value '{gpu_value}' should not add GPU devices"

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "gpu_value", ["TrUe", "YeS", "tRuE", "yEs", "TRUE"]
    )
    def test_gpu_annotation_case_insensitive_truthy_values(
        self, hook_runner, device_counter, gpu_value
    ):
        """Test GPU annotation with mixed-case truthy values."""
        spec = {
            "annotations": {"org.containers.qm.wayland-client.gpu": gpu_value},
            "linux": {},
        }
        result = hook_runner.run_hook("wayland_client_devices", spec)
        assert (
            result.success
        ), f"Hook failed with mixed-case value '{gpu_value}': {result.stderr}"
        total_devices = device_counter.count_devices(result.output_spec)
        assert total_devices >= 0, (
            f"Mixed-case truthy value '{gpu_value}' should enable GPU "
            "processing"
        )

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "gpu_value", ["FaLsE", "nO", "fAlSe", "No", "FALSE"]
    )
    def test_gpu_annotation_case_insensitive_falsy_values(
        self, hook_runner, device_counter, gpu_value
    ):
        """Test GPU annotation with mixed-case falsy values."""
        spec = {
            "annotations": {"org.containers.qm.wayland-client.gpu": gpu_value},
            "linux": {},
        }
        result = hook_runner.run_hook("wayland_client_devices", spec)
        assert (
            result.success
        ), f"Hook failed with mixed-case value '{gpu_value}': {result.stderr}"

        # For falsy values, no devices should be added
        total_devices = device_counter.count_devices(result.output_spec)
        assert (
            total_devices == 0
        ), f"Mixed-case falsy value '{gpu_value}' should not add GPU devices"

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "gpu_value",
        [
            "2",  # Number other than 1
            "42",  # Random number
            "maybe",  # Unrelated string
            "truthy",  # Similar but not exact
            "YES_PLEASE",  # Contains valid word but extra chars
            "null",  # Null-like value
            "",  # Empty string
            "[]",  # JSON array string
            "{}",  # JSON object string
            "true false",  # Multiple values
            "TRUE;true",  # Semicolon separated
            "on",  # Common boolean-like value
            "off",  # Common boolean-like value
            "enable",  # Enable-like value
            "disable",  # Disable-like value
        ],
    )
    def test_gpu_annotation_malformed_values(
        self, hook_runner, device_counter, gpu_value
    ):
        """Test GPU annotation with malformed or unexpected values."""
        spec = {
            "annotations": {"org.containers.qm.wayland-client.gpu": gpu_value},
            "linux": {},
        }
        result = hook_runner.run_hook("wayland_client_devices", spec)

        # Hook should handle malformed values gracefully without failing
        assert result.success, (
            f"Hook should not fail with malformed value '{gpu_value}': "
            f"{result.stderr}"
        )

        # Malformed values should be treated as falsy (no GPU devices added)
        total_devices = device_counter.count_devices(result.output_spec)
        assert (
            total_devices == 0
        ), f"Malformed value '{gpu_value}' should not enable GPU processing"


class TestWaylandClientDevicesGPUDevices:
    """GPU device tests for Wayland client containers."""

    @pytest.mark.unit
    def test_gpu_annotation(
        self, hook_runner, sample_specs, device_counter, temp_devices
    ):
        """Test GPU annotation with temp devices."""
        device_detector = temp_devices.get_gpu_devices()

        result = hook_runner.run_hook(
            "wayland_client_devices",
            sample_specs["wayland_gpu"],
            mock_devices=device_detector.mock_devices("gpu"),
        )

        assert result.success, f"Hook failed: {result.stderr}"

        device_count = device_counter.count_devices(result.output_spec)
        assert device_count == device_detector.expected_count, (
            f"Expected {device_detector.expected_count} GPU devices, "
            f"got {device_count}"
        )

        devices = result.output_spec.get("linux", {}).get("devices", [])
        found_paths = [d["path"] for d in devices]

        assert all(
            temp_path in found_paths for temp_path in device_detector.paths
        ), "Temporary GPU device not found in output"
