#!/usr/bin/env python3

# Licensed under the Apache License, Version 2.0
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# flake8: noqa: E501

"""A Python interface for interacting with the 'qm' container.

This module provides the QmController class for interacting with the 'qm'
container managed by podman. It allows for executing commands, copying
files, and inspecting various aspects of the container's state.
"""

import argparse
import errno
import importlib.util
import json
import os
import pty
import shutil
import subprocess  # nosec B404
import sys

from collections import defaultdict
from typing import Any, Callable, Generator, Optional, Union


# Constants - Default configuration values
DEFAULT_CONFIG_PATH = "/usr/share/containers/systemd/qm.container"  # Default path to container config file
DEFAULT_CONTAINER_NAME = "qm"  # Default container name to operate on
DEFAULT_JSON_INDENT = 4  # Number of spaces for JSON pretty-printing
BUFFER_SIZE = 1024  # Buffer size for reading output streams

# Command patterns - String patterns used for parsing configuration files
ADD_DEVICE_PREFIX = "AddDevice="  # Prefix for device declarations in config files
COMMENT_PREFIX = "#"  # Comment prefix in configuration files

# Container commands - Base podman command arrays for container operations
PODMAN_EXEC = ["podman", "exec"]  # Base command for executing in containers
PODMAN_CP = ["podman", "cp"]  # Base command for copying files to/from containers


class QmError(Exception):
    """Base exception for QM operations.

    This is the parent class for all QM-related exceptions. It includes
    an exit_code attribute to support proper program termination with
    appropriate exit codes for different error conditions.
    """

    EXIT_CODE_GENERAL_ERROR = 1
    EXIT_CODE_FILE_NOT_FOUND = errno.ENOENT  # 2
    EXIT_CODE_INVALID_ARGUMENT = errno.EINVAL  # 22
    EXIT_CODE_TEST_CUSTOM = 42 # Custom exit code for testing
    EXIT_COMMAND_NOT_FOUND = 127

    def __init__(self, message: str, exit_code: int = 1) -> None:
        """Initialize QmError with message and exit code.

        Args:
            message: Human-readable error description
            exit_code: Process exit code (default: 1 for general errors)
        """
        super().__init__(message)
        self.exit_code = exit_code


class ConfigNotFoundError(QmError):
    """Raised when configuration file is not found.

    This exception is raised when the specified container configuration
    file cannot be located on the filesystem. Uses errno.ENOENT (2)
    as the exit code to indicate file not found.
    """

    def __init__(self, config_path: str) -> None:
        """Initialize ConfigNotFoundError with config path.

        Args:
            config_path: Path to the missing configuration file
        """
        super().__init__(
            f"Configuration file {config_path} not found.",
            QmError.EXIT_CODE_FILE_NOT_FOUND
        )


class ContainerNotFoundError(QmError):
    """Raised when container does not exist.

    This exception is raised when attempting to interact with a container
    that is not currently running or does not exist in the podman environment.
    """

    def __init__(self, container_name: str) -> None:
        """Initialize ContainerNotFoundError with container name.

        Args:
            container_name: Name of the missing container
        """
        super().__init__(
            f"Container '{container_name}' does not exist.",
            QmError.EXIT_COMMAND_NOT_FOUND
            )


class CommandNotFoundError(QmError):
    """Raised when command is not found in container.

    This exception is raised when attempting to execute a command that
    is not available within the container environment. Typically occurs
    when the command binary is missing or not in the container's PATH.
    """

    def __init__(self, command: list[str], container: str) -> None:
        """Initialize CommandNotFoundError with command and container.

            command: List of command components that were not found
        Args:
            container: Name of the container where command was attempted
        """
        super().__init__(
            f"Command '{' '.join(command)}' not found in container "
            f"'{container}'.",
            QmError.EXIT_COMMAND_NOT_FOUND
        )


class ValidationError(QmError):
    """Raised when validation fails.

    This exception is raised for various input validation failures,
    such as missing required parameters, invalid path formats, or
    malformed command arguments.
    """

    def __init__(self, message: str) -> None:
        """Initialize ValidationError with message.

        Args:
            message: Description of the validation failure
        """
        super().__init__(
            message,
            QmError.EXIT_CODE_INVALID_ARGUMENT
        )


class OutputConfig:
    """Configuration for output formatting.

    This class encapsulates the output formatting preferences for the
    QmController operations. It supports both human-readable text output
    and machine-readable JSON output with optional pretty-printing.
    """

    def __init__(self, output_json: bool = False, pretty: bool = True) -> None:
        """Initialize OutputConfig with JSON and pretty print settings.

        Args:
            output_json: Enable JSON output format instead of plain text
            pretty: Enable pretty-printing for JSON output (indentation and formatting)
        """
        self.output_json = output_json  # Controls output format (JSON vs text)
        self.pretty = pretty  # Controls JSON formatting (pretty vs compact)


