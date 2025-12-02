# Testing Guide

## Running Tests

### Quick Test

```bash
uv run pytest tests/ -v
```

### With Coverage Report

```bash
uv run pytest tests/ --cov=src --cov-report=html
# Open htmlcov/index.html to view coverage
```

### Run Specific Test File

```bash
uv run pytest tests/test_portfolio_analytics.py -v
```

### Run Specific Test

```bash
uv run pytest tests/test_portfolio_analytics.py::TestPortfolioMetrics::test_pnl_calculation -v
```

## Test Organization

```
tests/
├── test_portfolio_flows.py         # Prefect flow orchestration
├── test_portfolio_analytics.py     # P&L, signals, metrics
├── test_portfolio_prices.py        # Price fetching
├── test_portfolio_technical.py     # Technical indicators
├── test_portfolio_fundamentals.py  # Fundamental metrics
├── test_xbrl.py                    # SEC XBRL parsing
├── test_cache.py                   # Caching layer
├── test_parquet_db.py              # Data storage
├── test_fx_rates.py                # Currency conversion
├── test_news_analysis.py           # News scraping & sentiment analysis
├── test_integration.py             # End-to-end workflows
└── test_portfolio_integration.py   # Multi-component flows
```

## Test Categories

### Unit Tests
Component-level tests with mocked dependencies:

```bash
uv run pytest tests/ -k "not integration" -v
```

### Integration Tests
Full workflow tests with real data:

```bash
uv run pytest tests/test_integration.py -v
```

### News Analysis & RSS Feed Tests
Validates news scraping and sentiment analysis:

```bash
# Test all news analysis functionality
uv run pytest tests/test_news_analysis.py -v

# Test RSS feed health (scrapes real feeds)
uv run pytest tests/test_news_analysis.py::test_scrape_news_headlines -v

# Test sentiment analysis
uv run pytest tests/test_news_analysis.py::test_analyze_news_sentiment -v

# Test portfolio impact assessment
uv run pytest tests/test_news_analysis.py::test_portfolio_impact_assessment -v
```

**Expected Results:**
- Scrapes 150+ articles from 13-18 news sources
- Completes in ~5-10 seconds
- Analyzes sentiment for all articles
- Identifies affected sectors and timeframes
- Correlates with portfolio holdings

**Note:** Individual feed timeouts are normal (2-4 sources may fail). System automatically uses fallback sources and continues analysis.

### Performance Tests
Benchmark-style tests:

```bash
uv run pytest tests/ -v -m performance --durations=10
```

## Writing Tests

### Basic Unit Test

```python
import pytest
from src.portfolio_analytics import PortfolioAnalyzer

def test_pnl_calculation():
    analyzer = PortfolioAnalyzer()
    pnl = analyzer.calculate_pnl(
        entry_price=100.0,
        current_price=110.0,
        shares=10
    )
    assert pnl == 100.0
```

### Fixture Usage

```python
@pytest.fixture
def sample_holdings():
    return [
        {"ticker": "AAPL", "shares": 10, "entry_price": 150},
        {"ticker": "MSFT", "shares": 5, "entry_price": 300},
    ]

def test_portfolio_value(sample_holdings):
    analyzer = PortfolioAnalyzer(sample_holdings)
    assert analyzer.total_value > 0
```

### Mocking External APIs

```python
from unittest.mock import patch

@patch('src.portfolio_prices.PriceFetcher.fetch_price')
def test_price_fetch_with_mock(mock_fetch):
    mock_fetch.return_value = 150.00
    
    price = fetch_price("AAPL")
    assert price == 150.00
    mock_fetch.assert_called_once_with("AAPL")
```

### Async Test

```python
@pytest.mark.asyncio
async def test_async_workflow():
    result = await async_fetch_prices(["AAPL", "MSFT"])
    assert len(result) == 2
```

## CI/CD Integration

### GitHub Actions

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: astral-sh/setup-uv@v1
      - run: uv sync
      - run: uv run pytest tests/ --cov=src
      - uses: codecov/codecov-action@v3
