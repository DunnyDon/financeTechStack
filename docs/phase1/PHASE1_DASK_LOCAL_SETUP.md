# Phase 1: Local Dask Integration - Quick Start

## Overview

This guide walks you through adding Dask to your local development environment in 30-60 minutes.

**End Goal**: Run Prefect flows with distributed Dask execution on your machine.

---

## Step 1: Create Dask Docker Compose File

Create `docker/docker-compose.dask.yml`:

```yaml
version: '3.8'

services:
  dask-scheduler:
    image: daskdev/dask:latest
    container_name: techstack-dask-scheduler
    hostname: dask-scheduler
    command: dask-scheduler --port 8786 --bokeh-port 8787
    ports:
      - "8786:8786"  # Scheduler communication port
      - "8787:8787"  # Bokeh dashboard
    environment:
      DASK_SCHEDULER__TASKS__LOG_LENGTH: 100000
      DASK_SCHEDULER__ALLOWED_FAILURES: 5
      DASK_SCHEDULER__BANDWIDTH: 100000000  # 100 MB/s
    networks:
      - techstack-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8786/health"]
      interval: 10s
      timeout: 5s
      retries: 3
      start_period: 10s

  dask-worker-1:
    image: daskdev/dask:latest
    container_name: techstack-dask-worker-1
    hostname: dask-worker-1
    command: >
      dask-worker
      --scheduler-address tcp://dask-scheduler:8786
      --nworkers 1
      --nthreads 4
      --memory-limit 2GB
      --worker-port 8788
      --nanny-port 8789
    ports:
      - "8788:8788"
      - "8789:8789"
    environment:
      DASK_WORKER__MEMORY__TARGET: 0.85
      DASK_WORKER__MEMORY__SPILL: 0.9
      DASK_WORKER__MEMORY__PAUSE: 0.95
    depends_on:
      dask-scheduler:
        condition: service_healthy
    networks:
      - techstack-network

  dask-worker-2:
    image: daskdev/dask:latest
    container_name: techstack-dask-worker-2
    hostname: dask-worker-2
    command: >
      dask-worker
      --scheduler-address tcp://dask-scheduler:8786
      --nworkers 1
      --nthreads 4
      --memory-limit 2GB
      --worker-port 8790
      --nanny-port 8791
    ports:
      - "8790:8790"
      - "8791:8791"
    environment:
      DASK_WORKER__MEMORY__TARGET: 0.85
      DASK_WORKER__MEMORY__SPILL: 0.9
      DASK_WORKER__MEMORY__PAUSE: 0.95
    depends_on:
      dask-scheduler:
        condition: service_healthy
    networks:
      - techstack-network

networks:
  techstack-network:
    external: true
```

---

## Step 2: Update pyproject.toml

Add Dask dependencies:

```toml
[project]
# ... existing config ...
dependencies = [
    # ... existing ...
    "dask[distributed]>=2024.1.0",
    "dask-distributed>=2024.1.0",
    "bokeh>=3.0",  # Dask dashboard
]

[project.optional-dependencies]
dask = [
    "dask[distributed]>=2024.1.0",
    "dask-distributed>=2024.1.0",
    "bokeh>=3.0",
]
```

Then install:
```bash
uv pip install -e ".[dask]"
```

---

## Step 3: Create Dask Integration Module

Create `src/dask_integration.py`:

