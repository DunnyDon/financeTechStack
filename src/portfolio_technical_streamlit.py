"""
Streamlit-compatible technical analysis with Prefect flow integration.

Provides technical indicator calculation functions that work both directly
in Streamlit and with Prefect for logging and monitoring.
"""

from typing import Dict, List, Optional, Tuple

import pandas as pd
import numpy as np

try:
    from prefect import flow, task, get_run_logger
    HAS_PREFECT = True
except ImportError:
    HAS_PREFECT = False


def calculate_indicators_for_symbol(
    symbol: str,
    symbol_prices: pd.DataFrame
) -> Optional[pd.DataFrame]:
    """
    Calculate technical indicators for a single symbol.
    
    Args:
        symbol: Stock ticker symbol
        symbol_prices: DataFrame with OHLCV data for the symbol
    
    Returns:
        DataFrame with indicators or None if insufficient data
    """
    try:
        from src.portfolio_technical import TechnicalAnalyzer
        
        if len(symbol_prices) < 20:  # Need minimum data
            return None
        
        # Calculate indicators using the static method
        indicators = TechnicalAnalyzer.calculate_all(symbol_prices)
        
        return indicators if indicators is not None and not indicators.empty else None
        
    except Exception as e:
        return None


def validate_technical_data(
    symbol_prices: pd.DataFrame
) -> bool:
    """
    Validate that price data is suitable for technical analysis.
    
    Args:
        symbol_prices: DataFrame with price data
    
    Returns:
        True if data is valid, False otherwise
    """
    if symbol_prices is None or symbol_prices.empty:
        return False
    
    if len(symbol_prices) < 20:
        return False
    
    required_cols = ['timestamp', 'close_price']
    if not all(col in symbol_prices.columns for col in required_cols):
        return False
    
    return True


def save_technical_to_db(
    technical_df: pd.DataFrame,
    db=None
) -> bool:
    """
    Save technical analysis results to ParquetDB.
    
    Args:
        technical_df: DataFrame with technical indicators
        db: ParquetDB instance (creates new if None)
    
    Returns:
        True if successful, False otherwise
    """
    try:
        if db is None:
            from src.parquet_db import ParquetDB
            db = ParquetDB(root_path="db")
        
        db.upsert_technical_analysis(technical_df)
        return True
        
    except Exception as e:
        return False


def calculate_technical_streamlit(
    holdings_df: pd.DataFrame,
    db=None,
    prices_df: pd.DataFrame = None
) -> Tuple[int, List[str]]:
    """
    Calculate technical indicators for all holdings (Streamlit-compatible).
    
    Works directly in Streamlit without Prefect context.
    
    Args:
        holdings_df: DataFrame with holdings
        db: ParquetDB instance (creates new if None)
        prices_df: DataFrame with price data (fetches from DB if None)
    
    Returns:
        Tuple of (number of symbols processed, list of failed symbols)
    """
    try:
        from src.parquet_db import ParquetDB
        
        if db is None:
            db = ParquetDB(root_path="db")
        
        # Get price data if not provided
        if prices_df is None:
            prices_df = db.read_table('prices')
        
        if prices_df is None or prices_df.empty:
            return 0, holdings_df['sym'].unique().tolist()
        
        symbols = holdings_df['sym'].unique().tolist()
        holdings_prices = prices_df[prices_df['symbol'].isin(symbols)].copy()
        
        if holdings_prices.empty:
            return 0, symbols
        
        all_indicators = []
        failed_symbols = []
        
        for symbol in symbols:
            try:
                symbol_prices = holdings_prices[holdings_prices['symbol'] == symbol].sort_values('timestamp')
                
                if not validate_technical_data(symbol_prices):
                    failed_symbols.append(symbol)
                    continue
                
                indicators = calculate_indicators_for_symbol(symbol, symbol_prices)
                
                if indicators is not None and not indicators.empty:
                    all_indicators.append(indicators)
                else:
                    failed_symbols.append(symbol)
                    
            except Exception as e:
                failed_symbols.append(symbol)
                continue
        
        if all_indicators:
            combined = pd.concat(all_indicators, ignore_index=True)
            success = save_technical_to_db(combined, db)
            
            if success:
                return len(all_indicators), failed_symbols
            else:
                return 0, symbols
        else:
            return 0, symbols
            
    except Exception as e:
        return 0, holdings_df['sym'].unique().tolist()


# Prefect task wrappers (optional, if Prefect available)
if HAS_PREFECT:
    @task(name="calculate_indicators_task")
    def calculate_indicators_task(
        symbol: str,
        symbol_prices: pd.DataFrame
    ) -> Optional[pd.DataFrame]:
        """Prefect task for calculating indicators."""
        task_logger = get_run_logger()
        task_logger.info(f"Calculating indicators for {symbol}")
        
        indicators = calculate_indicators_for_symbol(symbol, symbol_prices)
        
        if indicators is not None:
            task_logger.info(f"Calculated {len(indicators)} records for {symbol}")
        else:
            task_logger.warning(f"Failed to calculate indicators for {symbol}")
        
        return indicators
    
    @task(name="validate_price_data_task")
    def validate_price_data_task(
        symbol: str,
        symbol_prices: pd.DataFrame
    ) -> bool:
        """Prefect task for validating price data."""
        task_logger = get_run_logger()
        
        is_valid = validate_technical_data(symbol_prices)
        
        if is_valid:
            task_logger.info(f"Price data valid for {symbol} ({len(symbol_prices)} records)")
        else:
            task_logger.warning(f"Price data invalid for {symbol}")
        
        return is_valid
    
    @task(name="save_technical_task")
    def save_technical_task(technical_df: pd.DataFrame) -> bool:
        """Prefect task for saving technical indicators."""
        task_logger = get_run_logger()
        task_logger.info(f"Saving {len(technical_df)} technical records")
        
        success = save_technical_to_db(technical_df)
        
        if success:
            task_logger.info("Technical indicators saved successfully")
        else:
            task_logger.error("Failed to save technical indicators")
        
        return success
    
    @flow(name="calculate_technical_flow")
    def calculate_technical_flow(
        holdings_df: pd.DataFrame,
        prices_df: pd.DataFrame = None
    ) -> Tuple[int, List[str]]:
        """
        Streamlit-compatible technical analysis flow with Prefect logging.
        
        Args:
            holdings_df: DataFrame with holdings data
            prices_df: DataFrame with price data (optional)
        
        Returns:
            Tuple of (number of processed symbols, list of failed symbols)
        """
        from src.parquet_db import ParquetDB
        
        flow_logger = get_run_logger()
        
        if holdings_df is None or holdings_df.empty:
            flow_logger.warning("No holdings data provided")
            return 0, []
        
        try:
            db = ParquetDB(root_path="db")
            
            # Get price data if not provided
            if prices_df is None:
                prices_df = db.read_table('prices')
            
            if prices_df is None or prices_df.empty:
                flow_logger.error("No price data available")
                return 0, holdings_df['sym'].unique().tolist()
            
            symbols = holdings_df['sym'].unique().tolist()
            holdings_prices = prices_df[prices_df['symbol'].isin(symbols)].copy()
            
            if holdings_prices.empty:
                flow_logger.error("No price data for holdings")
                return 0, symbols
            
            flow_logger.info(f"Starting technical analysis for {len(symbols)} symbols")
            
            all_indicators = []
            failed_symbols = []
            
            # Process each symbol
            for symbol in symbols:
                try:
                    symbol_prices = holdings_prices[holdings_prices['symbol'] == symbol].sort_values('timestamp')
                    
                    # Validate price data
                    is_valid = validate_price_data_task(symbol, symbol_prices)
                    
                    if not is_valid:
                        failed_symbols.append(symbol)
                        continue
                    
                    # Calculate indicators
                    indicators = calculate_indicators_task(symbol, symbol_prices)
                    
                    if indicators is not None and not indicators.empty:
                        all_indicators.append(indicators)
                    else:
                        failed_symbols.append(symbol)
                        
                except Exception as e:
                    flow_logger.warning(f"Error processing {symbol}: {str(e)[:100]}")
                    failed_symbols.append(symbol)
                    continue
            
            if all_indicators:
                combined = pd.concat(all_indicators, ignore_index=True)
                
                # Save to database
                success = save_technical_task(combined)
                
                flow_logger.info(f"Technical analysis complete: {len(all_indicators)} processed, {len(failed_symbols)} failed")
                
                return len(all_indicators), failed_symbols if success else symbols
            else:
                flow_logger.warning("No indicators calculated")
                return 0, symbols
                
        except Exception as e:
            flow_logger.error(f"Technical analysis flow failed: {str(e)[:150]}")
            return 0, holdings_df['sym'].unique().tolist()

else:
    # Fallback if Prefect not available
    def calculate_technical_flow(
        holdings_df: pd.DataFrame,
        prices_df: pd.DataFrame = None
    ) -> Tuple[int, List[str]]:
        """Fallback technical analysis without Prefect."""
        return calculate_technical_streamlit(holdings_df, prices_df=prices_df)
