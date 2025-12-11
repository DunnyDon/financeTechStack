#!/usr/bin/env python
"""
Fix data gaps for specific dates with missing or incomplete price data.

This script identifies and refetches price data for dates where the coverage
is incomplete, ensuring all portfolio symbols have prices.
"""

import sys
import os
from datetime import datetime, timedelta
import pandas as pd

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.portfolio_holdings import Holdings
from src.portfolio_prices import PriceFetcher
from src.parquet_db import ParquetDB
from src.utils import get_logger

logger = get_logger(__name__)


def get_portfolio_tickers() -> list:
    """Get all valid tickers from portfolio holdings."""
    try:
        holdings = Holdings()
        holdings_df = holdings.all_holdings
        
        if holdings_df.empty:
            logger.error("No holdings found")
            return []
        
        # Filter out non-tradable holdings
        skip_keywords = ["MANUAL", "BITCOIN", "ETHEREUM", "CRYPTO", "SAVINGS"]
        valid_tickers = []
        
        for ticker in holdings_df["sym"].unique():
            if not any(keyword in str(ticker).upper() for keyword in skip_keywords):
                valid_tickers.append(ticker)
        
        logger.info(f"✓ Found {len(valid_tickers)} valid portfolio tickers")
        return valid_tickers
    
    except Exception as e:
        logger.error(f"Error loading portfolio: {e}")
        return []


def identify_incomplete_dates(db: ParquetDB, tickers: list) -> dict:
    """
    Identify dates with incomplete symbol coverage.
    
    Returns dict with date -> list of missing symbols
    """
    prices = db.read_table('prices')
    if prices is None or prices.empty:
        return {}
    
    prices['date'] = pd.to_datetime(prices['timestamp']).dt.date
    all_dates = sorted(prices['date'].unique())
    
    incomplete_dates = {}
    
    for date in all_dates:
        date_symbols = set(prices[prices['date'] == date]['symbol'].unique())
        missing = set(tickers) - date_symbols
        
        # Only flag dates missing 3+ symbols (data quality issue)
        if len(missing) >= 3:
            incomplete_dates[date] = sorted(missing)
    
    return incomplete_dates


def fetch_price_for_date(ticker: str, target_date: datetime) -> dict:
    """Fetch price for a specific ticker and date."""
    try:
        fetcher = PriceFetcher()
        
        # Determine asset type
        holdings = pd.read_csv('holdings.csv')
        holding = holdings[holdings['sym'] == ticker]
        
        if not holding.empty:
            asset_type = holding.iloc[0]['asset']
            if asset_type not in ['crypto', 'commodity']:
                asset_type = 'eq'
        else:
            asset_type = 'eq'
        
        # Fetch price - this gets the latest available price
        price_data = fetcher.fetch_price(ticker, asset_type=asset_type)
        
        if price_data:
            price_data['timestamp'] = target_date
            return price_data
        return None
        
    except Exception as e:
        logger.warning(f"Failed to fetch {ticker}: {str(e)[:50]}")
        return None


def fix_incomplete_dates(db: ParquetDB, problem_dates: list):
    """
    Refetch prices for specific dates with incomplete data.
    
    Args:
        db: ParquetDB instance
        problem_dates: List of dates to fix (datetime.date objects)
    """
    if not problem_dates:
        print("✅ No incomplete dates found")
        return
    
    tickers = get_portfolio_tickers()
    if not tickers:
        print("❌ No tickers found")
        return
    
    print(f"\n🔧 Fixing {len(problem_dates)} dates with incomplete data:")
    print("=" * 80)
    
    for problem_date in problem_dates:
        print(f"\n📅 Processing {problem_date}...")
        
        # Get all prices for this date
        all_prices = []
        failed = 0
        
        for ticker in tickers:
            try:
                price_data = fetch_price_for_date(ticker, problem_date)
                if price_data:
                    all_prices.append(price_data)
                else:
                    failed += 1
            except Exception as e:
                failed += 1
                continue
        
        if all_prices:
            # Convert to DataFrame
            prices_df = pd.DataFrame(all_prices)
            batch_timestamp = datetime.combine(problem_date, datetime.min.time())
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
            
            # Add missing columns
            if 'currency' not in prices_df.columns:
                prices_df['currency'] = 'USD'
            if 'frequency' not in prices_df.columns:
                prices_df['frequency'] = 'daily'
            
            # Upsert to database
            db.upsert_prices(prices_df)
            print(f"  ✅ Updated {len(all_prices)} prices" + (f" ({failed} failed)" if failed > 0 else ""))
        else:
            print(f"  ❌ Failed to fetch any prices for {problem_date}")


def main():
    """Main entry point."""
    print("\n" + "=" * 80)
    print("PRICE DATA GAP FIXER")
    print("=" * 80)
    
    db = ParquetDB()
    tickers = get_portfolio_tickers()
    
    if not tickers:
        print("❌ Could not load portfolio tickers")
        sys.exit(1)
    
    # Identify incomplete dates
    print("\n🔍 Scanning for incomplete dates...")
    incomplete_dates = identify_incomplete_dates(db, tickers)
    
    if not incomplete_dates:
        print("✅ All dates have complete data!")
        sys.exit(0)
    
    print(f"\n⚠️  Found {len(incomplete_dates)} dates with incomplete data:")
    for date, missing in sorted(incomplete_dates.items()):
        print(f"  {date}: Missing {len(missing)} symbols - {', '.join(missing[:5])}" + 
              (f"... (+{len(missing)-5} more)" if len(missing) > 5 else ""))
    
    # Fix specific problem dates we know about
    problem_dates = [
        datetime.strptime('2025-11-20', '%Y-%m-%d').date(),
        datetime.strptime('2025-12-06', '%Y-%m-%d').date(),
        datetime.strptime('2025-12-07', '%Y-%m-%d').date(),
    ]
    
    print(f"\n🔧 Targeting known problem dates for fix: {problem_dates}")
    fix_incomplete_dates(db, problem_dates)
    
    print("\n" + "=" * 80)
    print("✅ Data gap fix complete!")
    print("=" * 80)


if __name__ == "__main__":
    main()
