#!/usr/bin/env python3
"""Comprehensive pytest tests for qmctl CLI binary."""

import json
import errno
import os
import tempfile
from unittest.mock import Mock, patch

import pytest
# Import the qmctl module by adding the directory to sys.path
from qmctl import qmctl  # this is qmctl/qmctl


# Import classes and functions from qmctl
QmController = qmctl.QmController
QmError = qmctl.QmError
ConfigNotFoundError = qmctl.ConfigNotFoundError
ContainerNotFoundError = qmctl.ContainerNotFoundError
CommandNotFoundError = qmctl.CommandNotFoundError
ValidationError = qmctl.ValidationError
OutputConfig = qmctl.OutputConfig
create_argument_parser = qmctl.create_argument_parser
main = qmctl.main
handle_show_command = qmctl.handle_show_command
handle_exec_command = qmctl.handle_exec_command
handle_execin_command = qmctl.handle_execin_command
handle_cp_command = qmctl.handle_cp_command
DEFAULT_CONFIG_PATH = qmctl.DEFAULT_CONFIG_PATH
DEFAULT_CONTAINER_NAME = qmctl.DEFAULT_CONTAINER_NAME


@pytest.fixture
def mock_config_content():
    """Sample container configuration content for testing."""
    return """[Container]
Image=localhost/qm:latest
Exec=/bin/bash
Environment=DISPLAY=:0
Network=host
Volume=/tmp:/tmp:rw

[Service]
Restart=always
"""


@pytest.fixture
def temp_config_file(mock_config_content):
    """Create a temporary configuration file for testing."""
    with tempfile.NamedTemporaryFile(
        mode='w', suffix='.container', delete=False
    ) as f:
        f.write(mock_config_content)
        f.flush()
        yield f.name
    os.unlink(f.name)


@pytest.fixture
def qm_controller(temp_config_file):
    """Create a QmController instance with temporary config."""
    return QmController(
        config_path=temp_config_file,
        verbose=False,
        container_name="test-qm"
    )


@pytest.fixture
def qm_controller_verbose(temp_config_file):
    """Create a verbose QmController instance."""
    return QmController(
        config_path=temp_config_file,
        verbose=True,
        container_name="test-qm"
    )


@pytest.fixture
def mock_subprocess_run():
    """Mock subprocess.run for testing."""
    with patch('qmctl.qmctl.subprocess.run') as mock:
        yield mock


@pytest.fixture
def mock_container_exists():
    """Mock container existence check."""
    with patch.object(QmController, '_container_exists') as mock:
        mock.return_value = True
        yield mock


@pytest.fixture
def mock_path_exists():
    """Mock os.path.exists for config file."""
    with patch('qmctl.qmctl.os.path.exists') as mock:
        mock.return_value = True
        yield mock


@pytest.fixture
def sample_cli_args():
    """Sample command line arguments for testing."""
    class MockArgs:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

    return {
        'show_container': MockArgs(
            show_command_topic='container',
            json=False,
            subcommand='show'
        ),
        'show_all_json': MockArgs(
            show_command_topic='all',
            json=True,
            subcommand='show'
        ),
        'exec_ls': MockArgs(
            cmd=['ls', '-la', '/tmp'],
            json=False,
            subcommand='exec'
        ),
        'execin_radio': MockArgs(
            cmd=['radio', 'ps', 'aux'],
            json=False,
            subcommand='execin'
        ),
        'cp_files': MockArgs(
            paths=['/host/file.txt', 'qm:/tmp/file.txt'],
            json=False,
            subcommand='cp'
        )
    }


