# Finance TechStack Analytics Dashboard

## Overview

A comprehensive web-based UI for portfolio analytics, backtesting, and financial insights. Provides access to all analytics capabilities with an integrated help section explaining financial concepts and metrics.

## Features

### 📈 Portfolio Analytics
- **Real-time P&L Tracking**: Position-level and portfolio-level P&L calculation
- **Technical Signals**: MACD, RSI, Bollinger Bands, Moving Averages
- **Fundamental Metrics**: P/E, ROE, ROA, Dividend Yields, Valuation Assessment
- **Portfolio Weights**: Asset allocation and concentration analysis
- **Risk Analysis**: Volatility, Sharpe Ratio, Max Drawdown, VaR, CVaR

### 📰 News & Sentiment Analysis
- **News Scraping**: Aggregates from 12+ financial news sources
- **Sentiment Classification**: Bullish/Neutral/Bearish sentiment scoring
- **Portfolio Impact Assessment**: Identifies which positions are affected by news
- **Timeline Classification**: Immediate, short-term, long-term impact
- **Sector Analysis**: Sector-wide sentiment and impact trends

### 🎯 Backtesting Framework
- **Strategy Selection**: 4 pre-built strategies (Momentum, Mean Reversion, Sector Rotation, Portfolio Beta)
- **Parameter Configuration**: Customizable dates, initial capital, commission, slippage
- **Performance Metrics**: 14+ metrics including Sharpe, Sortino, Calmar ratios
- **Trade Analysis**: Best/worst trades, trade-by-trade breakdown
- **Risk Metrics**: Maximum drawdown, consecutive losses, underwater plots

### ❓ Integrated Help & Glossary
- **Key Concepts**: P&L, Portfolio Weights, Technical/Fundamental Analysis, Risk Metrics
- **Metrics Explained**: Detailed formulas and interpretations for all metrics
- **Strategy Guides**: How each strategy works, parameters, use cases
- **FAQ Section**: Answers to common questions about portfolio management

## Installation

### Requirements
- Python 3.13+
- `uv` package manager (or pip)

### Setup

```bash
# Clone repository
git clone <repo>
cd TechStack

# Install dependencies
uv sync

# Or with pip
pip install streamlit streamlit-option-menu pandas numpy

# Create config file
cp config.csv.template config.csv
# Edit config.csv with your settings
```

### Optional: Streamlit Dependencies
```bash
# For enhanced features
uv pip install plotly altair scipy scikit-learn
```

## Running the Dashboard

### Option 1: Using the Run Script (Recommended)
```bash
chmod +x run_dashboard.sh
./run_dashboard.sh
```

### Option 2: Direct Streamlit Command
```bash
streamlit run app.py
```

### Option 3: Using uv
```bash
uv run streamlit run app.py
```

The dashboard will open at `http://localhost:8501`

## Dashboard Sections

### 1. Home
Overview of all features and capabilities:
- Quick statistics on available features and data sources
- Core feature highlights
- Feature comparison cards

### 2. Portfolio Analytics
Complete portfolio analysis with 4 tabs:

**Overview Tab:**
- Portfolio metrics (total value, P&L, return %, positions)
- Position-level breakdown with prices, quantities, returns
- Real-time P&L and allocation tracking

**Technical Signals Tab:**
- RSI (Relative Strength Index) values
- MACD status (Bullish/Neutral/Bearish)
- Bollinger Bands position
- Trading signals (Buy/Hold/Sell)
- Moving average analysis

**Fundamentals Tab:**
- P/E (Price-to-Earnings) ratios
- PB (Price-to-Book) ratios
- ROE (Return on Equity) percentages
- Dividend yields
- Valuation assessment (Attractive/Fair/Expensive)

**Risk Analysis Tab:**
- Volatility (annualized)
- Sharpe Ratio
- Maximum drawdown
- Value at Risk (95%)
- Conditional VaR
- Portfolio Beta
- Correlation metrics

### 3. News & Sentiment Analysis
News analysis with 3 tabs:

**Sentiment Overview Tab:**
- Overall market sentiment (Bullish/Neutral/Bearish)
- Number of articles analyzed
- Sentiment confidence score
- Sentiment distribution pie chart

**Impact Analysis Tab:**
- Per-symbol impact scores
- Sentiment classification
- Timeframe assessment
- Key themes and topics
- Sector-level sentiment and article counts

**Recent Headlines Tab:**
- Live news feed
- Source and timestamp
- Sentiment classification
- Impact assessment
- Quick-access to relevant stories

### 4. Backtesting
Strategy backtesting with 4 tabs:

**Strategy Selection Tab:**
- Choose from 4 pre-built strategies
- Strategy descriptions and parameters
- How the strategy works

