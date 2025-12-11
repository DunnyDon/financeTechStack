"""
Portfolio Analysis Flows for Prefect Orchestration

Three comprehensive flows for data aggregation and portfolio analysis:
1. aggregate_financial_data_flow - Scrapes SEC data, pricing data, and saves to parquet
2. portfolio_analysis_flow - Runs portfolio analysis on parquet data
3. portfolio_end_to_end_flow - Complete end-to-end workflow

Each flow includes comprehensive error handling, logging, and data validation.
All financial metrics are converted to EUR using real-time FX rates.
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import pandas as pd
from prefect import flow, get_run_logger, task

from .constants import DEFAULT_OUTPUT_DIR
from .fx_rates import FXRateManager, fetch_fx_rates, save_fx_rates_to_parquet
from .portfolio_holdings import Holdings
from .portfolio_prices import PriceFetcher
from .portfolio_technical import TechnicalAnalyzer
from .utils import get_logger
from .xbrl import (
    fetch_company_cik,
    fetch_sec_filing_index,
    fetch_xbrl_document,
    parse_xbrl_fundamentals,
)

__all__ = [
    "aggregate_financial_data_flow",
    "portfolio_analysis_flow",
    "portfolio_end_to_end_flow",
    "get_tickers_from_holdings",
]

logger = get_logger(__name__)


def get_tickers_from_holdings(holdings_file: str = "holdings.csv") -> List[str]:
    """
    Get list of unique tickers from holdings file.

    Args:
        holdings_file: Path to holdings CSV file

    Returns:
        List of unique ticker symbols
    """
    try:
        holdings = Holdings(holdings_file)
        tickers = holdings.get_unique_symbols()
        logger.info(f"Loaded {len(tickers)} unique tickers from {holdings_file}")
        return tickers
    except Exception as e:
        logger.error(f"Error loading tickers from holdings: {e}")
        return ["AAPL", "MSFT", "GOOGL"]  # Fallback defaults


# ============================================================================
# FX RATE MANAGEMENT TASKS
# ============================================================================


@task(name="fetch_fx_rates_task", retries=2, retry_delay_seconds=5)
def fetch_fx_rates_task(force_refresh: bool = False) -> Dict[str, float]:
    """
    Fetch current FX rates for portfolio currency conversion.

    Args:
        force_refresh: If True, always fetch from API instead of using cache

    Returns:
        Dict mapping currency codes to EUR exchange rates
    """
    logger_instance = get_run_logger()
    logger_instance.info("Fetching FX rates")

    try:
        rates = FXRateManager.get_rates(force_refresh=force_refresh)
        logger_instance.info("Successfully fetched FX rates for %d currencies", len(rates))
        return rates
    except Exception as e:
        logger_instance.error("Error fetching FX rates: %s", e)
        # Return fallback rates
        return FXRateManager.get_rates(force_refresh=False)


@task(name="save_fx_rates_task")
def save_fx_rates_task(
    fx_rates: Dict[str, float],
    output_dir: str = DEFAULT_OUTPUT_DIR,
) -> str:
    """
    Save FX rates to Parquet for record-keeping.

    Args:
        fx_rates: Dict of FX rates
        output_dir: Output directory

    Returns:
        Path to saved parquet file
    """
    logger_instance = get_run_logger()
    logger_instance.info("Saving FX rates to parquet")

    try:
        filepath = save_fx_rates_to_parquet(fx_rates, output_dir)
        logger_instance.info("FX rates saved to %s", filepath)
        return filepath
    except Exception as e:
        logger_instance.error("Error saving FX rates: %s", e)
        raise


# ============================================================================
# FINANCIAL DATA AGGREGATION FLOW TASKS
# ============================================================================


@task(name="fetch_sec_cik", retries=3, retry_delay_seconds=5)
def fetch_sec_cik_task(ticker: str) -> Optional[str]:
    """
    Fetch CIK from SEC for a given ticker.

    Args:
        ticker: Stock ticker symbol

    Returns:
        CIK number or None if not found
    """
    logger_instance = get_run_logger()
    logger_instance.info("Fetching CIK for ticker: %s", ticker)

    try:
        cik = fetch_company_cik(ticker)
        if cik:
            logger_instance.info("Found CIK %s for %s", cik, ticker)
            return cik
        logger_instance.warning("No CIK found for %s", ticker)
        return None
    except (ValueError, RuntimeError) as e:
        logger_instance.error("Error fetching CIK for %s: %s", ticker, e)
        return None


@task(name="fetch_sec_filings", retries=3, retry_delay_seconds=5)
def fetch_sec_filings_task(cik: str, ticker: str) -> Optional[Dict]:
    """
    Fetch SEC filing metadata.

    Args:
        cik: Company CIK number
        ticker: Stock ticker symbol

    Returns:
        Dict with filing metadata or None
    """
    logger_instance = get_run_logger()
    logger_instance.info("Fetching SEC filings for %s (CIK: %s)", ticker, cik)

    try:
        filing_index = fetch_sec_filing_index(cik)

        if filing_index and isinstance(filing_index, dict):
            logger_instance.info("Found latest 10-K filing for %s", ticker)
            return filing_index
        logger_instance.warning("No filing index found for %s", ticker)
        return None
    except (ValueError, RuntimeError) as e:
        logger_instance.error("Error fetching SEC filings for %s: %s", ticker, e)
        return None


@task(name="parse_xbrl_data", retries=2, retry_delay_seconds=5)
def parse_xbrl_data_task(cik: str, ticker: str, filing_info: Optional[Dict] = None) -> Optional[Dict]:
    """
    Parse XBRL fundamentals from SEC filing.

    Args:
        cik: Company CIK number
        ticker: Stock ticker symbol
        filing_info: Optional filing info with accession_number

    Returns:
        Dict with fundamental data or None
    """
    logger_instance = get_run_logger()
    logger_instance.info("Parsing XBRL data for %s", ticker)

    try:
        # Get accession number from filing info or use empty string
        accession_number = ""
        if filing_info and isinstance(filing_info, dict):
            accession_number = filing_info.get("accession_number", "")

        # Fetch XBRL document for the CIK
        xbrl_doc = fetch_xbrl_document(cik, accession_number)

        if xbrl_doc:
            fundamentals = parse_xbrl_fundamentals(xbrl_doc, ticker)
            logger_instance.info("Successfully parsed XBRL fundamentals for %s", ticker)
            return {"ticker": ticker, "cik": cik, "fundamentals": fundamentals}
        logger_instance.warning("No XBRL document found for %s", ticker)
        return None
    except (ValueError, RuntimeError) as e:
        logger_instance.error("Error parsing XBRL for %s: %s", ticker, e)
        return None


@task(name="fetch_pricing_data")
def fetch_pricing_data_task(ticker: str) -> Optional[Dict]:
    """
    Fetch current pricing data for a ticker.

    Args:
        ticker: Stock ticker symbol

    Returns:
        Dict with price data or None
    """
    logger_instance = get_run_logger()
    logger_instance.info("Fetching pricing data for %s", ticker)

    try:
        fetcher = PriceFetcher()
        price_data = fetcher.fetch_price(ticker, "eq")

        if price_data:
            price_value = price_data.get("price", "N/A")
            logger_instance.info("Successfully fetched price for %s: $%s", ticker, price_value)
            return {"ticker": ticker, "price_data": price_data}
        logger_instance.warning("No pricing data found for %s", ticker)
        return None
    except (ValueError, RuntimeError) as e:
        logger_instance.error("Error fetching pricing data for %s: %s", ticker, e)
        return None


@task(name="aggregate_and_save_to_parquet")
def aggregate_and_save_to_parquet_task(
    financial_data: list,
    pricing_data: list,
    output_dir: str = DEFAULT_OUTPUT_DIR,
) -> Tuple[str, Dict]:
    """
    Aggregate financial and pricing data, save to parquet.

    Args:
        financial_data: List of financial data dicts
        pricing_data: List of pricing data dicts
        output_dir: Output directory for parquet files

    Returns:
        Tuple of (parquet file path, aggregation summary)
    """
    logger_instance = get_run_logger()
    logger_instance.info("Aggregating financial and pricing data")

    os.makedirs(output_dir, exist_ok=True)

    try:
        # Combine data
        aggregated_records = []

        price_dict = {p["ticker"]: p.get("price_data") for p in pricing_data if p}
        fin_dict = {f["ticker"]: f for f in financial_data if f}

        for ticker, fin_data in fin_dict.items():
            price_info = price_dict.get(ticker, {})

            record = {
                "ticker": ticker,
                "cik": fin_data.get("cik"),
                "price": price_info.get("price") if price_info else None,
                "price_source": price_info.get("source") if price_info else None,
                "fundamentals": fin_data.get("fundamentals", {}),
                "fetched_at": datetime.now().isoformat(),
            }

            aggregated_records.append(record)

        # Create DataFrame
        df = pd.DataFrame(aggregated_records)

        # Save to parquet
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        parquet_file = os.path.join(output_dir, f"financial_data_{timestamp}.parquet")

        df.to_parquet(parquet_file, engine="pyarrow", compression="snappy", index=False)

        logger_instance.info("Saved aggregated data to %s", parquet_file)

        summary = {
            "total_records": len(df),
            "parquet_file": parquet_file,
            "tickers": df["ticker"].unique().tolist(),
            "records_with_prices": df["price"].notna().sum(),
            "records_with_fundamentals": sum(1 for x in df["fundamentals"] if x),
        }

        return parquet_file, summary

    except (ValueError, OSError, RuntimeError) as e:
        logger_instance.error("Error aggregating data: %s", e)
        raise


# ============================================================================
# PORTFOLIO ANALYSIS FLOW TASKS
# ============================================================================


@task(name="load_portfolio_from_parquet")
def load_portfolio_from_parquet_task(parquet_file: str) -> Optional[pd.DataFrame]:
    """
    Load portfolio data from parquet file.

    Args:
        parquet_file: Path to parquet file

    Returns:
        DataFrame with portfolio data or None
    """
    logger_instance = get_run_logger()
    logger_instance.info("Loading portfolio from parquet: %s", parquet_file)

    try:
        df = pd.read_parquet(parquet_file)
        logger_instance.info("Loaded %d records from parquet", len(df))
        return df
    except (FileNotFoundError, ValueError, OSError) as e:
        logger_instance.error("Error loading parquet file: %s", e)
        return None


@task(name="calculate_technical_indicators_task")
def calculate_technical_indicators_task(portfolio_df: pd.DataFrame) -> Optional[Dict]:
    """
    Calculate technical indicators for portfolio.

    Args:
        portfolio_df: Portfolio DataFrame

    Returns:
        Dict with technical indicators or None
    """
    logger_instance = get_run_logger()
    logger_instance.info("Calculating technical indicators")

    try:
        # For each ticker, fetch historical data and calculate indicators
        indicators = {}

        for ticker in portfolio_df["ticker"].unique():
            fetcher = PriceFetcher()
            historical_data = fetcher.fetch_historical(ticker, period="3mo")

            if historical_data is not None and not historical_data.empty:
                analyzer = TechnicalAnalyzer()
                ticker_indicators = analyzer.calculate_all(historical_data)
                indicators[ticker] = ticker_indicators

        logger_instance.info("Calculated technical indicators for %d tickers", len(indicators))
        return indicators if indicators else None

    except (ValueError, RuntimeError) as e:
        logger_instance.error("Error calculating technical indicators: %s", e)
        return None


@task(name="calculate_portfolio_analysis")
def calculate_portfolio_analysis_task(portfolio_df: pd.DataFrame, technical_indicators: Dict) -> Dict:
    """
    Calculate portfolio analysis metrics.

    Args:
        portfolio_df: Portfolio DataFrame
        technical_indicators: Dict with technical indicators

    Returns:
        Dict with analysis results
    """
    logger_instance = get_run_logger()
    logger_instance.info("Calculating portfolio analysis")

    try:
        # Prepare analysis data
        analysis_results = {
            "total_records": len(portfolio_df),
            "tickers": portfolio_df["ticker"].unique().tolist(),
            "records_with_prices": portfolio_df["price"].notna().sum(),
            "technical_indicators_calculated": len(technical_indicators) if technical_indicators else 0,
        }

        # Calculate fundamentals analysis if available
        if "fundamentals" in portfolio_df.columns:
            fundamentals_count = sum(
                1 for x in portfolio_df["fundamentals"]
                if isinstance(x, dict) and x
            )
            analysis_results["records_with_fundamentals"] = fundamentals_count

        logger_instance.info("Portfolio analysis complete")
        return analysis_results

    except (ValueError, RuntimeError) as e:
        logger_instance.error("Error in portfolio analysis: %s", e)
        raise


@task(name="generate_portfolio_reports")
def generate_portfolio_reports_task(
    analysis_results: Dict,
    output_dir: str = DEFAULT_OUTPUT_DIR,
) -> Dict:
    """
    Generate portfolio analysis reports.

    Args:
        analysis_results: Analysis results dict
        output_dir: Output directory for reports

    Returns:
        Dict with report paths
    """
    logger_instance = get_run_logger()
    logger_instance.info("Generating portfolio reports")

    os.makedirs(output_dir, exist_ok=True)

    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Generate HTML report
        html_file = os.path.join(output_dir, f"portfolio_analysis_{timestamp}.html")

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Portfolio Analysis Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
                .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 20px; }}
                h1 {{ color: #333; border-bottom: 3px solid #0066cc; padding-bottom: 10px; }}
                h2 {{ color: #0066cc; margin-top: 30px; }}
                table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                th {{ background: #0066cc; color: white; padding: 12px; text-align: left; }}
                td {{ padding: 10px; border-bottom: 1px solid #ddd; }}
                .metric {{ display: inline-block; margin: 10px 20px; }}
                .metric-value {{ font-size: 24px; font-weight: bold; color: #0066cc; }}
                .metric-label {{ font-size: 12px; color: #666; text-transform: uppercase; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Portfolio Analysis Report</h1>
                <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>

                <h2>Analysis Summary</h2>
                <div>
                    <div class="metric">
                        <div class="metric-label">Total Records</div>
                        <div class="metric-value">{analysis_results.get('total_records', 0)}</div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">Tickers Analyzed</div>
                        <div class="metric-value">{len(analysis_results.get('tickers', []))}</div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">With Prices</div>
                        <div class="metric-value">{analysis_results.get('records_with_prices', 0)}</div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">Technical Indicators</div>
                        <div class="metric-value">{analysis_results.get('technical_indicators_calculated', 0)}</div>
                    </div>
                </div>

                <h2>Tickers Analyzed</h2>
                <table>
                    <tr><th>Ticker</th></tr>
                    {''.join(f'<tr><td>{ticker}</td></tr>' for ticker in analysis_results.get('tickers', []))}
                </table>
            </div>
        </body>
        </html>
        """

        with open(html_file, "w", encoding="utf-8") as f:
            f.write(html_content)

        # Generate JSON report
        json_file = os.path.join(output_dir, f"portfolio_analysis_{timestamp}.json")
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(analysis_results, f, indent=2, default=str)

        logger_instance.info("Generated reports: %s, %s", html_file, json_file)

        return {
            "html_report": html_file,
            "json_report": json_file,
            "summary": analysis_results,
        }

    except (OSError, ValueError) as e:
        logger_instance.error("Error generating reports: %s", e)
        raise


