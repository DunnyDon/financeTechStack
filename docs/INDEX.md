# Documentation Index

Quick reference guide for the Finance TechStack project.

## Getting Started (5 minutes)

1. **[Quick Start](../README.md)** - Read the main README
2. **[Installation](INSTALL.md)** - Setup Python environment and config
3. **[Usage](USAGE.md)** - Run your first workflow

## Working with Code

- **[API Reference](API.md)** - Complete API documentation
- **[Testing Guide](TESTING.md)** - Run and write tests

## Deployment

- **[Deployment Guide](DEPLOY.md)** - Docker, AWS ECS, Kubernetes

## Common Tasks

| Task | Reference |
|------|-----------|
| Run portfolio analytics | [Usage: Portfolio Analytics](USAGE.md#1-portfolio-analytics--email-report) |
| Fetch financial data | [Usage: Financial Data](USAGE.md#2-fetch-financial-data) |
| Access price data | [API: PriceFetcher](API.md#pricefetcher) |
| Query SEC filings | [API: XBRL Functions](API.md#helper-functions) |
| Deploy to AWS | [Deploy: AWS ECS](DEPLOY.md#aws-ecs) |
| Run tests | [Testing: Quick Test](TESTING.md#quick-test) |

## File Structure

```
TechStack/
├── src/                          # Source code
│   ├── analytics_flows.py        # Portfolio analytics
│   ├── portfolio_flows.py        # Data aggregation
│   ├── portfolio_analytics.py    # P&L & metrics
│   ├── portfolio_holdings.py     # Position management
│   ├── portfolio_prices.py       # Price fetching
│   ├── portfolio_technical.py    # Technical indicators
│   ├── portfolio_fundamentals.py # Fundamental metrics
│   ├── xbrl.py                   # SEC XBRL parsing
│   ├── fx_rates.py               # Currency conversion
│   ├── parquet_db.py             # Data storage
│   ├── cache.py                  # Caching layer
│   └── config.py                 # Config management
│
├── tests/                        # Test suite
│
├── db/                           # Data storage (Parquet files)
│
├── config.csv                    # Configuration (user edits)
├── config.csv.template           # Config template
├── holdings.csv                  # Portfolio positions
├── pyproject.toml                # Python project config
└── README.md                     # Start here
```

## Environment Setup

**Requirements:**
- Python 3.13+
- `uv` package manager

**Installation:**
```bash
git clone <repo>
cd TechStack
uv sync
cp config.csv.template config.csv
# Edit config.csv with your API keys and email settings
```

## Main Workflows

| Workflow | Purpose | Command |
|----------|---------|---------|
| Enhanced Analytics | Portfolio P&L, signals, email | `python -c "from src.analytics_flows import enhanced_analytics_flow; enhanced_analytics_flow(send_email_report=True)"` |
| Data Aggregation | Fetch prices, SEC, fundamentals | `portfolio_flows.aggregate_financial_data_flow()` |
| Portfolio Analysis | Technical analysis, metrics | `portfolio_flows.portfolio_analysis_flow()` |

## Key Concepts

- **Parquet DB**: All data stored in Apache Parquet format with Snappy compression
- **Prefect Workflows**: Task orchestration with automatic retries and monitoring
- **Caching**: In-memory cache with configurable TTL to reduce API calls
- **Multi-broker Support**: DEGIRO, REVOLUT, Kraken position tracking
- **Email Reports**: HTML-formatted reports sent via SMTP

## Configuration

Edit `config.csv` to set:
- Email delivery (SMTP settings)
- API keys (Alpha Vantage, etc.)
- Application preferences

See [Installation](INSTALL.md#configuration) for detailed setup.

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Import errors | Run `uv sync` again |
| Email not sending | Check Gmail app password settings |
| API rate limits | Enable caching or use `force_refresh=False` |
| Parquet read errors | Clear cache: `rm -rf db/__pycache__` |

See individual documentation files for more detailed troubleshooting.

## Quick Commands

```bash
# Run everything
uv run pytest tests/ -v && uv run python -c "from src.analytics_flows import enhanced_analytics_flow; enhanced_analytics_flow(send_email_report=True)"

# Format code
uv run black src/ tests/ && uv run ruff check --fix src/ tests/

# Type checking
uv run mypy src/

# Monitor workflows
uv run prefect server start
# Visit http://localhost:4200
```

## Need Help?

1. Check the relevant documentation file above
2. See [Testing Guide](TESTING.md) to verify installation works
3. Run with verbose logging: `uv run pytest -vv`
4. Review inline code comments in `src/` files
