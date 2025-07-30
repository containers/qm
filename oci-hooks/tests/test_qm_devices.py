#!/usr/bin/env python3
"""Device detection and annotation tests for QM device manager."""

import pytest

from conftest import DeviceCounter


class TestQMDeviceManagerDevices:
    """Device annotation tests for QM device manager."""

    @pytest.mark.integration
    @pytest.mark.hook_execution
    def test_audio_device_annotation(
        self, hook_runner, sample_specs, device_counter
    ):
        """Test audio device annotation executes successfully."""
        result = hook_runner.run_hook(
            "qm_device_manager", sample_specs["audio_device"]
        )

        assert result.success, f"Hook failed: {result.stderr}"

        # Hook should succeed and produce valid output regardless of
        # available devices (device-specific testing in temp_devices tests)
        total_devices = device_counter.count_devices(result.output_spec)
        assert total_devices >= 0, "Device count should be non-negative"

    @pytest.mark.integration
    @pytest.mark.hook_execution
    def test_multiple_device_annotations(
        self, hook_runner, sample_specs, device_counter
    ):
        """Test multiple device annotations."""
        result = hook_runner.run_hook(
            "qm_device_manager", sample_specs["multiple_devices"]
        )

        assert result.success, f"Hook failed: {result.stderr}"

        # Should have devices for at least one of the requested types
        # (depending on what's available in test environment)
        total_devices = device_counter.count_devices(result.output_spec)

        # Even if no devices are available, hook should succeed
        assert total_devices >= 0, "Device count should be non-negative"

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "device_type,annotation_key",
        [
            ("audio", "org.containers.qm.device.audio"),
            ("video", "org.containers.qm.device.video"),
            ("input", "org.containers.qm.device.input"),
            ("ttys", "org.containers.qm.device.ttys"),
            ("ttyUSB", "org.containers.qm.device.ttyUSB"),
            ("dvb", "org.containers.qm.device.dvb"),
            ("radio", "org.containers.qm.device.radio"),
        ],
    )
    def test_individual_device_types(
        self, hook_runner, device_type, annotation_key
    ):
        """Test individual device type annotations."""
        spec = {"annotations": {annotation_key: "true"}, "linux": {}}

        result = hook_runner.run_hook("qm_device_manager", spec)
        assert (
            result.success
        ), f"Hook failed for {device_type}: {result.stderr}"

        # Validate result.output_spec structure
        assert "linux" in result.output_spec
        assert ("devices" in result.output_spec.get("linux", {})) or (
            DeviceCounter.count_devices(result.output_spec) == 0
        )

    @pytest.mark.unit
    def test_audio_device_annotation_with_temp_devices(
        self, hook_runner, sample_specs, device_counter, temp_devices
    ):
        """Test audio device annotation with specific device creation."""
        device_detector = temp_devices.get_audio_devices()

        result = hook_runner.run_hook(
            "qm_device_manager",
            sample_specs["audio_device"],
            mock_devices=device_detector.mock_devices(device_type="audio"),
        )

        assert result.success, f"Hook failed: {result.stderr}"

        # Verify expected number of devices
        device_count = device_counter.count_devices(result.output_spec)
        assert device_count == device_detector.expected_count, (
            f"Expected {device_detector.expected_count} audio devices, "
            f"got {device_count}"
        )

        # Verify the specific temporary devices are present
        devices = result.output_spec.get("linux", {}).get("devices", [])
        found_paths = [d["path"] for d in devices]

        assert all(
            temp_path in found_paths for temp_path in device_detector.paths
        ), (
            f"All temporary audio devices should be found in output. "
            f"Expected: {device_detector.paths}, Found: {found_paths}"
        )

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "device_type,device_method",
        [
            ("video", "get_video_devices"),
            ("input", "get_input_devices"),
            ("dvb", "get_dvb_devices"),
            ("ttyUSB", "get_ttyusb_devices"),
            ("radio", "get_radio_devices"),
            ("ttys", "get_ttys_devices"),
        ],
    )
    # pylint: disable=too-many-positional-arguments
    def test_device_annotation_with_temp_devices(
        self,
        hook_runner,
        device_counter,
        temp_devices,
        device_type,
        device_method,
    ):
        """Test various device types with specific device creation."""
        device_detector = getattr(temp_devices, device_method)()

        annotation_key = f"org.containers.qm.device.{device_type}"
        spec = {
            "annotations": {annotation_key: "true"},
            "linux": {},
        }

        result = hook_runner.run_hook(
            "qm_device_manager",
            spec,
            mock_devices=device_detector.mock_devices(device_type),
        )

        assert (
            result.success
        ), f"Hook failed for {device_type}: {result.stderr}"

        device_count = device_counter.count_devices(result.output_spec)
        assert device_count == device_detector.expected_count, (
            f"Expected {device_detector.expected_count} {device_type} "
            f"devices, got {device_count}"
        )