```

## Test Coverage Goals

| Component | Target |
|-----------|--------|
| analytics_flows.py | 85%+ |
| portfolio_flows.py | 85%+ |
| portfolio_analytics.py | 90%+ |
| portfolio_prices.py | 80%+ |
| xbrl.py | 75%+ |
| **Overall** | **80%+** |

Current coverage: Run `uv run pytest --cov=src --cov-report=term-missing`

## Debugging Tests

### Verbose Output

```bash
uv run pytest tests/ -vv --tb=long
```

### Print Debug Info

```python
def test_something():
    result = some_function()
    print(f"DEBUG: {result}")  # Shows with -s flag
    assert result == expected
```

Enable prints:

```bash
uv run pytest tests/ -s  # Show print statements
```

### Drop into Debugger

```python
def test_something():
    import pdb; pdb.set_trace()  # Breakpoint
    result = some_function()
    assert result == expected
```

Run with:

```bash
uv run pytest tests/ --pdb
```

## Performance Profiling

```bash
# Run with timing
uv run pytest tests/ --durations=10

# Profile specific test
uv run pytest tests/test_portfolio_analytics.py::test_large_portfolio -v --profile
```

## Known Issues & Workarounds

| Issue | Workaround |
|-------|-----------|
| Timeout on slow network | Increase pytest timeout: `pytest --timeout=30` |
| Flaky API tests | Use `@pytest.mark.flaky(reruns=3)` |
| Cache interference | Clear cache: `rm -rf .pytest_cache src/__pycache__` |

- **TestCIKExtraction** (5 tests - Skipped)
  - Reason: Prefect task mocking - use test_sec_scraper.py instead

- **TestFilingIndexRetrieval** (4 tests - Skipped)
  - Reason: Prefect task mocking - use test_sec_scraper.py instead

- **TestXBRLParsing** (6 tests - All passing)
  - Valid XBRL data parsing from SEC JSON API
  - Debt-to-equity ratio calculation
  - Current ratio calculation
  - Missing field handling
  - Invalid data handling
  - Empty data handling

- **TestParquetStorage** (3 tests - All passing)
  - Single record storage
  - Multiple records storage
  - Compression validation

- **TestXBRLIntegration** (2 tests - All passing)
  - XBRL data structure validation for AAPL
  - XBRL data structure validation for MSFT

### `tests/test_integration.py`

Prefect workflow integration for comprehensive testing:

- **SEC Scraper Test Suite Flow**: Runs all pytest tests through Prefect
- **SEC Scraper Test Classes Flow**: Runs each test class individually
- **SEC Scraper Comprehensive Testing Flow**: Main orchestration flow

Features:
- Subprocess-based pytest execution
- Result validation and metrics extraction
- JSON report generation
- Detailed Prefect logging
- Automatic retry logic

## Running Tests

### Quick Test Run (Recommended)

```bash
# Run all unit tests
uv run --with pytest python -m pytest tests/ -v

# Run specific test file
uv run --with pytest python -m pytest tests/test_sec_scraper.py -v
uv run --with pytest python -m pytest tests/test_xbrl.py -v
```

### Run Specific Tests

```bash
# Run specific test class
uv run --with pytest python -m pytest tests/test_sec_scraper.py::TestCIKExtraction -v

# Run specific test method
uv run --with pytest python -m pytest tests/test_sec_scraper.py::TestCIKExtraction::test_extract_cik_aapl -v

# Run tests matching pattern
uv run --with pytest python -m pytest tests/ -k "extract_cik" -v
```

### Run with Prefect Integration

```bash
# Run full Prefect test suite (recommended for production)
uv run python tests/test_integration.py
```

This will:
1. Start a temporary Prefect server
2. Run all pytest tests through Prefect tasks
3. Execute individual test classes for granular monitoring
4. Generate `test_results.json` report
5. Display comprehensive summary

### Run with Coverage

```bash
# Generate coverage report
uv run --with pytest python -m pytest tests/ --cov=src --cov-report=html

# View coverage (opens in browser)
open htmlcov/index.html
```

### Run with Additional Options

```bash
# Verbose output with tracebacks
uv run --with pytest python -m pytest tests/ -vv --tb=long

# Stop at first failure
uv run --with pytest python -m pytest tests/ -x

# Show print statements
uv run --with pytest python -m pytest tests/ -s

# Run tests in parallel
uv run --with pytest python -m pytest tests/ -n auto
```

## Docker & Containerized Testing

### Run Tests in Docker

All tests can be executed in a containerized environment to ensure consistency across machines.

```bash
# Build the Docker image
docker build -t finance-techstack:latest .

