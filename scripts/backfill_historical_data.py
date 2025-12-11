#!/usr/bin/env python
"""
Historical Price Data Backfill Utility

Backfills historical price data for the past 252 days (1 year).
Intelligently identifies gaps in existing data and fills them.
Saves all data to ParquetDB for persistent storage.

Usage:
    uv run python backfill_historical_data.py [--tickers TICKER1,TICKER2] [--days 252]
    
    # Backfill all portfolio tickers
    uv run python backfill_historical_data.py
    
    # Backfill specific tickers
    uv run python backfill_historical_data.py --tickers MSFT,AAPL,TSLA
    
    # Backfill only 90 days
    uv run python backfill_historical_data.py --days 90
"""

import argparse
import sys
import os
from datetime import datetime, timedelta
from typing import List, Set, Dict, Optional, Tuple
import pandas as pd
from dask import delayed
import dask
from dask.diagnostics import ProgressBar

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.portfolio_holdings import Holdings
from src.portfolio_prices import PriceFetcher
from src.parquet_db import ParquetDB
from src.utils import get_logger


logger = get_logger(__name__)


def get_portfolio_tickers() -> List[str]:
    """Get all valid tickers from portfolio holdings, plus S&P 500 benchmark."""
    try:
        holdings = Holdings()
        holdings_df = holdings.all_holdings
        
        if holdings_df.empty:
            logger.error("No holdings found")
            return ['^GSPC']  # Still fetch S&P 500 for benchmarking
        
        # Filter out only manual and savings holdings
        # Crypto tickers with -USD suffix are now yfinance-compatible
        skip_keywords = ["MANUAL", "SAVINGS"]
        valid_tickers = []
        
        for ticker in holdings_df["sym"].unique():
            if not any(keyword in str(ticker).upper() for keyword in skip_keywords):
                valid_tickers.append(ticker)
        
        # Add S&P 500 as benchmark for alpha/beta calculations
        if '^GSPC' not in valid_tickers:
            valid_tickers.append('^GSPC')
        
        logger.info(f"✓ Found {len(valid_tickers) - 1} portfolio tickers + S&P 500 benchmark")
        return valid_tickers
    
    except Exception as e:
        logger.error(f"Error loading portfolio: {e}")
        return ['^GSPC']  # Return at least S&P 500


def get_data_gaps(db: ParquetDB, ticker: str, start_date: datetime, end_date: datetime) -> List[tuple]:
    """
    Identify gaps in existing data.
    
    Returns list of (gap_start, gap_end) tuples for missing date ranges.
    """
    try:
        # Read existing data for ticker
        existing = db.read_table(
            'prices',
            filters=[('symbol', '==', ticker)],
            columns=['timestamp']
        )
        
        if existing is None or existing.empty:
            # No data at all - entire range is a gap
            return [(start_date.date(), end_date.date())]
        
        # Convert to datetime and sort
        existing['timestamp'] = pd.to_datetime(existing['timestamp'])
        existing_dates = set(existing['timestamp'].dt.date)
        
        # Generate all expected trading days (simplified: weekdays only)
        current = start_date.date()
        all_dates = []
        while current <= end_date.date():
            # Weekday: 0=Monday, 4=Friday
            if current.weekday() < 5:
                all_dates.append(current)
            current += timedelta(days=1)
        
        # Find gaps
        missing_dates = [d for d in all_dates if d not in existing_dates]
        
        if not missing_dates:
            return []
        
        # Group consecutive missing dates into ranges
        gaps = []
        gap_start = missing_dates[0]
        gap_end = missing_dates[0]
        
        for date in missing_dates[1:]:
            if (date - gap_end).days == 1:
                gap_end = date
            else:
                gaps.append((gap_start, gap_end))
                gap_start = date
                gap_end = date
        
        # Add final gap
        gaps.append((gap_start, gap_end))
        
        return gaps
    
    except Exception as e:
        logger.debug(f"Could not read existing data for {ticker}: {e}")
        # Return entire range as gap if there's an error
        return [(start_date.date(), end_date.date())]


