"""
Integrated Dask-Prefect workflows for Phase 1 completion.

Combines technical analysis, news analysis, and pricing parallelization
into comprehensive portfolio analysis workflows.

This module provides:
- Comprehensive portfolio analysis flow with full parallelization
- Per-asset-type analytics parallelization
- Combined multi-analysis flow (technical + news + pricing)
"""

import time
from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd
from prefect import flow, get_run_logger, task

from .portfolio_holdings import Holdings
from .dask_portfolio_flows import (
    setup_dask_client,
    teardown_dask_client,
    fetch_security_pricing,
)
from .dask_analysis_flows import (
    calculate_security_technicals,
    fetch_price_from_multiple_sources,
    fetch_news_for_ticker,
    aggregate_technical_results,
    aggregate_news_results,
)

__all__ = [
    "dask_comprehensive_portfolio_analysis_flow",
    "dask_per_asset_type_analysis_flow",
    "dask_combined_analysis_flow",
]


# ============================================================================
# AGGREGATION TASKS
# ============================================================================


@task(name="combine_all_analysis_results")
def combine_all_analysis_results(
    technical_df: pd.DataFrame,
    news_summary: Dict,
    pricing_data: Dict,
) -> pd.DataFrame:
    """
    Combine technical, news, and pricing analysis into single DataFrame.

    Args:
        technical_df: Technical indicators DataFrame
        news_summary: News analysis summary dict
        pricing_data: Pricing data dict

    Returns:
        Combined analysis DataFrame
    """
    logger_instance = get_run_logger()
    logger_instance.info("Combining analysis results")

    try:
        # Start with technical data
        combined = technical_df.copy() if not technical_df.empty else pd.DataFrame()

        # Add news sentiment
        if news_summary and "sentiment_by_ticker" in news_summary:
            sentiment_series = pd.Series(
                news_summary["sentiment_by_ticker"], name="news_sentiment"
            )
            if not combined.empty:
                combined = combined.join(sentiment_series.to_frame(), on="ticker")
            else:
                combined = sentiment_series.to_frame().reset_index()
                combined.columns = ["ticker", "news_sentiment"]

        # Add pricing data
        if pricing_data:
            price_df = pd.DataFrame(
                [
                    {"ticker": t, "latest_price": p}
                    for t, p in pricing_data.get("prices", {}).items()
                ]
            )
            if not combined.empty:
                combined = combined.merge(price_df, on="ticker", how="left")
            else:
                combined = price_df

        logger_instance.info(f"Combined analysis for {len(combined)} securities")
        return combined

    except Exception as e:
        logger_instance.error(f"Error combining results: {e}")
        return pd.DataFrame()


@task(name="generate_portfolio_analysis_report")
def generate_portfolio_analysis_report(
    combined_df: pd.DataFrame,
    execution_time: float,
) -> Dict:
    """
    Generate summary report from combined analysis.

    Args:
        combined_df: Combined analysis DataFrame
        execution_time: Total execution time in seconds

    Returns:
        Report dict with summary statistics
    """
    logger_instance = get_run_logger()

    if combined_df.empty:
        return {
            "status": "error",
            "message": "No analysis data available",
        }

    report = {
        "timestamp": datetime.now().isoformat(),
        "execution_time_seconds": execution_time,
        "securities_analyzed": len(combined_df),
        "summary": {
            "avg_rsi": float(combined_df["rsi_14"].mean()) if "rsi_14" in combined_df.columns else None,
            "avg_sma_20": float(combined_df["sma_20"].mean()) if "sma_20" in combined_df.columns else None,
            "avg_news_sentiment": float(combined_df["news_sentiment"].mean())
            if "news_sentiment" in combined_df.columns
            else None,
            "securities_with_positive_sentiment": int(
                (combined_df["news_sentiment"] > 0.1).sum()
            )
            if "news_sentiment" in combined_df.columns
            else 0,
            "securities_with_negative_sentiment": int(
                (combined_df["news_sentiment"] < -0.1).sum()
            )
            if "news_sentiment" in combined_df.columns
            else 0,
        },
    }

    logger_instance.info(f"Generated report: {len(combined_df)} securities analyzed in {execution_time:.2f}s")

    return report


