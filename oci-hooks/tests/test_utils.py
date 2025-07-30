"""Shared test utilities for OCI hooks testing."""

import json
import subprocess
import time
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, Any, Optional

import jsonschema


@dataclass
class HookResult:
    """Result of running an OCI hook."""

    success: bool
    output_spec: Dict[str, Any]
    stdout: str
    stderr: str
    execution_time: float


class HookRunner:
    """Class for running OCI hooks in test environment."""

    def __init__(self, test_env: Dict[str, str]):
        """Initialize with test environment variables."""
        self.test_env = test_env

    def run_hook(
        self,
        hook_name: str,
        input_spec: Dict[str, Any],
        mock_devices: Optional[Dict[str, str]] = None,
    ) -> HookResult:
        """Run a hook with given input spec and return result."""
        hook_paths = {
            "qm_device_manager": "../qm-device-manager/oci-qm-device-manager",
            "wayland_client_devices": (
                "../wayland-client-devices/oci-qm-wayland-client-devices"
            ),
        }

        if hook_name not in hook_paths:
            raise ValueError(f"Unknown hook: {hook_name}")

        hook_path = hook_paths[hook_name]
        input_json = json.dumps(input_spec)

        # Use provided test environment (including TEST_LOGFILE)
        env = self.test_env.copy()

        # Add mock device environment variables if provided
        if mock_devices:
            for device_type, device_list in mock_devices.items():
                env_var = f"TEST_MOCK_{device_type.upper()}_DEVICES"
                env[env_var] = device_list

        start_time = time.time()
        result = subprocess.run(
            [hook_path],
            input=input_json,
            text=True,
            capture_output=True,
            env=env,
            cwd=Path(__file__).parent,
            check=False,
        )
        execution_time = time.time() - start_time

        # Parse output JSON if hook succeeded
        output_spec = {}
        if result.returncode == 0 and result.stdout.strip():
            try:
                output_spec = json.loads(result.stdout)
            except json.JSONDecodeError:
                # If output is not valid JSON, treat as failure
                pass

        return HookResult(
            success=result.returncode == 0,
            output_spec=output_spec,
            stdout=result.stdout,
            stderr=result.stderr,
            execution_time=execution_time,
        )


class HookConfigLoader:
    """Utility for loading and managing hook configurations."""

    @staticmethod
    def load_all_hook_configs() -> Dict[str, Dict[str, Any]]:
        """Load all hook configuration files."""
        hook_dir = Path(__file__).parent.parent

        def _load_config(json_file):
            with open(json_file, "r", encoding="utf-8") as f:
                return json.load(f)

        return {
            json_file.stem: {
                "path": json_file,
                "config": _load_config(json_file),
            }
            for json_file in hook_dir.rglob("*.json")
            if "oci-qm-" in json_file.name
        }

    @staticmethod
    def get_hook_names() -> list:
        """Get list of all hook names."""
        return list(HookConfigLoader.load_all_hook_configs().keys())


class OciSpecValidator:
    """JSON schema validator for OCI specifications."""

    # Simplified OCI spec schema for validation
    OCI_SCHEMA = {
        "type": "object",
        "properties": {
            "annotations": {
                "type": "object",
                "additionalProperties": {"type": "string"},
            },
            "linux": {
                "type": "object",
                "properties": {
                    "devices": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "path": {"type": "string"},
                                "type": {"type": "string"},
                                "major": {"type": "integer"},
                                "minor": {"type": "integer"},
                                "fileMode": {"type": "integer"},
                                "uid": {"type": "integer"},
                                "gid": {"type": "integer"},
                            },
                            "required": ["path", "type", "major", "minor"],
                        },
                    },
                    "resources": {
                        "type": "object",
                        "properties": {
                            "devices": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "allow": {"type": "boolean"},
                                        "type": {"type": "string"},
                                        "major": {"type": "integer"},
                                        "minor": {"type": "integer"},
                                        "access": {"type": "string"},
                                    },
                                    "required": [
                                        "allow",
                                        "type",
                                        "major",
                                        "minor",
                                        "access",
                                    ],
                                },
                            }
                        },
                    },
                },
                "additionalProperties": False,
            },
        },
        "required": ["annotations", "linux"],
        "additionalProperties": False,
    }

    @classmethod
    def validate(cls, spec: Dict[str, Any]) -> bool:
        """Validate an OCI spec against the schema."""
        try:
            jsonschema.validate(spec, cls.OCI_SCHEMA)
            return True
        except jsonschema.ValidationError:
            return False


class LogChecker:
    """Utility for checking hook log files."""

    def __init__(self, log_file_path: str):
        """Initialize with log file path."""
        self.log_file_path = Path(log_file_path)

    def __call__(self, pattern: str, should_exist: bool = True) -> bool:
        """
        Check if pattern exists in hook log file (backward compatibility).

        Args:
            pattern: String pattern to search for
            should_exist: Whether pattern should exist (True) or not (False)

        Returns:
            True if check passes, False otherwise
        """
        if not self.log_exists():
            return not should_exist

        try:
            content = self.log_file_path.read_text(encoding="utf-8")
            pattern_found = pattern in content
            return pattern_found if should_exist else not pattern_found
        except OSError:
            return False

    def log_exists(self) -> bool:
        """Check if log file exists."""
        return self.log_file_path.exists()

    def log_contains(self, text: str) -> bool:
        """Check if log contains specific text."""
        if not self.log_exists():
            return False
        content = self.log_file_path.read_text(encoding="utf-8")
        return text in content

    def get_log_lines(self) -> list:
        """Get all log lines as a list."""
        try:
            return (
                self.log_file_path.read_text(encoding="utf-8")
                .strip()
                .split("\n")
            )
        except OSError:
            return []
