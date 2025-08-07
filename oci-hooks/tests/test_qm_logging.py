#!/usr/bin/env python3
"""Logging tests for QM device manager and Wayland client devices."""

import pytest


class TestQMDeviceManagerLogging:
    """Logging functionality tests."""

    @pytest.mark.unit
    @pytest.mark.hook_execution
    def test_log_file_creation(self, hook_runner, log_checker):
        """Test that hook creates log file."""
        empty_spec = {"annotations": {}, "linux": {}}
        result = hook_runner.run_hook("qm_device_manager", empty_spec)

        assert result.success, f"Hook failed: {result.stderr}"
        assert log_checker("qm-device-manager"), "Log should contain hook name"

    @pytest.mark.unit
    @pytest.mark.hook_execution
    def test_log_content_validation(
        self, hook_runner, sample_specs, log_checker
    ):
        """Test that hook logs contain expected content."""
        result = hook_runner.run_hook(
            "qm_device_manager", sample_specs["audio_device"]
        )

        assert result.success, f"Hook failed: {result.stderr}"
        assert log_checker(
            "QM Device Manager"
        ), "Log should contain hook description"
        assert log_checker("completed successfully")


class TestWaylandClientDevicesLogging:
    """Logging functionality tests."""

    @pytest.mark.unit
    @pytest.mark.hook_execution
    def test_log_file_creation(self, hook_runner, log_checker):
        """Test that hook creates log file."""
        empty_spec = {"annotations": {}, "linux": {}}
        result = hook_runner.run_hook("wayland_client_devices", empty_spec)

        assert result.success, f"Hook failed: {result.stderr}"
        assert log_checker(
            "qm-wayland-client-devices"
        ), "Log should contain hook name"

    @pytest.mark.unit
    @pytest.mark.hook_execution
    def test_log_content_validation(
        self, hook_runner, sample_specs, log_checker
    ):
        """Test that hook logs contain expected content."""
        result = hook_runner.run_hook(
            "wayland_client_devices", sample_specs["wayland_gpu"]
        )

        assert result.success, f"Hook failed: {result.stderr}"
        assert log_checker(
            "qm-wayland-client-devices"
        ), "Log should contain hook name"
