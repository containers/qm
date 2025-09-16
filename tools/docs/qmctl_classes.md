# QmCTL Classes Documentation

## Overview

The QmCTL module provides a Python interface for interacting with containerized environments managed by podman. It consists of several core classes that handle configuration, error management, output formatting, and container operations.

## Core Classes

### QmController

The `QmController` class is the main interface for interacting with the 'qm' container managed by podman.

#### Constructor

```python
QmController(
    config_path: str = DEFAULT_CONFIG_PATH,
    verbose: bool = False,
    container_name: str = DEFAULT_CONTAINER_NAME
)
```

**Parameters:**

- `config_path` (str): Path to the container configuration file
(Default: `/usr/share/containers/systemd/qm.container`)
- `verbose` (bool): Enable verbose logging to stderr (Default: `False`)
- `container_name` (str): Name of the container to interact with (Default: `"qm"`)

#### Key Methods

##### Container Management

- `exec_in_container(command, output_json=False, pretty=True)`: Execute commands inside the primary container
- `execin_in_container(command, output_json=False, pretty=True)`: Execute commands in nested containers
- `copy_in_container(paths, output_json=False, pretty=True)`: Copy files between host and container

##### Information Display

- `show_container(output_json=False, pretty=True)`: Display container configuration
- `show_unix_sockets(output_json=False, pretty=True)`: Show active UNIX domain sockets
- `show_shared_memory(output_json=False, pretty=True)`: Show shared memory segments
- `show_resources(output_json=False, pretty=True)`: Stream live resource usage
- `show_available_devices(output_json=False, pretty=True)`: Verify device existence
- `show_namespaces(output_json=False, pretty=True)`: Show namespace information
- `show_all(output_json=False, pretty=True)`: Display all available information

##### Utility Methods

- `parse_to_dict(content)`: Parse INI-style configuration content into dictionary format

#### Private Methods

The class includes several private methods for internal operations:

- `_validate_*` methods: Input validation and error checking
- `_container_exists()`: Check container existence
- `_run_podman_exec()`: Execute podman commands with error handling
- `_print_output()`: Format and display output in text or JSON
- `_log_path()`: Verbose logging functionality

### OutputConfig

Configuration class for output formatting options.

```python
OutputConfig(output_json: bool = False, pretty: bool = True)
```

**Parameters:**

- `output_json` (bool): Enable JSON output format
- `pretty` (bool): Enable pretty-printing for JSON output

## Exception Classes

### QmError

Base exception class for all QM operations.

```python
QmError(message: str, exit_code: int = 1)
```

**Attributes:**

- `message`: Error description
- `exit_code`: Process exit code (default: 1)

### ConfigNotFoundError

Raised when configuration files cannot be found.

```python
ConfigNotFoundError(config_path: str)
```

**Attributes:**

- Inherits from `QmError`
- `exit_code`: Set to `errno.ENOENT` (2)

### ContainerNotFoundError

Raised when the specified container does not exist.

```python
ContainerNotFoundError(container_name: str)
```

### CommandNotFoundError

Raised when a command is not found within the container.

```python
CommandNotFoundError(command: list[str], container: str)
```

### ValidationError

Raised when input validation fails.

```python
ValidationError(message: str)
```

## Helper Classes

### ArgumentParserWithDefaults

Enhanced argument parser that automatically includes default values in help text.

```python
ArgumentParserWithDefaults(*args, **kwargs)
```

Extends `argparse.ArgumentParser` to provide better help formatting.

### HandleLineInContent

Internal helper class for parsing INI-style configuration content.

```python
HandleLineInContent(parsed: dict, current_section: Optional[str] = None)
```

Used internally by `QmController.parse_to_dict()` method.

## Constants

- `DEFAULT_CONFIG_PATH`: `/usr/share/containers/systemd/qm.container`
- `DEFAULT_CONTAINER_NAME`: `"qm"`
- `DEFAULT_JSON_INDENT`: `4`
- `BUFFER_SIZE`: `1024`
- `ADD_DEVICE_PREFIX`: `"AddDevice="`
- `COMMENT_PREFIX`: `"#"`
- `PODMAN_EXEC`: `["podman", "exec"]`
- `PODMAN_CP`: `["podman", "cp"]`

## Usage Examples

### Basic Container Operations

```python
# Initialize controller
controller = QmController(verbose=True)

# Execute command in container
controller.exec_in_container(["ls", "-la", "/tmp"])

# Copy files
controller.copy_in_container(["/host/file.txt", "qm:/container/file.txt"])

# Show container configuration
controller.show_container(output_json=True)
```

### Error Handling

```python
try:
    controller.exec_in_container(["nonexistent_command"])
except SystemExit as e:
    print(f"Command failed with exit code: {e.code}")
```

### Nested Container Operations

```python
# Execute command in nested container
controller.execin_in_container(["radio", "ps", "aux"])
```

## Design Patterns

### Error Handling Strategy

The module follows a centralized error handling pattern:

1. Methods validate inputs using `_validate_*` methods
2. Specific exceptions are raised for different error conditions
3. All public methods catch exceptions and call `_print_error_and_exit()`
4. This results in consistent error reporting and proper exit codes

### Output Formatting

The module supports dual output modes:

- **Text mode**: Human-readable formatted output
- **JSON mode**: Machine-readable structured output

Output is controlled through the `OutputConfig` class and method parameters.

### Validation Pipeline

Input validation follows a consistent pattern:

1. Path existence validation
2. Container existence validation
3. Command/argument validation
4. Type-specific validation (devices, paths, etc.)