```python
"""
Dask distributed computing integration for Prefect flows.
"""

from typing import Optional, Dict, Any
from functools import lru_cache
import logging

from dask.distributed import Client, as_completed
import dask.dataframe as dd
import pandas as pd
from prefect import task, get_run_logger

logger = logging.getLogger(__name__)


class DaskClientManager:
    """Manages Dask client lifecycle."""
    
    _instance: Optional[Client] = None
    
    @classmethod
    def get_client(cls, scheduler_address: str = "tcp://localhost:8786") -> Client:
        """
        Get or create Dask client.
        
        Args:
            scheduler_address: Address of Dask scheduler
            
        Returns:
            Dask Client instance
        """
        if cls._instance is None:
            logger.info(f"Connecting to Dask scheduler at {scheduler_address}")
            cls._instance = Client(scheduler_address=scheduler_address)
        return cls._instance
    
    @classmethod
    def close(cls):
        """Close Dask client."""
        if cls._instance is not None:
            cls._instance.close()
            cls._instance = None
    
    @classmethod
    def get_dashboard_url(cls) -> str:
        """Get Dask dashboard URL."""
        return "http://localhost:8787"


@task(name="dask_portfolio_parallel_fetch")
def fetch_prices_parallel(tickers: list) -> Dict[str, float]:
    """
    Fetch stock prices in parallel using Dask.
    
    Args:
        tickers: List of stock tickers
        
    Returns:
        Dictionary of ticker: price
        
    Example:
        >>> prices = fetch_prices_parallel(["AAPL", "MSFT", "GOOGL"])
        >>> print(prices)
        {'AAPL': 150.25, 'MSFT': 380.15, 'GOOGL': 140.50}
    """
    task_logger = get_run_logger()
    client = DaskClientManager.get_client()
    
    try:
        task_logger.info(f"Fetching prices for {len(tickers)} tickers in parallel")
        
        # Create futures for parallel execution
        futures = {}
        for ticker in tickers:
            future = client.submit(_fetch_single_price, ticker)
            futures[ticker] = future
        
        # Collect results
        prices = {}
        for ticker, future in futures.items():
            try:
                prices[ticker] = future.result(timeout=5)
            except Exception as e:
                task_logger.warning(f"Failed to fetch {ticker}: {e}")
                prices[ticker] = None
        
        task_logger.info(f"Successfully fetched {len([p for p in prices.values() if p])} prices")
        return prices
        
    except Exception as e:
        task_logger.error(f"Error in parallel price fetch: {e}")
        raise


def _fetch_single_price(ticker: str) -> float:
    """Fetch single stock price (runs on Dask worker)."""
    import yfinance as yf
    try:
        data = yf.download(ticker, period="1d", progress=False)
        return float(data["Close"].iloc[-1])
    except Exception as e:
        print(f"Error fetching {ticker}: {e}")
        return None


@task(name="dask_technical_analysis_parallel")
def analyze_technicals_parallel(df: pd.DataFrame) -> pd.DataFrame:
    """
    Analyze technical indicators in parallel using Dask.
    
    Args:
        df: DataFrame with OHLCV data
        
    Returns:
        DataFrame with calculated indicators
    """
    task_logger = get_run_logger()
    client = DaskClientManager.get_client()
    
    task_logger.info(f"Analyzing technical indicators for {len(df)} rows in parallel")
    
    # Convert to Dask DataFrame for parallel processing
    dask_df = dd.from_pandas(df, npartitions=4)
    
    # Apply technical analysis to partitions
    result = dask_df.map_partitions(
        _calculate_technicals_partition,
        meta=df
    ).compute()
    
    task_logger.info("Technical analysis complete")
    return result


def _calculate_technicals_partition(df_partition: pd.DataFrame) -> pd.DataFrame:
    """Calculate technicals on a partition (runs on Dask worker)."""
    # Your technical analysis logic here
    # This is just a placeholder
    df_partition['rsi'] = 50  # Placeholder
    df_partition['bollinger_upper'] = df_partition['close'] * 1.02
    df_partition['bollinger_lower'] = df_partition['close'] * 0.98
    return df_partition


@task(name="dask_news_sentiment_parallel")
def analyze_sentiment_parallel(articles: list, batch_size: int = 50) -> list:
    """
    Analyze news sentiment in parallel using Dask.
    
    Args:
        articles: List of article dictionaries
        batch_size: Articles per batch
        
    Returns:
        Articles with sentiment scores
    """
    task_logger = get_run_logger()
    client = DaskClientManager.get_client()
    
    task_logger.info(f"Analyzing sentiment for {len(articles)} articles in parallel")
    
    # Split into batches
    batches = [articles[i:i+batch_size] for i in range(0, len(articles), batch_size)]
    
    # Submit batches to Dask
    futures = [
        client.submit(_analyze_sentiment_batch, batch)
        for batch in batches
    ]
    
    # Collect results
    results = []
    for future in as_completed(futures):
        batch_results = future.result()
        results.extend(batch_results)
    
    task_logger.info(f"Sentiment analysis complete for {len(results)} articles")
    return results


def _analyze_sentiment_batch(articles: list) -> list:
    """Analyze sentiment for batch (runs on Dask worker)."""
    from src.news_analysis import analyze_news_sentiment
    return analyze_news_sentiment(articles)


def get_dask_stats() -> Dict[str, Any]:
    """Get current Dask cluster statistics."""
    try:
        client = DaskClientManager.get_client()
        
        return {
            "scheduler_address": client.scheduler_address,
            "n_workers": len(client.nthreads()),
            "total_threads": sum(client.nthreads().values()),
            "total_memory": sum(client.memory_info()["memory"].values()) if "memory" in client.memory_info() else "Unknown",
            "dashboard_url": DaskClientManager.get_dashboard_url(),
        }
    except Exception as e:
        return {"error": str(e)}
```

---

## Step 4: Create Example Dask Flow