class TestQmError:
    """Test custom exception classes."""

    def test_qm_error_creation(self):
        """Test QmError creation with message and exit code."""
        error = QmError("Test error", QmError.EXIT_CODE_TEST_CUSTOM)
        assert str(error) == "Test error"
        assert error.exit_code == QmError.EXIT_CODE_TEST_CUSTOM

    def test_qm_error_default_exit_code(self):
        """Test QmError with default exit code."""
        error = QmError("Test error")
        assert error.exit_code == QmError.EXIT_CODE_GENERAL_ERROR

    def test_config_not_found_error(self):
        """Test ConfigNotFoundError exception."""
        error = ConfigNotFoundError("/path/to/config")
        assert "Configuration file /path/to/config not found" in str(error)
        assert error.exit_code == QmError.EXIT_CODE_FILE_NOT_FOUND

    def test_container_not_found_error(self):
        """Test ContainerNotFoundError exception."""
        error = ContainerNotFoundError("test-container")
        assert "Container 'test-container' does not exist" in str(error)
        assert error.exit_code == QmError.EXIT_COMMAND_NOT_FOUND

    def test_command_not_found_error(self):
        """Test CommandNotFoundError exception."""
        error = CommandNotFoundError(["unknown", "command"], "test-container")
        assert (
            "Command 'unknown command' not found in container 'test-container'"
            in str(error)
        )
        assert error.exit_code == QmError.EXIT_COMMAND_NOT_FOUND

    def test_validation_error(self):
        """Test ValidationError exception."""
        error = ValidationError("Invalid input")
        assert str(error) == "Invalid input"
        assert error.exit_code == QmError.EXIT_CODE_INVALID_ARGUMENT


class TestOutputConfig:
    """Test OutputConfig class."""

    def test_output_config_defaults(self):
        """Test OutputConfig with default values."""
        config = OutputConfig()
        assert config.output_json is False
        assert config.pretty is True

    def test_output_config_custom(self):
        """Test OutputConfig with custom values."""
        config = OutputConfig(output_json=True, pretty=False)
        assert config.output_json is True
        assert config.pretty is False


