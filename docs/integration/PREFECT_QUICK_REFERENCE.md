# Prefect Integration Reference - Quick Lookup

## New Modules Quick Reference

### 1️⃣ Quick Wins Analytics Flows

**Module**: `src/quick_wins_analytics_streamlit.py`

```python
from src.quick_wins_analytics_streamlit import (
    momentum_analysis_flow,
    mean_reversion_flow,
    sector_rotation_flow,
    portfolio_beta_flow
)

# Momentum: Find uptrend/downtrend candidates
momentum_df, stats = momentum_analysis_flow(holdings_df)
# Returns: (DataFrame with Symbol/Return%/Signal, Dict with uptrend_count)

# Mean Reversion: Find overbought/oversold positions
reversion_df, stats = mean_reversion_flow(holdings_df)
# Returns: (DataFrame with Symbol/P&L%/Signal, Dict with oversold_count)

# Sector Rotation: Analyze asset class allocation
sector_df, stats = sector_rotation_flow(holdings_df)
# Returns: (DataFrame with Asset Class/Value/P&L, Dict with sector stats)

# Portfolio Beta: Calculate risk profile
beta_metrics = portfolio_beta_flow(holdings_df)
# Returns: Dict with beta/volatility/sharpe_ratio/risk_profile
```

---

### 2️⃣ Portfolio Price Updates Flow

**Module**: `src/portfolio_prices_streamlit.py`

```python
from src.portfolio_prices_streamlit import (
    update_prices_flow,
    fetch_price_for_symbol,
    prepare_prices_for_storage,
    save_prices_to_db
)

# Main flow - fetch and save prices for all holdings
success_count, failed_tickers = update_prices_flow(holdings_df)
# Returns: (int count of successful updates, list of failed tickers)

# Can also use components separately:
price_data = fetch_price_for_symbol('AAPL', asset_type='eq')
prices_df = prepare_prices_for_storage([price_data, ...])
success = save_prices_to_db(prices_df)
```

---

### 3️⃣ Technical Analysis Flow

**Module**: `src/portfolio_technical_streamlit.py`

```python
from src.portfolio_technical_streamlit import (
    calculate_technical_flow,
    calculate_indicators_for_symbol,
    validate_technical_data,
    save_technical_to_db
)

# Main flow - calculate and save technical indicators
processed_count, failed_symbols = calculate_technical_flow(holdings_df)
# Returns: (int count of symbols processed, list of failed symbols)

# Can also use components separately:
valid = validate_technical_data(symbol_prices_df)
indicators = calculate_indicators_for_symbol('AAPL', symbol_prices_df)
success = save_technical_to_db(indicators)
```

---

### 4️⃣ News Sentiment Analysis Flow ✅ (Already Integrated)

**Module**: `src/news_analysis_streamlit.py`

```python
from src.news_analysis_streamlit import news_sentiment_analysis_flow

articles, stats = news_sentiment_analysis_flow(
    max_articles=100,
    hours_back=24,
    symbols=['AAPL', 'MSFT']
)
# Returns: (List of articles with sentiment, Dict with statistics)
```

---

## Usage Patterns

### Pattern 1: Simple Flow Call in Streamlit

```python
import streamlit as st
from src.quick_wins_analytics_streamlit import momentum_analysis_flow

if st.button("Analyze Momentum"):
    with st.spinner("Analyzing..."):
        try:
            momentum_df, stats = momentum_analysis_flow(
                st.session_state.prices_with_holdings
            )
            
            st.success("✅ Analysis Complete")
            st.dataframe(momentum_df)
            st.info("📋 View logs: http://localhost:4200")
            
        except Exception as e:
            st.error(f"Error: {str(e)}")
```

### Pattern 2: With Progress Tracking

```python
import streamlit as st
from src.portfolio_prices_streamlit import update_prices_flow

if st.button("🔄 Update Prices"):
    with st.spinner("Fetching prices..."):
        success, failed = update_prices_flow(holdings_df)
        
        if success:
            st.success(f"✅ Updated {success} prices")
        
        if failed:
            st.warning(f"⚠️ Failed: {', '.join(failed)}")
        
        st.info("📋 Check Prefect UI for task details")
```

### Pattern 3: Multiple Analyses

```python
import streamlit as st
from src.quick_wins_analytics_streamlit import (
    momentum_analysis_flow,
    mean_reversion_flow,
    portfolio_beta_flow
)

col1, col2 = st.columns(2)

with col1:
    if st.button("Momentum"):
        momentum_df, _ = momentum_analysis_flow(holdings_df)
        st.dataframe(momentum_df)

with col2:
    if st.button("Mean Reversion"):
        reversion_df, _ = mean_reversion_flow(holdings_df)
        st.dataframe(reversion_df)

if st.button("Portfolio Beta"):
    beta = portfolio_beta_flow(holdings_df)
    st.metric("Beta", f"{beta['beta']:.2f}")
    st.metric("Risk Profile", beta['risk_profile'])
```

---

## Return Value Reference

### momentum_analysis_flow()
```python
momentum_df = {
    'Symbol': ['AAPL', 'MSFT', ...],
    'Return %': [12.5, -2.3, ...],
    'Current Price': [150.25, 240.10, ...],
    'Signal': ['Strong Uptrend', 'Downtrend', ...]
}

stats = {
    'total_symbols': 10,
    'uptrend_count': 7,
    'downtrend_count': 3,
    'avg_return': 5.2,
    'best_performer': 'AAPL',
    'worst_performer': 'MSFT'
}
```