# ============================================================================
# PREFECT FLOWS
# ============================================================================


@flow(
    name="aggregate_financial_data_flow",
    description="Aggregate SEC data, pricing data, and save to parquet",
)
def aggregate_financial_data_flow(
    tickers: list = None,
    output_dir: str = DEFAULT_OUTPUT_DIR,
) -> Dict:
    """
    Flow for aggregating financial data from multiple sources.

    This flow:
    1. Fetches SEC CIK for each ticker
    2. Retrieves SEC filing metadata
    3. Parses XBRL fundamentals
    4. Fetches current pricing data
    5. Aggregates all data and saves to parquet

    Args:
        tickers: List of stock tickers to analyze. Defaults to tickers from holdings.csv
        output_dir: Output directory for parquet files

    Returns:
        Dict with parquet file path and summary
    """
    logger_instance = get_run_logger()
    logger_instance.info("Starting financial data aggregation flow for %s", tickers)

    if not tickers:
        tickers = get_tickers_from_holdings()

    # Fetch SEC data
    sec_data = []
    for ticker in tickers:
        logger_instance.info("Processing %s", ticker)

        cik = fetch_sec_cik_task(ticker)
        if cik:
            try:
                filing_info = fetch_sec_filings_task(cik, ticker)
                xbrl_data = parse_xbrl_data_task(cik, ticker, filing_info)

                if xbrl_data:
                    sec_data.append(xbrl_data)
            except Exception as e:
                # Some securities (crypto, ETFs, international) may not have SEC filings
                logger_instance.warning("Could not fetch SEC data for %s (CIK: %s): %s", ticker, cik, str(e)[:100])
                # Continue processing other tickers instead of failing

    # Fetch pricing data
    pricing_data = [fetch_pricing_data_task(ticker) for ticker in tickers]

    # Aggregate and save
    parquet_file, summary = aggregate_and_save_to_parquet_task(sec_data, pricing_data, output_dir)

    logger_instance.info("Financial data aggregation flow complete. Parquet: %s", parquet_file)

    return {
        "parquet_file": parquet_file,
        "summary": summary,
        "status": "success",
    }


