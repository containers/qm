# OCI Hooks Unit Tests

Simple unit tests for QM OCI hooks using pytest and tox.

## Quick Start

```bash
# Set up virtual environment
cd oci-hooks
python -m venv .venv
source .venv/bin/activate  # Linux

# Install dependencies
pip install -r requirements.txt

# Install tox
pip install tox

# Run unit tests
tox -e unit
```

## Test Structure

### Test Files

- `test_qm_device_manager.py` - Tests for the unified device manager hook
- `test_wayland_client_devices.py` - Tests for the Wayland client GPU hook

### Test Categories

- **Unit tests**: Fast tests with no external dependencies
- **Integration tests**: Tests that may require system resources
- **Performance tests**: Tests with timing requirements

## Running Tests

### Using Tox

```bash
tox -e all               # Run all tests
tox -e lint              # Check code formatting for python and shell
tox -e format            # Auto-format code with black
```

### Direct Pytest

If you prefer to avoid tox, you can run pytest directly:

```bash
# Set up virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux

# Install dependencies
pip install -r requirements.txt

# Run tests
pytest -m unit --tb=short -v    # Unit tests only
pytest test_qm_device_manager.py        # Specific test file
```

## CI/CD Integration

Tests run automatically in GitHub Actions on:

- Push to `oci-hooks/**` paths
- Pull requests affecting `oci-hooks/**` paths

Matrix testing across Python versions 3.9-3.12.

## Development Workflow

1. **Make changes** to OCI hook scripts or tests
2. **Run tests locally**: `tox -e unit`
3. **Check code quality**: `tox -e lint`
4. **Auto-format if needed**: `tox -e format`
5. **Fix any failures** before committing
6. **Push changes** - CI will run full test suite

## Troubleshooting

### Permission Issues

If hooks fail with permission errors, ensure scripts are executable:

```bash
chmod +x ../qm-device-manager/oci-qm-device-manager
chmod +x ../wayland-client-devices/oci-qm-wayland-client-devices
```

### Missing Dependencies

```bash
# For tox
pip install tox

# For direct pytest
pip install -r requirements.txt
```

### Test Environment

Tests use temporary log files to avoid permission issues:

- Set `TEST_LOGFILE` environment variable for custom log location
- Default: `/tmp/test-oci-hooks.log` for test runs
