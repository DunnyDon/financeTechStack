#!/usr/bin/env bash
# Run the Finance TechStack Analytics Dashboard with Prefect logging

cd "$(dirname "$0")"

echo "🚀 Starting Finance TechStack Analytics Dashboard..."
echo "📊 Dashboard: http://localhost:8501"
echo "📋 Prefect UI: http://localhost:4200"
echo ""
echo "Prefect server will start in background..."
echo "Press Ctrl+C to stop all services"
echo ""

# Ensure virtual environment is activated
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
fi

# Start Prefect server in background (if not already running)
echo "Starting Prefect server..."
if ! curl -s http://localhost:4200 > /dev/null 2>&1; then
    uv run python -m prefect server start > /tmp/prefect_server.log 2>&1 &
    PREFECT_PID=$!
    echo "Prefect server starting (PID: $PREFECT_PID)"
    sleep 3  # Give Prefect time to start
else
    echo "Prefect server already running"
fi

# Refresh price data before starting dashboard
echo ""
echo "🔄 Checking for today's price data..."
uv run python << 'PYTHON_EOF'
import sys
from src.portfolio_prices import PriceFetcher
from src.parquet_db import ParquetDB
import pandas as pd
from datetime import datetime, date

try:
    db = ParquetDB(root_path="db")
    today = date.today()
    
    # Check if we have price data for today
    prices = db.read_table('prices')
    if prices is not None and not prices.empty:
        prices['date'] = pd.to_datetime(prices['timestamp']).dt.date
        latest_date = prices['date'].max()
        
        if latest_date == today:
            print(f"✅ Price data for today ({today}) already exists. Skipping refresh.")
            sys.exit(0)
        else:
            print(f"⚠️ Latest price data is from {latest_date}, fetching fresh data...")
    else:
        print("No price data found, fetching...")
    
    # Load holdings
    holdings = pd.read_csv('holdings.csv')
    if holdings is None or holdings.empty:
        print("❌ Could not load holdings")
        sys.exit(1)
    
    tickers = holdings['sym'].unique().tolist()
    print(f"Fetching prices for {len(tickers)} symbols...")
    
    price_fetcher = PriceFetcher()
    
    # Fetch prices for all tickers
    all_prices = []
    failed = 0
    
    for idx, ticker in enumerate(tickers):
        try:
            # Determine asset type
            holding = holdings[holdings['sym'] == ticker]
            if not holding.empty:
                asset_type = holding.iloc[0]['asset']
                if asset_type not in ['crypto', 'commodity']:
                    asset_type = 'eq'
            else:
                asset_type = 'eq'
            
            price_data = price_fetcher.fetch_price(ticker, asset_type=asset_type)
            if price_data:
                all_prices.append(price_data)
            else:
                failed += 1
        except Exception as e:
            failed += 1
            continue
    
    if all_prices:
        # Convert to DataFrame with single batch timestamp
        prices_df = pd.DataFrame(all_prices)
        batch_timestamp = datetime.now()
        prices_df['timestamp'] = batch_timestamp
        
        # Map column names
        if 'price' in prices_df.columns and 'close_price' not in prices_df.columns:
            prices_df['close_price'] = prices_df['price']
        if 'open' in prices_df.columns and 'open_price' not in prices_df.columns:
            prices_df['open_price'] = prices_df['open']
        if 'high' in prices_df.columns and 'high_price' not in prices_df.columns:
            prices_df['high_price'] = prices_df['high']
        if 'low' in prices_df.columns and 'low_price' not in prices_df.columns:
            prices_df['low_price'] = prices_df['low']
        if 'close' in prices_df.columns and 'close_price' not in prices_df.columns:
            prices_df['close_price'] = prices_df['close']
        
        # Add missing columns
        if 'currency' not in prices_df.columns:
            prices_df['currency'] = 'USD'
        if 'frequency' not in prices_df.columns:
            prices_df['frequency'] = 'daily'
        
        db.upsert_prices(prices_df)
        print(f"✅ Updated {len(all_prices)} prices" + (f" ({failed} failed)" if failed > 0 else ""))
    else:
        print(f"⚠️ Could not fetch any prices ({failed} symbols attempted)")
except Exception as e:
    print(f"⚠️ Price refresh failed: {str(e)[:100]}")
PYTHON_EOF

echo ""

# Cleanup function to stop Prefect when dashboard stops
cleanup() {
    echo ""
    echo "🛑 Stopping services..."
    if [ ! -z "$PREFECT_PID" ]; then
        kill $PREFECT_PID 2>/dev/null
    fi
    exit 0
}

trap cleanup SIGINT SIGTERM

# Run Streamlit app
uv run streamlit run app.py \
    --logger.level=info \
    --theme.base="light" \
    --client.toolbarMode="minimal"