# Run unit tests in Docker
docker run --rm finance-techstack:latest python -m pytest tests/test_sec_scraper.py -v

# Run XBRL tests in Docker
docker run --rm finance-techstack:latest python -m pytest tests/test_xbrl.py -v

# Run all tests in Docker
docker run --rm finance-techstack:latest python -m pytest tests/ -v
```

### Docker Compose Testing

For testing with full service stack (PostgreSQL, Prefect, Redis):

```bash
# Start all services
docker-compose up -d

# Run tests against services
docker-compose run --rm techstack python -m pytest tests/ -v

# Check service health
docker-compose ps

# View logs from any service
docker-compose logs prefect-server
docker-compose logs postgres

# Tear down all services
docker-compose down

# Clean up volumes
docker-compose down -v
```

### Docker Testing with Coverage

```bash
# Generate coverage report in Docker
docker run --rm -v $(pwd):/app finance-techstack:latest \
  python -m pytest tests/ --cov=src --cov-report=html

# View coverage report locally
open htmlcov/index.html
```

### Automated Docker Test Script

A comprehensive test script handles multi-phase testing:

```bash
# Make script executable
chmod +x scripts/docker-test.sh

# Run all Docker tests
./scripts/docker-test.sh

# Tests performed:
# - Single container image build
# - Unit test execution
# - Docker Compose service startup
# - Service health checks
# - Integration test execution
# - Data persistence validation
# - Service teardown and cleanup
```

### Docker Testing Benefits

- ✓ **Consistency**: Same environment as production
- ✓ **Isolation**: Tests don't affect local machine
- ✓ **CI/CD Ready**: Exact reproduction in pipelines
- ✓ **Multi-service Testing**: Full stack validation
- ✓ **Clean State**: Start fresh for each run
- ✓ **Dependency Testing**: Verify all service interactions

### Example: Full Test Lifecycle in Docker

```bash
# 1. Build fresh image
docker build -t finance-techstack:test .

# 2. Start services
docker-compose up -d

# 3. Wait for health checks
sleep 10
docker-compose ps

# 4. Run tests
docker-compose run --rm techstack python -m pytest tests/ -v

# 5. Run Prefect integration tests
docker-compose run --rm techstack python tests/test_integration.py

# 6. Verify data persistence
docker-compose exec postgres psql -U techstack -d techstack -c \
  "SELECT * FROM information_schema.tables WHERE table_schema='public';"

# 7. Clean up
docker-compose down
```

### Troubleshooting Docker Tests

**Image build fails:**
```bash
docker build -t finance-techstack:latest . --no-cache
```

**Services won't start:**
```bash
# Check logs
docker-compose logs -f

# Verify ports aren't in use
lsof -i :5432  # PostgreSQL
lsof -i :4200  # Prefect
lsof -i :6379  # Redis
```

**Tests hang in Docker:**
```bash
# Increase timeout
docker run --rm --timeout=300 finance-techstack:latest \
  python -m pytest tests/ -v
```

**Cleanup stuck containers:**
```bash
docker-compose down -v --remove-orphans
docker system prune -a
```

## Test Results

### Expected Output

```
======================== 33 passed, 9 skipped in 2.64s =========================

Passed:
- test_sec_scraper.py: 22 tests
- test_xbrl.py: 11 tests (6 parsing, 3 storage, 2 integration)

Skipped:
- test_xbrl.py: 9 tests (Prefect task mocking - use test_sec_scraper.py)
```

### Result Analysis

- ✓ All core functionality working
- ✓ All data sources integrated correctly
- ✓ Error handling robust
- ✓ Data storage and retrieval validated
- ✓ Parquet compression working
- ⊘ Skipped tests use different mocking strategy (see note below)

### Note on Skipped Tests

Some test_xbrl.py tests for `fetch_company_cik` and `fetch_sec_filing_index` are skipped because:
1. These are Prefect tasks that wrap the underlying functions
2. Mocking Prefect tasks requires special handling
3. Equivalent tests exist in test_sec_scraper.py with proper mocking
4. The actual functions are validated through test_integration.py

## Test Coverage by Component

### SEC EDGAR Integration
- ✓ Company CIK lookup
- ✓ Filing metadata extraction
- ✓ Multiple filing types (10-K, 10-Q, etc.)
- ✓ Error handling for non-existent tickers/filings

### XBRL Data Extraction
- ✓ Financial metrics parsing (revenue, income, assets, liabilities, equity)
- ✓ Financial ratios calculation (current ratio, debt-to-equity)
- ✓ Missing field handling
- ✓ Invalid data handling

### Data Storage
- ✓ Parquet file creation
- ✓ Data integrity validation
- ✓ Snappy compression
- ✓ Multiple record batching

### Prefect Integration
- ✓ Task execution and logging
- ✓ Retry logic
- ✓ Error handling
- ✓ Result validation

## Writing New Tests

### Test Structure

```python
import pytest
from src.module import function_to_test

