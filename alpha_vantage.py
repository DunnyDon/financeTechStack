"""
Alpha Vantage integration for fundamental financial data.
Provides tasks and flows for fetching and analyzing company fundamentals.
"""

import os
import time
from datetime import datetime
from typing import Optional

import requests
from prefect import flow, task, get_run_logger
import pandas as pd

from config import config


ALPHA_VANTAGE_BASE_URL = "https://www.alphavantage.co/query"


@task(retries=3, retry_delay_seconds=5)
def fetch_fundamental_data(ticker: str) -> dict:
    """
    Fetch fundamental financial data from Alpha Vantage.
    
    Args:
        ticker: Stock ticker symbol
        
    Returns:
        Dictionary containing fundamental financial metrics
    """
    logger = get_run_logger()
    logger.info(f"Fetching fundamental data for {ticker}")
    
    try:
        api_key = config.get_alpha_vantage_key()
        
        # Fetch overview data
        params = {
            "function": "OVERVIEW",
            "symbol": ticker,
            "apikey": api_key,
        }
        
        response = requests.get(ALPHA_VANTAGE_BASE_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if "Error Message" in data:
            logger.error(f"Alpha Vantage error: {data['Error Message']}")
            return {}
        
        # Extract key fundamentals
        fundamentals = {
            "ticker": ticker,
            "name": data.get("Name", "N/A"),
            "sector": data.get("Sector", "N/A"),
            "industry": data.get("Industry", "N/A"),
            "market_cap": data.get("MarketCapitalization", "N/A"),
            "pe_ratio": data.get("PERatio", "N/A"),
            "eps": data.get("EPS", "N/A"),
            "revenue": data.get("RevenueTTM", "N/A"),
            "gross_profit_margin": data.get("GrossProfitMargin", "N/A"),
            "profit_margin": data.get("ProfitMargin", "N/A"),
            "operating_margin": data.get("OperatingMarginTTM", "N/A"),
            "roe": data.get("ReturnOnEquityTTM", "N/A"),
            "roa": data.get("ReturnOnAssetsTTM", "N/A"),
            "debt_to_equity": data.get("DebtToEquity", "N/A"),
            "book_value": data.get("BookValue", "N/A"),
            "price_to_book": data.get("PriceToBookRatio", "N/A"),
            "dividend_yield": data.get("DividendYield", "N/A"),
            "updated_at": datetime.now().isoformat(),
        }
        
        logger.info(f"Retrieved fundamentals for {ticker}")
        return fundamentals
        
    except Exception as e:
        logger.error(f"Error fetching fundamental data for {ticker}: {e}")
        return {}


@task
def save_fundamentals_to_parquet(fundamentals_list: list[dict], output_dir: str = "db") -> str:
    """
    Save fundamental data to Parquet file.
    
    Args:
        fundamentals_list: List of fundamental data dictionaries
        output_dir: Output directory
        
    Returns:
        Path to saved Parquet file
    """
    logger = get_run_logger()
    logger.info(f"Saving {len(fundamentals_list)} companies' fundamental data")
    
    try:
        os.makedirs(output_dir, exist_ok=True)
        
        df = pd.DataFrame(fundamentals_list)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"{output_dir}/fundamentals_{timestamp}.parquet"
        
        df.to_parquet(output_file, engine="pyarrow", compression="snappy", index=False)
        logger.info(f"Saved fundamentals to {output_file}")
        return output_file
        
    except Exception as e:
        logger.error(f"Error saving fundamentals: {e}")
        raise


@flow(name="Fundamental Analysis Flow")
def fetch_fundamentals(tickers: list[str]):
    """
    Prefect flow to fetch fundamental data for multiple companies.
    
    Args:
        tickers: List of stock ticker symbols
    """
    logger = get_run_logger()
    logger.info(f"Starting fundamental analysis for tickers: {tickers}")
    
    fundamentals_list = []
    
    for ticker in tickers:
        logger.info(f"Fetching fundamentals for {ticker}")
        fundamentals = fetch_fundamental_data(ticker)
        if fundamentals:
            fundamentals_list.append(fundamentals)
        
        # Respect API rate limits (5 requests/min for free tier)
        time.sleep(12)
    
    if fundamentals_list:
        output_file = save_fundamentals_to_parquet(fundamentals_list)
        logger.info(f"Fundamental data saved to {output_file}")
    
    return fundamentals_list


def main():
    """Run fundamental analysis."""
    tickers = ["AAPL", "MSFT", "GOOGL"]
    results = fetch_fundamentals(tickers)
    print(f"\nFetched fundamentals for {len(results)} companies!")


if __name__ == "__main__":
    main()