### mean_reversion_flow()
```python
reversion_df = {
    'Symbol': ['AAPL', 'MSFT', ...],
    'P&L %': [50.5, -45.2, ...],
    'Current Price': [150.25, 240.10, ...],
    'Signal': ['Strong Overbought', 'Strong Oversold', ...]
}

stats = {
    'total_symbols': 10,
    'oversold_count': 3,
    'overbought_count': 2,
    'normal_count': 5,
    'avg_pnl': 15.3,
    'max_gain': 85.2,
    'max_loss': -60.1
}
```

### sector_rotation_flow()
```python
sector_df = {
    'Asset Class': ['Stocks', 'Bonds', 'Crypto'],
    'Value': [50000, 30000, 10000],
    'Cost': [45000, 32000, 12000],
    'P&L': [5000, -2000, -2000],
    'Positions': [15, 8, 2],
    'Avg Position Size': [3333, 3750, 5000]
}

stats = {
    'total_value': 90000.0,
    'num_sectors': 3,
    'top_sector': 'Stocks',
    'top_sector_value': 50000.0,
    'top_sector_pct': 55.5,
    'total_pnl': 1000.0
}
```

### portfolio_beta_flow()
```python
beta_metrics = {
    'beta': 1.25,
    'volatility': 15.5,
    'portfolio_return': 12.3,
    'sharpe_ratio': 0.79,
    'risk_profile': 'Moderate',  # or 'Aggressive', 'Conservative'
    'num_holdings': 25,
    'avg_return': 8.5,
    'std_dev': 12.1
}
```

### update_prices_flow()
```python
success_count = 20  # Number of successfully updated tickers
failed_tickers = ['VWRL', 'XYZ']  # Tickers that couldn't be fetched
```

### calculate_technical_flow()
```python
processed_count = 18  # Number of symbols with indicators calculated
failed_symbols = ['ABC', 'DEF']  # Symbols without sufficient data
```

---

## Error Handling

### Standard Try-Catch Pattern

```python
try:
    result = momentum_analysis_flow(holdings_df)
    st.success("✅ Analysis complete")
    
except TypeError as e:
    st.error(f"Invalid data type: {str(e)}")
    
except ValueError as e:
    st.error(f"Invalid value in data: {str(e)}")
    
except Exception as e:
    st.error(f"Unexpected error: {str(e)}")
    st.info("💡 Check Prefect logs at http://localhost:4200")
```

### Common Issues & Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| "No pnl_percent column" | Missing data | Ensure price data loaded first |
| "Empty holdings" | No positions | Load holdings with `load_holdings()` |
| "Invalid price data" | Too few bars | Need minimum 20 bars for technical |
| AttributeError | Module not imported | Check `from src.xxx_streamlit import yyy` |
| Prefect server error | Server not running | Restart with `run_dashboard.sh` |

---

## Integration Checklist

### ✅ Prerequisites
- [ ] Prefect installed (`pip list \| grep prefect`)
- [ ] Dashboard running (`./run_dashboard.sh`)
- [ ] Prefect server running (auto-started by script)
- [ ] Portfolio data loaded in session state

### ✅ First-Time Setup
- [ ] Import modules in `app.py`
- [ ] Test one flow with button handler
- [ ] Verify Prefect UI shows task execution
- [ ] Add Prefect logs link to UI

### ✅ Verification
- [ ] All flows return expected data types
- [ ] Error handling works gracefully
- [ ] Prefect UI captures logs
- [ ] Dashboard displays results correctly

---

## Performance Monitoring

### Using Prefect UI

1. Open http://localhost:4200
2. Click "Flows" to see all flow definitions
3. Click "Runs" to see execution history
4. Click on a specific run to see:
   - Task execution times
   - Task logs
   - Input/output data
   - Error messages

### Identifying Bottlenecks

Check Prefect UI for longest-running tasks:
- Technical analysis on many symbols = slow
- Price fetch on many tickers = network bound
- Database saves = I/O bound

Optimize by:
- Reducing symbol count
- Using smaller time windows
- Batch processing

---

## Dependencies

These flows require installed packages:
- `prefect>=3.0` (for logging)
- `pandas` (data handling)
- `numpy` (calculations)
- `plotly` (visualizations)
- `feedparser` (news scraping)
- `textblob` (sentiment)

All pre-installed in project `pyproject.toml`

---

## Related Files

**Core Modules**:
- `src/quick_wins_analytics_streamlit.py` - Analytics flows
- `src/portfolio_prices_streamlit.py` - Price flows
- `src/portfolio_technical_streamlit.py` - Technical flows
- `src/news_analysis_streamlit.py` - News flows

**Documentation**:
- `PREFECT_INTEGRATION_AUDIT.md` - Full audit
- `PREFECT_DASHBOARD_INTEGRATION_GUIDE.md` - Implementation guide
- `PREFECT_INTEGRATION_COMPLETE.md` - Status summary

**Scripts**:
- `run_dashboard.sh` - Starts Prefect + Dashboard
- `verify_news_integration.py` - Test script

---

## Support & Debugging

### Get Help
1. Check relevant module's docstrings
2. Read implementation guide
3. Review Prefect UI logs
4. Check module return values match expectations

### Report Issues
Include:
- Exact error message
- Which flow failed
- Input data (holdings_df shape/columns)
- Prefect UI logs if available

---

**Last Updated**: December 2024  
**Status**: ✅ Production Ready  
**Version**: 1.0