# ============================================================================
# COMPREHENSIVE FLOWS
# ============================================================================


@flow(
    name="dask_comprehensive_portfolio_analysis_flow",
    description="Complete portfolio analysis with parallel technical, news, and pricing",
)
def dask_comprehensive_portfolio_analysis_flow(
    tickers: List[str] = None,
    dask_scheduler: str = "tcp://localhost:8786",
) -> Dict:
    """
    Comprehensive portfolio analysis combining technical, news, and pricing.

    Args:
        tickers: List of tickers to analyze
        dask_scheduler: Dask scheduler address

    Returns:
        Dict with combined analysis results and report
    """
    logger_instance = get_run_logger()
    logger_instance.info("Starting comprehensive portfolio analysis flow")

    start_time = time.time()

    if not tickers:
        try:
            holdings = Holdings("holdings.csv")
            tickers = holdings.get_unique_symbols()
        except Exception as e:
            logger_instance.error(f"Error loading holdings: {e}")
            return {"status": "error", "message": str(e)}

    try:
        client = setup_dask_client(dask_scheduler)

        logger_instance.info(f"Analyzing {len(tickers)} securities in parallel")

        # Step 1: Fetch all pricing data first (needed for technicals)
        logger_instance.info("Step 1: Fetching pricing data...")
        price_futures = [
            client.submit(fetch_price_from_multiple_sources, t) for t in tickers
        ]
        price_results = client.gather(price_futures)
        price_results = [r for r in price_results if r]
        logger_instance.info(f"  ✓ Fetched prices for {len(price_results)} securities")

        # Step 2: Calculate technical indicators in parallel
        logger_instance.info("Step 2: Calculating technical indicators...")
        tech_futures = [
            client.submit(calculate_security_technicals, price_results[i]["ticker"], price_results[i]["price_data"])
            for i in range(len(price_results))
        ]
        tech_results = client.gather(tech_futures)
        tech_df = aggregate_technical_results(tech_results)
        logger_instance.info(f"  ✓ Calculated technicals for {len(tech_df)} securities")

        # Step 3: Fetch and analyze news in parallel
        logger_instance.info("Step 3: Analyzing news sentiment...")
        news_futures = client.map(fetch_news_for_ticker, tickers)
        news_results = client.gather(news_futures)
        news_summary = aggregate_news_results(news_results)
        logger_instance.info(f"  ✓ Analyzed news for {news_summary['securities_with_news']} securities")

        # Step 4: Combine all results
        logger_instance.info("Step 4: Combining analysis results...")
        combined_df = combine_all_analysis_results(
            tech_df,
            news_summary,
            {"prices": {r["ticker"]: r["price_data"].get("close") for r in price_results}},
        )

        # Step 5: Generate report
        execution_time = time.time() - start_time
        report = generate_portfolio_analysis_report(combined_df, execution_time)

        return {
            "status": "success",
            "report": report,
            "combined_analysis": combined_df.to_dict(orient="records"),
        }

    except Exception as e:
        logger_instance.error(f"Error in comprehensive analysis flow: {e}")
        return {"status": "error", "message": str(e)}

    finally:
        teardown_dask_client()