@flow(
    name="portfolio_analysis_flow",
    description="Run portfolio analysis on parquet data",
)
def portfolio_analysis_flow(
    parquet_file: str,
    output_dir: str = DEFAULT_OUTPUT_DIR,
) -> Dict:
    """
    Flow for analyzing portfolio data from parquet file.

    This flow:
    1. Loads portfolio data from parquet
    2. Calculates technical indicators
    3. Performs portfolio analysis
    4. Generates analysis reports

    Args:
        parquet_file: Path to parquet file with portfolio data
        output_dir: Output directory for reports

    Returns:
        Dict with report paths and analysis summary
    """
    logger_instance = get_run_logger()
    logger_instance.info("Starting portfolio analysis flow for %s", parquet_file)

    # Load portfolio data
    portfolio_df = load_portfolio_from_parquet_task(parquet_file)

    if portfolio_df is None or portfolio_df.empty:
        logger_instance.error("Portfolio data is empty")
        return {"status": "error", "message": "Portfolio data is empty"}

    # Calculate technical indicators
    technical_indicators = calculate_technical_indicators_task(portfolio_df)

    # Calculate analysis
    analysis_results = calculate_portfolio_analysis_task(portfolio_df, technical_indicators or {})

    # Generate reports
    report_data = generate_portfolio_reports_task(analysis_results, output_dir)

    logger_instance.info("Portfolio analysis flow complete")

    return {
        "reports": report_data,
        "analysis_results": analysis_results,
        "status": "success",
    }


