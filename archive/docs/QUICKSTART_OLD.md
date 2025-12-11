# Quick Start Guide - Options Strategy & Tax Optimization Integration

## What's New

You now have:
1. ✅ **Options Strategy Analyzer** - Full page in the Streamlit app
2. ✅ **Enhanced Tax Loss Harvesting** - Comprehensive tax optimization page
3. ✅ **Selenium UI Tests** - 80+ automated tests for both features

## Getting Started

### 1. Start the Dashboard

```bash
cd /Users/conordonohue/Desktop/TechStack

# Activate virtual environment
source .venv/bin/activate

# Run the Streamlit app
streamlit run app.py
```

The app will be available at: http://localhost:8501

### 2. Navigate to New Features

In the sidebar menu, you'll see:
- **⚙️ Options Strategy** - New options analysis tool
- **💰 Tax Optimization** - Enhanced tax loss harvesting

## Options Strategy Page

### What It Does
- Generate multi-leg options strategies (Iron Condor, Strangle, Straddle, Covered Call, Collar)
- Calculate Greeks (Delta, Gamma, Theta, Vega)
- Show payoff diagrams
- Calculate max profit/loss
- Recommend hedges

### How to Use
1. Click "⚙️ Options Strategy" in sidebar
2. Select a strategy type
3. Set your risk tolerance
4. Enter the underlying symbol and current price
5. Adjust IV percentile and other parameters
6. Click "🔧 Generate Strategy"
7. View the payoff diagram and Greeks
8. Export strategy as CSV if desired

### Example: Iron Condor on AAPL
```
Strategy Type: Iron Condor
Risk Tolerance: Moderate
Symbol: AAPL
Current Price: 150.00
IV Percentile: 65
Days to Expiration: 45
Spread Width: $5.00
OTM Distance: 3%
```

## Tax Optimization Page

### What It Does
- Identify tax loss harvesting opportunities
- Calculate estimated tax savings
- Analyze wash sale risk
- Suggest replacement securities
- Provide tax planning insights

### How to Use
1. Click "💰 Tax Optimization" in sidebar
2. Set your capital gains and ordinary income tax rates
3. Choose holdings input method (Sample, CSV, or Manual)
4. Adjust any settings (filing status, carryforward losses)
5. Click "🔍 Analyze Tax Opportunities"
6. Review opportunities sorted by tax benefit
7. Expand each opportunity to see details
8. Export report as CSV or Parquet

### Example: Using Sample Data
```
Capital Gains Rate: 20%
Ordinary Rate: 37%
Filing Status: Married Filing Jointly
Input Method: Sample Data

Results:
- Total Unrealized Losses: $3,500
- Tax Savings: $1,225
- Opportunities: 4
- Avg Wash Sale Risk: 42%
```

## Running the Tests

### Install Test Dependencies

```bash
pip install -r tests/requirements-test.txt
```

Or using uv:
```bash
uv pip install -r tests/requirements-test.txt
```

### Quick Start Script

```bash
cd tests
chmod +x run_tests.sh
./run_tests.sh
```

Then select from the menu:
1. Run all tests (headless)
2. Run options strategy tests
3. Run tax optimization tests
4. Run with UI (not headless for visual debugging)
5. Run with coverage report
6. Run specific test

### Run Tests Directly

```bash
# All tests in headless mode
HEADLESS_BROWSER=true pytest tests/ -v

# Options strategy tests only
pytest tests/test_ui_options_strategy.py -v

# Tax optimization tests only
pytest tests/test_ui_tax_optimization.py -v

# Specific test class
pytest tests/test_ui_options_strategy.py::TestOptionsStrategyGeneration -v

# With coverage report
pytest tests/ --cov=src --cov-report=html

# With visual browser (slow but you can see what's happening)
HEADLESS_BROWSER=false pytest tests/ -v -s
```

## Test Files Overview

### Configuration
- `tests/conftest.py` - Fixtures and test configuration
- `pytest.ini` - Pytest settings
- `tests/requirements-test.txt` - Test dependencies

### Test Suites
- `tests/test_ui_options_strategy.py` - 40+ tests for options strategy page
- `tests/test_ui_tax_optimization.py` - 40+ tests for tax optimization page

### Documentation & Scripts
- `tests/README_SELENIUM_TESTING.md` - Detailed testing guide
- `tests/run_tests.sh` - Interactive test runner
- `INTEGRATION_SUMMARY.md` - Complete implementation summary

## Code Structure

### New Pages in app.py

1. **render_options_strategy()** (Lines 2139-2407)
   - Strategy type selection
   - Parameter configuration
   - Strategy generation
   - Greeks and P&L visualization
   - Export functionality

2. **render_tax_optimization()** (Lines 2408-2696)
   - Tax settings configuration
   - Holdings input methods
   - Tax analysis execution
   - Opportunity display and ranking
   - Wash sale analysis
   - Export options

### Updated Navigation
```python
# Menu now includes:
["Home", "Portfolio", "Quick Wins", "Advanced Analytics", "Backtesting",
 "Options Strategy",  # NEW
 "Tax Optimization", "Crypto Analytics", "Advanced News", "Email Reports", "Help"]
```

## Key Features

