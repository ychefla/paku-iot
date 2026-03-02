# Running Tests

This document explains how to run tests for the Paku IoT platform.

## Quick Start

### Prerequisites
```bash
# Python 3.11 or later
python3 --version

# Install test dependencies
pip install pytest pytest-cov
```

### Run All Tests
```bash
# From repository root
pytest -v

# With coverage report
pytest -v --cov=. --cov-report=term-missing --cov-report=html
```

## Service-Specific Tests

### OTA Service
```bash
cd stack/ota-service
pip install -r requirements.txt
pytest -v
```

**Test Coverage:**
- Health check endpoint
- Metrics endpoint
- Firmware check API
- Update status reporting
- Device listing
- Core device eligibility logic

**Run with coverage:**
```bash
pytest -v --cov=. --cov-report=html
# Open htmlcov/index.html to view detailed coverage
```

### Collector Service
```bash
cd stack/collector
pip install -r requirements.txt

# Run pytest unit tests
pytest -v

# Run legacy validation tests
python test_validation.py
```

**Test Coverage:**
- Topic parsing (hierarchical MQTT topics)
- Payload validation
- Database insertion logic
- Configuration loading
- MQTT connection callbacks

### EcoFlow Collector
```bash
cd stack/ecoflow-collector
pip install -r requirements.txt
pytest -v
```

**Test Coverage:**
- EcoFlow API client
- HMAC signature generation
- API request handling
- Data transformation and extraction
- Database insertion
- Connection management

**Configuration test (requires credentials):**
```bash
export ECOFLOW_ACCESS_KEY="your_key"
export ECOFLOW_SECRET_KEY="your_secret"
python test_config.py
```

## End-to-End Tests

### Full Stack E2E Test
```bash
# Requires Docker and Docker Compose
./tests/e2e_test.sh
```

**What it tests:**
- Docker stack deployment
- PostgreSQL schema creation
- MQTT message flow
- Data persistence
- Grafana dashboard access
- Grafana data queries

**Prerequisites:**
```bash
# Ensure .env file exists
cp compose/.env.example compose/.env

# Edit compose/.env with your configuration
nano compose/.env
```

## Continuous Integration

Tests run automatically on:
- Every push to `main` or `develop`
- Every pull request to `main` or `develop`

See `.github/workflows/tests.yml` for the full CI configuration.

### GitHub Actions Workflow

The CI workflow runs:
1. **OTA Service Tests** - Unit tests with coverage
2. **Collector Tests** - Unit and validation tests with coverage
3. **EcoFlow Collector Tests** - Unit tests with coverage
4. **Linting** - Code quality checks (flake8, black, isort)

Coverage reports are uploaded to Codecov for tracking over time.

## Running Specific Tests

### Run a Single Test File
```bash
pytest stack/collector/test_collector.py -v
```

### Run a Single Test Function
```bash
pytest stack/collector/test_collector.py::test_parse_topic_valid -v
```

### Run Tests Matching a Pattern
```bash
pytest -k "parse_topic" -v
```

### Run Tests with Markers
```bash
# Run only async tests
pytest -m asyncio -v
```

## Coverage Reports

### Generate HTML Coverage Report
```bash
cd stack/collector
pytest --cov=. --cov-report=html
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

### Generate Terminal Coverage Report
```bash
pytest --cov=. --cov-report=term-missing
```

### Generate XML Coverage Report (for CI)
```bash
pytest --cov=. --cov-report=xml
```

## Test Configuration

### pytest Configuration
Tests are configured in `pyproject.toml`:
```toml
[tool.pytest.ini_options]
minversion = "7.0"
testpaths = ["stack", "tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
```

### Coverage Configuration
Coverage settings in `pyproject.toml`:
```toml
[tool.coverage.run]
source = ["."]
omit = [
    "*/test_*.py",
    "*/__pycache__/*",
    "*/venv/*",
]

[tool.coverage.report]
show_missing = true
precision = 2
```

## Debugging Tests

### Run Tests with Verbose Output
```bash
pytest -vv
```

### Show Print Statements
```bash
pytest -s
```

### Stop on First Failure
```bash
pytest -x
```

### Run Last Failed Tests
```bash
pytest --lf
```

### Drop into Debugger on Failure
```bash
pytest --pdb
```

## Writing New Tests

### Test File Naming
- Unit tests: `test_<module_name>.py`
- Integration tests: `test_integration_<feature>.py`
- Place tests next to the code they test

### Test Function Naming
```python
def test_<function_name>_<scenario>():
    """Brief description of what is being tested."""
    # Arrange
    # Act
    # Assert
```

### Example Test
```python
def test_parse_topic_valid():
    """Test parsing valid topic structure."""
    result = parse_topic("van/ruuvi/sensor1/data")
    assert result == ("van", "ruuvi", "sensor1", "data")
```

### Using Mocks
```python
from unittest.mock import Mock, patch

@patch('collector.psycopg.Connection')
def test_insert_measurement(mock_conn):
    """Test database insertion."""
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    
    insert_measurement(mock_conn, "van", "ruuvi", "sensor1", {})
    
    assert mock_cursor.execute.called
```

## Test Fixtures

### Creating Fixtures
```python
import pytest

@pytest.fixture
def sample_payload():
    """Provide a sample valid payload."""
    return {
        "timestamp": "2025-12-13T10:00:00Z",
        "device_id": "sensor1",
        "metrics": {"temperature_c": 22.5}
    }

def test_with_fixture(sample_payload):
    """Test using fixture."""
    assert validate_payload(sample_payload) == True
```

## Performance Testing

### Measure Test Execution Time
```bash
pytest --durations=10
```

### Profile Tests
```bash
pytest --profile
```

## Common Issues

### ImportError: No module named 'paho'
```bash
pip install -r requirements.txt
```

### Tests Not Discovered
Ensure:
- Test files start with `test_`
- Test functions start with `test_`
- Test files are in a directory listed in `testpaths`

### Coverage Report Empty
Ensure you're running from the correct directory and using:
```bash
pytest --cov=. --cov-report=term-missing
```

## Test Metrics

Track these metrics over time:
- **Line Coverage:** Aim for >70%
- **Test Count:** Should increase with new features
- **Test Duration:** Keep total under 5 minutes
- **Flaky Tests:** Aim for 0 flaky tests

## Resources

- [pytest documentation](https://docs.pytest.org/)
- [pytest-cov documentation](https://pytest-cov.readthedocs.io/)
- [Coverage.py documentation](https://coverage.readthedocs.io/)
- [Codecov](https://about.codecov.io/)

## Getting Help

If tests fail or you need help:
1. Check the test output for error messages
2. Run with `-vv` for more detailed output
3. Check the test coverage evaluation: `TEST_COVERAGE_EVALUATION.md`
4. Review existing tests for examples
5. Open an issue with the test failure details