@flow(
    name="dask_per_asset_type_analysis_flow",
    description="Analyze portfolio metrics per asset type in parallel",
)
def dask_per_asset_type_analysis_flow(
    dask_scheduler: str = "tcp://localhost:8786",
) -> Dict:
    """
    Analyze portfolio metrics grouped by asset type in parallel.

    Args:
        dask_scheduler: Dask scheduler address

    Returns:
        Dict with per-asset-type analysis
    """
    logger_instance = get_run_logger()
    logger_instance.info("Starting per-asset-type analysis flow")

    try:
        holdings = Holdings("holdings.csv")
        asset_types = holdings.get_asset_types()

        logger_instance.info(f"Found {len(asset_types)} asset types")

        # Group holdings by asset type
        asset_type_groups = {}
        for asset_type in asset_types:
            symbols = holdings.filter_by_asset_type(asset_type)
            asset_type_groups[asset_type] = symbols

        logger_instance.info(f"Asset type groups: {asset_type_groups}")

        # Analyze each asset type in parallel
        client = setup_dask_client(dask_scheduler)

        results_by_type = {}
        for asset_type, symbols in asset_type_groups.items():
            logger_instance.info(f"Analyzing {len(symbols)} {asset_type} securities...")

            # Fetch prices
            price_futures = client.map(fetch_security_pricing, symbols)
            price_results = client.gather(price_futures)
            price_results = [r for r in price_results if r]

            results_by_type[asset_type] = {
                "symbol_count": len(symbols),
                "successful_fetches": len(price_results),
                "symbols": symbols,
            }

        logger_instance.info(f"✓ Analyzed {len(results_by_type)} asset types")

        return {
            "status": "success",
            "analysis_by_type": results_by_type,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger_instance.error(f"Error in per-asset-type analysis: {e}")
        return {"status": "error", "message": str(e)}

    finally:
        teardown_dask_client()


@flow(
    name="dask_combined_analysis_flow",
    description="Combined technical + news + pricing in single optimized flow",
)
def dask_combined_analysis_flow(
    tickers: List[str] = None,
    dask_scheduler: str = "tcp://localhost:8786",
) -> Dict:
    """
    Optimized combined analysis with single client connection.

    Args:
        tickers: List of tickers
        dask_scheduler: Dask scheduler address

    Returns:
        Dict with combined results
    """
    logger_instance = get_run_logger()
    logger_instance.info("Starting combined analysis flow")

    start = time.time()

    if not tickers:
        try:
            holdings = Holdings("holdings.csv")
            tickers = holdings.get_unique_symbols()
        except Exception as e:
            logger_instance.error(f"Error loading holdings: {e}")
            return {"status": "error", "message": str(e)}

    try:
        client = setup_dask_client(dask_scheduler)

        # Use client.map for cleaner parallelization
        logger_instance.info(f"Processing {len(tickers)} securities in parallel")

        # Map all operations across workers
        pricing_futures = client.map(fetch_price_from_multiple_sources, tickers)
        pricing_results = client.gather(pricing_futures)
        pricing_results = [r for r in pricing_results if r]

        # Use fetched prices for technical analysis
        if pricing_results:
            tech_futures = [
                client.submit(
                    calculate_security_technicals,
                    r["ticker"],
                    r["price_data"]
                )
                for r in pricing_results
            ]
            tech_results = client.gather(tech_futures)
            tech_df = aggregate_technical_results(tech_results)
        else:
            tech_df = pd.DataFrame()

        # Fetch news
        news_futures = client.map(fetch_news_for_ticker, tickers)
        news_results = client.gather(news_futures)
        news_summary = aggregate_news_results(news_results)

        duration = time.time() - start

        report = generate_portfolio_analysis_report(tech_df, duration)

        return {
            "status": "success",
            "report": report,
            "securities_processed": len(pricing_results),
            "execution_time": duration,
        }

    except Exception as e:
        logger_instance.error(f"Error in combined flow: {e}")
        return {"status": "error", "message": str(e)}

    finally:
        teardown_dask_client()


if __name__ == "__main__":
    # Run comprehensive analysis
    result = dask_comprehensive_portfolio_analysis_flow(
        tickers=["AAPL", "MSFT", "GOOGL"],
        dask_scheduler="tcp://localhost:8786",
    )
    print(result)
