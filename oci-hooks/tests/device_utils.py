"""Device testing utilities for OCI hooks."""

import os
import stat
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, Optional, List


class DeviceCounter:
    """Helper class for counting devices in OCI specifications."""

    @staticmethod
    def count_devices(
        spec: Dict[str, Any], device_pattern: Optional[str] = None
    ) -> int:
        """Count devices in OCI spec, optionally filtered by path pattern."""
        devices = spec.get("linux", {}).get("devices", [])

        if device_pattern is None:
            return len(devices)

        return len([d for d in devices if device_pattern in d.get("path", "")])

    @staticmethod
    def count_resources(spec: Dict[str, Any]) -> int:
        """Count device resources in OCI spec."""
        resources = (
            spec.get("linux", {}).get("resources", {}).get("devices", [])
        )
        return len(resources)

    @staticmethod
    def has_device_path(spec: Dict[str, Any], path: str) -> bool:
        """Check if OCI spec contains a device with specific path."""
        devices = spec.get("linux", {}).get("devices", [])
        return any(d.get("path") == path for d in devices)


@dataclass
class DeviceDetector:
    """Class for detecting real devices for testing."""

    paths: List[str] = field(default_factory=list)
    expected_count: int = 0

    def mock_devices(self, device_type) -> Optional[Dict[str, str]]:
        """Mock devices for testing."""
        return {device_type: ",".join(self.paths)}


class TempDevices:
    """Class for creating temporary device files on-demand for testing."""

    def __init__(self, temp_path: Path):
        """Initialize TempDevices with temporary path."""
        self.temp_path = temp_path
        self._created_devices = {}

        # Create base directory structure
        for subdir in ["snd", "dri", "input", "dvb"]:
            (self.temp_path / subdir).mkdir(exist_ok=True)

    def _create_device(
        self, device_path: Path, major: int, minor: int
    ) -> Path:
        """Create device node with mknod if possible, fall back to env vars."""
        device_path.parent.mkdir(parents=True, exist_ok=True)

        if os.environ.get("FORCE_MOCK_DEVICES", "false").lower() != "true":
            try:
                # Try to create real device nodes when not forced
                os.mknod(
                    device_path, stat.S_IFCHR | 0o600, os.makedev(major, minor)
                )
            except OSError:
                # Fallback to regular files if mknod fails
                device_path.touch()
        else:
            # Create regular files when forced to use mock mode
            device_path.touch()

        return device_path

    def _set_mock_env_for_devices(self, device_type: str, devices: List[Path]):
        """Set mock environment variables for device discovery."""
        env_var = f"TEST_MOCK_{device_type.upper()}_DEVICES"
        os.environ[env_var] = ",".join(str(d) for d in devices)

    def get_audio_devices(self) -> DeviceDetector:
        """Get audio device paths for testing."""
        if "audio" not in self._created_devices:
            devices = [
                self._create_device(
                    self.temp_path / "snd" / "controlC0", 116, 0
                ),
                self._create_device(
                    self.temp_path / "snd" / "pcmC0D0p", 116, 24
                ),
            ]
            self._created_devices["audio"] = devices
            self._set_mock_env_for_devices("audio", devices)

        device_paths = [str(d) for d in self._created_devices["audio"]]
        return DeviceDetector(
            paths=device_paths, expected_count=len(device_paths)
        )

    def get_video_devices(self) -> DeviceDetector:
        """Get video device paths for testing."""
        if "video" not in self._created_devices:
            devices = [
                self._create_device(self.temp_path / "video0", 81, 0),
                self._create_device(self.temp_path / "video1", 81, 1),
            ]
            self._created_devices["video"] = devices
            self._set_mock_env_for_devices("video", devices)

        device_paths = [str(d) for d in self._created_devices["video"]]
        return DeviceDetector(
            paths=device_paths, expected_count=len(device_paths)
        )

    def get_input_devices(self) -> DeviceDetector:
        """Get input device paths for testing."""
        if "input" not in self._created_devices:
            devices = [
                self._create_device(
                    self.temp_path / "input" / "event0", 13, 64
                ),
                self._create_device(
                    self.temp_path / "input" / "event1", 13, 65
                ),
                self._create_device(self.temp_path / "input" / "mice", 13, 63),
            ]
            self._created_devices["input"] = devices
            self._set_mock_env_for_devices("input", devices)

        device_paths = [str(d) for d in self._created_devices["input"]]
        return DeviceDetector(
            paths=device_paths, expected_count=len(device_paths)
        )

    def get_gpu_devices(self) -> DeviceDetector:
        """Get GPU device paths for testing."""
        if "gpu" not in self._created_devices:
            devices = [
                self._create_device(
                    self.temp_path / "dri" / "renderD128", 226, 128
                )
            ]
            self._created_devices["gpu"] = devices
            self._set_mock_env_for_devices("gpu", devices)

        device_paths = [str(d) for d in self._created_devices["gpu"]]
        return DeviceDetector(
            paths=device_paths, expected_count=len(device_paths)
        )

    def get_dvb_devices(self) -> DeviceDetector:
        """Get DVB device paths for testing."""
        if "dvb" not in self._created_devices:
            devices = [
                self._create_device(
                    self.temp_path / "dvb" / "adapter0" / "frontend0", 212, 4
                ),
                self._create_device(
                    self.temp_path / "dvb" / "adapter0" / "demux0", 212, 5
                ),
            ]
            self._created_devices["dvb"] = devices
            self._set_mock_env_for_devices("dvb", devices)

        device_paths = [str(d) for d in self._created_devices["dvb"]]
        return DeviceDetector(
            paths=device_paths, expected_count=len(device_paths)
        )

    def get_ttyusb_devices(self) -> DeviceDetector:
        """Get USB TTY device paths for testing."""
        if "ttyUSB" not in self._created_devices:
            devices = [
                self._create_device(self.temp_path / "ttyUSB0", 188, 0),
                self._create_device(self.temp_path / "ttyUSB1", 188, 1),
            ]
            self._created_devices["ttyUSB"] = devices
            self._set_mock_env_for_devices("ttyUSB", devices)

        device_paths = [str(d) for d in self._created_devices["ttyUSB"]]
        return DeviceDetector(
            paths=device_paths, expected_count=len(device_paths)
        )

    def get_radio_devices(self) -> DeviceDetector:
        """Get radio device paths for testing."""
        if "radio" not in self._created_devices:
            devices = [
                self._create_device(self.temp_path / "radio0", 81, 64),
                self._create_device(self.temp_path / "radio1", 81, 65),
            ]
            self._created_devices["radio"] = devices
            self._set_mock_env_for_devices("radio", devices)

        device_paths = [str(d) for d in self._created_devices["radio"]]
        return DeviceDetector(
            paths=device_paths, expected_count=len(device_paths)
        )

    def get_ttys_devices(self) -> DeviceDetector:
        """Get TTY device paths for testing."""
        if "ttys" not in self._created_devices:
            devices = [
                self._create_device(self.temp_path / "tty0", 4, 0),
                self._create_device(self.temp_path / "tty1", 4, 1),
                self._create_device(self.temp_path / "tty2", 4, 2),
            ]
            self._created_devices["ttys"] = devices
            self._set_mock_env_for_devices("ttys", devices)

        device_paths = [str(d) for d in self._created_devices["ttys"]]
        return DeviceDetector(
            paths=device_paths, expected_count=len(device_paths)
        )
