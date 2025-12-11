"""
Streamlit-compatible portfolio price updates with Prefect flow integration.

Provides price fetching and storage functions that work both directly
in Streamlit and with Prefect for logging and monitoring.
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime

import pandas as pd
import numpy as np

try:
    from prefect import flow, task, get_run_logger
    HAS_PREFECT = True
except ImportError:
    HAS_PREFECT = False


def fetch_price_for_symbol(
    ticker: str,
    asset_type: str = 'eq',
    price_fetcher=None
) -> Optional[Dict]:
    """
    Fetch price data for a single ticker.
    
    Args:
        ticker: Stock ticker symbol
        asset_type: Type of asset ('eq', 'crypto', 'commodity')
        price_fetcher: PriceFetcher instance
    
    Returns:
        Dictionary with price data or None if failed
    """
    try:
        if price_fetcher is None:
            from src.portfolio_prices import PriceFetcher
            price_fetcher = PriceFetcher()
        
        price_data = price_fetcher.fetch_price(ticker, asset_type=asset_type)
        return price_data
        
    except Exception as e:
        return None


def prepare_prices_for_storage(all_prices: List[Dict]) -> pd.DataFrame:
    """
    Prepare price data for storage in ParquetDB.
    
    Args:
        all_prices: List of price dictionaries
    
    Returns:
        DataFrame ready for ParquetDB storage
    """
    if not all_prices:
        return pd.DataFrame()
    
    prices_df = pd.DataFrame(all_prices)
    
    # Convert timestamp strings to datetime
    if 'timestamp' in prices_df.columns:
        prices_df['timestamp'] = pd.to_datetime(prices_df['timestamp'])
    else:
        prices_df['timestamp'] = datetime.now()
    
    # Map column names if needed
    if 'price' in prices_df.columns and 'close_price' not in prices_df.columns:
        prices_df['close_price'] = prices_df['price']
    
    # Add missing required columns
    if 'currency' not in prices_df.columns:
        prices_df['currency'] = 'USD'
    if 'frequency' not in prices_df.columns:
        prices_df['frequency'] = 'daily'
    
    return prices_df


def save_prices_to_db(prices_df: pd.DataFrame, db=None) -> bool:
    """
    Save price DataFrame to ParquetDB.
    
    Args:
        prices_df: DataFrame with price data
        db: ParquetDB instance (creates new if None)
    
    Returns:
        True if successful, False otherwise
    """
    try:
        if db is None:
            from src.parquet_db import ParquetDB
            db = ParquetDB(root_path="db")
        
        db.upsert_prices(prices_df)
        return True
        
    except Exception as e:
        return False


def update_prices_streamlit(
    holdings_df: pd.DataFrame,
    db=None
) -> Tuple[int, List[str]]:
    """
    Update price data for all holdings (Streamlit-compatible).
    
    Works directly in Streamlit without Prefect context.
    
    Args:
        holdings_df: DataFrame with holdings including 'sym' and 'asset' columns
        db: ParquetDB instance (creates new if None)
    
    Returns:
        Tuple of (number of successful updates, list of failed tickers)
    """
    if holdings_df is None or holdings_df.empty:
        return 0, []
    
    try:
        from src.portfolio_prices import PriceFetcher
        from src.parquet_db import ParquetDB
        
        if db is None:
            db = ParquetDB(root_path="db")
        
        price_fetcher = PriceFetcher()
        tickers = holdings_df['sym'].unique().tolist()
        
        all_prices = []
        failed_tickers = []
        
        for ticker in tickers:
            try:
                # Determine asset type
                holding = holdings_df[holdings_df['sym'] == ticker]
                if not holding.empty:
                    asset_type = holding.iloc[0].get('asset', 'eq')
                else:
                    asset_type = 'eq'
                
                price_data = fetch_price_for_symbol(ticker, asset_type=asset_type, price_fetcher=price_fetcher)
                
                if price_data:
                    all_prices.append(price_data)
                else:
                    failed_tickers.append(ticker)
                    
            except Exception as e:
                failed_tickers.append(ticker)
                continue
        
        # Prepare and save
        if all_prices:
            prices_df = prepare_prices_for_storage(all_prices)
            success = save_prices_to_db(prices_df, db)
            
            if success:
                return len(all_prices), failed_tickers
            else:
                return 0, tickers
        else:
            return 0, tickers
            
    except Exception as e:
        return 0, holdings_df['sym'].unique().tolist()


# Prefect task wrappers (optional, if Prefect available)
if HAS_PREFECT:
    @task(name="fetch_price_task")
    def fetch_price_task(
        ticker: str,
        asset_type: str = 'eq'
    ) -> Optional[Dict]:
        """Prefect task for fetching a single price."""
        task_logger = get_run_logger()
        task_logger.info(f"Fetching price for {ticker}")
        
        result = fetch_price_for_symbol(ticker, asset_type=asset_type)
        
        if result:
            task_logger.info(f"Successfully fetched {ticker}")
        else:
            task_logger.warning(f"Failed to fetch {ticker}")
        
        return result
    
    @task(name="prepare_prices_task")
    def prepare_prices_task(all_prices: List[Dict]) -> pd.DataFrame:
        """Prefect task for preparing prices for storage."""
        task_logger = get_run_logger()
        task_logger.info(f"Preparing {len(all_prices)} price records")
        
        prices_df = prepare_prices_for_storage(all_prices)
        
        task_logger.info(f"Prepared {len(prices_df)} records for storage")
        return prices_df
    
    @task(name="save_prices_task")
    def save_prices_task(prices_df: pd.DataFrame) -> bool:
        """Prefect task for saving prices to DB."""
        task_logger = get_run_logger()
        task_logger.info(f"Saving {len(prices_df)} price records to database")
        
        success = save_prices_to_db(prices_df)
        
        if success:
            task_logger.info(f"Successfully saved prices")
        else:
            task_logger.error(f"Failed to save prices")
        
        return success
    
    @flow(name="update_prices_flow")
    def update_prices_flow(holdings_df: pd.DataFrame) -> Tuple[int, List[str]]:
        """
        Streamlit-compatible price update flow with Prefect logging.
        
        Args:
            holdings_df: DataFrame with holdings data
        
        Returns:
            Tuple of (number of successful updates, list of failed tickers)
        """
        flow_logger = get_run_logger()
        
        if holdings_df is None or holdings_df.empty:
            flow_logger.warning("No holdings data provided")
            return 0, []
        
        try:
            from src.portfolio_prices import PriceFetcher
            from src.parquet_db import ParquetDB
            
            db = ParquetDB(root_path="db")
            price_fetcher = PriceFetcher()
            tickers = holdings_df['sym'].unique().tolist()
            
            flow_logger.info(f"Starting price update for {len(tickers)} tickers")
            
            all_prices = []
            failed_tickers = []
            
            # Fetch prices for each ticker
            for ticker in tickers:
                try:
                    holding = holdings_df[holdings_df['sym'] == ticker]
                    asset_type = holding.iloc[0].get('asset', 'eq') if not holding.empty else 'eq'
                    
                    price_data = fetch_price_task(ticker, asset_type=asset_type)
                    
                    if price_data:
                        all_prices.append(price_data)
                    else:
                        failed_tickers.append(ticker)
                        
                except Exception as e:
                    flow_logger.warning(f"Error fetching {ticker}: {str(e)[:100]}")
                    failed_tickers.append(ticker)
                    continue
            
            if all_prices:
                # Prepare prices
                prices_df = prepare_prices_task(all_prices)
                
                # Save to database
                success = save_prices_task(prices_df)
                
                flow_logger.info(f"Price update complete: {len(all_prices)} successful, {len(failed_tickers)} failed")
                
                return len(all_prices), failed_tickers if success else tickers
            else:
                flow_logger.warning("No price data retrieved")
                return 0, tickers
                
        except Exception as e:
            flow_logger.error(f"Price update flow failed: {str(e)[:150]}")
            return 0, holdings_df['sym'].unique().tolist()

else:
    # Fallback if Prefect not available
    def update_prices_flow(holdings_df: pd.DataFrame) -> Tuple[int, List[str]]:
        """Fallback price update without Prefect."""
        return update_prices_streamlit(holdings_df)