class QmController:
    """Manage and interact with the qm container.

    This is the main class for interacting with containerized environments
    managed by podman. It provides methods for executing commands, copying
    files, inspecting container state, and displaying various types of
    information about the container and its contents.

    The class follows a centralized error handling pattern where all public
    methods catch exceptions and call _print_error_and_exit() for consistent
    error reporting and proper exit codes.
    """

    @staticmethod
    def find_executable(binary_name: str) -> str:
        """Find a binary in the system PATH.

        Args:
            binary_name (str): Name of the executable to find.

        Returns:
            str: Full path to the executable.

        Raises:
            FileNotFoundError: If the binary cannot be found.
        """
        path = shutil.which(binary_name)
        if path is None or not os.access(path, os.X_OK):
            raise FileNotFoundError(f"Executable '{binary_name}' not found in PATH")
        return path

    def __init__(
        self,
        config_path: str = DEFAULT_CONFIG_PATH,
        verbose: bool = False,
        container_name: str = DEFAULT_CONTAINER_NAME,
    ) -> None:
        """Initialize the QmController class.

        Args:
            config_path: Path to the container configuration file
            verbose: Enable verbose logging to stderr for debugging
            container_name: Name of the container to interact with
        """
        self.config_path: str = config_path  # Path to container config file
        self.container: str = container_name  # Target container name
        self.verbose: bool = verbose  # Verbose logging flag
        self.output_config: OutputConfig = OutputConfig()  # Output formatting configuration

    def _log_path(self, action: str, path: str) -> None:
        """Log the action being performed on a path if verbose is enabled.

        Args:
            action: Description of the action being performed (e.g., "Reading", "Writing")
            path: File system path being acted upon
        """
        if self.verbose:
            print(f"[verbose] {action}: {path}", file=sys.stderr)

    def _run_subprocess(self, cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess:
        """Safely run a subprocess command.

        Args:
            cmd (List[str]): Command to run (must be a list of args, not a string).
            **kwargs: Additional arguments to pass to subprocess.run.

        Returns:
            subprocess.CompletedProcess: The completed process result.

        Raises:
            TypeError: If cmd is not a list.
            ValueError: If shell=True is passed in kwargs.
        """
        if not isinstance(cmd, list):
            raise TypeError("Command must be a list, not a string")
        if not all(isinstance(c, str) for c in cmd):
            raise TypeError("All command arguments must be strings")
        if kwargs.get("shell", False):
            raise ValueError("shell=True is forbidden for security reasons")

        defaults = {
            "capture_output": True,
            "text": True,
            "check": False,
        }

        options = kwargs if kwargs else defaults
        try:
            result = subprocess.run(    # nosec B603
                cmd,
                **options,
            )
            return result
        except Exception as e:
            raise RuntimeError(f"subprocess.run failed: {e}") from e

    def _print_error_and_exit(self, error: QmError) -> None:
        """Print error and exit - centralized error handling.

        This method provides consistent error handling across all public methods.
        It formats the error message and exits with the appropriate code.

        Args:
            error: The error object to handle and display
        """
        if isinstance(error, QmError):
            self._print_output({"Error": str(error)})
            exit(error.exit_code)  # Use the specific exit code from the error
        else:
            self._print_output({"Error": str(error)})
            exit(1)  # Default exit code for unexpected errors

    def _validate_path_exists(self, path: str) -> None:
        """Check if a path exists on the filesystem.

        Args:
            path: File system path to validate

        Raises:
            ConfigNotFoundError: If the path does not exist
        """
        if not os.path.exists(path):
            raise ConfigNotFoundError(path)

    def _validate_container_exists(self) -> None:
        """Check if the target container exists and is accessible.

        Raises:
            ContainerNotFoundError: If the container is not found or not running
        """
        if not self._container_exists(self.container):
            raise ContainerNotFoundError(self.container)

    def _validate_devices_specified(self, devices: list[str]) -> None:
        """Validate that at least one device is specified for operations.

        Args:
            devices: List of device paths to validate

        Raises:
            ValidationError: If no devices are provided
        """
        if not devices:
            raise ValidationError(
                "No devices specified in the container config. "
                "Please add 'AddDevice=' entries to the config file."
            )

    def _validate_command_provided(self, command: list[str], context: str = "") -> None:
        """Validate that a command is provided for execution.

        Args:
            command: List of command components to validate
            context: Additional context for error messages

        Raises:
            ValidationError: If no command is provided
        """
        if not command:
            context_msg = f" {context}" if context else ""
            raise ValidationError(f"No command provided{context_msg}.")

    def _validate_paths_for_cp(self, paths: list[str]) -> tuple[str, str]:
        """Validate and extract source and destination paths for copy operations.

        Ensures exactly two paths are provided and that exactly one contains
        the container prefix (container_name:).

        Args:
            paths: List of paths for copy operation

        Returns:
            Tuple of (source_path, destination_path)

        Raises:
            ValidationError: If paths are malformed or missing container prefix
        """
        if not paths or len(paths) != 2:
            raise ValidationError(
                "Please provide source and destination paths."
            )

        src, dst = paths
        container_prefix = f"{self.container}:"
        # Use XOR to ensure exactly one path has container prefix
        if not ((container_prefix in src) ^ (container_prefix in dst)):
            raise ValidationError(
                f"Provide `{self.container}:` only in source or destination"
            )

        return src, dst

    def _validate_exec_command(self, command: list[str]) -> tuple[str, list[str]]:
        """Validate command for nested container execution and extract components.

        Args:
            command: List containing container name and command arguments

        Returns:
            Tuple of (container_name, command_arguments)

        Raises:
            ValidationError: If command format is invalid
        """
        self._validate_command_provided(command, "to execute in container")

        if len(command) < 2:
            raise ValidationError("No command provided to execute.")
        return command[0], command[1:]  # Split container name from command args

    def _container_exists(self, name: str) -> bool:
        """Check if a podman container with the given name exists.

        Uses 'podman container exists' command to verify container availability.

        Args:
            name: Container name to check

        Returns:
            True if container exists and is accessible, False otherwise

        Raises:
            QmError: If the podman command fails unexpectedly
        """
        try:
            command = ["podman", "container", "exists", name]
            result = self._run_subprocess(
                command,
                stdout=subprocess.DEVNULL,  # overrides defaults
                stderr=subprocess.DEVNULL,  # overrides defaults
            )
            return result.returncode == 0  # 0 = exists, 1 = doesn't exist
        except Exception as e:
            raise QmError(str(e)) from e

    def _check_subprocess_result(self, result: subprocess.CompletedProcess, context: str, command: list[str]) -> None:
        """Check subprocess result and raise appropriate errors.

        Analyzes the result of a subprocess execution and raises specific
        exceptions based on the error conditions detected.

        Args:
            result: Completed subprocess result to analyze
            context: Description of the operation for error messages
            command: Original command that was executed

        Raises:
            CommandNotFoundError: If command was not found in container
            QmError: For other execution failures or empty output
        """
        # Check for command not found error
        if "command not found" in result.stderr.lower():
            cmd = command or ["unknown"]
            raise CommandNotFoundError(cmd, self.container)

        # Check for non-zero exit codes
        if result.returncode != 0:
            raise QmError(
                f"{context} Return code: {result.returncode}, "
                f"stderr: {result.stderr.strip()}"
            )

        # Check for empty output (might indicate a problem)
        if not result.stdout.strip():
            raise QmError(f"{context} No output returned.")

    def _extract_devices_from_config(self) -> list[str]:
        """Extract device paths from config file."""
        devices = []
        for line in self._read_config_lines(ADD_DEVICE_PREFIX):
            # Extract path after "AddDevice=" and remove leading "-" if present
            path = line.split("=", 1)[1].lstrip("-").strip()
            devices.append(path)
        return devices

    def _run_command_for_each_device(self, devices, base_command):
        """Run a command for each device in the container.

        Args:
            devices (list): List of device paths to test
            base_command (list): Base command to run (e.g., ["test", "-e"])

        Returns:
            dict: Device path -> success boolean mapping
        """
        results = {}
        for device in devices:
            command = base_command + [device]
            full_command = PODMAN_EXEC + [self.container] + command
            result = self._run_subprocess(
                full_command,
                stdout=subprocess.DEVNULL,  # overrides defaults
                stderr=subprocess.DEVNULL,  # overrides defaults
            )
            results[device] = result.returncode == 0
        return results

    def _print_output(self, data: dict) -> None:
        """Print data as either plain text or JSON.

        Args:
            data (dict or any): The data to print.
        """
        if not isinstance(data, dict):
            data = {"Output": data}

        if self.output_config.output_json:
            self._print_json_output(data)
        else:
            self._print_text_output(data)

    def _print_json_output(self, data: dict) -> None:
        """Print data as JSON."""
        print(json.dumps(
            data,
            indent=DEFAULT_JSON_INDENT if self.output_config.pretty else None
        ))

    def _print_text_output(self, data: dict) -> None:
        """Print data as formatted text."""
        if "Error" in data:
            self._print_error_output(data)
        elif self._is_boolean_status_data(data):
            self._print_boolean_output(data)
        else:
            self._print_general_output(data)

    def _print_error_output(self, data: dict) -> None:
        """Print error output to stderr."""
        print(data["Error"], file=sys.stderr)

    def _print_boolean_output(self, data: dict) -> None:
        """Print boolean status output."""
        for key, value in data.items():
            status = "present in QM" if value else "missing in QM"
            print(f"{key}: {status}")

    def _print_general_output(self, data: dict) -> None:
        """Print general key-value output."""
        for key, value in data.items():
            if isinstance(value, dict):
                print(f"{key}:")
                for sub_key, sub_val in value.items():
                    print(f"  {sub_key}: {sub_val}")
            else:
                print(f"{key}: {value}")

    def _is_boolean_status_data(self, data: dict) -> bool:
        """Check if data contains only boolean values."""
        return all(isinstance(v, bool) for v in data.values())

    def _verify_devices_existence(self) -> None:
        """Verify that devices specified in the config exist on the system."""
        self._log_path("Reading", self.config_path)
        devices = self._extract_devices_from_config()

        self._validate_devices_specified(devices)

        base_command = ["test", "-e"]
        results = self._run_command_for_each_device(devices, base_command)

        self._print_output(results)

    def _run_show_command_func(self, show_command_func: Callable) -> None:
        """Run a command and print its output.

        Args:
            show_command_func (callable): The function to run.
        """
        try:
            show_command_func()
        except Exception as e:
            self._print_error_and_exit(
                QmError(f"Failed to execute command: {str(e)}")
            )

    class HandleLineInContent:
        """Helper class to parse a single line of INI-style content."""

        def __init__(self, parsed: dict, current_section: Optional[str] = None) -> None:
            """Initialize the handler for a line in the content."""
            self.parsed = parsed
            self.current_section = current_section

        def handle(self, stripped_line: str) -> None:
            """Handle a line in the content based on its format."""
            if not stripped_line or stripped_line.startswith("#"):
                return
            if stripped_line.startswith("[") and stripped_line.endswith("]"):
                self.current_section = stripped_line[1:-1]
                self.parsed[self.current_section] = {}
            elif "=" in stripped_line and self.current_section:
                key, value = map(str.strip, stripped_line.split("=", 1))
                self.parsed[self.current_section][key] = value
            elif self.current_section:
                self.parsed[self.current_section][stripped_line] = True

        def get_parsed(self) -> dict:
            """Return the parsed content."""
            return self.parsed

    def parse_to_dict(self, content: str) -> dict:
        """Parse an INI-style string content into a dictionary.

        Args:
            content (str): The string content to parse.

        Returns:
            dict: A dictionary representing the parsed content.
        """
        handle_line_in_context = self.HandleLineInContent(defaultdict(dict))

        for line in content.splitlines():
            handle_line_in_context.handle(line.strip())
        return handle_line_in_context.get_parsed()

    def show_all(self, output_json: bool = False, pretty: bool = True) -> None:
        """Display the content of the container configuration file.

        Args:
            output_json (bool): If True, format the output as JSON.
            pretty (bool): If True and output_json is True, pretty-print
                the JSON.
        """
        self._configure_output(output_json, pretty)
        all_show_commands_functions = [
            self.show_container,
            self.show_unix_sockets,
            self.show_shared_memory,
            self.show_resources,
            self.show_available_devices,
            self.show_namespaces,
        ]

        for func in all_show_commands_functions:
            self._run_show_command_func(
                func
            )

    def show_container(self, output_json: bool = False, pretty: bool = True) -> None:
        """Display the content of the container configuration file.

        Args:
            output_json (bool): If True, format the output as JSON.
            pretty (bool): If True and output_json is True, pretty-print
                the JSON.
        """
        self._configure_output(output_json, pretty)

        try:
            self._validate_path_exists(self.config_path)
            self._log_path("Reading", self.config_path)

            with open(self.config_path, "r") as file:
                content = file.read()

            if self.output_config.output_json:
                parsed = self.parse_to_dict(content)
                self._print_output(
                    {"path": self.config_path, "sections": parsed}
                )
            else:
                print(content, end="")
        except Exception as e:
            self._print_error_and_exit(QmError(str(e)))

    def show_unix_sockets(self, output_json: bool = False, pretty: bool = True) -> None:
        """Show active UNIX domain sockets inside the container using 'ss'.

        Args:
            output_json (bool): If True, format the output as JSON.
            pretty (bool): If True and output_json is True, pretty-print
                the JSON.
        """
        self._configure_output(output_json, pretty)
        try:
            result = self._run_podman_exec(
                ["ss", "-xl"],
                "Failed to retrieve UNIX domain sockets with 'ss -xl'"
            )

            self._print_output(
                {"UNIX domain sockets": result.stdout.strip()}
            )

        except Exception as e:
            self._print_error_and_exit(QmError(str(e)))

    def show_shared_memory(self, output_json: bool = False, pretty: bool = True) -> None:
        """Show shared memory segments in the container using 'ipcs'.

        Args:
            output_json (bool): If True, format the output as JSON.
            pretty (bool): If True and output_json is True, pretty-print
                the JSON.
        """
        self.exec_in_container(["ipcs"], output_json=output_json,
                               pretty=pretty)

    def show_resources(self, output_json: bool = False, pretty: bool = True) -> None:
        """Stream live resource usage for qm.service using systemd-cgtop.

        Note:
            This method runs until interrupted with Ctrl+C. It does not
            support JSON output directly due to its streaming nature.

        Args:
            output_json (bool): This parameter is ignored.
            pretty (bool): This parameter is ignored.
        """
        self._configure_output(output_json, pretty)
        try:
            print(
                "[INFO] Starting systemd-cgtop stream for qm.service. "
                "Press Ctrl+C to exit.\n"
            )
            pid, fd = pty.fork()
            if pid == 0:
                cmd_path = self.find_executable("systemd-cgtop")
                # Safe: cmd_path is resolved with find_executable() and args are hardcoded
                os.execvp(cmd_path, ["systemd-cgtop", "--batch", "qm.service"]
                ) # nosec B606
            else:
                while True:
                    try:
                        output = os.read(fd, 1024).decode()
                        print(output, end="")
                    except OSError:
                        break
        except KeyboardInterrupt:
            msg = "KeyboardInterrupt: Exiting systemd-cgtop stream."
            self._print_error_and_exit(QmError(msg, exit_code=0))
        except Exception as e:
            self._print_error_and_exit(QmError(str(e)))

    def show_available_devices(self, output_json: bool = False, pretty: bool = True) -> None:
        """Verify device existence specified in the container config.

        Args:
            output_json (bool): If True, format the output as JSON.
            pretty (bool): If True and output_json is True, pretty-print
                the JSON.
        """
        self._configure_output(output_json, pretty)

        try:
            self._validate_path_exists(self.config_path)
            self._validate_container_exists()
            self._verify_devices_existence()
        except Exception as e:
            self._print_error_and_exit(QmError(str(e)))

    def show_namespaces(self, output_json: bool = False, pretty: bool = True) -> None:
        """Show namespace information inside the container using 'lsns'.

        Args:
            output_json (bool): If True, format the output as JSON.
            pretty (bool): If True and output_json is True, pretty-print
                the JSON.
        """
        self._configure_output(output_json, pretty)
        try:
            result = self._run_podman_exec(
                ["lsns"],
                "Failed to retrieve namespace info using 'lsns'"
            )

            self._print_output(
                {"Namespaces": result.stdout.strip()}
            )

        except Exception as e:
            self._print_error_and_exit(QmError(str(e)))

    def exec_in_container(self, command: list[str], output_json: bool = False, pretty: bool = True) -> None:
        """Execute a command inside the primary 'qm' container.

        Args:
            command (list): The command and its arguments to execute.
            output_json (bool): If True, format the output as JSON.
            pretty (bool): If True and output_json is True, pretty-print
                the JSON.
        """
        self._configure_output(output_json, pretty)

        try:
            self._validate_container_exists()
            self._validate_command_provided(
                command,
                "No command provided to execute in the container."
            )
            result = self._run_podman_exec(
                command,
                f"Failed to execute command in container '{self.container}'"
            )

            self._print_output(
                {"output": result.stdout.strip()}
            )

        except QmError as e:
            # Handle empty output gracefully, but re-raise other QmErrors
            if "No output returned" in str(e):
                return  # Silent success for commands with no output
            else:
                self._print_error_and_exit(e)
        except Exception as e:
            self._print_error_and_exit(QmError(str(e)))

    def copy_in_container(self, paths: list[str], output_json: bool = False, pretty: bool = True) -> None:
        """Copy files or directories between the host and the container.

        Args:
            paths (list): A list with the source and destination paths.
            output_json (bool): If True, format the output as JSON.
            pretty (bool): If True and output_json is True, pretty-print
                the JSON.
        """
        self._configure_output(output_json, pretty)

        try:
            self._validate_container_exists()
            src, dst = self._validate_paths_for_cp(paths)
            full_command = PODMAN_CP + [src, dst]
            result = self._run_subprocess(full_command)
            if result.returncode != 0:
                raise RuntimeError(result.stderr or "Copy operation failed")

        except Exception as e:
            self._print_error_and_exit(QmError(str(e)))

    def execin_in_container(self, command: list[str], output_json: bool = False, pretty: bool = True) -> None:
        """Execute a command in a nested container inside the 'qm' container.

        Args:
            command (list): A list where the first element is the nested
                container name and the rest is the command to execute.
            output_json (bool): If True, format the output as JSON.
            pretty (bool): If True and output_json is True, pretty-print
                the JSON.
        """
        self._configure_output(output_json, pretty)

        try:
            self._validate_container_exists()
            container_name, command_args = (
                self._validate_exec_command(command)
            )
            cmd_list = [
                *PODMAN_EXEC, self.container,
                *PODMAN_EXEC, container_name,
                *command_args
            ]
            result = self._run_subprocess(cmd_list)

            if result.returncode != 0:
                cmd_str = " ".join(command)
                err_msg = (
                    f"Command '{cmd_str}' failed with Error: "
                    f"{result.stderr.strip()}"
                )
                raise RuntimeError(err_msg)

            self._print_output(
                {"output": result.stdout.strip()}
            )

        except Exception as e:
            self._print_error_and_exit(QmError(str(e)))

    def _configure_output(self, output_json: bool = False, pretty: bool = True) -> None:
        """Configure output settings for this operation."""
        self.output_config = OutputConfig(output_json, pretty)

    def _run_podman_exec(self, command: list[str], context: str = "Execute command") -> subprocess.CompletedProcess:
        """Run podman exec with standard error handling.

        Args:
            command (list): Command to execute in container
            context (str): Context description for error messages

        Returns:
            subprocess.CompletedProcess: The result of the subprocess run
        """
        full_command = PODMAN_EXEC + [self.container] + command
        result = self._run_subprocess(full_command)

        self._check_subprocess_result(result, context, command)
        return result

    def _read_config_lines(self, filter_prefix: Optional[str] = None) -> Generator[str, None, None]:
        """Read and filter config file lines.

        Args:
            filter_prefix (str, optional): Only yield lines starting with
                this prefix

        Yields:
            str: Stripped lines from the config file
        """
        self._validate_path_exists(self.config_path)
        self._log_path("Reading", self.config_path)

        with open(self.config_path, "r") as file:
            for line in file:
                stripped = line.strip()
                if not stripped or stripped.startswith(COMMENT_PREFIX):
                    continue
                if not filter_prefix or stripped.startswith(filter_prefix):
                    yield stripped


class ArgumentParserWithDefaults(argparse.ArgumentParser):
    """Subclass ArgumentParser to enhance help messages.

    This class automatically adds default values to the help text of
    arguments.
    """

    def add_argument(
        self, *args, help: Optional[str] = None, default: Optional[Any] = None, completer: Optional[Any] = None, **kwargs
    ) -> argparse.Action:
        """Add an argument and automatically format the help message.

        This method includes the default value in the help text.

        Args:
            *args: Positional arguments for the argument.
            help (str): The help text for the argument.
            default: The default value for the argument.
            completer: A completer for shell autocompletion.
            **kwargs: Additional keyword arguments.

        Returns:
            The Action object created by the parent class.
        """
        if (
            default is not None
            and args[0] != "-h"
            and help is not None
            and help != "==SUPPRESS=="
        ):
            kwargs["help"] = (f"{help} (default: {default})")
        action = super().add_argument(*args, **kwargs)
        if completer is not None:
            # Set completer for shell autocompletion if available
            action.completer = completer  # type: ignore
        return action


def create_subcommand(
    subparsers: argparse._SubParsersAction, name: str, help_text: str, default_func: Callable, args_config: Optional[list[dict[str, Any]]] = None, epilog: Optional[str] = None
) -> argparse.ArgumentParser:
    """Create and configure a subcommand parser.

    Args:
        subparsers: The subparser object from the main parser.
        name (str): The name of the subcommand.
        help_text (str): The help string for the subcommand.
        default_func (callable): The function to be called when this
            subcommand is used.
        args_config (list, optional): List of argument configurations.
        epilog (str, optional): Additional text to display after the help.

    Returns:
        argparse.ArgumentParser: The created subparser.
    """
    args_config = args_config or []
    parser = subparsers.add_parser(name, help=help_text, epilog=epilog, formatter_class=argparse.RawTextHelpFormatter)

    for arg_cfg in args_config:
        arg_names = arg_cfg.pop('name')
        parser.add_argument(*arg_names, **arg_cfg)

    parser.set_defaults(func=default_func)
    return parser


def perror(*args: Any, **kwargs: Any) -> None:
    """Print a message to the standard error stream."""
    print(*args, file=sys.stderr, **kwargs)


def handle_error(e: Exception, exit_code: int) -> None:
    """Print an error message and exit the script.

    Args:
        e (Exception): The exception object caught.
        exit_code (int): The exit code to use when exiting the script.
    """
    error_message = str(e).strip("'\"")
    perror(f"Error: {error_message}")
    sys.exit(exit_code)


def run_command_with_error_handling(args: argparse.Namespace, controller: QmController, parser: argparse.ArgumentParser) -> None:
    """Execute the subcommand with centralized error handling.

    Args:
        args: The parsed command-line arguments.
        controller: An instance of the QmController class.
        parser: The argparse parser object, used for printing usage.
    """
    try:
        if not args.subcommand:
            parser.print_usage()
            perror("Error: requires a subcommand")
            sys.exit(errno.EINVAL)
        args.func(args, controller)
    except QmError as e:
        handle_error(e, e.exit_code)
    except KeyError as e:
        handle_error(e, 1)
    except NotImplementedError as e:
        handle_error(e, errno.ENOTSUP)
    except subprocess.CalledProcessError as e:
        handle_error(e, e.returncode)
    except KeyboardInterrupt:
        sys.exit(0)
    except (IndexError, ConnectionError, ValueError) as e:
        handle_error(e, errno.EINVAL)
    except IOError as e:
        handle_error(e, errno.EIO)


def create_argument_parser(description: str) -> argparse.ArgumentParser:
    """Create and configure the argument parser for the CLI.

    Args:
        description (str): The description text for the CLI tool.

    Returns:
        An initialized ArgumentParser for the CLI.
    """
    parser = ArgumentParserWithDefaults(
        prog="qmctl",
        description=description,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    configure_arguments(parser)
    return parser


def configure_arguments(parser: argparse.ArgumentParser) -> None:
    """Configure the base command-line arguments for the parser.

    Args:
        parser (argparse.ArgumentParser): The main argument parser.
    """
    verbosity_group = parser.add_mutually_exclusive_group()
    verbosity_group.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose output."
    )


def parse_arguments(parser: argparse.ArgumentParser) -> argparse.Namespace:
    """Parse command line arguments.

    Args:
        parser (argparse.ArgumentParser): The argument parser.

    Returns:
        The parsed arguments object.
    """
    return parser.parse_args()


def post_parse_setup(args: argparse.Namespace) -> None:
    """Perform additional setup after parsing arguments.

    Args:
        args: The parsed command-line arguments.
    """
    pass


def init_cli() -> tuple[argparse.ArgumentParser, argparse.Namespace]:
    """Initialize the QmController CLI, parse arguments, set up environment.

    Returns:
        A tuple containing the configured parser and the parsed arguments.
    """
    description = get_description()
    parser = create_argument_parser(description)
    configure_subcommands(parser)
    args = parse_arguments(parser)
    post_parse_setup(args)
    return parser, args


def get_description() -> str:
    """Return the description of the QmController tool.

    Returns:
        A string containing the tool's description.
    """
    return """QmCTL: Command Line Interface for QM Container

Examples:
  # Show container configuration
  qmctl show
  qmctl show container
  # Show specific information

  qmctl show available-devices
  qmctl show unix-domain-sockets
  qmctl show shared-memory
  qmctl show resources
  qmctl show namespaces
  qmctl show all

  # Execute commands in QM container
  qmctl exec ls -la /tmp
  qmctl exec cat /etc/hostname
  qmctl exec ps aux

  # Execute commands in nested container
  qmctl execin radio bash -c "echo 'Hello from radio container'"
  qmctl execin rear_camera ps aux

  # Copy files between host and container named qm
  qmctl cp /host/file.txt qm:/tmp/file.txt
  qmctl cp qm:/tmp/data.log /host/backup/data.log

  # Output as JSON
  qmctl show --json
  qmctl exec --json hostname
  qmctl cp --json /host/file.txt qm:/tmp/file.txt"""


def configure_subcommands(parser: argparse.ArgumentParser) -> None:
    """Add subcommand parsers to the main argument parser.

    Args:
        parser (argparse.ArgumentParser): The main argument parser.
    """
    subparsers = parser.add_subparsers(dest="subcommand", required=True)
    subparsers.required = False
    init_show_subcommand(subparsers)
    init_exec_subcommand(subparsers)
    init_execin_subcommand(subparsers)
    init_cp_subcommand(subparsers)


def init_show_subcommand(subparsers: argparse._SubParsersAction) -> None    :
    """Initialize the 'show' subcommand for displaying container info.

    Args:
        subparsers: The subparser object from the main parser.
    """
    name = "show"
    help_text = "Show information about the QM container"
    default_func = handle_show_command
    epilog = """Examples:
  # Show container configuration (default)
  qmctl show
  qmctl show container

  # Show available devices
  qmctl show available-devices

  # Show Unix domain sockets
  qmctl show unix-domain-sockets

  # Show shared memory segments
  qmctl show shared-memory

  # Show resource usage (interactive)
  qmctl show resources

  # Show namespaces
  qmctl show namespaces

  # Show all information
  qmctl show all

  # Output as JSON
  qmctl show --json
  qmctl show available-devices --json"""
    args_config = [
        {
            'name': ['show_command_topic'],
            'nargs': '?',
            'default': 'container',
            'choices': [
                "container",
                "unix-domain-sockets",
                "shared-memory",
                "resources",
                "available-devices",
                "namespaces",
                "all",
            ],
            'help': "What to show"
        },
        {
            'name': ['--json'],
            'action': 'store_true',
            'help': "Output as JSON"
        }
    ]
    create_subcommand(
        subparsers, name, help_text, default_func, args_config, epilog
    )


def init_exec_subcommand(subparsers: argparse._SubParsersAction) -> None:
    """Initialize the 'exec' subcommand for running commands.

    Args:
        subparsers: The subparser object from the main parser.
    """
    name = "exec"
    help_text = "Run command inside QM container"
    default_func = handle_exec_command
    epilog = """Examples:
  # List files in /tmp directory
  qmctl exec ls -la /tmp

  # Check container hostname
  qmctl exec hostname

  # View running processes
  qmctl exec ps aux

  # Check system information
  qmctl exec uname -a

  # Read file contents
  qmctl exec cat /etc/os-release

  # Output as JSON
  qmctl exec --json hostname"""
    args_config = [
        {
            'name': ['cmd'],
            'nargs': argparse.REMAINDER,
            'help': "Command to execute"
        },
        {
            'name': ['--json'],
            'action': 'store_true',
            'help': "Output as JSON"
        }
    ]
    create_subcommand(
        subparsers, name, help_text, default_func, args_config, epilog
    )


def init_execin_subcommand(subparsers: argparse._SubParsersAction) -> None:
    """Initialize the 'execin' subcommand for nested execution.

    Args:
        subparsers: The subparser object from the main parser.
    """
    name = "execin"
    help_text = "Run command inside QM container in a nested container"
    default_func = handle_execin_command
    epilog = """Examples:
  # Execute command in radio container
  qmctl execin radio ps aux

  # Execute command in rear_camera container
  qmctl execin rear_camera ls -la /tmp

  # Run interactive bash in nested container
  qmctl execin radio bash -c "echo 'Hello from radio container'"

  # Check hostname in nested container
  qmctl execin rear_camera hostname

  # Output as JSON
  qmctl execin --json radio hostname"""
    args_config = [
        {
            'name': ['cmd'],
            'nargs': argparse.REMAINDER,
            'help': "Command to execute in the nested container"
        },
        {
            'name': ['--json'],
            'action': 'store_true',
            'help': "Output as JSON"
        }
    ]
    create_subcommand(
        subparsers, name, help_text, default_func, args_config, epilog
    )


def init_cp_subcommand(subparsers: argparse._SubParsersAction) -> None:
    """Initialize the 'cp' subcommand for copying files.

    Args:
        subparsers: The subparser object from the main parser.
    """
    name = "cp"
    help_text = "Copy files between host and QM container"
    default_func = handle_cp_command
    epilog = """Examples:
  # Copy file from host to container named qm
  qmctl cp /host/file.txt qm:/tmp/file.txt

  # Copy file from container to host
  qmctl cp qm:/tmp/data.log /host/backup/data.log

  # Copy directory from host to container
  qmctl cp /host/config/ qm:/etc/myapp/

  # Copy with different filename
  qmctl cp /host/source.conf qm:/etc/target.conf

  # Output as JSON
  qmctl cp --json /host/file.txt qm:/tmp/file.txt"""
    args_config = [
        {
            'name': ['paths'],
            'nargs': 2,
            'help': ("Source and destination paths (e.g., "
                     "/path/to/file /path/in/container)")
        },
        {
            'name': ['--json'],
            'action': 'store_true',
            'help': "Output as JSON"
        }
    ]
    create_subcommand(
        subparsers, name, help_text, default_func, args_config, epilog
    )


def handle_show_command(args: argparse.Namespace, controller: QmController) -> None:
    """Handle the logic for the 'show' subcommand.

    Args:
        args: The parsed command-line arguments.
        controller: An instance of the QmController class.
    """
    all_show_commands = {
        "all": controller.show_all,
        "container": controller.show_container,
        "unix-domain-sockets": controller.show_unix_sockets,
        "shared-memory": controller.show_shared_memory,
        "resources": controller.show_resources,
        "available-devices": controller.show_available_devices,
        "namespaces": controller.show_namespaces,
    }

    command_to_execute = all_show_commands.get(
        args.show_command_topic,
        controller.show_container if args.show_command_topic is None else None)

    if command_to_execute:
        command_to_execute(output_json=args.json, pretty=True)
    else:
        print(f"Error: Unknown show command '{args.show_command_topic}'.")


def handle_exec_command(args: argparse.Namespace, controller: QmController) -> None:
    """Handle the logic for the 'exec' subcommand.

    Args:
        args: The parsed command-line arguments.
        controller: An instance of the QmController class.
    """
    controller.exec_in_container(
        command=args.cmd, output_json=args.json, pretty=True
    )


def handle_execin_command(args: argparse.Namespace, controller: QmController) -> None:
    """Handle the logic for the 'execin' subcommand.

    Args:
        args: The parsed command-line arguments.
        controller: An instance of the QmController class.
    """
    controller.execin_in_container(
        command=args.cmd, output_json=args.json, pretty=True
    )


def handle_cp_command(args: argparse.Namespace, controller: QmController) -> None:
    """Handle the logic for the 'cp' subcommand.

    Args:
        args: The parsed command-line arguments.
        controller: An instance of the QmController class.
    """
    controller.copy_in_container(
        paths=args.paths, output_json=args.json, pretty=True
    )


def main() -> None:
    """Run the main qmctl command-line interface."""
    parser, args = init_cli()
    controller = QmController(verbose=args.verbose)

    if importlib.util.find_spec("argcomplete") is not None:
        import argcomplete
        try:
            argcomplete.autocomplete(parser)
        except Exception as e:
            print(f"[WARNING] argcomplete failed: {e}", file=sys.stderr)
            pass

    run_command_with_error_handling(args, controller, parser)

