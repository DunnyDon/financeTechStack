"""
XBRL data extraction from SEC filings.

Fetches and parses financial data from 10-K and 10-Q filings.
"""

import os
import time
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Optional

import pandas as pd
import requests
from prefect import flow, get_run_logger, task

from .cache import CIKCache
from .config import config
from .constants import (
    CIK_ZERO_PADDING,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_TIMEOUT,
    FILING_TYPE_10_K,
    SEC_BASE_URL,
    SEC_COMPANY_TICKERS_URL,
    SEC_FILINGS_URL,
)
from .exceptions import CIKNotFoundError, DataParseError, FilingNotFoundError
from .utils import (
    format_timestamp,
    get_logger,
    get_next_user_agent,
    make_request_with_backoff,
    safe_float_conversion,
    validate_cik,
    validate_ticker,
)

__all__ = [
    "fetch_company_cik",
    "fetch_sec_filing_index",
    "fetch_xbrl_document",
    "parse_xbrl_fundamentals",
    "save_xbrl_data_to_parquet",
    "fetch_xbrl_filings",
]

logger = get_logger(__name__)

# XBRL financial metric tags to extract
XBRL_REVENUE_TAGS = ["Revenues", "RevenueFromContractWithCustomer"]
XBRL_INCOME_TAGS = ["NetIncomeLoss"]
XBRL_OPERATING_TAGS = ["OperatingIncomeLoss"]
XBRL_NAMESPACES = {
    "us-gaap": "http://xbrl.us/us-gaap/2023-01-31",
    "iso4217": "http://www.xbrl.org/2003/iso4217",
    "xbrli": "http://www.xbrl.org/2003/instance",
}


@task(retries=3, retry_delay_seconds=5)
def fetch_company_cik(ticker: str) -> Optional[str]:
    """
    Fetch the CIK (Central Index Key) for a company given its ticker symbol.

    Checks cache first before querying SEC's official company tickers JSON file.
    Caches result for future use to avoid API rate limits.

    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL').

    Returns:
        CIK number as a zero-padded string, or None if not found.

    Raises:
        ValidationError: If ticker format is invalid.
        CIKNotFoundError: If CIK cannot be found.
    """
    logger_instance = get_run_logger()
    logger_instance.info(f"Fetching CIK for ticker: {ticker}")

    if not validate_ticker(ticker):
        raise ValueError(f"Invalid ticker format: {ticker}")

    # Check cache first
    cached_cik = CIKCache.get(ticker)
    if cached_cik:
        logger_instance.info(f"Using cached CIK for {ticker}: {cached_cik}")
        return cached_cik

    try:
        # Use make_request_with_backoff for proper retry and rate limiting
        tickers_data = make_request_with_backoff(
            SEC_COMPANY_TICKERS_URL,
            max_retries=5,
            initial_delay=2.0,
            timeout=DEFAULT_TIMEOUT,
            rate_limit_delay=0.1,
        )

        if not tickers_data:
            logger_instance.error(f"Failed to fetch company tickers for {ticker}")
            raise CIKNotFoundError(f"Could not fetch company data for {ticker}")

        for entry in tickers_data.values():
            if entry.get("ticker", "").upper() == ticker.upper():
                cik = str(entry.get("cik_str", "")).zfill(CIK_ZERO_PADDING)
                logger_instance.info(f"Found CIK: {cik} for ticker: {ticker}")
                # Cache the result
                CIKCache.set(ticker, cik)
                return cik

        logger_instance.warning(f"CIK not found for ticker: {ticker}")
        raise CIKNotFoundError(f"CIK not found for ticker: {ticker}")

    except CIKNotFoundError:
        raise
    except Exception as e:
        logger_instance.error(f"Error fetching CIK for {ticker}: {e}")
        raise CIKNotFoundError(f"Could not fetch company data for {ticker}") from e


