"""Pytest configuration and fixtures for OCI hooks testing."""

import os
import tempfile
from pathlib import Path

import pytest

from device_utils import DeviceCounter, TempDevices
from test_utils import (
    HookRunner,
    OciSpecValidator,
    LogChecker,
)


@pytest.fixture(scope="session")
def test_env():
    """Set up test environment with temporary log files."""
    with tempfile.TemporaryDirectory(prefix="oci_hooks_test_") as temp_dir:
        env = os.environ.copy()
        env["TEST_LOGFILE"] = os.path.join(temp_dir, "test-hook.log")
        yield {
            "env": env,
            "log_file": env["TEST_LOGFILE"],
            "temp_dir": temp_dir,
        }


@pytest.fixture
def hook_runner(test_env):
    """Create a HookRunner instance with test environment and hook paths."""
    yield HookRunner(test_env["env"])


@pytest.fixture
def oci_spec_validator():
    """Provide validator for OCI specification JSON."""
    return OciSpecValidator.validate


@pytest.fixture
def sample_specs():
    """Sample OCI specifications for testing."""
    yield {
        "audio_device": {
            "annotations": {"org.containers.qm.device.audio": "true"},
            "linux": {},
        },
        "multiple_devices": {
            "annotations": {
                "org.containers.qm.device.audio": "true",
                "org.containers.qm.device.input": "true",
                "org.containers.qm.device.ttys": "true",
            },
            "linux": {},
        },
        "wayland_seat": {
            "annotations": {"org.containers.qm.wayland.seat": "seat0"},
            "linux": {},
        },
        "wayland_gpu": {
            "annotations": {"org.containers.qm.wayland-client.gpu": "true"},
            "linux": {},
        },
        "combined": {
            "annotations": {
                "org.containers.qm.device.audio": "true",
                "org.containers.qm.wayland.seat": "seat0",
            },
            "linux": {},
        },
        "invalid_device": {
            "annotations": {"org.containers.qm.device.audio": "false"},
            "linux": {},
        },
    }


@pytest.fixture
def log_checker(test_env):
    """Check hook log files for expected content."""
    return LogChecker(test_env["log_file"])


@pytest.fixture
def device_counter():
    """Fixture providing device counting utilities."""
    return DeviceCounter


@pytest.fixture
def temp_devices():
    """Fixture providing on-demand temporary device creation."""
    with tempfile.TemporaryDirectory(prefix="test_devices_") as temp_dir:
        temp_path = Path(temp_dir)

        yield TempDevices(temp_path)
