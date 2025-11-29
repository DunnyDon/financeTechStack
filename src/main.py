"""
Comprehensive financial data aggregation with Prefect orchestration.

Integrates SEC EDGAR filings, XBRL fundamentals, and Alpha Vantage data
into unified financial datasets.
"""

import os
import time
from datetime import datetime
from typing import Optional

import pandas as pd
from prefect import flow, get_run_logger, task

from .alpha_vantage import fetch_fundamental_data
from .config import config
from .constants import (
    ALPHA_VANTAGE_RATE_LIMIT_DELAY,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_TIMEOUT,
    FILING_TYPE_10_K,
    INITIAL_BACKOFF_DELAY,
    REQUEST_MAX_RETRIES,
)
from .exceptions import CIKNotFoundError, FilingNotFoundError, ValidationError
from .utils import (
    format_timestamp,
    get_logger,
    make_request_with_backoff,
    validate_cik,
    validate_ticker,
)
from .xbrl import (
    fetch_company_cik as fetch_cik_xbrl,
    fetch_sec_filing_index,
    fetch_xbrl_document,
    parse_xbrl_fundamentals,
    save_xbrl_data_to_parquet,
)

__all__ = [
    "fetch_company_cik",
    "fetch_integrated_data",
    "aggregate_financial_data",
]

logger = get_logger(__name__)

# SEC API endpoints
SEC_BASE_URL = "https://data.sec.gov/submissions"
SEC_COMPANY_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"


@task(retries=3, retry_delay_seconds=5)
def fetch_company_cik(ticker: str) -> Optional[dict]:
    """
    Fetch company information including CIK and filing data.

    Args:
        ticker: Stock ticker symbol.

    Returns:
        Dictionary with company info and CIK, or None if not found.

    Raises:
        ValidationError: If ticker format is invalid.
        CIKNotFoundError: If CIK cannot be found.
    """
    logger_instance = get_run_logger()
    logger_instance.info(f"Fetching company info for ticker: {ticker}")

    if not validate_ticker(ticker):
        raise ValidationError(f"Invalid ticker format: {ticker}")

    try:
        # Use the efficient xbrl function which already has proper headers/retries
        cik = fetch_cik_xbrl(ticker)

        if not cik:
            raise CIKNotFoundError(f"Could not find CIK for {ticker}")

        logger_instance.info(f"Found CIK: {cik} for ticker: {ticker}")
        return {
            "ticker": ticker,
            "cik": cik,
            "fetched_at": datetime.now().isoformat(),
        }

    except CIKNotFoundError:
        raise
    except Exception as e:
        logger_instance.error(f"Error fetching company info for {ticker}: {e}")
        raise CIKNotFoundError(f"Error fetching company info for {ticker}: {e}") from e


@task(retries=3, retry_delay_seconds=5)
def fetch_filing_metadata(cik: str, filing_type: str = FILING_TYPE_10_K) -> Optional[dict]:
    """
    Fetch latest filing metadata from SEC.

    Args:
        cik: Company's CIK number.
        filing_type: Type of filing (e.g., '10-K', '10-Q').

    Returns:
        Dictionary with filing details and timestamps.

    Raises:
        FilingNotFoundError: If filing cannot be found.
    """
    logger_instance = get_run_logger()
    logger_instance.info(f"Fetching {filing_type} filing metadata for CIK: {cik}")

    if not validate_cik(cik):
        raise ValidationError(f"Invalid CIK format: {cik}")

    try:
        # Use the xbrl function which already has proper headers/retries
        filing_info = fetch_sec_filing_index(cik, filing_type)

        if not filing_info:
            raise FilingNotFoundError(f"No {filing_type} filing found for CIK: {cik}")

        # Add fetch timestamp
        filing_info["fetched_at"] = datetime.now().isoformat()
        logger_instance.info(f"Found {filing_type} filing: {filing_info['accession_number']}")
        return filing_info

    except FilingNotFoundError:
        raise
    except Exception as e:
        logger_instance.error(f"Error fetching filing metadata for {cik}: {e}")
        raise FilingNotFoundError(f"Error fetching filing metadata for {cik}: {e}") from e