class TestQmController:
    """Test QmController class functionality."""

    def test_qm_controller_initialization(self, temp_config_file):
        """Test QmController initialization with custom parameters."""
        controller = QmController(
            config_path=temp_config_file,
            verbose=True,
            container_name="custom-qm"
        )

        assert controller.config_path == temp_config_file
        assert controller.container == "custom-qm"
        assert controller.verbose is True
        assert isinstance(controller.output_config, OutputConfig)

    def test_qm_controller_defaults(self):
        """Test QmController with default values."""
        controller = QmController()

        assert controller.config_path == DEFAULT_CONFIG_PATH
        assert controller.container == DEFAULT_CONTAINER_NAME
        assert controller.verbose is False

    @patch('qmctl.qmctl.sys.stderr')
    def test_log_path_verbose(self, mock_stderr, qm_controller_verbose):
        """Test verbose logging functionality."""
        qm_controller_verbose._log_path("Reading", "/test/path")
        mock_stderr.write.assert_called()

    def test_log_path_not_verbose(self, qm_controller):
        """Test that logging is disabled when verbose=False."""
        with patch('qmctl.qmctl.sys.stderr') as mock_stderr:
            qm_controller._log_path("Reading", "/test/path")
            mock_stderr.write.assert_not_called()

    def test_validate_path_exists_valid(self, qm_controller, mock_path_exists):
        """Test path validation with existing path."""
        qm_controller._validate_path_exists("/valid/path")
        # Should not raise exception

    def test_validate_path_exists_invalid(self, qm_controller):
        """Test path validation with non-existing path."""
        with patch('qmctl.qmctl.os.path.exists', return_value=False):
            with pytest.raises(ConfigNotFoundError):
                qm_controller._validate_path_exists("/invalid/path")

    def test_validate_container_exists_valid(
        self, qm_controller, mock_container_exists
    ):
        """Test container validation with existing container."""
        qm_controller._validate_container_exists()
        # Should not raise exception

    def test_validate_container_exists_invalid(self, qm_controller):
        """Test container validation with non-existing container."""
        with patch.object(
            qm_controller, '_container_exists', return_value=False
        ):
            with pytest.raises(ContainerNotFoundError):
                qm_controller._validate_container_exists()

    def test_validate_devices_specified_valid(self, qm_controller):
        """Test device validation with devices present."""
        qm_controller._validate_devices_specified(
            ["/dev/device1", "/dev/device2"]
        )
        # Should not raise exception

    def test_validate_devices_specified_empty(self, qm_controller):
        """Test device validation with no devices."""
        with pytest.raises(ValidationError) as exc_info:
            qm_controller._validate_devices_specified([])
        assert "No devices specified" in str(exc_info.value)

    def test_validate_command_provided_valid(self, qm_controller):
        """Test command validation with valid command."""
        qm_controller._validate_command_provided(["ls", "-la"])
        # Should not raise exception

    def test_validate_command_provided_empty(self, qm_controller):
        """Test command validation with empty command."""
        with pytest.raises(ValidationError) as exc_info:
            qm_controller._validate_command_provided([])
        assert "No command provided" in str(exc_info.value)

    def test_validate_paths_for_cp_valid(self, qm_controller):
        """Test cp path validation with valid paths."""
        src, dst = qm_controller._validate_paths_for_cp(
            ["/host/file", "test-qm:/container/file"]
        )
        assert src == "/host/file"
        assert dst == "test-qm:/container/file"

    def test_validate_paths_for_cp_invalid_count(self, qm_controller):
        """Test cp path validation with wrong number of paths."""
        with pytest.raises(ValidationError) as exc_info:
            qm_controller._validate_paths_for_cp(["/only/one/path"])
        assert "provide source and destination paths" in str(exc_info.value)

    def test_validate_paths_for_cp_invalid_prefix(self, qm_controller):
        """Test cp path validation with invalid container prefix."""
        with pytest.raises(ValidationError) as exc_info:
            qm_controller._validate_paths_for_cp(["/host/file", "/host/other"])
        assert (
            "Provide `test-qm:` only in source or destination"
            in str(exc_info.value)
        )

    def test_validate_exec_command_valid(self, qm_controller):
        """Test exec command validation with valid command."""
        name, args = qm_controller._validate_exec_command(
            ["container", "ls", "-la"]
        )
        assert name == "container"
        assert args == ["ls", "-la"]

    def test_validate_exec_command_invalid(self, qm_controller):
        """Test exec command validation with invalid command."""
        with pytest.raises(ValidationError):
            qm_controller._validate_exec_command(["only_one_arg"])

    def test_container_exists_true(self, qm_controller, mock_subprocess_run):
        """Test container existence check returning True."""
        mock_subprocess_run.return_value.returncode = 0
        assert qm_controller._container_exists("existing-container") is True

    def test_container_exists_false(self, qm_controller, mock_subprocess_run):
        """Test container existence check returning False."""
        mock_subprocess_run.return_value.returncode = 1
        assert (
            qm_controller._container_exists("non-existing-container") is False
        )

    def test_container_exists_exception(
        self, qm_controller, mock_subprocess_run
    ):
        """Test container existence check with exception."""
        mock_subprocess_run.side_effect = Exception("Test error")
        with pytest.raises(QmError):
            qm_controller._container_exists("test-container")

    def test_extract_devices_from_config_empty(self, qm_controller):
        """Test device extraction from config file with no devices."""
        devices = qm_controller._extract_devices_from_config()
        expected_devices = []
        assert devices == expected_devices

    def test_run_command_for_each_device(
        self, qm_controller, mock_subprocess_run
    ):
        """Test running commands for each device."""
        devices = ["/dev/device1", "/dev/device2"]
        base_command = ["test", "-e"]

        # Mock successful run for first device, failure for second
        mock_subprocess_run.side_effect = [
            Mock(returncode=0),
            Mock(returncode=1)
        ]

        results = qm_controller._run_command_for_each_device(
            devices, base_command
        )

        assert results == {"/dev/device1": True, "/dev/device2": False}
        assert mock_subprocess_run.call_count == 2

    def test_print_output_text_mode(self, qm_controller, capsys):
        """Test text output printing."""
        qm_controller.output_config.output_json = False
        qm_controller._print_output({"key": "value"})

        captured = capsys.readouterr()
        assert "key: value" in captured.out

    def test_print_output_json_mode(self, qm_controller, capsys):
        """Test JSON output printing."""
        qm_controller.output_config.output_json = True
        qm_controller._print_output({"key": "value"})

        captured = capsys.readouterr()
        output_data = json.loads(captured.out)
        assert output_data == {"key": "value"}

    def test_print_boolean_output(self, qm_controller, capsys):
        """Test boolean status output formatting."""
        qm_controller.output_config.output_json = False
        qm_controller._print_output(
            {"/dev/device1": True, "/dev/device2": False}
        )

        captured = capsys.readouterr()
        assert "present in QM" in captured.out
        assert "missing in QM" in captured.out

    def test_print_error_output(self, qm_controller, capsys):
        """Test error output to stderr."""
        qm_controller.output_config.output_json = False
        qm_controller._print_output({"Error": "Test error message"})

        captured = capsys.readouterr()
        assert "Test error message" in captured.err

    @patch('qmctl.qmctl.os.path.exists')
    def test_show_container_text(self, mock_exists, qm_controller, capsys):
        """Test show_container in text mode."""
        mock_exists.return_value = True
        qm_controller.show_container(output_json=False)

        captured = capsys.readouterr()
        assert "[Container]" in captured.out
        assert "Image=localhost/qm:latest" in captured.out

    @patch('qmctl.qmctl.os.path.exists')
    def test_show_container_json(self, mock_exists, qm_controller, capsys):
        """Test show_container in JSON mode."""
        mock_exists.return_value = True
        qm_controller.show_container(output_json=True)

        captured = capsys.readouterr()
        output_data = json.loads(captured.out)
        assert "path" in output_data
        assert "sections" in output_data
        assert "Container" in output_data["sections"]

    def test_show_container_file_not_found(self, qm_controller):
        """Test show_container with non-existing config file."""
        with patch('qmctl.qmctl.os.path.exists', return_value=False):
            with pytest.raises(SystemExit) as exc_info:
                qm_controller.show_container()
            assert exc_info.value.code == 1


