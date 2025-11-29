"""
Data merge module for combining Alpha Vantage and SEC XBRL financial data.

Provides utilities to join and analyze fundamental data from multiple sources.
"""

import glob
import os
from datetime import datetime
from typing import Optional

import pandas as pd
from prefect import get_run_logger, task

from .constants import DEFAULT_OUTPUT_DIR
from .utils import format_timestamp, get_logger

__all__ = [
    "read_alpha_vantage_data",
    "read_xbrl_data",
    "merge_fundamental_data",
    "enrich_with_calculated_metrics",
    "save_merged_data_to_parquet",
    "get_ticker_analysis",
    "compare_tickers",
]

logger = get_logger(__name__)


@task
def read_alpha_vantage_data(
    file_pattern: str = "db/fundamentals_*.parquet",
) -> Optional[pd.DataFrame]:
    """
    Read Alpha Vantage fundamental data from Parquet files.

    Reads the most recent file matching the pattern.

    Args:
        file_pattern: Glob pattern for Parquet files.

    Returns:
        DataFrame with Alpha Vantage data or None if no files found.
    """
    logger_instance = get_run_logger()
    logger_instance.info(f"Reading Alpha Vantage data from {file_pattern}")

    try:
        files = glob.glob(file_pattern)

        if not files:
            logger_instance.warning(
                f"No Alpha Vantage files found matching {file_pattern}"
            )
            return None

        # Read the most recent file
        latest_file = sorted(files)[-1]
        logger_instance.info(f"Reading from: {latest_file}")

        df = pd.read_parquet(latest_file)
        logger_instance.info(f"Loaded {len(df)} rows from Alpha Vantage data")

        return df

    except Exception as e:
        logger_instance.error(f"Error reading Alpha Vantage data: {e}")
        return None


@task
def read_xbrl_data(
    file_pattern: str = "db/xbrl_data_*.parquet",
) -> Optional[pd.DataFrame]:
    """
    Read XBRL fundamental data from Parquet files.

    Reads the most recent file matching the pattern.

    Args:
        file_pattern: Glob pattern for Parquet files.

    Returns:
        DataFrame with XBRL data or None if no files found.
    """
    logger_instance = get_run_logger()
    logger_instance.info(f"Reading XBRL data from {file_pattern}")

    try:
        files = glob.glob(file_pattern)

        if not files:
            logger_instance.warning(f"No XBRL files found matching {file_pattern}")
            return None

        # Read the most recent file
        latest_file = sorted(files)[-1]
        logger_instance.info(f"Reading from: {latest_file}")

        df = pd.read_parquet(latest_file)
        logger_instance.info(f"Loaded {len(df)} rows from XBRL data")

        return df

    except Exception as e:
        logger_instance.error(f"Error reading XBRL data: {e}")
        return None


@task
def merge_fundamental_data(
    alpha_vantage_df: Optional[pd.DataFrame],
    xbrl_df: Optional[pd.DataFrame],
) -> Optional[pd.DataFrame]:
    """
    Merge Alpha Vantage and XBRL data by ticker.

    Alpha Vantage provides current fundamentals while XBRL provides
    detailed historical data from SEC filings.

    Args:
        alpha_vantage_df: DataFrame with Alpha Vantage data.
        xbrl_df: DataFrame with XBRL data.

    Returns:
        Merged DataFrame with combined data, or None if merge fails.
    """
    logger_instance = get_run_logger()
    logger_instance.info("Merging Alpha Vantage and XBRL data")

    try:
        if alpha_vantage_df is None and xbrl_df is None:
            logger_instance.warning("Both DataFrames are None, nothing to merge")
            return None

        if alpha_vantage_df is None:
            logger_instance.info("Only XBRL data available")
            return xbrl_df

        if xbrl_df is None:
            logger_instance.info("Only Alpha Vantage data available")
            return alpha_vantage_df

        # Merge on ticker (case-insensitive)
        alpha_vantage_df["ticker_lower"] = (
            alpha_vantage_df.get("ticker", "").str.lower()
        )
        xbrl_df["ticker_lower"] = xbrl_df.get("ticker", "").str.lower()

        merged = pd.merge(
            alpha_vantage_df,
            xbrl_df,
            on="ticker_lower",
            how="outer",
            suffixes=("_alpha_vantage", "_xbrl"),
        )

        # Clean up temporary column
        merged = merged.drop("ticker_lower", axis=1)

        # Consolidate ticker column if both sources have it
        if (
            "ticker_alpha_vantage" in merged.columns
            and "ticker_xbrl" in merged.columns
        ):
            merged["ticker"] = merged["ticker_alpha_vantage"].fillna(
                merged["ticker_xbrl"]
            )
            merged = merged.drop(["ticker_alpha_vantage", "ticker_xbrl"], axis=1)

        logger_instance.info(f"Merged data contains {len(merged)} unique tickers")
        logger_instance.info(f"Total columns: {len(merged.columns)}")

        return merged

    except Exception as e:
        logger_instance.error(f"Error merging data: {e}")
        return None