Create `src/dask_portfolio_flow.py`:

```python
"""
Portfolio analysis flows using Dask for distributed computing.
"""

from typing import Dict, Optional
from datetime import datetime
import pandas as pd

from prefect import flow, task, get_run_logger
from src.dask_integration import (
    DaskClientManager,
    fetch_prices_parallel,
    analyze_technicals_parallel,
    analyze_sentiment_parallel,
    get_dask_stats,
)
from src.portfolio_holdings import Holdings
from src.news_analysis import scrape_news_headlines, assess_portfolio_impact


@task(name="load_portfolio")
def load_portfolio() -> pd.DataFrame:
    """Load portfolio from CSV."""
    holdings = Holdings("holdings.csv")
    return holdings.all_holdings


@task(name="prepare_dask_cluster")
def prepare_dask_cluster() -> Dict:
    """Check Dask cluster is ready."""
    logger = get_run_logger()
    
    try:
        stats = get_dask_stats()
        logger.info(f"Dask cluster ready: {stats['n_workers']} workers, {stats['total_threads']} threads")
        logger.info(f"Dashboard: {stats['dashboard_url']}")
        return stats
    except Exception as e:
        logger.error(f"Dask cluster not available: {e}")
        raise


@flow(name="portfolio_analysis_with_dask")
def analyze_portfolio_with_dask(use_dask: bool = True) -> Dict:
    """
    Analyze portfolio using Dask for distributed computing.
    
    This flow demonstrates:
    - Parallel price fetching
    - Parallel technical analysis
    - Parallel news sentiment analysis
    
    Args:
        use_dask: Whether to use Dask (vs sequential)
        
    Returns:
        Analysis results with timing comparison
    """
    logger = get_run_logger()
    
    logger.info("=" * 80)
    logger.info(f"PORTFOLIO ANALYSIS WITH {'DASK' if use_dask else 'SEQUENTIAL'}")
    logger.info("=" * 80)
    
    start_time = datetime.now()
    
    # Prepare
    cluster_stats = prepare_dask_cluster()
    portfolio = load_portfolio()
    tickers = portfolio['sym'].tolist()
    
    logger.info(f"Analyzing {len(tickers)} holdings")
    
    if use_dask:
        # Parallel execution
        logger.info("Using Dask for distributed computation")
        
        # Fetch prices in parallel
        prices = fetch_prices_parallel(tickers)
        
        # Scrape news
        articles = scrape_news_headlines(max_articles=100, hours_back=24)
        
        # Analyze sentiment in parallel
        if articles:
            analyzed_articles = analyze_sentiment_parallel(articles)
        else:
            analyzed_articles = []
        
        # Portfolio impact
        impact = assess_portfolio_impact(analyzed_articles, portfolio) if analyzed_articles else {}
        
        results = {
            "prices": prices,
            "articles_analyzed": len(analyzed_articles),
            "portfolio_impact": impact,
        }
    else:
        # Sequential execution (for comparison)
        logger.info("Using sequential execution for comparison")
        results = {
            "prices": {},
            "articles_analyzed": 0,
        }
    
    elapsed = (datetime.now() - start_time).total_seconds()
    
    logger.info("=" * 80)
    logger.info(f"COMPLETED IN {elapsed:.1f} SECONDS")
    logger.info("=" * 80)
    logger.info(f"Cluster stats: {cluster_stats}")
    
    return {
        "success": True,
        "duration_seconds": elapsed,
        "cluster": cluster_stats,
        "results": results,
    }


@flow(name="portfolio_analysis_comparison")
def compare_dask_vs_sequential() -> Dict:
    """Compare Dask vs sequential execution."""
    
    logger = get_run_logger()
    
    logger.info("Starting comparison: Dask vs Sequential")
    
    # Sequential
    logger.info("\n" + "=" * 80)
    logger.info("SEQUENTIAL EXECUTION")
    logger.info("=" * 80)
    sequential_result = analyze_portfolio_with_dask(use_dask=False)
    
    # Dask
    logger.info("\n" + "=" * 80)
    logger.info("DASK DISTRIBUTED EXECUTION")
    logger.info("=" * 80)
    dask_result = analyze_portfolio_with_dask(use_dask=True)
    
    # Report
    logger.info("\n" + "=" * 80)
    logger.info("COMPARISON RESULTS")
    logger.info("=" * 80)
    logger.info(f"Sequential time: {sequential_result['duration_seconds']:.1f}s")
    logger.info(f"Dask time:       {dask_result['duration_seconds']:.1f}s")
    
    if sequential_result['duration_seconds'] > 0:
        speedup = sequential_result['duration_seconds'] / dask_result['duration_seconds']
        logger.info(f"Speedup: {speedup:.1f}x faster with Dask")
    
    return {
        "sequential": sequential_result,
        "dask": dask_result,
    }


if __name__ == "__main__":
    # Run comparison
    result = compare_dask_vs_sequential()
    print(result)
```