### Options Strategy
- ✅ 5 Strategy types
- ✅ Greeks calculations (Delta, Gamma, Theta, Vega)
- ✅ Payoff diagrams
- ✅ Risk analysis
- ✅ Hedge recommendations
- ✅ CSV export

### Tax Optimization
- ✅ Multiple tax rates
- ✅ 3 input methods (sample, CSV, manual)
- ✅ Wash sale risk analysis
- ✅ Replacement security suggestions
- ✅ Tax planning insights
- ✅ CSV/Parquet export

### Testing Framework
- ✅ 80+ automated UI tests
- ✅ Headless and visual modes
- ✅ Screenshot capture for debugging
- ✅ Parametrized tests
- ✅ Full coverage of user workflows

## File Locations

```
/Users/conordonohue/Desktop/TechStack/
├── app.py
│   ├── render_options_strategy()     # Lines 2139-2407
│   └── render_tax_optimization()     # Lines 2408-2696
│
├── src/
│   ├── options_strategy_automation.py (existing module)
│   └── tax_optimization.py (existing module)
│
├── tests/
│   ├── conftest.py                   # NEW - Test configuration
│   ├── test_ui_options_strategy.py   # NEW - 40+ tests
│   ├── test_ui_tax_optimization.py   # NEW - 40+ tests
│   ├── requirements-test.txt         # NEW - Test dependencies
│   ├── README_SELENIUM_TESTING.md    # NEW - Testing guide
│   ├── run_tests.sh                  # NEW - Quick start script
│   ├── screenshots/                  # Generated test screenshots
│   ├── reports/                      # Generated test reports
│   └── test_data/                    # Generated test data
│
├── INTEGRATION_SUMMARY.md            # NEW - Detailed summary
└── pytest.ini                        # NEW - Pytest configuration
```

## Examples

### Example 1: Generate Iron Condor Strategy

```python
# In Options Strategy page:
1. Navigate to Options Strategy
2. Strategy Type: Iron Condor
3. Risk Tolerance: Moderate
4. Symbol: SPY
5. Current Price: 400.00
6. IV Percentile: 70 (high volatility)
7. Days to Expiration: 45
8. Click "Generate Strategy"

# Results:
- See strategy legs (sell put spread, sell call spread)
- View Greeks: Delta ≈ 0.1 (slightly bullish)
- See payoff diagram with max profit/loss
- Option to export as CSV
```

### Example 2: Analyze Tax Loss Harvesting

```python
# In Tax Optimization page:
1. Navigate to Tax Optimization
2. Capital Gains Rate: 20%
3. Ordinary Rate: 37%
4. Filing Status: Married Filing Jointly
5. Input Method: Sample Data
6. Click "Analyze Tax Opportunities"

# Results:
- Summary: $3,500 losses, $1,225 tax savings
- See opportunities ranked by tax benefit
- Expand each to see details
- Wash sale risk indicators
- Replacement security suggestions
```

## Troubleshooting

### Streamlit App Won't Start
```bash
# Check if port 8501 is in use
lsof -i :8501

# Kill process using port
kill -9 <PID>

# Restart app
streamlit run app.py
```

### Tests Won't Run
```bash
# Ensure dependencies are installed
pip install -r tests/requirements-test.txt

# Check Python version (3.8+)
python --version

# Verify Streamlit is running
curl http://localhost:8501

# Run with verbose output
pytest tests/ -v -s
```

### Elements Not Found in Tests
```bash
# Run with visual browser to debug
HEADLESS_BROWSER=false pytest tests/test_ui_options_strategy.py::TestOptionsStrategyPageNavigation::test_navigate_to_options_strategy_page -v -s

# Check browser console and page source
```

## Next Steps

1. **Try the Features:**
   - Generate a few options strategies
   - Analyze tax opportunities with sample data
   - Explore the visualizations

2. **Run the Tests:**
   - Start with: `pytest tests/test_ui_options_strategy.py -v`
   - Review test output and screenshots
   - Check that all 40+ tests pass

3. **Integrate with CI/CD:**
   - Add tests to your GitHub Actions workflow
   - Set up automated testing on pull requests
   - Generate coverage reports

4. **Customize as Needed:**
   - Add more strategy types
   - Customize tax rates for your situation
   - Add more test scenarios

## Resources

- **Streamlit Docs**: https://docs.streamlit.io/
- **Selenium Docs**: https://www.selenium.dev/documentation/
- **Options Strategy Info**: https://www.investopedia.com/
- **Tax Loss Harvesting**: https://www.investopedia.com/terms/t/tax-loss-harvesting.asp

## Support

For detailed information:
1. Read `INTEGRATION_SUMMARY.md` for complete implementation details
2. Check `tests/README_SELENIUM_TESTING.md` for testing documentation
3. Review inline code comments in `app.py`
4. Look at test examples in `test_ui_options_strategy.py` and `test_ui_tax_optimization.py`

## Success Criteria

You'll know everything is working when:
✅ Streamlit app starts without errors
✅ "Options Strategy" and "Tax Optimization" pages are in sidebar
✅ Options Strategy page loads with strategy generation
✅ Tax Optimization page loads with tax analysis
✅ Tests run successfully: `pytest tests/ -v`
✅ Test screenshots are captured in `tests/screenshots/`

---

**Congratulations! You now have a professional-grade options strategy analyzer and tax loss harvesting tool with automated UI testing! 🎉**