@delayed
def fetch_and_save_ticker(
    ticker: str,
    start_date: datetime,
    end_date: datetime,
    auto_gaps: bool = True
) -> Dict:
    """
    Delayed Dask task to fetch historical data for a single ticker (FETCH ONLY, NO WRITE).
    
    Args:
        ticker: Ticker symbol
        start_date: Start date for backfill
        end_date: End date for backfill
        auto_gaps: Whether to use gap detection
    
    Returns:
        Dict with fetched data for this ticker
    """
    fetcher = PriceFetcher()
    db = ParquetDB()
    
    try:
        if auto_gaps:
            gaps = get_data_gaps(db, ticker, start_date, end_date)
            if not gaps:
                return {"ticker": ticker, "status": "complete", "records": 0, "source": "existing", "data": None}
            
            # Fetch only for gap periods
            all_data = []
            gap_errors = []
            
            for gap_start_date, gap_end_date in gaps:
                price_data = fetcher.fetch_historical(
                    ticker,
                    start_date=gap_start_date.strftime("%Y-%m-%d"),
                    end_date=gap_end_date.strftime("%Y-%m-%d")
                )
                
                # Handle None (market holiday) vs actual data
                if price_data is None:
                    # No data available - likely a market holiday
                    gap_errors.append({
                        'gap': f"{gap_start_date} to {gap_end_date}",
                        'reason': 'likely_market_holiday'
                    })
                    continue
                
                if len(price_data) > 0:
                    all_data.append(price_data)
            
            if all_data:
                # Combine all data
                combined_data = pd.concat(all_data, ignore_index=True)
                return {"ticker": ticker, "status": "fetched", "records": len(combined_data), "data": combined_data, "gap_errors": len(gap_errors)}
            elif gap_errors and len(gap_errors) == len(gaps):
                return {"ticker": ticker, "status": "complete", "records": 0, "reason": "gaps_are_market_holidays", "data": None}
            else:
                return {"ticker": ticker, "status": "no_data", "records": 0, "data": None}
        
        else:
            # Full backfill (overwrite)
            price_data = fetcher.fetch_historical(ticker, period="1y")
            
            if price_data is not None and len(price_data) > 0:
                return {"ticker": ticker, "status": "fetched", "records": len(price_data), "data": price_data}
            else:
                return {"ticker": ticker, "status": "no_data", "records": 0, "data": None}
    
    except Exception as e:
        logger.error(f"Error processing {ticker}: {e}")
        return {"ticker": ticker, "status": "error", "error": str(e), "data": None}