---

## Step 5: Run Locally

### Start Dask cluster:
```bash
# Create network
docker network create techstack-network

# Start Dask services
docker-compose -f docker/docker-compose.dask.yml up -d

# Check status
docker-compose -f docker/docker-compose.dask.yml logs dask-scheduler

# View dashboard
open http://localhost:8787
```

### Run Prefect flow with Dask:
```bash
# Terminal 1: Start Prefect server
docker-compose up prefect-server

# Terminal 2: Start Prefect worker
docker-compose up prefect-worker

# Terminal 3: Run the flow
cd /Users/conordonohue/Desktop/TechStack
uv run python -c "
from src.dask_portfolio_flow import analyze_portfolio_with_dask
result = analyze_portfolio_with_dask(use_dask=True)
print(f'Duration: {result[\"duration_seconds\"]:.1f}s')
"
```

### Monitor execution:
- **Dask Dashboard**: http://localhost:8787 (watch tasks execute)
- **Prefect UI**: http://localhost:4200 (watch flow runs)

---

## Step 6: Integration Tests

Add `tests/test_dask_integration.py`:

```python
"""Tests for Dask integration."""

import pytest
from src.dask_integration import DaskClientManager, get_dask_stats


@pytest.fixture
def dask_client():
    """Get Dask client for testing."""
    client = DaskClientManager.get_client()
    yield client
    # Don't close - keep for other tests


def test_dask_cluster_available():
    """Test Dask cluster is accessible."""
    stats = get_dask_stats()
    
    assert "error" not in stats
    assert stats["n_workers"] >= 1
    assert stats["total_threads"] >= 1


def test_dask_simple_computation(dask_client):
    """Test simple Dask computation."""
    # Simple distributed computation
    futures = [
        dask_client.submit(lambda x: x ** 2, i)
        for i in range(10)
    ]
    
    results = [f.result() for f in futures]
    expected = [i ** 2 for i in range(10)]
    
    assert results == expected


def test_dask_parallel_pricing():
    """Test parallel price fetching."""
    from src.dask_integration import fetch_prices_parallel
    
    tickers = ["AAPL", "MSFT", "GOOGL"]
    prices = fetch_prices_parallel(tickers)
    
    assert len(prices) == 3
    for price in prices.values():
        assert price is None or isinstance(price, (int, float))


def test_portfolio_flow_with_dask():
    """Test portfolio analysis flow."""
    from src.dask_portfolio_flow import analyze_portfolio_with_dask
    
    result = analyze_portfolio_with_dask(use_dask=True)
    
    assert result["success"]
    assert result["duration_seconds"] > 0
    assert "cluster" in result
```

Run tests:
```bash
uv run pytest tests/test_dask_integration.py -v
```

---

## Monitoring & Debugging

### Check Dask cluster status:
```bash
# View all workers
docker-compose -f docker/docker-compose.dask.yml ps

# View scheduler logs
docker-compose -f docker/docker-compose.dask.yml logs dask-scheduler

# View worker logs
docker-compose -f docker/docker-compose.dask.yml logs dask-worker-1
```

### Common issues:

**Issue: "Connection refused" to Dask**
```
Solution: Ensure network exists and Dask is running
docker network create techstack-network
docker-compose -f docker/docker-compose.dask.yml up -d
```

**Issue: "No available workers"**
```
Solution: Workers may still be starting
Wait 10 seconds and retry
docker-compose -f docker/docker-compose.dask.yml logs dask-worker-1
```

**Issue: "Memory error"**
```
Solution: Reduce partitions or data size
Use: dask_df = dd.from_pandas(df, npartitions=2)  # Fewer partitions
```

---

## Next: Phase 2 - Coiled

Once this works locally and you understand Dask basics:

```bash
# Install Coiled
pip install coiled

# Try on Coiled (free tier)
uv run python -c "
import coiled
cluster = coiled.Cluster(n_workers=2, worker_cpu=2, worker_memory='4GB')
print(cluster.dashboard_link)
"
```

---

## Resources

- **Dask Docs**: https://docs.dask.org
- **Dask Tutorial**: https://docs.dask.org/en/stable/array-api.html
- **Bokeh Dashboard**: https://docs.dask.org/en/stable/dashboard.html
- **Prefect + Dask**: https://docs.prefect.io/latest/guides/dask-distributed/
