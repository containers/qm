#!/usr/bin/env python3
"""Performance tests for QM device manager and Wayland client devices."""

import time

import pytest


class TestQMDeviceManagerPerformance:
    """Performance and timing tests."""

    @pytest.mark.performance
    def test_hook_performance(self, hook_runner, sample_specs):
        """Test that hook executes within reasonable time."""
        start_time = time.time()
        result = hook_runner.run_hook(
            "qm_device_manager", sample_specs["multiple_devices"]
        )
        end_time = time.time()

        assert result.success, f"Hook failed: {result.stderr}"

        execution_time = end_time - start_time
        # Hook should complete within 5 seconds (generous limit)
        assert (
            execution_time < 5.0
        ), f"Hook took too long: {execution_time:.2f}s"

    @pytest.mark.performance
    @pytest.mark.parametrize("iteration", range(5))
    def test_multiple_executions_performance(
        self, hook_runner, sample_specs, iteration
    ):
        """Test consistent performance across multiple executions."""
        start_time = time.time()
        result = hook_runner.run_hook(
            "qm_device_manager", sample_specs["audio_device"]
        )
        end_time = time.time()

        assert (
            result.success
        ), f"Hook failed on iteration {iteration}: {result.stderr}"

        execution_time = end_time - start_time
        assert (
            execution_time < 3.0
        ), f"Execution {iteration} too slow: {execution_time:.2f}s"


class TestWaylandClientDevicesPerformance:
    """Performance tests for Wayland client devices."""

    @pytest.mark.performance
    def test_hook_performance(self, hook_runner, sample_specs):
        """Test Wayland client devices hook performance."""
        start_time = time.time()
        result = hook_runner.run_hook(
            "wayland_client_devices", sample_specs["wayland_gpu"]
        )
        end_time = time.time()

        assert result.success, f"Hook failed: {result.stderr}"

        execution_time = end_time - start_time
        assert (
            execution_time < 3.0
        ), f"Hook took too long: {execution_time:.2f}s"

    @pytest.mark.performance
    @pytest.mark.parametrize("iteration", range(3))
    def test_multiple_executions_performance(
        self, hook_runner, sample_specs, iteration
    ):
        """Test consistent performance across multiple executions."""
        start_time = time.time()
        result = hook_runner.run_hook(
            "wayland_client_devices", sample_specs["wayland_gpu"]
        )
        end_time = time.time()

        assert (
            result.success
        ), f"Hook failed on iteration {iteration}: {result.stderr}"

        execution_time = end_time - start_time
        assert (
            execution_time < 2.0
        ), f"Execution {iteration} too slow: {execution_time:.2f}s"