class TestNewFeature:
    """Test class for new feature."""
    
    def test_feature_success(self):
        """Test successful execution."""
        result = function_to_test(valid_input)
        assert result == expected_value
    
    def test_feature_error(self):
        """Test error handling."""
        with pytest.raises(ExpectedException):
            function_to_test(invalid_input)
```

### Using Fixtures

```python
@pytest.fixture
def sample_data():
    """Provide sample test data."""
    return {
        "ticker": "AAPL",
        "cik": "0000320193",
    }

def test_with_fixture(self, sample_data):
    """Test using fixture data."""
    result = process_company(sample_data)
    assert result["ticker"] == "AAPL"
```

### Parametrized Tests

```python
@pytest.mark.parametrize("ticker,expected_cik", [
    ("AAPL", "0000320193"),
    ("MSFT", "0000789019"),
    ("AMZN", "0001018724"),
])
def test_multiple_tickers(self, ticker, expected_cik):
    """Test multiple ticker inputs."""
    result = get_company_cik(ticker)
    assert result == expected_cik
```

## Troubleshooting

### Tests fail with "No module named pytest"

```bash
# Install test dependencies
uv sync
# or with pip
pip install -e ".[dev]"
```

### Import errors in tests

Ensure package is installed in development mode:

```bash
cd /Users/conordonohue/Desktop/TechStack
uv sync
# or
pip install -e .
```

### Prefect server won't start

```bash
# Clean up old Prefect state
uv run python -m prefect config set PREFECT_HOME=/tmp/prefect-test
uv run python -m prefect server start
```

### Tests timeout

Increase timeout in task decorators if network is slow:

```python
@task(retries=3, retry_delay_seconds=10)
def my_task():
    pass
```

### Mock not working

For Prefect tasks, use:

```python
from unittest.mock import patch

# Patch at the import location
@patch("src.module.function_to_mock")
def test_with_prefect_task(mock_fn):
    mock_fn.return_value = {"mocked": "value"}
    # Now the task will use the mock
```

## Performance

### Execution Times

- Full test suite: ~2.6 seconds
- Unit tests only: ~0.4 seconds
- With Prefect overhead: ~35-40 seconds total
- Coverage report generation: ~5 seconds additional

### Optimization Tips

1. Run specific tests during development
2. Use `-x` flag to stop at first failure
3. Skip coverage during active development
4. Run Prefect tests only before commits

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: astral-sh/setup-uv@v1
      - name: Run Tests
        run: uv run --with pytest python -m pytest tests/ -v
      - name: Upload Coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage.xml
```

## Best Practices

1. ✓ Always use temporary directories for file I/O
2. ✓ Mock external API calls to avoid rate limits
3. ✓ Use descriptive test names (test_<feature>_<scenario>)
4. ✓ Organize tests into logical classes by functionality
5. ✓ Keep tests fast by avoiding unnecessary sleep/delays
6. ✓ Use parametrized tests for multiple input variations
7. ✓ Test both success and failure paths
8. ✓ Validate data types and ranges
9. ✓ Document complex test setup in comments
10. ✓ Run full test suite before committing

## Related Documentation

- [README.md](README.md) - Project overview and quick start
- [.github/copilot-instructions.md](.github/copilot-instructions.md) - Development guidelines
- [pyproject.toml](pyproject.toml) - Project dependencies

## Next Steps

- [ ] Add performance benchmarking tests
- [ ] Implement end-to-end tests with real SEC API (separate test suite)
- [ ] Add stress tests for large data batches
- [ ] Create integration tests for database backend
- [ ] Add visual regression tests for reports