@task(retries=3, retry_delay_seconds=5)
def fetch_sec_filing_index(
    cik: str, filing_type: str = FILING_TYPE_10_K
) -> Optional[dict]:
    """
    Fetch the most recent SEC filing index for a given CIK.

    Args:
        cik: Company's CIK number.
        filing_type: Type of filing (e.g., '10-K', '10-Q').

    Returns:
        Dictionary with filing details, or None if not found.

    Raises:
        FilingNotFoundError: If filing cannot be retrieved.
    """
    logger_instance = get_run_logger()
    logger_instance.info(f"Fetching {filing_type} filing index for CIK: {cik}")

    if not validate_cik(cik):
        raise ValueError(f"Invalid CIK format: {cik}")

    try:
        url = f"{SEC_BASE_URL}/CIK{cik}.json"
        
        # Use make_request_with_backoff for proper retry and rate limiting
        data = make_request_with_backoff(
            url,
            max_retries=5,
            initial_delay=2.0,
            timeout=DEFAULT_TIMEOUT,
            rate_limit_delay=0.1,
        )

        if not data or "filings" not in data or "recent" not in data["filings"]:
            logger_instance.warning(f"No filings found for CIK: {cik}")
            raise FilingNotFoundError(f"No filings found for CIK: {cik}")

        recent = data["filings"]["recent"]

        # Find the most recent filing of the specified type
        for i, form_type in enumerate(recent.get("form", [])):
            if form_type == filing_type:
                accession_number = recent["accessionNumber"][i]
                filing_date = recent["filingDate"][i]

                filing_info = {
                    "accession_number": accession_number,
                    "filing_date": filing_date,
                    "filing_type": filing_type,
                    "cik": cik,
                }

                logger_instance.info(f"Found {filing_type} filing: {accession_number}")
                return filing_info

        logger_instance.warning(
            f"No {filing_type} filings found for CIK: {cik}"
        )
        raise FilingNotFoundError(
            f"No {filing_type} filings found for CIK: {cik}"
        )

    except FilingNotFoundError:
        raise
    except Exception as e:
        logger_instance.error(f"Error fetching filing index for {cik}: {e}")
        raise FilingNotFoundError(
            f"Error fetching filing index for {cik}: {e}"
        ) from e


@task(retries=3, retry_delay_seconds=5)
def fetch_xbrl_document(
    cik: str, accession_number: str
) -> Optional[dict]:
    """
    Fetch XBRL document facts from SEC EDGAR JSON API.

    Uses the SEC's JSON API for company facts which is more reliable
    than downloading ZIP files and parsing XML.

    Args:
        cik: Company's CIK number.
        accession_number: Filing accession number (not used for JSON API but kept for compatibility).

    Returns:
        Dictionary with XBRL facts/metrics, or None if error.
    """
    logger_instance = get_run_logger()
    logger_instance.info(f"Fetching XBRL data for CIK: {cik}")

    try:
        # Use SEC's company facts JSON API for XBRL data
        # This endpoint provides all financial facts in structured JSON format
        url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"

        # Fetch with proper headers and rate limiting
        data = make_request_with_backoff(
            url,
            max_retries=5,
            initial_delay=2.0,
            timeout=DEFAULT_TIMEOUT,
            rate_limit_delay=0.1,
        )

        if data:
            logger_instance.info(f"Successfully retrieved XBRL data for CIK {cik}")
            return data
        else:
            logger_instance.warning(f"No XBRL data found for CIK: {cik}")
            return None

    except Exception as e:
        logger_instance.error(f"Error fetching XBRL data for CIK {cik}: {e}")
        return None


