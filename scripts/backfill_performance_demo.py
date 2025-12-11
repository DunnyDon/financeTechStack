#!/usr/bin/env python
"""
Backfill Performance Comparison Utility

Demonstrates the performance improvement from Dask parallelization.
Compares sequential vs parallel execution times.

Usage:
    uv run python backfill_performance_demo.py
"""

import time
import sys
from datetime import datetime, timedelta
from typing import List, Dict
import pandas as pd

from src.portfolio_holdings import Holdings
from src.portfolio_prices import PriceFetcher
from src.parquet_db import ParquetDB
from src.utils import get_logger

logger = get_logger(__name__)


def get_portfolio_tickers(limit: int = None) -> List[str]:
    """Get valid tickers from portfolio holdings."""
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
        
        if limit:
            valid_tickers = valid_tickers[:limit]
        
        return valid_tickers
    
    except Exception as e:
        logger.error(f"Error loading portfolio: {e}")
        return []


def benchmark_sequential(tickers: List[str], days: int = 90) -> Dict:
    """
    Benchmark sequential (non-parallel) execution.
    This simulates the old behavior before Dask.
    """
    fetcher = PriceFetcher()
    db = ParquetDB()
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    print(f"\n{'='*80}")
    print("SEQUENTIAL EXECUTION (Original - No Parallelization)")
    print(f"{'='*80}")
    print(f"Tickers: {len(tickers)}")
    print(f"Date range: {start_date.date()} to {end_date.date()}")
    
    times = []
    total_start = time.time()
    
    for i, ticker in enumerate(tickers, 1):
        ticker_start = time.time()
        print(f"[{i:2d}/{len(tickers)}] {ticker:15} ... ", end="", flush=True)
        
        try:
            # Simulate gap detection (simplified)
            price_data = fetcher.fetch_historical(
                ticker,
                start_date=start_date.strftime("%Y-%m-%d"),
                end_date=end_date.strftime("%Y-%m-%d")
            )
            
            ticker_time = time.time() - ticker_start
            times.append(ticker_time)
            
            if price_data is not None and len(price_data) > 0:
                print(f"✓ ({ticker_time:.2f}s)")
            else:
                print(f"⚠️  no data ({ticker_time:.2f}s)")
        
        except Exception as e:
            ticker_time = time.time() - ticker_start
            times.append(ticker_time)
            print(f"❌ error ({ticker_time:.2f}s)")
    
    total_time = time.time() - total_start
    
    return {
        "type": "sequential",
        "tickers": len(tickers),
        "total_time": total_time,
        "times": times,
        "avg_time_per_ticker": total_time / len(tickers) if tickers else 0
    }


def benchmark_parallel(tickers: List[str], days: int = 90, workers: int = 4) -> Dict:
    """
    Benchmark parallel (Dask) execution.
    This uses the new optimized implementation.
    """
    from dask import delayed
    import dask
    from dask.diagnostics import ProgressBar
    
    @delayed
    def fetch_ticker(ticker: str) -> float:
        """Delayed task for single ticker."""
        fetcher = PriceFetcher()
        ticker_start = time.time()
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        try:
            fetcher.fetch_historical(
                ticker,
                start_date=start_date.strftime("%Y-%m-%d"),
                end_date=end_date.strftime("%Y-%m-%d")
            )
        except Exception:
            pass
        
        return time.time() - ticker_start
    
    print(f"\n{'='*80}")
    print("PARALLEL EXECUTION (Dask - WITH Parallelization)")
    print(f"{'='*80}")
    print(f"Tickers: {len(tickers)}")
    print(f"Workers: {workers}")
    print(f"Date range: {datetime.now().date()} ± {days} days")
    
    # Create delayed tasks
    tasks = [fetch_ticker(ticker) for ticker in tickers]
    
    # Execute in parallel
    print("\n🚀 Executing in parallel...")
    total_start = time.time()
    
    with ProgressBar(dt=0.5):
        times = dask.compute(*tasks, scheduler="threads", num_workers=workers)
    
    total_time = time.time() - total_start
    
    return {
        "type": "parallel",
        "tickers": len(tickers),
        "workers": workers,
        "total_time": total_time,
        "times": list(times),
        "avg_time_per_ticker": total_time / len(tickers) if tickers else 0
    }


def print_comparison(seq_result: Dict, par_result: Dict):
    """Print comparison of sequential vs parallel results."""
    print(f"\n{'='*80}")
    print("PERFORMANCE COMPARISON")
    print(f"{'='*80}")
    
    speedup = seq_result["total_time"] / par_result["total_time"]
    time_saved = seq_result["total_time"] - par_result["total_time"]
    cpu_util_seq = 100 / seq_result["total_time"] * seq_result["avg_time_per_ticker"]  # Rough estimate
    
    print(f"\nSequential Execution:")
    print(f"  Total Time:     {seq_result['total_time']:7.2f} seconds")
    print(f"  Avg per ticker: {seq_result['avg_time_per_ticker']:7.2f} seconds")
    print(f"  Tickers:        {seq_result['tickers']:7d}")
    
    print(f"\nParallel Execution (Dask):")
    print(f"  Total Time:     {par_result['total_time']:7.2f} seconds")
    print(f"  Avg per ticker: {par_result['avg_time_per_ticker']:7.2f} seconds")
    print(f"  Tickers:        {par_result['tickers']:7d}")
    print(f"  Workers:        {par_result.get('workers', 'auto'):7}")
    
    print(f"\n📊 RESULTS:")
    print(f"  Speedup:        {speedup:7.2f}x faster")
    print(f"  Time Saved:     {time_saved:7.2f} seconds")
    print(f"  Efficiency:     {(speedup / par_result.get('workers', 4)) * 100:6.1f}%")
    
    if speedup > 2:
        print(f"\n✅ EXCELLENT! Dask parallelization is highly effective for this workload!")
    elif speedup > 1.5:
        print(f"\n✅ GOOD! Dask provides significant speedup!")
    else:
        print(f"\n⚠️  Limited speedup - consider I/O or network bottlenecks")


def main():
    """Run performance comparison benchmark."""
    
    print("\n" + "="*80)
    print("BACKFILL PERFORMANCE BENCHMARKING UTILITY")
    print("="*80)
    print("\nThis utility demonstrates the performance improvement from Dask parallelization.")
    print("It will run two tests: sequential and parallel execution.\n")
    
    # Get tickers (use first 10 for reasonable benchmark time)
    tickers = get_portfolio_tickers(limit=10)
    
    if not tickers:
        logger.error("No tickers available for benchmarking")
        sys.exit(1)
    
    print(f"Using tickers: {', '.join(tickers[:5])}{'...' if len(tickers) > 5 else ''}")
    
    # Run benchmarks
    print("\n⏱️  Running sequential benchmark (this will take a while)...")
    seq_result = benchmark_sequential(tickers, days=90)
    
    print("\n⏱️  Running parallel benchmark (with Dask)...")
    par_result = benchmark_parallel(tickers, days=90, workers=4)
    
    # Compare results
    print_comparison(seq_result, par_result)
    
    print(f"\n{'='*80}")
    print("BENCHMARK COMPLETE")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()
