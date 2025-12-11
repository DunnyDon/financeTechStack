# Installation & Setup

## Prerequisites

- **Python 3.13 or higher**
- **uv** package manager ([install](https://docs.astral.sh/uv/getting-started/))

## Installation

```bash
# Clone repository
git clone https://github.com/DunnyDon/financeTechStack.git
cd TechStack

# Install dependencies
uv sync
```

## Configuration

### 1. Create Config File

```bash
cp config.csv.template config.csv
```

### 2. Configure API Keys & Email

Edit `config.csv`:

```csv
# Email settings for report delivery
report_email,your-email@example.com
sender_email,gmail-account@gmail.com
sender_password,your-app-specific-password
smtp_host,smtp.gmail.com
smtp_port,587

# Financial data APIs
alpha_vantage_key,your-key
```

**Email Setup (Gmail):**
1. Enable 2-factor authentication on your Google account
2. Create an [App Password](https://myaccount.google.com/apppasswords)
3. Use the app password in `sender_password`

### 3. Portfolio Holdings

Create/update `holdings.csv` with your positions:

```csv
ticker,shares,entry_price,currency,broker
AAPL,100,150.00,USD,DEGIRO
MSFT,50,300.00,USD,REVOLUT
BTC,0.5,45000.00,USD,KRAKEN
```

## Environment Variables (Optional)

Export as environment variables instead of using `config.csv`:

```bash
export REPORT_EMAIL="your-email@example.com"
export ALPHA_VANTAGE_KEY="your-key"
export SENDER_EMAIL="gmail@gmail.com"
export SENDER_PASSWORD="app-password"
```

## Verification

```bash
# Run tests to verify installation
uv run pytest tests/ -v

# Test portfolio loading
uv run python -c "from src.portfolio_holdings import Holdings; h = Holdings('holdings.csv'); print(f'Holdings: {len(h.all_holdings)}')"
```

## Docker

Build and run with Docker:

```bash
docker build -t techstack .
docker run --env-file .env techstack uv run python src/analytics_flows.py
```

See [DEPLOY.md](DEPLOY.md) for full deployment options.

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError: No module named 'src'` | Run `uv sync` again |
| Email not sending | Verify Gmail 2FA and app password settings |
| Alpha Vantage rate limit | Free tier: 5 req/min. Use `cache.py` for repeated lookups |
| API connection errors | Check network, verify API keys in `config.csv` |