class TestCLICommands:
    """Test CLI command handling functions."""

    def test_handle_show_command_container(
        self, sample_cli_args, qm_controller
    ):
        """Test show command for container."""
        args = sample_cli_args['show_container']

        with patch.object(qm_controller, 'show_container') as mock_show:
            handle_show_command(args, qm_controller)
            mock_show.assert_called_once_with(output_json=False, pretty=True)

    def test_handle_show_command_all_json(
        self, sample_cli_args, qm_controller
    ):
        """Test show all command with JSON output."""
        args = sample_cli_args['show_all_json']

        with patch.object(qm_controller, 'show_all') as mock_show:
            handle_show_command(args, qm_controller)
            mock_show.assert_called_once_with(output_json=True, pretty=True)

    def test_handle_exec_command(self, sample_cli_args, qm_controller):
        """Test exec command handling."""
        args = sample_cli_args['exec_ls']

        with patch.object(qm_controller, 'exec_in_container') as mock_exec:
            handle_exec_command(args, qm_controller)
            mock_exec.assert_called_once_with(
                command=['ls', '-la', '/tmp'],
                output_json=False,
                pretty=True
            )

    def test_handle_execin_command(self, sample_cli_args, qm_controller):
        """Test execin command handling."""
        args = sample_cli_args['execin_radio']

        with patch.object(qm_controller, 'execin_in_container') as mock_execin:
            handle_execin_command(args, qm_controller)
            mock_execin.assert_called_once_with(
                command=['radio', 'ps', 'aux'],
                output_json=False,
                pretty=True
            )

    def test_handle_cp_command(self, sample_cli_args, qm_controller):
        """Test cp command handling."""
        args = sample_cli_args['cp_files']

        with patch.object(qm_controller, 'copy_in_container') as mock_cp:
            handle_cp_command(args, qm_controller)
            mock_cp.assert_called_once_with(
                paths=['/host/file.txt', 'qm:/tmp/file.txt'],
                output_json=False,
                pretty=True
            )