@task
def parse_xbrl_fundamentals(xbrl_data: Optional[dict], ticker: str) -> dict:
    """
    Parse fundamental data from SEC JSON API response.

    Extracts financial metrics from the SEC's company facts JSON format.

    Args:
        xbrl_data: XBRL data dictionary from SEC JSON API.
        ticker: Stock ticker symbol.

    Returns:
        Dictionary with extracted financial metrics.

    Raises:
        DataParseError: If parsing fails.
    """
    logger_instance = get_run_logger()
    logger_instance.info(f"Parsing XBRL data for {ticker}")

    fundamentals: dict[str, Optional[float]] = {
        "ticker": ticker,
        "revenue": None,
        "net_income": None,
        "gross_profit": None,
        "operating_income": None,
        "total_assets": None,
        "total_liabilities": None,
        "shareholders_equity": None,
        "operating_cash_flow": None,
        "free_cash_flow": None,
        "current_assets": None,
        "current_liabilities": None,
        "current_ratio": None,
        "quick_ratio": None,
        "debt_to_equity": None,
        "timestamp": datetime.now().isoformat(),
    }

    if not xbrl_data or "facts" not in xbrl_data:
        logger_instance.warning(f"No XBRL data provided for {ticker}")
        return fundamentals

    try:
        facts = xbrl_data.get("facts", {})
        
        # Try US GAAP first, then IFRS
        us_gaap = facts.get("us-gaap", {})
        ifrs = facts.get("ifrs-full", {})
        
        # Determine which accounting standard to use
        accounting_data = us_gaap if us_gaap else ifrs
        is_ifrs = bool(not us_gaap and ifrs)
        
        if not accounting_data:
            logger_instance.warning(f"No accounting data (us-gaap or ifrs-full) found for {ticker}")
            return fundamentals

        # Helper function to extract value from accounting data
        def get_latest_value(field_name, preferred_currencies=None):
            """Get the most recent value for a field, trying multiple currencies."""
            if preferred_currencies is None:
                preferred_currencies = ["USD", "EUR", "GBP", "JPY"]
            
            if field_name not in accounting_data:
                return None
            
            field_info = accounting_data[field_name]
            units = field_info.get("units", {})
            
            # Try preferred currencies first
            for currency in preferred_currencies:
                field_data = units.get(currency, [])
                if field_data:
                    try:
                        # Get the most recent value by filed date
                        latest = max(field_data, key=lambda x: x.get("filed", ""))
                        return safe_float_conversion(latest.get("val"))
                    except (ValueError, KeyError):
                        continue
            
            # If no preferred currency found, try any available currency
            for currency, field_data in units.items():
                if field_data:
                    try:
                        latest = max(field_data, key=lambda x: x.get("filed", ""))
                        return safe_float_conversion(latest.get("val"))
                    except (ValueError, KeyError):
                        continue
            
            return None

        # Extract revenue (US GAAP: Revenues, IFRS: Revenue)
        revenue_field = "Revenues" if not is_ifrs else "Revenue"
        fundamentals["revenue"] = get_latest_value(revenue_field)

        # Extract net income (US GAAP: NetIncomeLoss, IFRS: ProfitLoss)
        income_field = "NetIncomeLoss" if not is_ifrs else "ProfitLoss"
        fundamentals["net_income"] = get_latest_value(income_field)

        # Extract total assets
        fundamentals["total_assets"] = get_latest_value("Assets")

        # Extract total liabilities
        fundamentals["total_liabilities"] = get_latest_value("Liabilities")

        # Extract shareholders' equity
        for equity_tag in ["StockholdersEquity", "ShareholdersEquity", "EquityAttributableToOwnersOfParent"]:
            equity_value = get_latest_value(equity_tag)
            if equity_value:
                fundamentals["shareholders_equity"] = equity_value
                break

        # Extract current assets
        fundamentals["current_assets"] = get_latest_value("CurrentAssets")

        # Extract current liabilities
        fundamentals["current_liabilities"] = get_latest_value("CurrentLiabilities")

        # Calculate derived metrics
        if fundamentals["total_assets"] and fundamentals["total_liabilities"]:
            try:
                equity = fundamentals["total_assets"] - fundamentals["total_liabilities"]
                if equity != 0:
                    fundamentals["debt_to_equity"] = (
                        fundamentals["total_liabilities"] / equity
                    )
            except (TypeError, ZeroDivisionError):
                pass

        if fundamentals["current_assets"] and fundamentals["current_liabilities"]:
            try:
                fundamentals["current_ratio"] = (
                    fundamentals["current_assets"] / fundamentals["current_liabilities"]
                )
            except (TypeError, ZeroDivisionError):
                pass

        logger_instance.info(f"Successfully parsed XBRL data for {ticker}")

    except Exception as e:
        logger_instance.error(f"Error parsing XBRL data for {ticker}: {e}")
        raise DataParseError(f"Error parsing XBRL data for {ticker}: {e}") from e

    return fundamentals


