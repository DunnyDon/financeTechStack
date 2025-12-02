# Quick Reference

Central quick reference for Finance TechStack.

## 📖 Documentation Hub

**Start here:** [docs/INDEX.md](docs/INDEX.md) - Complete documentation index

### Core Docs
- [Installation](docs/INSTALL.md) - Setup instructions
- [Usage Guide](docs/USAGE.md) - How to run workflows  
- [API Reference](docs/API.md) - Function documentation
- [Testing](docs/TESTING.md) - Run and write tests
- [Deployment](docs/DEPLOY.md) - Production deployment

### Dask Parallelization (NEW ⭐)
- **[Phase 1 Expansion](docs/phase1/PHASE1_EXPANSION_COMPLETE.md)** - 3-5x faster analysis
- [Quick Start Commands](docs/phase1/QUICK_REFERENCE.md) - Run parallel flows
- [Complete Guide](docs/phase1/EXPANSION_GUIDE.md) - Architecture & details
- [Setup Instructions](docs/phase1/PHASE1_DASK_LOCAL_SETUP.md) - Local cluster setup

## 🚀 Common Commands

### Setup (one-time)
```bash
uv sync
cp config.csv.template config.csv
# Edit config.csv with your settings
```

### Prefect Server Management
```bash
# Start Prefect server and verify setup
uv run python scripts/prefect_manager.py start

# Deploy flows to dashboard
uv run python scripts/prefect_manager.py deploy

# Check server status
uv run python scripts/prefect_manager.py status

# Open dashboard at http://localhost:4200
```

### Run Main Workflows
```bash
# Portfolio Analytics (P&L + Signals + Email)
uv run python -c "from src.analytics_flows import enhanced_analytics_flow; enhanced_analytics_flow(send_email_report=True)"

# Parallel Analysis (NEW - 3-5x faster)
uv run python -c "from src.dask_integrated_flows import dask_combined_analysis_flow; print(dask_combined_analysis_flow(tickers=['AAPL', 'MSFT']))"

# Run Tests
uv run pytest tests/ -v

# Run with Coverage
uv run pytest tests/ --cov=src --cov-report=html
```

### Check Setup
```bash
# Verify Python version
python --version  # Should be 3.13+

# Verify dependencies
uv pip list | grep -E "prefect|dask|pandas"

# Verify config
cat config.csv | head -5
```

## 📋 Key Modules

| Module | Purpose |

|--------|---------|
| `analytics_flows.py` | Portfolio P&L + signals |
| `portfolio_flows.py` | Data aggregation orchestration |
| `portfolio_prices.py` | Price fetching |
| `portfolio_technical.py` | RSI, MACD, Bollinger Bands |
| `portfolio_fundamentals.py` | P/E, ROE, ROA, dividend yields |
| `xbrl.py` | SEC EDGAR filings parsing |
| `parquet_db.py` | Data storage (Parquet) |
| `cache.py` | Caching with TTL |

## Core Classes

```python
# Holdings Management
from src.portfolio_holdings import Holdings
h = Holdings("holdings.csv")
print(h.all_holdings)

# Price Fetching
from src.portfolio_prices import PriceFetcher
prices = PriceFetcher().fetch_prices(["AAPL", "MSFT"])

# Technical Indicators
from src.portfolio_technical import TechnicalAnalyzer
analyzer = TechnicalAnalyzer()
rsi = analyzer.calculate_rsi(prices_series)

# Fundamental Data
from src.portfolio_fundamentals import FundamentalAnalyzer
fundamentals = FundamentalAnalyzer().get_fundamentals("AAPL")

# Data Storage
from src.parquet_db import ParquetDB
db = ParquetDB()
df = db.load("prices")

# Caching
from src.cache import Cache
cache = Cache()
cache.set("key", value, ttl=3600)
```

## Configuration (config.csv)

```csv
report_email,your-email@example.com
sender_email,gmail@gmail.com
sender_password,app-password
smtp_host,smtp.gmail.com
smtp_port,587
alpha_vantage_key,YOUR_KEY
```

## Testing

```bash
uv run pytest tests/ -v                          # Run all tests
uv run pytest tests/ --cov=src --cov-report=html # With coverage
uv run pytest tests/test_portfolio_analytics.py  # Specific file
uv run pytest tests/ -k "pnl" -v                 # Specific test
```

## Code Quality

```bash
uv run black src/ tests/              # Format
uv run ruff check --fix src/ tests/   # Lint
uv run mypy src/                      # Type check
```

## Deployment

```bash
# Docker
docker build -t techstack . && docker run --env-file .env techstack

# AWS ECS - See docs/DEPLOY.md
# Kubernetes - See docs/DEPLOY.md
```

## Documentation

| Document | Purpose |
|----------|---------|
| [README.md](README.md) | Overview & quick start |
| [docs/INSTALL.md](docs/INSTALL.md) | Setup instructions |
| [docs/USAGE.md](docs/USAGE.md) | Workflow examples |
| [docs/API.md](docs/API.md) | API reference |
| [docs/DEPLOY.md](docs/DEPLOY.md) | Deployment guide |
| [docs/TESTING.md](docs/TESTING.md) | Testing guide |
| [docs/INDEX.md](docs/INDEX.md) | Documentation hub |

## Data Structure

**Holdings CSV** (holdings.csv)
```csv
ticker,shares,entry_price,currency,broker
AAPL,100,150.00,USD,DEGIRO
```

**Config CSV** (config.csv)
```csv
report_email,user@example.com
sender_email,gmail@gmail.com
sender_password,app-password
```

**Output Parquet**
- Schema: ticker, shares, current_price, pe_ratio, rsi, macd, pnl, date
- Compression: Snappy
- Location: db/

## Common Tasks

| Task | Command |
|------|---------|
| Get current prices | `PriceFetcher().fetch_prices(["AAPL", "MSFT"])` |
| Calculate P&L | `PortfolioAnalyzer().calculate_pnl()` |
| Get technical signals | `TechnicalAnalyzer().calculate_all_indicators()` |
| Fetch SEC data | `fetch_xbrl_filings("AAPL", ["10-K"])` |
| Save to Parquet | `ParquetDB().save(df, "prices")` |
| Schedule daily | Add cron: `0 16 * * * cd /path && uv run ...` |

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Import error | `uv sync` |
| Email not sending | Check Gmail app password |
| API rate limit | Use `force_refresh=False` for caching |
| Slow performance | Check cache TTL settings |

## Features

✓ Real-time portfolio P&L  
✓ Technical indicators (MACD, RSI, Bollinger Bands)  
✓ Fundamental metrics (P/E, ROE, ROA)  
✓ SEC EDGAR integration  
✓ Multi-broker support  
✓ Email HTML reports  
✓ Prefect orchestration  
✓ Parquet storage  
✓ Rate limiting  
✓ Docker ready  

## Next Steps

1. Run `uv sync`
2. Edit `config.csv`
3. Run `uv run pytest tests/ -v` (verify setup)
4. Run `enhanced_analytics_flow(send_email_report=True)` (test email)
5. See [docs/USAGE.md](docs/USAGE.md) for examples