class TestArgumentParser:
    """Test argument parser functionality."""

    def test_create_argument_parser(self):
        """Test argument parser creation."""
        parser = create_argument_parser("Test description")

        assert parser.prog == "qmctl"
        assert "Test description" in parser.description

    @pytest.mark.parametrize("args,expected_subcommand", [
        (["show"], "show"),
        (["exec", "ls"], "exec"),
        (["execin", "radio", "ps"], "execin"),
        (["cp", "/host/file", "qm:/container/file"], "cp"),
    ])
    def test_parse_subcommands(self, args, expected_subcommand):
        """Test parsing of different subcommands."""
        parser = create_argument_parser("Test")

        # We need to configure subcommands for this test
        configure_subcommands = qmctl.configure_subcommands
        configure_subcommands(parser)

        parsed_args = parser.parse_args(args)
        assert parsed_args.subcommand == expected_subcommand

    def test_parse_show_with_json(self):
        """Test parsing show command with JSON flag."""
        parser = create_argument_parser("Test")
        configure_subcommands = qmctl.configure_subcommands
        configure_subcommands(parser)

        parsed_args = parser.parse_args(["show", "--json"])
        assert parsed_args.subcommand == "show"
        assert parsed_args.json is True

    def test_parse_verbose_flag(self):
        """Test parsing verbose flag."""
        parser = create_argument_parser("Test")
        configure_subcommands = qmctl.configure_subcommands
        configure_subcommands(parser)

        parsed_args = parser.parse_args(["-v", "show"])
        assert parsed_args.verbose is True


