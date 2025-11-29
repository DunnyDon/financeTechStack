"""
XBRL data extraction from SEC filings.
Fetches and parses financial data from 10-K and 10-Q filings.
"""

import os
import time
from datetime import datetime
from typing import Optional
import xml.etree.ElementTree as ET

import requests
from prefect import flow, task, get_run_logger
import pandas as pd

try:
    from .config import config
except ImportError:
    from config import config


SEC_BASE_URL = "https://data.sec.gov/submissions"
SEC_COMPANY_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SEC_FILINGS_URL = "https://www.sec.gov/cgi-bin/browse-edgar"


@task(retries=3, retry_delay_seconds=5)
def fetch_company_cik(ticker: str) -> Optional[str]:
    """
    Fetch the CIK (Central Index Key) for a company given its ticker symbol.
    Uses SEC's official company tickers JSON file.
    
    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL')
        
    Returns:
        CIK number as a zero-padded string, or None if not found
    """
    logger = get_run_logger()
    logger.info(f"Fetching CIK for ticker: {ticker}")
    
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.9",
        }
        
        response = requests.get(SEC_COMPANY_TICKERS_URL, headers=headers, timeout=10)
        response.raise_for_status()
        
        tickers_data = response.json()
        
        for entry in tickers_data.values():
            if entry.get("ticker", "").upper() == ticker.upper():
                cik = str(entry.get("cik_str", "")).zfill(10)
                logger.info(f"Found CIK: {cik} for ticker: {ticker}")
                return cik
        
        logger.warning(f"CIK not found for ticker: {ticker}")
        return None
            
    except Exception as e:
        logger.error(f"Error fetching CIK for {ticker}: {e}")
        raise


@task(retries=3, retry_delay_seconds=5)
def fetch_sec_filing_index(cik: str, filing_type: str = "10-K") -> Optional[dict]:
    """
    Fetch the most recent SEC filing index for a given CIK.
    
    Args:
        cik: Company's CIK number
        filing_type: Type of filing (e.g., '10-K', '10-Q')
        
    Returns:
        Dictionary with filing details (accession number, filing date, index URL)
    """
    logger = get_run_logger()
    logger.info(f"Fetching {filing_type} filing index for CIK: {cik}")
    
    try:
        url = f"{SEC_BASE_URL}/CIK{cik}.json"
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.9",
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if "filings" not in data or "recent" not in data["filings"]:
            logger.warning(f"No filings found for CIK: {cik}")
            return None
        
        recent = data["filings"]["recent"]
        
        # Find the most recent filing of the specified type
        for i, form_type in enumerate(recent.get("form", [])):
            if form_type == filing_type:
                accession_number = recent["accessionNumber"][i]
                filing_date = recent["filingDate"][i]
                filing_url = recent.get("primaryDocument", [None])[i] if i < len(recent.get("primaryDocument", [])) else None
                
                filing_info = {
                    "accession_number": accession_number,
                    "filing_date": filing_date,
                    "filing_type": filing_type,
                    "cik": cik,
                }
                
                logger.info(f"Found {filing_type} filing: {accession_number}")
                return filing_info
        
        logger.warning(f"No {filing_type} filings found for CIK: {cik}")
        return None
            
    except Exception as e:
        logger.error(f"Error fetching filing index for {cik}: {e}")
        raise