def fetch_and_save_historical(
    tickers: List[str],
    days: int = 252,
    auto_gaps: bool = True,
    n_workers: Optional[int] = None
) -> Dict[str, Dict]:
    """
    Fetch historical data in parallel, then write sequentially to avoid race conditions.
    
    Args:
        tickers: List of ticker symbols
        days: Number of days to backfill
        auto_gaps: Whether to automatically detect and fill gaps
        n_workers: Number of Dask workers (None = auto-detect)
    
    Returns:
        Dict with results for each ticker
    """
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    logger.info(f"🔄 Starting backfill for {len(tickers)} tickers ({days} days)")
    logger.info(f"   Date range: {start_date.date()} to {end_date.date()}")
    logger.info("   Strategy: Parallel fetch, sequential write (prevents Parquet corruption)")
    
    if auto_gaps:
        logger.info("   Mode: Smart gap detection")
    else:
        logger.info("   Mode: Full backfill")
    
    print("\n" + "=" * 100)
    print("HISTORICAL DATA BACKFILL (PARALLEL FETCH + SEQUENTIAL WRITE)")
    print(f"Date Range: {start_date.date()} to {end_date.date()} ({days} days)")
    print(f"Workers: {n_workers or 'auto-detect'}")
    print(f"Tickers: {len(tickers)}")
    print("=" * 100)
    
    # PHASE 1: Fetch data in parallel (no I/O conflicts)
    print(f"\n📊 PHASE 1: Parallel fetch of price data...")
    
    # Create delayed tasks for each ticker
    tasks = [
        fetch_and_save_ticker(ticker, start_date, end_date, auto_gaps)
        for ticker in tickers
    ]
    
    # Execute all tasks in parallel
    print(f"\n🚀 Launching {len(tasks)} parallel fetch tasks...")
    
    # Determine scheduler
    scheduler = "threads"
    
    # Compute results with progress bar
    with ProgressBar(dt=0.5):
        results_list = dask.compute(*tasks, scheduler=scheduler, num_workers=n_workers)
    
    # Convert list of dicts to keyed dict
    results = {r["ticker"]: r for r in results_list}
    
    # PHASE 2: Write data sequentially to avoid Parquet corruption
    print(f"\n💾 PHASE 2: Sequential write to ParquetDB...")
    db = ParquetDB()
    total_written = 0
    write_errors = []
    
    for ticker, result in results.items():
        if result.get("status") == "fetched" and result.get("data") is not None:
            try:
                # Prepare data for storage
                save_data = result["data"].copy()
                
                # Normalize column names to lowercase
                save_data.columns = [col.lower().strip() for col in save_data.columns]
                
                # Select and rename required columns
                required_cols = {
                    'date': 'timestamp',
                    'open': 'open_price',
                    'high': 'high_price',
                    'low': 'low_price',
                    'close': 'close_price',
                    'volume': 'volume'
                }
                
                # Build dataframe with only required columns
                new_data = {}
                for src_col, dst_col in required_cols.items():
                    if src_col in save_data.columns:
                        new_data[dst_col] = save_data[src_col]
                
                save_data = pd.DataFrame(new_data)
                save_data['symbol'] = ticker
                save_data['currency'] = 'USD'
                save_data['frequency'] = 'daily'
                
                # Ensure timestamp is datetime and strip timezone
                if 'timestamp' in save_data.columns:
                    save_data['timestamp'] = pd.to_datetime(save_data['timestamp']).dt.tz_localize(None)
                
                # Save to DB (sequential - no race conditions)
                inserted, updated = db.upsert_prices(save_data)
                total_written += inserted + updated
                result["status"] = "saved"
                result["records"] = inserted + updated
                
            except Exception as e:
                logger.error(f"Error writing {ticker}: {e}")
                write_errors.append((ticker, str(e)))
                result["status"] = "write_error"
                result["error"] = str(e)
    
    # Summary
    print("\n" + "=" * 100)
    print("BACKFILL SUMMARY")
    print("=" * 100)
    
    saved = sum(1 for r in results.values() if r["status"] == "saved")
    completed = sum(1 for r in results.values() if r["status"] in ["complete", "saved"])
    failed = sum(1 for r in results.values() if r["status"] in ["error", "no_data", "write_error"])
    total_records = sum(r.get("records", 0) for r in results.values() if r["status"] == "saved")
    
    print(f"\n✓ Successful: {completed}/{len(tickers)}")
    print(f"  └─ Written to DB: {saved} tickers, {total_records:,} records")
    print(f"⚠️  Failed: {failed}/{len(tickers)}")
    
    # Show failed tickers
    failed_tickers = [t for t, r in results.items() if r["status"] in ["error", "no_data", "write_error"]]
    if failed_tickers:
        print(f"\nFailed tickers: {', '.join(failed_tickers)}")
    
    if completed > 0:
        print("\n✅ Price backfill complete! Data is ready for analytics.")
        
        # PHASE 3: Calculate technical indicators
        print("\n" + "=" * 100)
        print("PHASE 3: Technical Analysis Calculation")
        print("=" * 100)
        print(f"\n🔧 Calculating technical indicators for {len(tickers)} tickers...")
        
        try:
            from app import run_technical_analysis
            run_technical_analysis()
            print("✅ Technical indicators calculated successfully!")
        except ImportError:
            logger.warning("Could not import run_technical_analysis - skipping technical analysis")
        except Exception as e:
            logger.error(f"Error calculating technical indicators: {e}")
    
    return results


def main():
    parser = argparse.ArgumentParser(
        description="Backfill historical price data to ParquetDB (with Dask parallelization)"
    )
    parser.add_argument(
        "--tickers",
        type=str,
        default=None,
        help="Comma-separated list of tickers (default: all portfolio holdings)"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=252,
        help="Number of days to backfill (default: 252)"
    )
    parser.add_argument(
        "--no-gaps",
        action="store_true",
        help="Disable smart gap detection (full backfill all tickers)"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=None,
        help="Number of parallel workers (default: auto-detect)"
    )
    
    args = parser.parse_args()
    
    # Determine tickers
    if args.tickers:
        tickers = [t.strip().upper() for t in args.tickers.split(",")]
        logger.info(f"Using specified tickers: {', '.join(tickers)}")
    else:
        tickers = get_portfolio_tickers()
        if not tickers:
            logger.error("No tickers to backfill")
            sys.exit(1)
    
    # Run backfill with Dask parallelization
    results = fetch_and_save_historical(
        tickers=tickers,
        days=args.days,
        auto_gaps=not args.no_gaps,
        n_workers=args.workers
    )
    
    # Check if any failed
    failed = sum(1 for r in results.values() if r["status"] in ["error", "no_data"])
    if failed > 0:
        logger.warning(f"{failed} tickers had issues")


if __name__ == "__main__":
    main()
