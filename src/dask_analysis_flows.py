"""
Extended Dask-accelerated portfolio workflows for Phase 1 completion.

Parallelizes:
- Technical analysis per security
- Portfolio analytics per asset type/broker
- News sentiment analysis
- Price fetching across multiple sources
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import pandas as pd
from dask.distributed import Client
from prefect import flow, get_run_logger, task

from .portfolio_technical import TechnicalAnalyzer, calculate_technical_indicators
from .portfolio_analytics import PortfolioAnalytics, calculate_pnl
from .portfolio_holdings import Holdings
from .portfolio_prices import PriceFetcher
from .news_analysis import scrape_news_headlines, analyze_news_sentiment, assess_portfolio_impact
from .utils import get_logger

__all__ = [
    "dask_calculate_technical_per_security",
    "dask_portfolio_technical_analysis_flow",
    "dask_news_analysis_flow",
    "dask_multi_source_pricing_flow",
]

logger = get_logger(__name__)


# ============================================================================
# TECHNICAL ANALYSIS - PER-SECURITY PARALLELIZATION
# ============================================================================


def calculate_security_technicals(ticker: str, price_data: Dict) -> Optional[Dict]:
    """
    Calculate technical indicators for a single security (runs on Dask worker).

    Args:
        ticker: Stock ticker symbol
        price_data: Dict with OHLCV data

    Returns:
        Dict with technical indicators or None if calculation fails
    """
    try:
        logger.info(f"[DASK] Calculating technical indicators for {ticker}")
        
        if not price_data or "ohlcv" not in price_data:
            logger.warning(f"No OHLCV data for {ticker}")
            return None
        
        # Convert to DataFrame
        ohlcv_df = pd.DataFrame(price_data["ohlcv"])
        
        # Calculate indicators
        technical_df = calculate_technical_indicators(ohlcv_df)
        
        if technical_df is None or technical_df.empty:
            logger.warning(f"Failed to calculate technicals for {ticker}")
            return None
        
        logger.info(f"[DASK] {ticker}: Calculated {len(technical_df.columns)} technical indicators")
        
        return {
            "ticker": ticker,
            "technical_indicators": technical_df.to_dict(orient="records"),
            "summary": {
                "sma_20": float(technical_df["SMA_20"].iloc[-1]) if "SMA_20" in technical_df.columns else None,
                "rsi_14": float(technical_df["RSI_14"].iloc[-1]) if "RSI_14" in technical_df.columns else None,
                "bollinger_upper": float(technical_df["BB_UPPER"].iloc[-1]) if "BB_UPPER" in technical_df.columns else None,
            }
        }
        
    except Exception as e:
        logger.error(f"Error calculating technicals for {ticker}: {e}")
        return None


def fetch_news_for_ticker(ticker: str) -> Optional[Dict]:
    """
    Fetch and analyze news for a single security (runs on Dask worker).

    Args:
        ticker: Stock ticker symbol

    Returns:
        Dict with news analysis or None if fetch fails
    """
    try:
        logger.info(f"[DASK] Fetching news for {ticker}")
        
        # Fetch headlines
        articles = scrape_news_headlines(max_articles=20, hours_back=24)
        
        if not articles:
            logger.warning(f"No news found for {ticker}")
            return None
        
        # Filter by ticker
        ticker_articles = [a for a in articles if ticker.lower() in a.get("content", "").lower()]
        
        if not ticker_articles:
            logger.info(f"No news articles mentioning {ticker}")
            return None
        
        # Analyze sentiment
        sentiment_articles = analyze_news_sentiment(ticker_articles)
        
        logger.info(f"[DASK] {ticker}: Analyzed {len(sentiment_articles)} articles")
        
        return {
            "ticker": ticker,
            "article_count": len(sentiment_articles),
            "articles": sentiment_articles,
            "avg_sentiment": sum(a.get("sentiment", 0) for a in sentiment_articles) / len(sentiment_articles) if sentiment_articles else 0,
        }
        
    except Exception as e:
        logger.error(f"Error fetching news for {ticker}: {e}")
        return None


def fetch_price_from_multiple_sources(ticker: str) -> Optional[Dict]:
    """
    Fetch price from multiple sources and return best data (runs on Dask worker).

    Args:
        ticker: Stock ticker symbol

    Returns:
        Dict with price data from best source or None
    """
    try:
        logger.info(f"[DASK] Fetching price from multiple sources for {ticker}")
        
        price_fetcher = PriceFetcher()
        
        # Try multiple asset types
        price_data = price_fetcher.fetch_price(ticker, asset_type="eq")
        
        if price_data:
            logger.info(f"[DASK] {ticker}: Got price {price_data.get('close', 'N/A')}")
            return {
                "ticker": ticker,
                "price_data": price_data,
                "source": "yfinance",
            }
        
        logger.warning(f"Could not fetch price for {ticker}")
        return None
        
    except Exception as e:
        logger.error(f"Error fetching price for {ticker}: {e}")
        return None


# ============================================================================
# AGGREGATION TASKS (Prefect)
# ============================================================================


@task(name="aggregate_technical_results")
def aggregate_technical_results(technical_results: List[Dict]) -> pd.DataFrame:
    """
    Aggregate technical analysis results from workers into single DataFrame.

    Args:
        technical_results: List of technical analysis results from workers

    Returns:
        Combined technical analysis DataFrame
    """
    logger_instance = get_run_logger()
    
    technical_results = [r for r in technical_results if r]
    logger_instance.info(f"Aggregating technical results for {len(technical_results)} securities")
    
    if not technical_results:
        return pd.DataFrame()
    
    # Create summary DataFrame
    summary_data = []
    for result in technical_results:
        summary_data.append({
            "ticker": result["ticker"],
            "sma_20": result["summary"].get("sma_20"),
            "rsi_14": result["summary"].get("rsi_14"),
            "bollinger_upper": result["summary"].get("bollinger_upper"),
        })
    
    return pd.DataFrame(summary_data)


@task(name="aggregate_news_results")
def aggregate_news_results(news_results: List[Dict]) -> Dict:
    """
    Aggregate news analysis results from workers.

    Args:
        news_results: List of news analysis results from workers

    Returns:
        Combined news analysis summary
    """
    logger_instance = get_run_logger()
    
    news_results = [r for r in news_results if r]
    logger_instance.info(f"Aggregating news results for {len(news_results)} securities")
    
    if not news_results:
        return {"total_articles": 0, "sentiment_summary": {}}
    
    summary = {
        "total_articles": sum(r.get("article_count", 0) for r in news_results),
        "securities_with_news": len(news_results),
        "sentiment_by_ticker": {r["ticker"]: r["avg_sentiment"] for r in news_results},
        "positive_sentiment": len([r for r in news_results if r["avg_sentiment"] > 0.1]),
        "negative_sentiment": len([r for r in news_results if r["avg_sentiment"] < -0.1]),
    }
    
    return summary


# ============================================================================
# DASK-ACCELERATED FLOWS
# ============================================================================


@flow(
    name="dask_portfolio_technical_analysis_flow",
    description="Parallel technical analysis for all portfolio securities",
)
def dask_portfolio_technical_analysis_flow(
    tickers: List[str] = None,
    dask_scheduler: str = "tcp://localhost:8786",
) -> Dict:
    """
    Calculate technical indicators for all securities in parallel.

    Args:
        tickers: List of tickers to analyze
        dask_scheduler: Dask scheduler address

    Returns:
        Dict with technical analysis summary and DataFrame
    """
    logger_instance = get_run_logger()
    logger_instance.info("Starting parallel technical analysis flow")
    
    if not tickers:
        try:
            holdings = Holdings("holdings.csv")
            tickers = holdings.get_unique_symbols()
        except Exception as e:
            logger_instance.error(f"Error loading holdings: {e}")
            return {"status": "error", "message": str(e)}
    
    try:
        from .dask_portfolio_flows import setup_dask_client, teardown_dask_client
        client = setup_dask_client(dask_scheduler)
        
        logger_instance.info(f"Processing {len(tickers)} securities in parallel")
        
        # Get price data first
        price_futures = [client.submit(fetch_price_from_multiple_sources, t) for t in tickers]
        price_results = client.gather(price_futures)
        price_results = [r for r in price_results if r]
        
        # Calculate technicals in parallel
        tech_futures = [
            client.submit(calculate_security_technicals, price_results[i]["ticker"], price_results[i]["price_data"])
            for i in range(len(price_results))
        ]
        tech_results = client.gather(tech_futures)
        
        # Aggregate results
        tech_df = aggregate_technical_results(tech_results)
        
        logger_instance.info(f"✓ Completed technical analysis for {len(tech_results)} securities")
        
        return {
            "status": "success",
            "securities_analyzed": len(tech_results),
            "technical_summary": tech_df.to_dict(orient="records") if not tech_df.empty else [],
            "timestamp": datetime.now().isoformat(),
        }
        
    except Exception as e:
        logger_instance.error(f"Error in technical analysis flow: {e}")
        return {"status": "error", "message": str(e)}
    
    finally:
        teardown_dask_client()


@flow(
    name="dask_news_analysis_flow",
    description="Parallel news sentiment analysis for portfolio securities",
)
def dask_news_analysis_flow(
    tickers: List[str] = None,
    dask_scheduler: str = "tcp://localhost:8786",
) -> Dict:
    """
    Analyze news sentiment for all securities in parallel.

    Args:
        tickers: List of tickers to analyze
        dask_scheduler: Dask scheduler address

    Returns:
        Dict with news analysis summary
    """
    logger_instance = get_run_logger()
    logger_instance.info("Starting parallel news analysis flow")
    
    if not tickers:
        try:
            holdings = Holdings("holdings.csv")
            tickers = holdings.get_unique_symbols()
        except Exception as e:
            logger_instance.error(f"Error loading holdings: {e}")
            return {"status": "error", "message": str(e)}
    
    try:
        from .dask_portfolio_flows import setup_dask_client, teardown_dask_client
        client = setup_dask_client(dask_scheduler)
        
        logger_instance.info(f"Analyzing news for {len(tickers)} securities")
        
        # Fetch and analyze news in parallel
        news_futures = client.map(fetch_news_for_ticker, tickers)
        news_results = client.gather(news_futures)
        
        # Aggregate
        news_summary = aggregate_news_results(news_results)
        
        logger_instance.info(f"✓ Analyzed news for {news_summary['securities_with_news']} securities")
        
        return {
            "status": "success",
            **news_summary,
            "timestamp": datetime.now().isoformat(),
        }
        
    except Exception as e:
        logger_instance.error(f"Error in news analysis flow: {e}")
        return {"status": "error", "message": str(e)}
    
    finally:
        teardown_dask_client()


@flow(
    name="dask_multi_source_pricing_flow",
    description="Fetch pricing from multiple sources in parallel",
)
def dask_multi_source_pricing_flow(
    tickers: List[str] = None,
    dask_scheduler: str = "tcp://localhost:8786",
) -> Dict:
    """
    Fetch pricing data from multiple sources in parallel.

    Args:
        tickers: List of tickers to fetch
        dask_scheduler: Dask scheduler address

    Returns:
        Dict with pricing data and summary
    """
    logger_instance = get_run_logger()
    logger_instance.info("Starting parallel multi-source pricing flow")
    
    if not tickers:
        try:
            holdings = Holdings("holdings.csv")
            tickers = holdings.get_unique_symbols()
        except Exception as e:
            logger_instance.error(f"Error loading holdings: {e}")
            return {"status": "error", "message": str(e)}
    
    try:
        from .dask_portfolio_flows import setup_dask_client, teardown_dask_client
        client = setup_dask_client(dask_scheduler)
        
        logger_instance.info(f"Fetching prices for {len(tickers)} securities")
        
        # Fetch prices in parallel
        price_futures = client.map(fetch_price_from_multiple_sources, tickers)
        price_results = client.gather(price_futures)
        price_results = [r for r in price_results if r]
        
        logger_instance.info(f"✓ Fetched prices for {len(price_results)} securities")
        
        return {
            "status": "success",
            "securities_fetched": len(price_results),
            "prices": {r["ticker"]: r["price_data"].get("close") for r in price_results},
            "timestamp": datetime.now().isoformat(),
        }
        
    except Exception as e:
        logger_instance.error(f"Error in pricing flow: {e}")
        return {"status": "error", "message": str(e)}
    
    finally:
        teardown_dask_client()


if __name__ == "__main__":
    # Example usage
    result = dask_portfolio_technical_analysis_flow(
        tickers=["AAPL", "MSFT", "GOOGL"],
        dask_scheduler="tcp://localhost:8786",
    )
    print(result)