@task
def save_xbrl_data_to_parquet(
    xbrl_list: list[dict], output_dir: str = DEFAULT_OUTPUT_DIR
) -> str:
    """
    Save XBRL data to Parquet file.

    Args:
        xbrl_list: List of XBRL data dictionaries.
        output_dir: Output directory.

    Returns:
        Path to saved Parquet file.

    Raises:
        IOError: If file cannot be written.
    """
    logger_instance = get_run_logger()
    logger_instance.info(f"Saving {len(xbrl_list)} XBRL records to Parquet")

    try:
        from .parquet_db import ParquetDB
        
        df = pd.DataFrame(xbrl_list)
        
        # Ensure required columns for XBRL_FILINGS table
        if 'filing_date' not in df.columns:
            df['filing_date'] = pd.Timestamp.now()
        if 'period_end_date' not in df.columns:
            df['period_end_date'] = pd.Timestamp.now()
        if 'created_at' not in df.columns:
            df['created_at'] = pd.Timestamp.now()
        if 'updated_at' not in df.columns:
            df['updated_at'] = pd.Timestamp.now()
        if 'ticker' not in df.columns:
            df['ticker'] = 'unknown'
        if 'cik' not in df.columns:
            df['cik'] = 'unknown'

        # Use ParquetDB for optimized storage with partitioning
        db = ParquetDB(output_dir)
        inserted, updated = db.upsert_xbrl_filings(df)
        logger_instance.info(f"Saved XBRL data: {inserted} new, {updated} updated")

        return file_path

    except Exception as e:
        logger_instance.error(f"Error saving XBRL data to Parquet: {e}")
        raise


@flow
def fetch_xbrl_filings(
    tickers: list[str], filing_type: str = FILING_TYPE_10_K
) -> str:
    """
    Main Prefect flow to fetch XBRL data for multiple companies.

    Args:
        tickers: List of stock tickers.
        filing_type: Type of filing (10-K or 10-Q).

    Returns:
        Path to saved Parquet file.
    """
    logger_instance = get_run_logger()
    logger_instance.info(f"Starting XBRL fetch flow for tickers: {tickers}")

    xbrl_data = []

    for ticker in tickers:
        logger_instance.info(f"Processing {ticker}")

        try:
            # Fetch CIK
            cik = fetch_company_cik(ticker)
            if not cik:
                logger_instance.warning(f"Could not find CIK for {ticker}")
                continue

            # Fetch filing index
            filing_info = fetch_sec_filing_index(cik, filing_type)
            if not filing_info:
                logger_instance.warning(
                    f"Could not find {filing_type} filing for {ticker}"
                )
                continue

            # Fetch XBRL document
            xbrl_doc = fetch_xbrl_document(cik, filing_info["accession_number"])
            if not xbrl_doc:
                logger_instance.warning(f"Could not fetch XBRL document for {ticker}")
                continue

            # Parse XBRL data
            fundamentals = parse_xbrl_fundamentals(xbrl_doc, ticker)
            xbrl_data.append(fundamentals)

        except (CIKNotFoundError, FilingNotFoundError, DataParseError) as e:
            logger_instance.warning(f"Error processing {ticker}: {e}")
            continue

        # Rate limiting: wait 2 seconds between requests
        time.sleep(2)

    # Save to Parquet
    if xbrl_data:
        file_path = save_xbrl_data_to_parquet(xbrl_data)
        logger_instance.info(f"XBRL flow completed. Data saved to {file_path}")
        return file_path
    else:
        logger_instance.warning("No XBRL data collected")
        return ""


def main() -> None:
    """Test XBRL fetching with example companies."""
    result = fetch_xbrl_filings(["AAPL", "MSFT"])
    print(f"Results saved to: {result}")


if __name__ == "__main__":
    main()