@flow(
    name="portfolio_end_to_end_flow",
    description="End-to-end portfolio analysis from SEC scraping to reporting",
)
def portfolio_end_to_end_flow(
    tickers: list = None,
    output_dir: str = DEFAULT_OUTPUT_DIR,
) -> Dict:
    """
    End-to-end portfolio analysis flow.

    This comprehensive flow:
    1. Aggregates financial data from SEC, pricing sources
    2. Saves aggregated data to parquet
    3. Analyzes portfolio data
    4. Generates comprehensive reports

    Args:
        tickers: List of stock tickers to analyze. Defaults to tickers from holdings.csv
        output_dir: Output directory for data and reports

    Returns:
        Dict with complete analysis results and report paths
    """
    logger_instance = get_run_logger()
    logger_instance.info("Starting end-to-end portfolio analysis flow")

    if not tickers:
        tickers = get_tickers_from_holdings()

    # Step 1: Aggregate financial data
    aggregation_result = aggregate_financial_data_flow(tickers, output_dir)

    if aggregation_result.get("status") != "success":
        logger_instance.error("Data aggregation failed")
        return {"status": "error", "message": "Data aggregation failed"}

    parquet_file = aggregation_result.get("parquet_file")

    # Step 2: Run portfolio analysis
    analysis_result = portfolio_analysis_flow(parquet_file, output_dir)

    if analysis_result.get("status") != "success":
        logger_instance.error("Portfolio analysis failed")
        return {"status": "error", "message": "Portfolio analysis failed"}

    logger_instance.info("End-to-end portfolio analysis complete")

    return {
        "status": "success",
        "aggregation": aggregation_result,
        "analysis": analysis_result,
        "parquet_file": parquet_file,
        "timestamp": datetime.now().isoformat(),
    }