class TestIntegration:
    """Integration tests for qmctl functionality."""

    @patch('qmctl.qmctl.subprocess.run')
    @patch('qmctl.qmctl.os.path.exists')
    def test_exec_in_container_empty_output(
        self, mock_exists, mock_run, qm_controller
    ):
        """Test command execution with empty output.

        For example rm, touch commands.
        """
        mock_exists.return_value = True
        mock_run.return_value = Mock(
            returncode=0,
            stdout="",  # Empty output
            stderr=""
        )

        with patch.object(
            qm_controller, '_container_exists', return_value=True
        ):
            qm_controller.exec_in_container(["rm", "/tmp/testfile"])

        # Verify podman exec dest not raising an exception
        expected_cmd = ["podman", "exec", "test-qm", "rm", "/tmp/testfile"]

        mock_run.assert_called_with(
            expected_cmd,
            capture_output=True,
            text=True,
            check=False
        )

    @patch('qmctl.qmctl.subprocess.run')
    @patch('qmctl.qmctl.os.path.exists')
    def test_exec_in_container_success(
        self, mock_exists, mock_run, qm_controller
    ):
        """Test successful command execution in container."""
        mock_exists.return_value = True
        mock_run.return_value = Mock(
            returncode=0,
            stdout="Hello World\n",
            stderr=""
        )

        with patch.object(
            qm_controller, '_container_exists', return_value=True
        ):
            qm_controller.exec_in_container(["echo", "Hello World"])

        # Verify podman exec was called correctly
        expected_cmd = ["podman", "exec", "test-qm", "echo", "Hello World"]
        mock_run.assert_called_with(
            expected_cmd,
            capture_output=True,
            text=True,
            check=False
        )

    @patch('qmctl.qmctl.subprocess.run')
    def test_copy_in_container_success(self, mock_run, qm_controller):
        """Test successful file copy operation."""
        mock_run.return_value = Mock(returncode=0, stderr="")

        with patch.object(
            qm_controller, '_container_exists', return_value=True
        ):
            qm_controller.copy_in_container(
                ["/host/file", "test-qm:/container/file"]
            )

        expected_cmd = [
            "podman", "cp", "/host/file", "test-qm:/container/file"
        ]
        mock_run.assert_called_with(
            expected_cmd,
            capture_output=True,
            text=True,
            check=False
        )

    @patch('qmctl.qmctl.subprocess.run')
    def test_execin_in_container_success(self, mock_run, qm_controller):
        """Test successful nested container execution."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="nested output\n",
            stderr=""
        )

        with patch.object(
            qm_controller, '_container_exists', return_value=True
        ):
            qm_controller.execin_in_container(["radio", "ps", "aux"])

        expected_cmd = [
            "podman", "exec", "test-qm",
            "podman", "exec", "radio",
            "ps", "aux"
        ]
        mock_run.assert_called_with(
            expected_cmd,
            capture_output=True,
            text=True,
            check=False
        )


class TestErrorHandling:
    """Test error handling scenarios."""

    def test_command_not_found_error_handling(
        self, qm_controller, mock_subprocess_run
    ):
        """Test handling of command not found errors."""
        mock_subprocess_run.return_value = Mock(
            returncode=QmError.EXIT_COMMAND_NOT_FOUND,
            stdout="",
            stderr="command not found"
        )

        with patch.object(
            qm_controller, '_container_exists', return_value=True
        ):
            with pytest.raises(SystemExit) as exc_info:
                qm_controller.exec_in_container(["nonexistent_command"])
            assert exc_info.value.code == QmError.EXIT_COMMAND_NOT_FOUND

    def test_container_not_running_error(self, qm_controller):
        """Test error when container is not running."""
        with patch.object(
            qm_controller, '_container_exists', return_value=False
        ):
            with pytest.raises(SystemExit) as exc_info:
                qm_controller.exec_in_container(["ls"])
            assert exc_info.value.code == QmError.EXIT_COMMAND_NOT_FOUND

    def test_config_file_not_found_error(self, qm_controller):
        """Test error when config file is not found."""
        with patch('qmctl.qmctl.os.path.exists', return_value=False):
            with pytest.raises(SystemExit) as exc_info:
                qm_controller.show_container()
            assert exc_info.value.code == QmError.EXIT_CODE_GENERAL_ERROR


class TestMainFunction:
    """Test the main function and CLI entry point."""

    @patch('qmctl.qmctl.sys.argv')
    @patch('qmctl.qmctl.run_command_with_error_handling')
    def test_main_function_calls(self, mock_run_command, mock_argv):
        """Test that main function initializes and runs correctly."""
        mock_argv[:] = ['qmctl', 'show']

        # Mock the argcomplete import to avoid dependency
        with patch('qmctl.qmctl.argcomplete', create=True) as mock_argcomplete:
            mock_argcomplete.autocomplete = lambda _: None
            main()

        mock_run_command.assert_called_once()

    @patch('qmctl.qmctl.sys.argv')
    def test_main_function_handles_error(self, mock_argv):
        """Failure path.

        main should exit with code 1 when handler raises an error.
        """
        mock_argv[:] = ['qmctl', 'show']

        with patch('qmctl.qmctl.argcomplete', create=True) as mock_argcomplete:
            mock_argcomplete.autocomplete = lambda _: None
            # Mock a function that raises RuntimeError
            with patch('qmctl.qmctl.handle_show_command') as mock_handler:
                mock_handler.side_effect = RuntimeError("Simulated failure")
                with pytest.raises(SystemExit) as exec_info:
                    main()
                assert exec_info.value.code == errno.EINVAL


@pytest.mark.parametrize(
    "device_results,expected_output",
    [
        ({"/dev/device1": True}, "present in QM"),
        ({"/dev/device2": False}, "missing in QM"),
        ({"/dev/device1": True, "/dev/device2": False}, "present in QM"),
    ]
)
def test_device_status_output(
    qm_controller, device_results, expected_output, capsys
):
    """Test device status output formatting."""
    qm_controller.output_config.output_json = False
    qm_controller._print_output(device_results)

    captured = capsys.readouterr()
    assert expected_output in captured.out


def test_parse_to_dict_complex_config():
    """Test parsing complex INI-style configuration."""
    controller = QmController()
    content = """# Comment line
[Container]
Image=localhost/qm:latest
Volume=/host:/container:rw
Environment=DISPLAY=:0

[Service]
Restart=always
Type=notify
"""

    result = controller.parse_to_dict(content)

    assert "Container" in result
    assert "Service" in result
    assert result["Container"]["Image"] == "localhost/qm:latest"
    assert result["Container"]["Volume"] == "/host:/container:rw"
    assert result["Service"]["Restart"] == "always"