@task(retries=3, retry_delay_seconds=5)
def fetch_xbrl_data(cik: str, ticker: str) -> Optional[dict]:
    """
    Fetch and parse XBRL fundamental data from SEC.

    Args:
        cik: Company's CIK number.
        ticker: Stock ticker symbol.

    Returns:
        Dictionary with extracted financial metrics and timestamps.
    """
    logger_instance = get_run_logger()
    logger_instance.info(f"Fetching XBRL data for {ticker} (CIK: {cik})")

    try:
        # Fetch XBRL document from SEC API
        xbrl_data = fetch_xbrl_document(cik, "")

        if not xbrl_data:
            logger_instance.warning(f"No XBRL data found for {ticker}")
            return None

        # Parse the XBRL data
        fundamentals = parse_xbrl_fundamentals(xbrl_data, ticker)

        logger_instance.info(f"Successfully parsed XBRL data for {ticker}")
        return fundamentals

    except Exception as e:
        logger_instance.error(f"Error fetching XBRL data for {ticker}: {e}")
        return None


@task(retries=3, retry_delay_seconds=5)
def fetch_alpha_vantage_data(ticker: str) -> Optional[dict]:
    """
    Fetch fundamental and technical data from Alpha Vantage.

    Args:
        ticker: Stock ticker symbol.

    Returns:
        Dictionary with Alpha Vantage metrics and timestamp.
    """
    logger_instance = get_run_logger()
    logger_instance.info(f"Fetching Alpha Vantage data for {ticker}")

    try:
        # Check if API key is configured
        if not config.get_alpha_vantage_key():
            logger_instance.warning("Alpha Vantage API key not configured, skipping")
            return None

        # Fetch fundamental data
        av_data = fetch_fundamental_data(ticker)

        if av_data:
            av_data["fetched_at"] = datetime.now().isoformat()
            logger_instance.info(f"Successfully fetched Alpha Vantage data for {ticker}")
            return av_data
        else:
            logger_instance.warning(f"No Alpha Vantage data found for {ticker}")
            return None

    except Exception as e:
        logger_instance.error(f"Error fetching Alpha Vantage data for {ticker}: {e}")
        return None


@task
def merge_financial_data(
    company_info: dict,
    filing_metadata: Optional[dict],
    xbrl_data: Optional[dict],
    alpha_vantage_data: Optional[dict],
) -> dict:
    """
    Merge all financial data sources into a unified record.

    Args:
        company_info: Basic company information.
        filing_metadata: SEC filing metadata.
        xbrl_data: XBRL fundamentals from SEC.
        alpha_vantage_data: Alpha Vantage fundamentals.

    Returns:
        Merged dictionary with all available financial data.
    """
    logger_instance = get_run_logger()
    logger_instance.info(f"Merging financial data for {company_info['ticker']}")

    merged = {
        **company_info,
        "data_sources": [],
        "aggregated_at": datetime.now().isoformat(),
    }

    if filing_metadata:
        merged.update({
            f"sec_filing_{k}": v
            for k, v in filing_metadata.items()
        })
        merged["data_sources"].append("sec_filings")

    if xbrl_data:
        merged.update({
            f"xbrl_{k}": v
            for k, v in xbrl_data.items()
        })
        merged["data_sources"].append("xbrl")

    if alpha_vantage_data:
        merged.update({
            f"av_{k}": v
            for k, v in alpha_vantage_data.items()
        })
        merged["data_sources"].append("alpha_vantage")

    return merged


@task
def save_aggregated_data(
    records: list[dict], output_dir: str = DEFAULT_OUTPUT_DIR
) -> str:
    """
    Save aggregated financial data to Parquet file.

    Args:
        records: List of merged financial data records.
        output_dir: Output directory for Parquet files.

    Returns:
        Path to saved Parquet file.
    """
    logger_instance = get_run_logger()
    logger_instance.info(f"Saving {len(records)} aggregated records to Parquet")

    try:
        os.makedirs(output_dir, exist_ok=True)

        df = pd.DataFrame(records)
        timestamp = format_timestamp()
        output_file = f"{output_dir}/financial_data_{timestamp}.parquet"

        df.to_parquet(
            output_file, engine="pyarrow", compression="snappy", index=False
        )
        logger_instance.info(f"Saved aggregated data to {output_file}")
        return output_file

    except Exception as e:
        logger_instance.error(f"Error saving aggregated data: {e}")
        raise


@flow(name="Integrated Financial Data Aggregator")
def aggregate_financial_data(
    tickers: list[str],
    filing_type: str = FILING_TYPE_10_K,
    include_alpha_vantage: bool = True,
) -> dict:
    """
    Main Prefect flow to aggregate financial data from multiple sources.

    Combines SEC EDGAR filings, XBRL fundamentals, and Alpha Vantage data
    into unified financial records for each company.

    Args:
        tickers: List of stock ticker symbols.
        filing_type: Type of SEC filing to retrieve (default: '10-K').
        include_alpha_vantage: Whether to fetch Alpha Vantage data.

    Returns:
        Dictionary with path to saved data and summary statistics.
    """
    logger_instance = get_run_logger()
    logger_instance.info(
        f"Starting financial data aggregation for tickers: {tickers}"
    )

    aggregated_records = []
    summary = {
        "total_tickers": len(tickers),
        "successful": 0,
        "failed": 0,
        "partial": 0,
        "output_file": None,
        "started_at": datetime.now().isoformat(),
    }

    for ticker in tickers:
        logger_instance.info(f"Processing {ticker}")

        try:
            # Step 1: Get company info and CIK
            company_info = fetch_company_cik(ticker)
            if not company_info:
                logger_instance.warning(f"Failed to get company info for {ticker}")
                summary["failed"] += 1
                continue

            cik = company_info["cik"]

            # Step 2: Fetch filing metadata
            filing_metadata = None
            try:
                filing_metadata = fetch_filing_metadata(cik, filing_type)
            except FilingNotFoundError:
                logger_instance.warning(f"No {filing_type} filing found for {ticker}")

            # Step 3: Fetch XBRL fundamentals
            xbrl_data = fetch_xbrl_data(cik, ticker)

            # Step 4: Fetch Alpha Vantage data (if enabled)
            alpha_vantage_data = None
            if include_alpha_vantage:
                alpha_vantage_data = fetch_alpha_vantage_data(ticker)
                time.sleep(ALPHA_VANTAGE_RATE_LIMIT_DELAY)  # Rate limiting

            # Step 5: Merge all data
            merged_data = merge_financial_data(
                company_info,
                filing_metadata,
                xbrl_data,
                alpha_vantage_data,
            )
            aggregated_records.append(merged_data)

            # Track success
            if filing_metadata and xbrl_data:
                summary["successful"] += 1
            else:
                summary["partial"] += 1

            # Rate limiting between companies
            time.sleep(2)

        except (CIKNotFoundError, ValidationError) as e:
            logger_instance.warning(f"Error processing {ticker}: {e}")
            summary["failed"] += 1
            continue

    # Step 6: Save aggregated data
    if aggregated_records:
        output_file = save_aggregated_data(aggregated_records)
        summary["output_file"] = output_file
        logger_instance.info(
            f"Aggregation complete! Saved {len(aggregated_records)} records"
        )
    else:
        logger_instance.warning("No data was aggregated")

    summary["completed_at"] = datetime.now().isoformat()
    return summary


def main() -> None:
    """Run the financial data aggregation with example companies."""
    tickers = ["AAPL", "MSFT"]
    results = aggregate_financial_data(tickers, filing_type=FILING_TYPE_10_K)
    print(f"\n{'='*60}")
    print("Financial Data Aggregation Summary")
    print(f"{'='*60}")
    print(f"Total tickers processed: {results['total_tickers']}")
    print(f"Successful: {results['successful']}")
    print(f"Partial (missing some data): {results['partial']}")
    print(f"Failed: {results['failed']}")
    if results["output_file"]:
        print(f"Output file: {results['output_file']}")
    print(f"Started: {results['started_at']}")
    print(f"Completed: {results['completed_at']}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()