**Parameters Tab:**
- Date range selection (start/end)
- Initial capital configuration
- Symbol selection (multiselect)
- Commission percentage
- Slippage in basis points

**Results Tab:**
- Summary metrics (return, Sharpe, drawdown, win rate)
- Comprehensive performance metrics table
- Equity curve and performance charts

**Analysis Tab:**
- Trade statistics (count, winners, losers)
- Average win/loss values
- Best trades breakdown
- Trade-by-trade analysis with entry/exit dates and prices

### 5. Help & Glossary
Comprehensive help section with 4 tabs:

**Key Concepts Tab:**
- P&L and position analysis
- Portfolio weights and allocation
- Technical analysis overview
- Fundamental analysis explanation
- Risk metrics introduction

**Metrics Explained Tab:**
- Sharpe Ratio: formula, interpretation, examples
- Sortino Ratio: downside-focused risk metric
- Calmar Ratio: return vs. max drawdown
- Maximum Drawdown: worst-case loss
- Win Rate: trading success percentage
- Profit Factor: profit-to-loss ratio

**Strategies Tab:**
- Momentum Strategy: how it works, parameters, use cases
- Mean Reversion Strategy: statistical deviation trading
- Sector Rotation Strategy: sector performance rotation
- Portfolio Beta Strategy: beta-targeted positioning

**FAQ Tab:**
- 8+ frequently asked questions
- Answers covering portfolio management best practices
- Strategy selection guidance
- Risk management advice

### 6. Settings
Configuration and preferences:

**Data Sources Tab:**
- Enable/disable price data sources
- Fundamental data provider selection
- News source configuration (select from 12+ sources)

**Preferences Tab:**
- Theme selection (Light/Dark)
- Currency preference (EUR/USD/GBP)
- Refresh interval configuration
- Notification preferences
- Email settings and daily report scheduling

**API Keys Tab:**
- Secure API key management
- Connection testing for each provider
- Support for: Yahoo Finance, Alpha Vantage, NewsAPI, SEC Edgar, FX providers

## Key Metrics Explained

### Performance Metrics

**Sharpe Ratio**
- Measures risk-adjusted return
- Formula: (Return - Risk-Free Rate) / Volatility
- Interpretation: Higher is better (>1.0 good, >2.0 excellent)
- Example: 1.42 Sharpe means 1.42% excess return per 1% of volatility

**Sortino Ratio**
- Like Sharpe but only penalizes downside volatility
- More meaningful for risk management
- Example: 2.15 indicates excellent downside-adjusted returns

**Calmar Ratio**
- Measures return per unit of maximum risk
- Formula: Annual Return / Maximum Drawdown
- Example: 1.48 = 1.48% return for each 1% of max drawdown

**Maximum Drawdown**
- Worst peak-to-trough decline experienced
- Example: -8.2% means portfolio fell 8.2% from its highest point
- Important for understanding risk tolerance

**Win Rate**
- Percentage of profitable trades
- Formula: Winning Trades / Total Trades × 100%
- Example: 58% = 58 out of 100 trades profitable

**Profit Factor**
- Ratio of total profit to total loss
- Example: 1.75 = €1.75 profit for every €1 lost
- Values >1.5 indicate profitability, >2.0 excellent

### Risk Metrics

**Volatility**
- Annualized standard deviation of returns
- Higher volatility = higher risk and potential returns
- Used in Sharpe and Sortino ratio calculations

**Value at Risk (VaR)**
- Maximum expected loss at given confidence level (e.g., 95%)
- Example: €2,350 VaR means 95% chance losses won't exceed €2,350

**Conditional VaR (CVaR)**
- Expected loss if VaR threshold is breached
- More conservative than VaR
- Example: €3,100 CVaR = average loss if worst 5% happens

**Beta**
- Correlation with market movements
- Beta = 1.0: moves with market
- Beta > 1.0: more volatile than market
- Beta < 1.0: less volatile than market

### Fundamental Metrics

**P/E Ratio (Price-to-Earnings)**
- How much investors pay per dollar of earnings
- Low P/E: potentially undervalued
- High P/E: growth or overvalued

**P/B Ratio (Price-to-Book)**
- How much investors pay per dollar of assets
- Low P/B: potentially undervalued

**ROE (Return on Equity)**
- How efficiently company converts shareholder equity into profits
- Higher is better (>15% excellent)

**ROA (Return on Assets)**
- How efficiently company uses assets to generate profits
- Higher is better

**Dividend Yield**
- Annual dividend as percentage of stock price
- Higher yield = more income
- May indicate undervaluation or financial stress

## Trading Strategies Explained

### Momentum Strategy
**How It Works:** Identifies stocks with positive momentum and buys them; sells stocks with negative momentum

**Parameters:**
- Lookback Period: Number of days to calculate momentum (e.g., 20)
- Momentum Threshold: Minimum momentum percentage (e.g., 10%)

**Philosophy:** "The trend is your friend" - assumes continued momentum

**Best For:** Trending markets with strong directional moves

**Risks:** Whipsaw losses when momentum reverses

### Mean Reversion Strategy
**How It Works:** Buys oversold stocks (z-score < -2) and sells overbought stocks (z-score > 2)

**Parameters:**
- Lookback Period: Days for calculating mean/std deviation (e.g., 20)
- Z-Score Threshold: Statistical deviation threshold (e.g., ±2σ)

**Philosophy:** Extremes don't last - prices tend to return to normal

**Best For:** Range-bound markets without strong trends

**Risks:** Can exit too early if trend continues

### Sector Rotation Strategy
**How It Works:** Rotates portfolio allocation from worst to best performing sectors

**Parameters:**
- Lookback Period: Days for calculating sector performance (e.g., 60)
- Rebalance Frequency: How often to rotate (monthly, quarterly)

**Philosophy:** Capitalize on relative strength differences between sectors

**Best For:** Diversified portfolios with multiple sectors

**Risks:** Can miss individual stock opportunities

### Portfolio Beta Strategy
**How It Works:** Adjusts position sizing to maintain target portfolio beta

**Parameters:**
- Target Beta: Target portfolio beta (1.0 = market correlation)
- Lookback Period: Days for calculating beta (e.g., 60)

**Philosophy:** Optimize portfolio risk profile relative to market

**Best For:** Risk management and volatility control

**Risks:** May underperform in strong market movements

## Data Integration

The dashboard integrates with:

- **ParquetDB**: Local storage of all financial data
- **Price Sources**: Yahoo Finance, Alpha Vantage, Crypto APIs
- **Fundamental Data**: SEC EDGAR filings, XBRL data
- **News Sources**: Bloomberg, Reuters, CNBC, MarketWatch, TechCrunch, Financial Times
- **Technical Analysis**: MACD, RSI, Bollinger Bands, Moving Averages
- **FX Rates**: Real-time currency conversion

## Customization

### Adding Custom Strategies
Extend the backtesting framework by inheriting from `BaseStrategy`:

```python
from src.backtesting.strategies import BaseStrategy, Signal, SignalAction

class MyStrategy(BaseStrategy):
    def __init__(self, param1, param2):
        super().__init__("my_strategy", {"param1": param1, "param2": param2})
    
    def generate_signals(self, prices_df, technical_df, holdings_df, date):
        signals = []
        # Your signal generation logic
        return signals
```

### Modifying Dashboard Layout
Edit `app.py` to customize:
- Column layouts
- Color schemes (via CSS)
- Chart types and styling
- Tab organization
- Help section content

## Troubleshooting

### "Module not found" errors
```bash
# Ensure dependencies are installed
uv sync

# Or manually install
uv pip install streamlit streamlit-option-menu
```

### Dashboard won't load
```bash
# Check Python version
python --version  # Should be 3.13+

# Try reinstalling Streamlit
uv pip install --upgrade streamlit
```

### Slow performance
- Reduce data date range in analytics
- Use Dask for large backtests
- Cache results using Streamlit's @st.cache decorator

### API key errors
- Verify keys in settings page
- Check API rate limits
- Test connections in settings

## Performance Tips

1. **Caching**: Dashboard caches data to reduce API calls
2. **Parallel Processing**: Use Dask for multi-strategy backtests
3. **Date Ranges**: Limit to necessary time periods for faster analysis
4. **Refresh Intervals**: Adjust based on trading frequency

## Security

⚠️ **Important:** Never commit API keys or credentials
- Store keys in environment variables or `.env` files
- Use settings page to configure securely
- Rotate keys regularly

## Next Steps

1. **Configure Data Sources**: Set up API keys in Settings
2. **Load Historical Data**: Run data aggregation flows
3. **Try Backtesting**: Test strategies on historical data
4. **Monitor Portfolio**: Set up daily reports and alerts
5. **Read Help Section**: Learn metrics and concepts

## Support & Resources

- **Full Documentation**: `docs/BACKTESTING_FRAMEWORK_GUIDE.md`
- **Quick Start**: `BACKTESTING_QUICK_START.md`
- **README**: `README.md`
- **GitHub Issues**: Report bugs and feature requests
- **Discord/Email**: Community support

## Version

**Current Version**: 0.1.0  
**Last Updated**: December 7, 2025  
**Status**: Production Ready ✅

## License

MIT License - See LICENSE file for details
