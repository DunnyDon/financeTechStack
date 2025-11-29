import os
import time
from datetime import datetime
from typing import Optional

import requests
from bs4 import BeautifulSoup
from prefect import flow, task, get_run_logger
from prefect.utilities.asyncutils import sync_compatible
import pandas as pd

try:
    from .config import config
except ImportError:
    from config import config


# SEC EDGAR API endpoints
SEC_BASE_URL = "https://data.sec.gov/submissions"
SEC_COMPANY_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SEC_FILINGS_URL = "https://www.sec.gov/cgi-bin/browse-edgar"

# Alpha Vantage API endpoint
ALPHA_VANTAGE_BASE_URL = "https://www.alphavantage.co/query"


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
        
        # Fetch the official SEC company tickers JSON
        response = requests.get(SEC_COMPANY_TICKERS_URL, headers=headers, timeout=10)
        response.raise_for_status()
        
        tickers_data = response.json()
        
        # Search for the ticker in the data
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
def fetch_sec_filings(cik: str, filing_type: str = "10-K", limit: int = 10) -> list[dict]:
    """
    Fetch SEC filings for a given CIK.
    
    Args:
        cik: Company's CIK number
        filing_type: Type of filing (e.g., '10-K', '10-Q', '8-K')
        limit: Maximum number of filings to retrieve
        
    Returns:
        List of filing details including accession number, date, and link
    """
    logger = get_run_logger()
    logger.info(f"Fetching {filing_type} filings for CIK: {cik}")
    
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
        
        filings = []
        if "filings" in data and "recent" in data["filings"]:
            recent = data["filings"]["recent"]
            
            for i, form_type in enumerate(recent.get("form", [])):
                if form_type == filing_type and len(filings) < limit:
                    accession_number = recent["accessionNumber"][i]
                    filing_date = recent["filingDate"][i]
                    report_date = recent["reportDate"][i]
                    
                    filing_info = {
                        "accession_number": accession_number,
                        "filing_date": filing_date,
                        "report_date": report_date,
                        "form_type": form_type,
                        "cik": cik
                    }
                    filings.append(filing_info)
        
        logger.info(f"Found {len(filings)} {filing_type} filings for CIK: {cik}")
        return filings
        
    except Exception as e:
        logger.error(f"Error fetching filings for CIK {cik}: {e}")
        raise


@task
def download_filing_document(accession_number: str, cik: str, filing_type: str = "10-K") -> Optional[str]:
    """
    Download the full text filing document.
    
    Args:
        accession_number: SEC accession number
        cik: Company's CIK number
        filing_type: Type of filing
        
    Returns:
        File path to the downloaded document or None if failed
    """
    logger = get_run_logger()
    logger.info(f"Downloading filing: {accession_number}")
    
    try:
        # Construct the filing URL
        accession_no_dash = accession_number.replace("-", "")
        url = f"https://www.sec.gov/Archives/edgar/{cik}/{accession_no_dash}/{accession_number}-index.htm"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # Save the filing
        os.makedirs("filings", exist_ok=True)
        filename = f"filings/{cik}_{accession_number}.html"
        
        with open(filename, "w", encoding="utf-8") as f:
            f.write(response.text)
        
        logger.info(f"Saved filing to: {filename}")
        return filename
        
    except Exception as e:
        logger.error(f"Error downloading filing {accession_number}: {e}")
        return None


@task
def parse_filing_content(file_path: str) -> dict:
    """
    Parse the filing HTML content to extract key information.
    
    Args:
        file_path: Path to the saved filing document
        
    Returns:
        Dictionary with extracted filing data
    """
    logger = get_run_logger()
    logger.info(f"Parsing filing content from: {file_path}")
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f.read(), "html.parser")
        
        # Extract key sections (this is a basic example)
        extracted_data = {
            "file_path": file_path,
            "parsed_at": datetime.now().isoformat(),
            "title": soup.title.string if soup.title else "N/A"
        }
        
        logger.info(f"Extracted data from filing")
        return extracted_data
        
    except Exception as e:
        logger.error(f"Error parsing filing {file_path}: {e}")
        raise


@task
def save_filings_to_parquet(filings_data: list[dict], output_dir: str = "db") -> str:
    """
    Save filings metadata to a Parquet file.
    
    Args:
        filings_data: List of filing dictionaries
        output_dir: Output directory for Parquet files
        
    Returns:
        Path to the saved Parquet file
    """
    logger = get_run_logger()
    logger.info(f"Saving filings data to Parquet in directory: {output_dir}")
    
    try:
        os.makedirs(output_dir, exist_ok=True)
        
        df = pd.DataFrame(filings_data)
        
        # Create filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"{output_dir}/sec_filings_{timestamp}.parquet"
        
        # Save to Parquet format
        df.to_parquet(output_file, engine="pyarrow", compression="snappy", index=False)
        logger.info(f"Saved {len(df)} filings to {output_file}")
        return output_file
        
    except Exception as e:
        logger.error(f"Error saving to Parquet: {e}")
        raise


@flow(name="SEC Filings Scraper")
def scrape_sec_filings(tickers: list[str], filing_type: str = "10-K", limit: int = 5):
    """
    Main Prefect flow to scrape SEC filings for multiple companies.
    
    Args:
        tickers: List of stock ticker symbols
        filing_type: Type of SEC filing to retrieve
        limit: Maximum number of filings per company
    """
    logger = get_run_logger()
    logger.info(f"Starting SEC filings scraper for tickers: {tickers}")
    
    all_filings = []
    
    for ticker in tickers:
        logger.info(f"Processing ticker: {ticker}")
        
        # Get CIK
        cik = fetch_company_cik(ticker)
        if not cik:
            logger.warning(f"Skipping {ticker} - CIK not found")
            continue
        
        # Fetch filings
        filings = fetch_sec_filings(cik, filing_type, limit)
        
        for filing in filings:
            all_filings.append(filing)
            
            # Add delay to respect SEC rate limits
            time.sleep(1)
            
            # Optionally download and parse documents
            # doc_path = download_filing_document(
            #     filing["accession_number"], 
            #     cik, 
            #     filing_type
            # )
            # if doc_path:
            #     parse_filing_content(doc_path)
    
    # Save results
    if all_filings:
        output_file = save_filings_to_parquet(all_filings)
        logger.info(f"Scraping complete! Results saved to {output_file}")
    else:
        logger.warning("No filings found")
    
    return all_filings


def main():
    """Run the SEC filings scraper."""
    # Example: Scrape 10-K filings for Apple and Microsoft
    tickers = ["AAPL", "MSFT"]
    filings = scrape_sec_filings(tickers, filing_type="10-K", limit=5)
    print(f"\nScraped {len(filings)} filings successfully!")


if __name__ == "__main__":
    main()