@task(retries=3, retry_delay_seconds=5)
def fetch_xbrl_document(cik: str, accession_number: str) -> Optional[str]:
    """
    Fetch XBRL document from SEC EDGAR.
    
    Args:
        cik: Company's CIK number
        accession_number: Filing accession number
        
    Returns:
        XBRL XML content as string, or None if error
    """
    logger = get_run_logger()
    logger.info(f"Fetching XBRL document for accession: {accession_number}")
    
    try:
        # Convert accession number to URL format (remove hyphens)
        accession_clean = accession_number.replace("-", "")
        
        # Construct XBRL file URL
        xbrl_url = (
            f"https://www.sec.gov/cgi-bin/viewer?"
            f"action=view&cik={cik}&accession_number={accession_number}"
            f"&xbrl_type=v"
        )
        
        # Try alternate URL for XBRL instance document
        instance_url = (
            f"https://www.sec.gov/Archives/edgar/full/{accession_clean[0:10]}/"
            f"{accession_clean[10:12]}/{accession_clean[12:20]}/"
            f"{accession_number}-xbrl.zip"
        )
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        # Attempt to fetch XBRL data
        logger.info(f"Fetching from: {instance_url}")
        response = requests.get(instance_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            logger.info(f"Successfully retrieved XBRL document")
            return response.content
        else:
            logger.warning(f"XBRL document not found at {instance_url}")
            return None
            
    except Exception as e:
        logger.error(f"Error fetching XBRL document: {e}")
        return None


@task
def parse_xbrl_fundamentals(xbrl_data: Optional[str], ticker: str) -> dict:
    """
    Parse fundamental data from XBRL document.
    
    Args:
        xbrl_data: XBRL XML content
        ticker: Stock ticker symbol
        
    Returns:
        Dictionary with extracted financial metrics
    """
    logger = get_run_logger()
    logger.info(f"Parsing XBRL data for {ticker}")
    
    fundamentals = {
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
    
    if not xbrl_data:
        logger.warning(f"No XBRL data provided for {ticker}")
        return fundamentals
    
    try:
        # Parse XBRL XML
        root = ET.fromstring(xbrl_data)
        
        # Define common namespaces used in XBRL documents
        namespaces = {
            "us-gaap": "http://xbrl.us/us-gaap/2023-01-31",
            "iso4217": "http://www.xbrl.org/2003/iso4217",
            "xbrli": "http://www.xbrl.org/2003/instance",
        }
        
        # Extract income statement data
        for element in root.iter():
            tag = element.tag
            text = element.text
            
            # Revenue
            if "Revenues" in tag or "RevenueFromContractWithCustomer" in tag:
                try:
                    fundamentals["revenue"] = float(text) if text else None
                except (ValueError, TypeError):
                    pass
            
            # Net Income
            if "NetIncomeLoss" in tag:
                try:
                    fundamentals["net_income"] = float(text) if text else None
                except (ValueError, TypeError):
                    pass
            
            # Operating Income
            if "OperatingIncomeLoss" in tag:
                try:
                    fundamentals["operating_income"] = float(text) if text else None
                except (ValueError, TypeError):
                    pass
            
            # Balance Sheet - Assets
            if "Assets" in tag and "Current" not in tag:
                try:
                    fundamentals["total_assets"] = float(text) if text else None
                except (ValueError, TypeError):
                    pass
            
            # Balance Sheet - Liabilities
            if "Liabilities" in tag and "Current" not in tag:
                try:
                    fundamentals["total_liabilities"] = float(text) if text else None
                except (ValueError, TypeError):
                    pass
            
            # Shareholders' Equity
            if "StockholdersEquity" in tag or "ShareholdersEquity" in tag:
                try:
                    fundamentals["shareholders_equity"] = float(text) if text else None
                except (ValueError, TypeError):
                    pass
            
            # Current Assets
            if "CurrentAssets" in tag:
                try:
                    fundamentals["current_assets"] = float(text) if text else None
                except (ValueError, TypeError):
                    pass
            
            # Current Liabilities
            if "CurrentLiabilities" in tag:
                try:
                    fundamentals["current_liabilities"] = float(text) if text else None
                except (ValueError, TypeError):
                    pass
            
            # Operating Cash Flow
            if "NetCashProvidedByUsedInOperatingActivities" in tag or "CashFlowFromOperatingActivities" in tag:
                try:
                    fundamentals["operating_cash_flow"] = float(text) if text else None
                except (ValueError, TypeError):
                    pass
        
        # Calculate derived metrics
        if fundamentals["total_assets"] and fundamentals["total_liabilities"]:
            try:
                equity = fundamentals["total_assets"] - fundamentals["total_liabilities"]
                if equity != 0:
                    fundamentals["debt_to_equity"] = fundamentals["total_liabilities"] / equity
            except (TypeError, ZeroDivisionError):
                pass
        
        if fundamentals["current_assets"] and fundamentals["current_liabilities"]:
            try:
                fundamentals["current_ratio"] = fundamentals["current_assets"] / fundamentals["current_liabilities"]
            except (TypeError, ZeroDivisionError):
                pass
        
        logger.info(f"Successfully parsed XBRL data for {ticker}")
        
    except ET.ParseError as e:
        logger.error(f"XML parse error for {ticker}: {e}")
    except Exception as e:
        logger.error(f"Error parsing XBRL data for {ticker}: {e}")
    
    return fundamentals


@task
def save_xbrl_data_to_parquet(xbrl_list: list[dict], output_dir: str = "db") -> str:
    """
    Save XBRL data to Parquet file.
    
    Args:
        xbrl_list: List of XBRL data dictionaries
        output_dir: Output directory
        
    Returns:
        Path to saved Parquet file
    """
    logger = get_run_logger()
    logger.info(f"Saving {len(xbrl_list)} XBRL records to Parquet")
    
    try:
        os.makedirs(output_dir, exist_ok=True)
        
        df = pd.DataFrame(xbrl_list)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = os.path.join(output_dir, f"xbrl_data_{timestamp}.parquet")
        
        df.to_parquet(file_path, compression="snappy", index=False)
        logger.info(f"Saved XBRL data to {file_path}")
        
        return file_path
        
    except Exception as e:
        logger.error(f"Error saving XBRL data to Parquet: {e}")
        raise


@flow
def fetch_xbrl_filings(tickers: list[str], filing_type: str = "10-K") -> str:
    """
    Main Prefect flow to fetch XBRL data for multiple companies.
    
    Args:
        tickers: List of stock tickers
        filing_type: Type of filing (10-K or 10-Q)
        
    Returns:
        Path to saved Parquet file
    """
    logger = get_run_logger()
    logger.info(f"Starting XBRL fetch flow for tickers: {tickers}")
    
    xbrl_data = []
    
    for ticker in tickers:
        logger.info(f"Processing {ticker}")
        
        # Fetch CIK
        cik = fetch_company_cik(ticker)
        if not cik:
            logger.warning(f"Could not find CIK for {ticker}")
            continue
        
        # Fetch filing index
        filing_info = fetch_sec_filing_index(cik, filing_type)
        if not filing_info:
            logger.warning(f"Could not find {filing_type} filing for {ticker}")
            continue
        
        # Fetch XBRL document
        xbrl_doc = fetch_xbrl_document(cik, filing_info["accession_number"])
        if not xbrl_doc:
            logger.warning(f"Could not fetch XBRL document for {ticker}")
            continue
        
        # Parse XBRL data
        fundamentals = parse_xbrl_fundamentals(xbrl_doc, ticker)
        xbrl_data.append(fundamentals)
        
        # Rate limiting: wait 2 seconds between requests
        time.sleep(2)
    
    # Save to Parquet
    if xbrl_data:
        file_path = save_xbrl_data_to_parquet(xbrl_data)
        logger.info(f"XBRL flow completed. Data saved to {file_path}")
        return file_path
    else:
        logger.warning("No XBRL data collected")
        return ""


if __name__ == "__main__":
    # Test with AAPL and MSFT
    result = fetch_xbrl_filings(["AAPL", "MSFT"])
    print(f"Results saved to: {result}")