@task
def enrich_with_calculated_metrics(
    merged_df: Optional[pd.DataFrame],
) -> Optional[pd.DataFrame]:
    """
    Add calculated financial metrics to merged data.

    Enriches data with composite scores for profitability, health, and value.

    Args:
        merged_df: DataFrame with merged fundamental data.

    Returns:
        DataFrame with additional calculated metrics.
    """
    logger_instance = get_run_logger()
    logger_instance.info("Enriching data with calculated metrics")

    if merged_df is None or len(merged_df) == 0:
        logger_instance.warning("No data to enrich")
        return merged_df

    try:
        df = merged_df.copy()

        # Profitability Score (combination of margins)
        margin_columns = [col for col in df.columns if "margin" in col.lower()]
        if margin_columns:
            # Convert to numeric and calculate average
            for col in margin_columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
            df["profit_score"] = df[margin_columns].mean(axis=1)

        # Financial Health Score (combination of ratios)
        ratio_columns = [
            col
            for col in df.columns
            if "ratio" in col.lower() and "pe" not in col.lower()
        ]
        if ratio_columns:
            for col in ratio_columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
            df["health_score"] = df[ratio_columns].mean(axis=1)

        # P/E Ratio conversion to numeric
        if "pe_ratio" in df.columns:
            df["pe_ratio_numeric"] = pd.to_numeric(df["pe_ratio"], errors="coerce")
            # Value Score (inverse of P/E ratio)
            df["value_score"] = 1 / df["pe_ratio_numeric"]

        df["enriched_at"] = datetime.now().isoformat()

        new_columns = len(
            [col for col in df.columns if col not in merged_df.columns]
        )
        logger_instance.info(f"Added {new_columns} calculated metrics")

        return df

    except Exception as e:
        logger_instance.error(f"Error enriching data: {e}")
        return merged_df


@task
def save_merged_data_to_parquet(
    merged_df: Optional[pd.DataFrame],
    output_dir: str = DEFAULT_OUTPUT_DIR,
    filename_prefix: str = "merged_fundamentals",
) -> Optional[str]:
    """
    Save merged fundamental data to Parquet file.

    Args:
        merged_df: DataFrame with merged data.
        output_dir: Output directory.
        filename_prefix: Prefix for output filename.

    Returns:
        Path to saved file or None if error.

    Raises:
        IOError: If file cannot be written.
    """
    logger_instance = get_run_logger()

    if merged_df is None or len(merged_df) == 0:
        logger_instance.warning("No data to save")
        return None

    try:
        os.makedirs(output_dir, exist_ok=True)

        timestamp = format_timestamp()
        file_path = os.path.join(
            output_dir, f"{filename_prefix}_{timestamp}.parquet"
        )

        merged_df.to_parquet(file_path, compression="snappy", index=False)
        logger_instance.info(f"Saved merged data to {file_path}")

        return file_path

    except Exception as e:
        logger_instance.error(f"Error saving merged data: {e}")
        return None


def get_ticker_analysis(merged_df: Optional[pd.DataFrame], ticker: str) -> dict:
    """
    Get combined analysis for a specific ticker.

    Args:
        merged_df: DataFrame with merged fundamental data.
        ticker: Stock ticker symbol.

    Returns:
        Dictionary with analysis for the ticker.
    """
    if merged_df is None or len(merged_df) == 0:
        return {"error": "No data available"}

    # Find ticker (case-insensitive)
    ticker_upper = ticker.upper()
    ticker_data = merged_df[merged_df.get("ticker", "").str.upper() == ticker_upper]

    if len(ticker_data) == 0:
        return {"error": f"Ticker {ticker} not found"}

    # Convert first row to dictionary, handling NaN values
    analysis = ticker_data.iloc[0].to_dict()

    # Replace NaN with None for cleaner output
    analysis = {k: (None if pd.isna(v) else v) for k, v in analysis.items()}

    return analysis


def compare_tickers(
    merged_df: Optional[pd.DataFrame], tickers: list[str], metric: str
) -> Optional[pd.DataFrame]:
    """
    Compare a specific metric across multiple tickers.

    Args:
        merged_df: DataFrame with merged fundamental data.
        tickers: List of ticker symbols to compare.
        metric: Column name to compare.

    Returns:
        DataFrame with comparison data, sorted by metric.
    """
    if merged_df is None or len(merged_df) == 0:
        return None

    if metric not in merged_df.columns:
        return None

    # Filter to requested tickers
    tickers_upper = [t.upper() for t in tickers]
    comparison_df = merged_df[
        merged_df.get("ticker", "").str.upper().isin(tickers_upper)
    ]

    if len(comparison_df) == 0:
        return None

    return comparison_df[["ticker", metric]].sort_values(metric, ascending=False)

