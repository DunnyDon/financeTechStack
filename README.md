# Finance TechStack

A production-ready Python application for portfolio analytics with real-time financial data aggregation.

## Features

**Core Functionality:**
- Portfolio position tracking with multi-broker support (DEGIRO, REVOLUT, Kraken)
- Real-time P&L calculation and portfolio metrics
- Technical analysis with MACD, RSI, Bollinger Bands, and moving averages
- Fundamental metrics aggregation (P/E, ROE, ROA, dividend yields)
- SEC EDGAR filings & XBRL data integration
- Multi-source price fetching (stocks, ETFs, crypto, commodities)
- Currency conversion (FX rates)
- **News scraping & NLP sentiment analysis** - Analyzes major world headlines to assess portfolio impact

**Automation & Delivery:**
- Automated HTML email reports with comprehensive analytics
- Scheduled workflow execution
- Prefect workflow orchestration with automatic retries
- In-memory caching with configurable TTL

**Data Management:**
- Apache Parquet storage with Snappy compression
- Efficient data aggregation and querying
- Rate limiting for API compliance

## Quick Start

**Requirements:** Python 3.13+, `uv` package manager

```bash
git clone <repo>
cd TechStack
uv sync
cp config.csv.template config.csv
# Edit config.csv with your email and API keys
```

## Main Workflows

### 1. Portfolio Analytics & Email
Comprehensive portfolio analysis with email delivery:
```bash
uv run python -c "from src.analytics_flows import enhanced_analytics_flow; enhanced_analytics_flow(send_email_report=True)"
```
Includes: Position P&L, technical indicators, fundamental metrics, trading signals

### 2. News-Informed Analytics
Portfolio analytics with news sentiment impact assessment:
```bash
uv run python -c "from src.news_flows import news_informed_analytics_flow; result = news_informed_analytics_flow(send_email_report=True); print(result['news_analysis']['report'])"
```
Analyzes headlines from 12+ news sources, identifies sector/region impact, classifies by timeframe

### 3. Financial Data Aggregation
Fetch and aggregate prices, SEC filings, fundamentals, and FX rates:
```bash
uv run python -c "from src.portfolio_flows import aggregate_financial_data_flow; aggregate_financial_data_flow()"
```
Output: Parquet file with complete financial dataset

### 4. Portfolio Analysis
Calculate technical indicators and portfolio metrics:
```bash
uv run python -c "from src.portfolio_flows import portfolio_analysis_flow; portfolio_analysis_flow()"
```

## Configuration

Create `config.csv` from template and set:

```csv
report_email,your-email@example.com
sender_email,gmail@gmail.com
sender_password,your-app-password
smtp_host,smtp.gmail.com
smtp_port,587
alpha_vantage_key,your-key-optional
```

See [docs/INSTALL.md](docs/INSTALL.md) for detailed setup instructions.

## Documentation

- **[INSTALL.md](docs/INSTALL.md)** - Setup and environment configuration
- **[USAGE.md](docs/USAGE.md)** - Workflow examples and usage patterns
- **[API.md](docs/API.md)** - Complete API reference
- **[NEWS_ANALYSIS.md](docs/NEWS_ANALYSIS.md)** - News scraping and sentiment analysis
- **[DEPLOY.md](docs/DEPLOY.md)** - Docker, AWS ECS, Kubernetes deployment
- **[TESTING.md](docs/TESTING.md)** - Testing guide
- **[INDEX.md](docs/INDEX.md)** - Documentation navigation

## Project Structure

```
src/
├── analytics_flows.py           # Portfolio analytics orchestration
├── portfolio_flows.py           # Financial data aggregation workflows
├── portfolio_holdings.py        # Portfolio position management
├── portfolio_prices.py          # Multi-source price fetching
├── portfolio_technical.py       # Technical indicator calculations
├── portfolio_fundamentals.py    # Fundamental metrics aggregation
├── portfolio_analytics.py       # P&L and portfolio metrics
├── xbrl.py                      # SEC XBRL data parsing
├── fx_rates.py                  # Currency conversion
├── parquet_db.py                # Data storage abstraction
├── cache.py                     # Caching layer
└── config.py                    # Configuration management

tests/
├── test_portfolio_flows.py
├── test_portfolio_analytics.py
├── test_portfolio_prices.py
├── test_portfolio_technical.py
├── test_portfolio_fundamentals.py
├── test_xbrl.py
├── test_cache.py
├── test_parquet_db.py
├── test_fx_rates.py
├── test_integration.py
└── test_portfolio_integration.py
```

## Development

```bash
# Setup
uv sync

# Run tests
uv run pytest tests/ -v

# Run with coverage
uv run pytest tests/ --cov=src --cov-report=html

# Format code
uv run black src/ tests/
uv run ruff check --fix src/ tests/

# Type checking
uv run mypy src/
```

For contribution guidelines, see [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT
