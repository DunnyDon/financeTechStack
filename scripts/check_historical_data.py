#!/usr/bin/env python
"""
Check historical price data collection status in ParquetDB.

Shows:
- How many days of data collected
- Which tickers have data
- Data freshness
"""

import sys
from pathlib import Path
from src.parquet_db import ParquetDB
import pandas as pd

def check_price_data():
    """Check price data collection status."""
    db = ParquetDB()
    
    print("\n" + "=" * 90)
    print("HISTORICAL PRICE DATA COLLECTION STATUS")
    print("=" * 90)
    
    try:
        # Read all price data
        prices = db.read_table('prices')
        
        if prices is None or prices.empty:
            print("❌ No price data collected yet")
            return
        
        print(f"\n📊 Total Records: {len(prices):,}")
        
        # Group by ticker
        ticker_groups = prices.groupby('symbol').size().sort_values(ascending=False)
        
        print(f"\n📈 Data Coverage: {len(ticker_groups)} tickers")
        print("\nTickers with Price Data:")
        print("-" * 90)
        
        for ticker, count in ticker_groups.head(15).items():
            ticker_data = prices[prices['symbol'] == ticker]
            first_date = ticker_data['timestamp'].min()
            latest_date = ticker_data['timestamp'].max()
            print(f"  {ticker:15} {count:4} days  ({first_date} to {latest_date})")
        
        # Overall stats
        print("\n📅 Overall Data Timeline:")
        print("-" * 90)
        earliest = prices['timestamp'].min()
        latest = prices['timestamp'].max()
        days_range = (pd.to_datetime(latest) - pd.to_datetime(earliest)).days + 1
        
        print(f"  First Data Point: {earliest}")
        print(f"  Latest Data Point: {latest}")
        print(f"  Date Range: {days_range} days")
        print(f"  Unique Dates: {prices['timestamp'].nunique()}")
        
        # Recommendations
        print("\n💡 Recommendations:")
        print("-" * 90)
        if days_range < 30:
            print(f"  ⚠️  Only {days_range} days collected. Run flow regularly to accumulate ~252 days for full risk analysis.")
        elif days_range < 60:
            print(f"  ⚠️  {days_range} days collected. Continue collecting for more accurate volatility calculations.")
        elif days_range < 252:
            print(f"  ℹ️  {days_range} days collected. Good progress. Target: 252 days (1 year) for reliable risk metrics.")
        else:
            print(f"  ✓ {days_range} days collected! Full year of data available for comprehensive risk analysis.")
        
        print("\n  Next Steps:")
        print("  1. Run portfolio_analytics_advanced_flow regularly (daily recommended)")
        print("  2. After ~30 days: Use for short-term risk analysis")
        print("  3. After ~252 days: Full risk calculations available")
        
        print("\n" + "=" * 90 + "\n")
        
    except Exception as e:
        print(f"❌ Error reading data: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_price_data()
