# Finance TechStack - Repository Organization

A production-ready Python application for portfolio analytics with real-time financial data aggregation.

## 📁 Directory Structure

```
TechStack/
├── app.py                          # Main Streamlit dashboard
├── README.md                       # This file
├── pyproject.toml                  # Project dependencies
├── data/
│   ├── config.csv                  # Configuration (email, API keys)
│   ├── config.csv.template         # Configuration template
│   └── holdings.csv                # Portfolio holdings
├── db/
│   ├── prices/                     # Stock/ETF prices (Parquet)
│   ├── technical_analysis/         # Technical indicators (Parquet)
│   ├── fundamental_analysis/       # Fundamental metrics (Parquet)
│   ├── sec_filings/                # SEC EDGAR data (Parquet)
│   ├── xbrl_filings/               # XBRL data (Parquet)
│   ├── fx_rates/                   # Foreign exchange rates (Parquet)
│   ├── cache/                      # Runtime caching
│   └── backtesting/                # Historical simulation data
├── docs/
│   ├── INDEX.md                    # Documentation index & navigation
│   ├── FUTURE_WORK.md              # Roadmap and planned features
│   ├── architecture/               # System design documentation
│   │   ├── ARCHITECTURE_OVERVIEW.md
│   │   ├── BACKTESTING_ENGINE_ARCHITECTURE.md
│   │   ├── BACKTESTING_FRAMEWORK_GUIDE.md
│   │   ├── DASK_BACKFILL_DOCUMENTATION.md
│   │   ├── DASK_BEST_PRACTICES.md
│   │   └── PARQUETDB_INTEGRATION.md
│   ├── guides/                     # User guides & tutorials
│   │   ├── QUICK_START.md
│   │   ├── INSTALL.md
│   │   ├── USAGE.md
│   │   ├── DASHBOARD_GUIDE.md
│   │   ├── ADVANCED_ANALYTICS.md
│   │   ├── BACKTESTING_ADVANCED.md
│   │   ├── TAX_OPTIMIZATION.md
│   │   ├── CRYPTO_ANALYTICS.md
│   │   ├── DATA_PIPELINE_ROBUSTNESS.md
│   │   ├── OBSERVABILITY.md
│   │   └── OPTIONS_STRATEGY_AUTOMATION.md
│   ├── integration/                # System integration documentation
│   │   ├── PREFECT_INTEGRATION_INDEX.md
│   │   ├── PREFECT_QUICK_REFERENCE.md
│   │   ├── PREFECT_NEWS_INTEGRATION.md
│   │   ├── NEWS_ANALYSIS.md
│   │   └── QUICK_WINS_INTEGRATION.md
│   └── reference/                  # Technical references
│       ├── API.md
│       ├── DEPLOY.md
│       ├── TESTING.md
│       └── VWRL_FAILURE_ANALYSIS.md
├── src/                            # Application code
│   ├── __init__.py
│   ├── analytics_flows.py          # Prefect analytics flows
│   ├── analytics_report.py         # Report generation
│   ├── advanced_analytics_flows.py # Advanced analytics orchestration
│   ├── cache.py                    # In-memory caching
│   ├── config.py                   # Configuration management
│   ├── constants.py                # Application constants
│   ├── dask_*.py                   # Dask parallelization flows
│   ├── exceptions.py               # Custom exceptions
│   ├── fixed_income_analysis.py    # Bond/fixed income metrics
│   ├── fx_rates.py                 # Foreign exchange data
│   ├── news_analysis.py            # NLP sentiment analysis
│   ├── news_analysis_streamlit.py  # Streamlit news UI
│   ├── news_flows.py               # News analysis workflows
│   ├── options_analysis.py         # Options pricing & Greeks
│   ├── parquet_db.py               # ParquetDB abstraction layer
│   ├── portfolio_*.py              # Portfolio analytics modules
│   │   ├── portfolio_analytics.py
│   │   ├── portfolio_analytics_advanced_flow.py
│   │   ├── portfolio_flows.py      # Main Prefect flows
│   │   ├── portfolio_fundamentals.py
│   │   ├── portfolio_holdings.py
│   │   ├── portfolio_optimization.py
│   │   ├── portfolio_prices.py
│   │   ├── portfolio_prices_streamlit.py
│   │   ├── portfolio_risk.py
│   │   ├── portfolio_technical.py
│   │   └── portfolio_technical_streamlit.py
│   ├── quick_wins_analytics.py     # Quick trading signals
│   ├── quick_wins_analytics_streamlit.py
│   ├── quick_wins_flows.py         # Quick wins workflows
│   ├── utils.py                    # Utility functions
│   ├── xbrl.py                     # XBRL data extraction
│   └── backtesting/                # Backtesting framework
│       ├── __init__.py
│       ├── backtesting_engine.py
│       └── strategies/
├── scripts/                        # Standalone utilities & scripts
│   ├── run_dashboard.sh            # Start dashboard
│   ├── setup_dashboard.sh          # Initial setup
│   ├── docker-test.sh              # Docker testing
│   ├── backfill_historical_data.py # Historical data backfill with Dask
│   ├── backfill_performance_demo.py# Backfill performance benchmark
│   ├── check_historical_data.py    # Data collection status
│   └── prefect_manager.py          # Prefect server management
├── tests/                          # Unit & integration tests
│   ├── __init__.py
│   ├── test_advanced_analytics.py
│   ├── test_analytics_report.py
│   ├── test_backtesting_setup.py   # Backtesting setup verification
│   ├── test_cache.py
│   ├── test_dask_analysis_flows.py
│   ├── test_fx_rates.py
│   ├── test_integration.py         # End-to-end integration tests
│   ├── test_news_analysis.py
│   ├── test_parquet_db.py
│   ├── test_portfolio_*.py         # Portfolio component tests
│   ├── test_price_fetching.py
│   ├── test_quick_wins_new.py
│   ├── test_xbrl.py
│   ├── verify_news_integration.py  # News integration verification
│   └── benchmarks/                 # Performance benchmarks
├── examples/                       # Usage examples
│   ├── examples_backtesting.py
│   ├── news_analysis_example.py
│   └── run_backtesting_examples.py
├── deploy/                         # Deployment configurations
│   ├── aws-ecs-deploy.sh
│   ├── ecs-task-definition.json
│   ├── kubernetes/
│   └── terraform/
├── docker/                         # Docker configurations
│   ├── Dockerfile
│   ├── Dockerfile.dask-py313
│   ├── Dockerfile.prefect-worker
│   ├── docker-compose.yml
│   └── docker-compose.dask.yml
├── archive/                        # Old/deprecated versions
│   ├── app_old.py
│   └── app_csv_version.py
└── .github/
    └── copilot-instructions.md     # GitHub Copilot customization
```

