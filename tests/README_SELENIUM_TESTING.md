# Streamlit UI Testing with Selenium

Comprehensive UI testing framework for the Streamlit finance dashboard using Selenium WebDriver.

## Overview

This testing framework provides automated UI testing for:
- **Options Strategy Analyzer** - Strategy generation, visualization, and Greeks analysis
- **Tax Loss Harvesting Optimizer** - Tax analysis, wash sale risk, and recommendations
- All Streamlit UI components and interactions

## Setup

### Prerequisites

- Python 3.8+
- Chrome/Chromium browser
- pip packages: selenium, pytest, pytest-asyncio, webdriver-manager

### Installation

```bash
# Install test dependencies
pip install selenium pytest webdriver-manager

# Or using uv
uv pip install selenium pytest webdriver-manager
```

### Configuration

Edit `tests/conftest.py` to customize:

```python
class StreamlitTestConfig:
    STREAMLIT_HOST = "127.0.0.1"        # Streamlit server host
    STREAMLIT_PORT = 8501                # Streamlit server port
    HEADLESS = True                      # Run in headless mode
    BROWSER_WIDTH = 1920                 # Browser window width
    BROWSER_HEIGHT = 1080                # Browser window height
    IMPLICIT_WAIT = 10                   # Implicit wait in seconds
    EXPLICIT_WAIT = 20                   # Explicit wait timeout
    APP_STARTUP_TIMEOUT = 30             # Streamlit startup timeout
```

## Running Tests

### Run All Tests

```bash
# Standard run
pytest tests/ -v

# With headless browser
HEADLESS_BROWSER=true pytest tests/ -v

# With screenshots
pytest tests/ -v --tb=short

# With coverage
pytest tests/ --cov=src --cov-report=html
```

### Run Specific Test File

```bash
# Options Strategy tests
pytest tests/test_ui_options_strategy.py -v

# Tax Optimization tests
pytest tests/test_ui_tax_optimization.py -v
```

### Run Specific Test Class

```bash
# Test strategy generation
pytest tests/test_ui_options_strategy.py::TestOptionsStrategyGeneration -v

# Test tax configuration
pytest tests/test_ui_tax_optimization.py::TestTaxConfiguration -v
```

### Run Specific Test

```bash
# Test navigation
pytest tests/test_ui_options_strategy.py::TestOptionsStrategyPageNavigation::test_navigate_to_options_strategy_page -v
```

### Run with Debug Output

```bash
pytest tests/ -v -s  # -s shows print statements
pytest tests/ -v --tb=long  # Long traceback format
```

## Test Structure

### Fixtures

#### `streamlit_server`
Starts and manages Streamlit server for testing.
- Scope: session
- Returns: Base URL of running app

#### `chrome_driver`
Creates and configures Chrome WebDriver.
- Scope: function
- Returns: WebDriver instance

#### `wait`
Creates WebDriverWait helper.
- Scope: function
- Returns: WebDriverWait instance

#### `page`
Navigates to home page.
- Scope: function
- Returns: WebDriver at home page

#### `page_actions`
Provides helper methods for common actions.
- Scope: function
- Returns: StreamlitPageActions instance

### Helper Classes

#### `StreamlitPageActions`
Common Streamlit page action methods:
- `navigate_to_page(page_name)` - Navigate using sidebar menu
- `click_button(button_text)` - Click button by text
- `fill_text_input(label, text)` - Fill text input
- `select_dropdown_option(label, option)` - Select from dropdown
- `set_slider_value(label, value)` - Set slider value
- `get_metric_value(metric_label)` - Get metric value
- `wait_for_element(css_selector, timeout)` - Wait for element
- `screenshot(name)` - Take screenshot
- `get_page_source()` - Get HTML source

#### `StreamlitTestBase`
Base class with common selectors and utilities.

```python
class Selectors:
    SIDEBAR = "div[data-testid='stSidebar']"
    MAIN_CONTENT = "div[data-testid='stMainBlockContainer']"
    METRIC = "div[data-testid='metric-container']"
    # ... more selectors
```

## Test Files

### `test_ui_options_strategy.py`

**Test Classes:**
- `TestOptionsStrategyPageNavigation` - Page loading and navigation
- `TestOptionsStrategyGeneration` - Strategy generation (Iron Condor, Strangle, etc.)
- `TestOptionsStrategyParameters` - Parameter configuration
- `TestOptionsStrategyDisplay` - UI element display
- `TestOptionsStrategyMetrics` - Performance metrics
- `TestOptionsStrategyExport` - Export functionality
- `TestOptionsStrategyInputValidation` - Input validation
- `TestOptionsStrategyErrorHandling` - Error scenarios
- `TestOptionsStrategyIntegration` - Full workflow tests

**Sample Tests:**
```python
def test_generate_strategy(page_actions, page):
    """Test generating Iron Condor strategy."""
    page_actions.navigate_to_page("Options Strategy")
    page_actions.select_dropdown_option("Select Strategy Type", "Iron Condor")
    page_actions.fill_text_input("Underlying Symbol", "AAPL")
    page_actions.fill_text_input("Current Price", "150.00")
    page_actions.click_button("Generate Strategy")
    page_actions.wait_for_element("table", timeout=10)
```

### `test_ui_tax_optimization.py`

**Test Classes:**
- `TestTaxOptimizationPageNavigation` - Page loading
- `TestTaxConfiguration` - Tax settings configuration
- `TestHoldingsInput` - Holdings input methods
- `TestTaxAnalysisExecution` - Analysis execution
- `TestTaxOpportunitiesSummary` - Summary metrics
- `TestOpportunitiesDisplay` - Opportunity display
- `TestWashSaleAnalysis` - Wash sale risk analysis
- `TestReplacementSuggestions` - Replacement security suggestions
- `TestTaxPlanningInsights` - Tax insights display
- `TestTaxExportFunctionality` - Export features
- `TestTaxOptimizationIntegration` - Full workflow
- `TestTaxOptimizationErrorHandling` - Error handling

## Element Selectors

Common Streamlit element selectors in `StreamlitTestBase.Selectors`:

```python
# Common
SIDEBAR = "div[data-testid='stSidebar']"
MAIN_CONTENT = "div[data-testid='stMainBlockContainer']"
METRIC = "div[data-testid='metric-container']"
BUTTON = "button"
TEXT_INPUT = "input[type='text']"
NUMBER_INPUT = "input[type='number']"
SELECTBOX = "div[data-testid='stSelectbox']"
SLIDER = "div[data-testid='stSlider']"
RADIO = "div[data-testid='stRadio']"
EXPANDER = "details"
DATAFRAME = "table"

# Messages
SUCCESS_MESSAGE = "[data-testid='stSuccess']"
ERROR_MESSAGE = "[data-testid='stError']"
WARNING_MESSAGE = "[data-testid='stWarning']"
INFO_MESSAGE = "[data-testid='stInfo']"
```

## Output

### Screenshots
Screenshots are automatically saved to:
```
tests/screenshots/
  - test_name_YYYYMMDD_HHMMSS.png
```

### Test Reports
HTML reports are generated in:
```
tests/reports/
```

## Best Practices

### 1. Page Actions
Always use `page_actions` helper methods for consistency:
```python
# Good
page_actions.navigate_to_page("Options Strategy")
page_actions.fill_text_input("Symbol", "AAPL")

# Avoid
driver.find_element(...)
driver.send_keys(...)
```

### 2. Wait Strategies
Use explicit waits for reliability:
```python
# Good
page_actions.wait_for_element("table", timeout=10)
wait.until(EC.element_to_be_clickable(button))

# Avoid
time.sleep(5)  # Use only as last resort
```

### 3. Error Handling
Handle missing elements gracefully:
```python
try:
    page_actions.select_dropdown_option("Label", "Option")
except ValueError as e:
    # Handle missing element
    pass
```

### 4. Test Isolation
Each test should be independent:
```python
@pytest.fixture
def page(chrome_driver):
    # Navigate to home for each test
    chrome_driver.get(streamlit_server)
    yield chrome_driver
```

### 5. Screenshots for Debugging
Take screenshots at key points:
```python
page_actions.screenshot("strategy_generated")
page_actions.screenshot("error_occurred")
```

## Troubleshooting

### Streamlit Server Won't Start
- Ensure port 8501 is not in use
- Check app.py is in project root
- Review Streamlit logs

### Elements Not Found
- Verify test IDs match Streamlit version
- Check page fully loaded with wait
- Use `page_actions.get_page_source()` to inspect HTML

### WebDriver Issues
- Update ChromeDriver: `webdriver-manager` handles this
- Check Chrome version matches
- Verify no other Chrome instances running

### Slow Tests
- Increase timeouts in `StreamlitTestConfig`
- Reduce browser window size for faster rendering
- Run headless for better performance

## CI/CD Integration

### GitHub Actions

```yaml
name: UI Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - run: pip install -e . pytest selenium webdriver-manager
      - run: HEADLESS_BROWSER=true pytest tests/ -v
```

## Performance Tips

1. **Headless Mode**: Set `HEADLESS = True` for faster execution
2. **Parallel Execution**: Use pytest-xdist
   ```bash
   pytest tests/ -n auto
   ```
3. **Reduce Waits**: Adjust timeouts based on actual performance
4. **Screenshots**: Disable screenshots for faster runs (comment out)

## Contributing Tests

When adding new tests:

1. **Follow naming conventions**
   ```python
   def test_feature_name(page_actions, page):
       """Test description."""
   ```

2. **Use fixtures properly**
   ```python
   def test_something(page_actions, page, wait):
       # Fixtures are automatically provided
   ```

3. **Group related tests in classes**
   ```python
   class TestFeatureName:
       def test_aspect_one(self): ...
       def test_aspect_two(self): ...
   ```

4. **Document assumptions**
   ```python
   def test_with_assumptions(page_actions):
       """Test assuming sample data is loaded."""
       # Describe what the test assumes
   ```

## References

- [Selenium Python Documentation](https://www.selenium.dev/documentation/)
- [Pytest Documentation](https://docs.pytest.org/)
- [Streamlit Testing Guide](https://docs.streamlit.io/develop/concepts/app-testing)
- [WebDriver Manager](https://github.com/SergeyPirogov/webdriver_manager)

## Support

For issues or questions:
1. Check test logs and screenshots in `tests/` directory
2. Review Selenium documentation
3. Check Streamlit component IDs match your version
4. Run tests with verbose output: `pytest tests/ -v -s`
