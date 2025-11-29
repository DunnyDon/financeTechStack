# SEC Scraper Testing Guide

This document describes the testing infrastructure for the SEC Scraper project, including unit tests, Prefect integration, and test execution options.

## Test Files

### `test_sec_scraper.py`
Core unit tests for the SEC scraper using pytest. Contains 22 test cases organized into 5 test classes:

- **TestCIKExtraction** (6 tests): Tests for fetching and validating company CIK numbers
- **TestFilingExtraction** (6 tests): Tests for extracting SEC filing data from API responses
- **TestParquetSaving** (3 tests): Tests for saving data to Parquet format with compression
- **TestIntegration** (2 tests): Integration tests with mocked HTTP requests
- **TestParametrized** (5 tests): Parametrized tests for multiple tickers and filing types

### `test_integration.py`
Prefect workflow integration for pytest execution. Provides:

- Prefect tasks for running pytest with subprocess integration
- Multiple flows for different testing scenarios
- Test result validation and reporting
- Comprehensive logging and error handling

### `run_tests.py`
Interactive test execution menu for convenient test running without remembering commands.

## Test Coverage

The test suite covers:
- ✓ CIK lookup from SEC company tickers JSON
- ✓ Filing data extraction and parsing
- ✓ Data storage in Parquet format with compression
- ✓ Error handling and edge cases
- ✓ Multiple ticker support (AAPL, MSFT, AMZN)
- ✓ Multiple filing types (10-K, 10-Q)
- ✓ Data integrity and field validation

## Running Tests

### Option 1: Run All Tests (Quick)
```bash
uv run --with pytest python -m pytest test_sec_scraper.py -v
```

### Option 2: Run Specific Test Class
```bash
uv run --with pytest python -m pytest test_sec_scraper.py::TestCIKExtraction -v
```

### Option 3: Run Parametrized Tests
```bash
uv run --with pytest python -m pytest test_sec_scraper.py -k "test_multiple_tickers" -v
```

### Option 4: Run with Prefect (Recommended)
**Run all tests through Prefect:**
```bash
uv run python test_integration.py
```

**Run interactive test menu:**
```bash
uv run python run_tests.py
```

### Option 5: Run with Coverage
```bash
uv run --with pytest,pytest-cov python -m pytest test_sec_scraper.py --cov=. --cov-report=term
```

## Test Results

### Sample Output
All tests pass successfully:
```
============================== 22 passed in 0.29s ==============================
```

### Test Report
After running tests through Prefect, a JSON report is generated at `test_results.json`:

```json
{
  "execution_time": "2025-11-29T09:38:58.379920",
  "exit_code": 0,
  "passed_count": 22,
  "failed_count": 0,
  "output": "...full pytest output..."
}
```

## Prefect Integration

### Available Flows

1. **SEC Scraper Test Suite** - Runs all tests and validates results
2. **SEC Scraper Test Classes** - Runs each test class separately for granular monitoring
3. **SEC Scraper Test Coverage** - Runs tests with coverage analysis
4. **SEC Scraper Comprehensive Testing** - Runs all of the above in sequence

### Prefect Features

- **Real-time logging**: All test output is logged through Prefect
- **Task retries**: Failed tests are retried automatically
- **Error handling**: Comprehensive error messages and stack traces
- **Report generation**: JSON reports for integration with other tools
- **Monitoring**: Monitor test execution in Prefect UI (if server is running)

### Example: Start Prefect Server
```bash
uv run python -m prefect server start
```

Then run tests and monitor at `http://localhost:4200`

## Test Data

### Mock Fixtures
Tests use mock fixtures for SEC API responses:
- `mock_company_tickers_response`: Sample company ticker data
- `mock_filings_response`: Sample SEC filing data

### Temporary Directories
Tests use temporary directories (via pytest's `tmp_path` fixture) to avoid polluting the project directory.

## Writing New Tests

### Test Structure
```python
class TestNewFeature:
    def test_feature_success(self):
        """Test successful execution."""
        assert result == expected_value

    def test_feature_error(self):
        """Test error handling."""
        with pytest.raises(Exception):
            function_that_fails()
```

### Using Fixtures
```python
def test_with_mock(self, mock_company_tickers_response):
    """Test using a mock fixture."""
    cik = extract_cik_from_tickers(mock_company_tickers_response, "AAPL")
    assert cik == "0000320193"
```

### Parametrized Tests
```python
@pytest.mark.parametrize("ticker,expected_cik", [
    ("AAPL", "0000320193"),
    ("MSFT", "0000789019"),
])
def test_multiple_tickers(self, ticker, expected_cik):
    """Test multiple ticker inputs."""
    assert extract_cik_from_tickers(data, ticker) == expected_cik
```

## Troubleshooting

### Tests fail with "No module named pytest"
```bash
uv sync --all-extras
```

### Prefect tasks not logging output
Ensure you're using `get_run_logger()` from prefect:
```python
from prefect import get_run_logger
logger = get_run_logger()
logger.info("Test message")
```

### Timeout errors
Increase the timeout in task decorators:
```python
@task(retries=2, retry_delay_seconds=5)  # Adjust these values
```

## CI/CD Integration

To integrate tests into CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Run Tests
  run: uv run python test_integration.py

- name: Upload Test Report
  if: always()
  uses: actions/upload-artifact@v2
  with:
    name: test-results
    path: test_results.json
```

## Best Practices

1. ✓ Always use temporary directories for file operations
2. ✓ Mock external API calls to avoid rate limits
3. ✓ Use descriptive test names that explain what they test
4. ✓ Organize tests into logical classes by functionality
5. ✓ Keep tests fast by avoiding unnecessary I/O operations
6. ✓ Use parametrized tests for testing multiple input variations

## Performance

- Full test suite: ~0.3 seconds
- Individual test class: ~0.15 seconds
- Through Prefect overhead: ~30-40 seconds total

## Next Steps

- Add more filing type tests (8-K, S-1, etc.)
- Implement performance benchmarking tests
- Add database integration tests
- Create end-to-end integration tests with real SEC API (in separate test suite)