## 🚀 Features

**Core Functionality:**
- Portfolio position tracking with multi-broker support (DEGIRO, REVOLUT, Kraken, TD Canada, Sunlife, Bank of Ireland)
- Real-time P&L calculation and portfolio metrics (Jensen's Alpha, Beta, Sharpe Ratio, Volatility)
- Technical analysis with MACD, RSI, Bollinger Bands, moving averages
- Fundamental metrics aggregation (P/E, ROE, ROA, dividend yields)
- SEC EDGAR filings & XBRL data integration
- Multi-source price fetching (stocks, ETFs, crypto, commodities)
- Currency conversion and FX analytics with hedging strategies
- **News scraping & NLP sentiment analysis** - Analyzes major world headlines to assess portfolio impact
- **Comprehensive FX Analytics** - Currency exposure analysis, risk metrics, hedging strategies, technical analysis, pair analytics

**Advanced Analytics (Completed):**
- **FX Analytics & Hedging** (NEW): 
  - Currency exposure mapping across all asset classes (equities, funds, commodities, crypto, cash, fixed-income, retirement)
  - FX Risk Metrics with VaR calculation at 90/95/99% confidence
  - Currency correlation matrix with pair-specific analysis
  - 5 comprehensive tabs: Exposure, Risk Metrics, Hedging Strategies, Technical & Sentiment, Pair Analytics
- **Enhanced Backtesting**: Parameter optimization via grid search, Monte Carlo simulation (1000+ iterations), drawdown analysis with recovery time, Sharpe/Sortino/Calmar ratios, trade-by-trade P&L
- **Advanced News Analytics**: Ticker mention extraction from article text, sector sentiment aggregation, price correlation analysis, weighted sentiment scoring with source quality weighting
- **Tax Loss Harvesting**: Unrealized loss identification by holding period, wash sale detection with risk scoring, replacement security suggestions by sector, tax savings calculation, CSV/Parquet reporting
- **Crypto Advanced Analytics**: On-chain metrics (whale watch, exchange flows, active addresses), market structure analysis (liquidity scoring, orderbook depth, volume profile), cross-asset correlation matrices, volatility term structure with mean reversion signals, portfolio VaR/CVaR calculation

**Automation & Delivery:**
- Automated HTML email reports with comprehensive analytics
- Scheduled workflow execution
- Prefect workflow orchestration with automatic retries
- In-memory caching with configurable TTL

**Data Management:**
- Apache Parquet storage with Snappy compression
- Efficient data aggregation and querying
- Rate limiting for API compliance
- **Smart historical data backfill with Dask parallelization** (4-6x faster)
- **Market holiday detection** for international exchanges (Euronext, etc.)
- Intelligent gap detection and filling for missing data

## 📋 Quick Start

**Requirements:** Python 3.13+, `uv` package manager

```bash
git clone <repo>
cd TechStack
uv sync
cp data/config.csv.template data/config.csv
# Edit data/config.csv with your email and API keys
```

## 🎯 Main Workflows

### 1. Portfolio Analytics Dashboard
Interactive Streamlit web interface:
```bash
uv run streamlit run app.py
# Opens at http://localhost:8501
```
**Dashboard Tabs:**
- **Home**: Portfolio overview, benchmark comparison vs S&P 500, performance visualization
- **Portfolio**: Position analysis, technical indicators, fundamental metrics, risk-adjusted performance
- **Advanced Analytics**: Multi-asset correlation, portfolio optimization, risk analysis
- **Backtesting**: Strategy backtesting with parameter optimization, Monte Carlo simulation, Sharpe/Sortino/Calmar ratios, drawdown analysis, educational guides
- **Options Strategy**: Strategy generation (Iron Condors, Strangles, Straddles, Covered Calls), Greeks analysis, hedge recommendations, market condition assessment
- **Tax Optimization**: Tax loss harvesting, wash sale detection, replacement suggestions, real portfolio holdings integration
- **Crypto Analytics**: Portfolio weights, on-chain metrics, market structure analysis, portfolio risk metrics (VaR, Expected Shortfall)
- **FX Analytics** (NEW): 
  - Currency Exposure Analysis (all asset classes: equities, funds, commodities, crypto, cash, fixed-income, retirement)
  - FX Risk Metrics (VaR, currency correlation, pair volatility)
  - Hedging Strategies (forward contracts, put options, currency swaps, no hedge comparison)
  - Technical & Sentiment Analysis (30+ currency pair technical levels, RSI, trends, market sentiment)
  - Pair Analytics (correlation patterns, volatility clustering, interest rate carry trades, currency strength indexing)
- **Advanced News**: Ticker extraction, weighted sentiment analysis, price correlation, news impact assessment
- **Email Reports**: Scheduled report generation and delivery
- **Help**: Documentation and FAQ

### 2. Portfolio Analytics with Email
```bash
uv run python -c "from src.analytics_flows import enhanced_analytics_flow; enhanced_analytics_flow(send_email_report=True)"
```
Includes: Position P&L, technical indicators, fundamental metrics, trading signals

### 3. News-Informed Analytics
```bash
uv run python -c "from src.news_flows import news_informed_analytics_flow; result = news_informed_analytics_flow(send_email_report=True); print(result['news_analysis']['report'])"
```
Analyzes headlines from 12+ news sources, identifies sector/region impact

### 4. Historical Data Backfill (with Dask)
```bash
# Backfill all tickers with technical analysis calculation
uv run python scripts/backfill_historical_data.py

# Specific tickers and workers
uv run python scripts/backfill_historical_data.py --tickers MSFT,AAPL,TSLA --workers 4

# Check progress
uv run python scripts/check_historical_data.py

# Benchmark performance
uv run python scripts/backfill_performance_demo.py
```

### 5. Prefect Workflow Management
```bash
# Start server and deploy flows
uv run python scripts/prefect_manager.py start

# Check status
uv run python scripts/prefect_manager.py verify

# View flows at http://localhost:4200
```

## ⚙️ Configuration

Create `data/config.csv` from template and set:

```csv
email_sender,your-email@gmail.com
email_password,your-app-password
email_recipients,recipient@example.com
send_to_emails,recipient@example.com
finnhub_key,your-finnhub-api-key
alpha_vantage_key,your-alpha-vantage-key
newsapi_key,your-newsapi-key
```

For email, use Gmail's App Passwords (2FA required).

## 🧪 Testing

```bash
# Run all tests
uv run pytest tests/

# Run specific test file
uv run pytest tests/test_portfolio_analytics.py

# With coverage
uv run pytest tests/ --cov=src --cov-report=html

# Run only integration tests
uv run pytest tests/test_integration.py -v
```

**Test Coverage:**
- 21 test files covering all major components
- Unit tests for data processing, analytics, caching
- Integration tests for end-to-end workflows
- Backtesting framework verification

## 📚 Documentation

**Quick Navigation:**
- **[docs/INDEX.md](docs/INDEX.md)** - Complete documentation index (start here!)
- **[docs/FUTURE_WORK.md](docs/FUTURE_WORK.md)** - Roadmap and planned features
- **[FEATURE_SUMMARY_DEC2025.md](FEATURE_SUMMARY_DEC2025.md)** - Current feature inventory

**Documentation Structure:**

| Category | Purpose | Examples |
|----------|---------|----------|
| **[docs/guides/](docs/guides/)** | User & implementation guides | Quick Start, Dashboard Guide, Advanced Analytics |
| **[docs/architecture/](docs/architecture/)** | System design & architecture | Backtesting Engine, Dask Implementation, ParquetDB |
| **[docs/integration/](docs/integration/)** | Workflow & system integration | Prefect Setup, News Analysis, Quick Wins |
| **[docs/reference/](docs/reference/)** | Technical references & troubleshooting | API, Deployment, Testing, Troubleshooting |

**Archived Documentation:**
Old development phase documents are preserved in `archive/docs/` for historical reference.

## 🏗️ Technology Stack

**Backend:**
- Python 3.13
- Prefect 3.x (workflow orchestration)
- Dask (parallelization)
- Pandas & NumPy (data manipulation)
- PyArrow (Parquet)

**Frontend:**
- Streamlit (interactive UI)
- Plotly (interactive charts)
- Custom CSS styling

**Data Storage:**
- Apache Parquet (columnar storage)
- Snappy compression
- Partitioned by timestamp

**External APIs:**
- Finnhub (real-time prices)
- Alpha Vantage (historical prices)
- SEC EDGAR API (company filings)
- NewsAPI (news aggregation)
- Open-Meteo (FX rates)

## 🚀 Performance

**Data Backfill (Dask Parallelization):**
- Sequential: ~3 seconds per 6 tickers
- Parallel (4 workers): ~0.5 seconds per 6 tickers
- **6x performance improvement**

**Technical Analysis:**
- 252-day dataset: <2 seconds calculation
- All indicators cached
- Per-symbol latest filtering

**Dashboard:**
- Page load: <2 seconds
- Data refresh: 60-second TTL cache
- Supports 50+ holdings

## 📦 Dependencies

**Core:**
- prefect>=3.6.4
- pandas>=2.0.0
- numpy>=1.24.0
- pyarrow>=14.0.0
- streamlit>=1.28.0

**Analytics:**
- scikit-learn>=1.3.0
- scipy>=1.11.0
- ta-lib (technical analysis)

**Data:**
- requests>=2.31.0
- beautifulsoup4>=4.12.0
- lxml>=4.9.0

**Deployment:**
- Docker
- AWS ECS
- Kubernetes (optional)

## 🔄 Workflow Overview

```
Holdings (CSV) → Price Fetcher → ParquetDB (Prices)
                                    ↓
                         Technical Analysis → ParquetDB (Tech)
                                    ↓
                         Fundamental Analysis → ParquetDB (Fund)
                                    ↓
                         Portfolio Analytics → Dashboard / Email
                                    ↓
                         News Sentiment Analysis → Impact Report
```

## 📝 Getting Started

1. **New to the project?** Start with [docs/guides/QUICK_START.md](docs/guides/QUICK_START.md)
2. **Want to understand the architecture?** See [docs/architecture/ARCHITECTURE_OVERVIEW.md](docs/architecture/ARCHITECTURE_OVERVIEW.md)
3. **Looking for the roadmap?** Check [docs/FUTURE_WORK.md](docs/FUTURE_WORK.md)
4. **Full documentation index?** Visit [docs/INDEX.md](docs/INDEX.md)

## 🤝 Contributing

1. Ensure code follows project structure
2. Add tests for new functionality
3. Update documentation in `docs/`
4. Run full test suite before committing
5. Use `uv` for dependency management

---

**Last Updated:** December 11, 2025  
**Repository:** Finance TechStack  
**Main Branch:** main  
**Documentation:** [docs/INDEX.md](docs/INDEX.md)
