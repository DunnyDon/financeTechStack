# Quick Start Guide

Get Finance TechStack running in 5 minutes.

## 30-Second Setup

```bash
# Clone and install
git clone <repo>
cd TechStack
uv sync

# Configure
cp data/config.csv.template data/config.csv
nano data/config.csv  # Add email, API keys

# Run dashboard
uv run streamlit run app.py
```

Open http://localhost:8501 and explore!

---

## Essential Workflows

### Dashboard (Interactive UI)
```bash
uv run streamlit run app.py
```
**Tabs:**
- **Overview** - Portfolio P&L, allocation, top holdings
- **Technical** - RSI, Bollinger Bands, moving averages (4 tabs)
- **Fundamental** - P/E, ROE, dividend yields
- **News** - Sentiment analysis, impact scoring
- **Advanced** - Risk, optimization, correlations
- **Backtesting** - Historical strategy testing

### Backfill Historical Data (with Dask)
```bash
# All tickers with technical analysis
uv run python scripts/backfill_historical_data.py

# Specific tickers with 4 workers
uv run python scripts/backfill_historical_data.py --tickers MSFT,AAPL,TSLA --workers 4

# Check progress
uv run python scripts/check_historical_data.py
```
**Performance:** 6x faster than sequential (4 workers)

### Email Report
```bash
python -c "from src.analytics_flows import enhanced_analytics_flow; enhanced_analytics_flow(send_email_report=True)"
```
Includes: P&L, technical signals, fundamentals, trading recommendations

### News-Informed Analysis
```bash
python -c "from src.news_flows import news_informed_analytics_flow; result = news_informed_analytics_flow(send_email_report=True); print(result['news_analysis']['report'])"
```
Analyzes 12+ news sources for portfolio impact

---

## Configuration (data/config.csv)

```csv
email_sender,your-email@gmail.com
email_password,your-app-password
email_recipients,recipient@example.com
finnhub_key,your-finnhub-api-key
alpha_vantage_key,your-alpha-vantage-key
newsapi_key,your-newsapi-key
```

**Gmail:** Use App Passwords (2FA required)

---

## Portfolio Setup (data/holdings.csv)

```csv
sym,quantity,avg_cost,broker,currency
AAPL,10,150.50,DEGIRO,USD
MSFT,5,320.00,REVOLUT,USD
BTC,0.5,45000.00,Kraken,USD
```

Supports: Stocks, ETFs, Crypto, Commodities, Bonds

---

## Testing

```bash
# All tests
uv run pytest tests/ -v

# Specific module
uv run pytest tests/test_portfolio_analytics.py -v

# With coverage
uv run pytest tests/ --cov=src --cov-report=html
```

---

## Troubleshooting

**"No data available"** → Run backfill script first  
**API errors** → Check API keys in config.csv  
**Slow performance** → Use Dask (--workers 4)  
**Email not sending** → Verify Gmail app password  

See `docs/reference/VWRL_FAILURE_ANALYSIS.md` for more solutions.

---

## Next Steps

1. **Add your holdings** to `data/holdings.csv`
2. **Configure API keys** in `data/config.csv`
3. **Run backfill** to populate historical data
4. **Open dashboard** to explore your portfolio
5. **Check docs** for advanced features

---

## Documentation Map

| Need | See |
|------|-----|
| Installation details | `docs/guides/INSTALL.md` |
| Core workflows | `docs/guides/USAGE.md` |
| Dashboard guide | `docs/guides/DASHBOARD_GUIDE.md` |
| API reference | `docs/reference/API.md` |
| Testing procedures | `docs/reference/TESTING.md` |
| Deployment | `docs/reference/DEPLOY.md` |
| Advanced analytics | `docs/guides/ADVANCED_ANALYTICS.md` |
| Prefect workflows | `docs/integration/PREFECT_INTEGRATION_INDEX.md` |
| Architecture | `docs/architecture/BACKTESTING_ENGINE_ARCHITECTURE.md` |
| Roadmap | `docs/FUTURE_WORK.md` |

---

**Ready?** Start with `uv run streamlit run app.py`! 🚀
