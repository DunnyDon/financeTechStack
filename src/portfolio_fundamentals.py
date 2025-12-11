"""
Fundamental analysis for portfolio securities.

Integrates with existing SEC/XBRL data to provide fundamental analysis
of portfolio holdings including financial ratios and metrics.
"""

from typing import Dict, List, Optional

import pandas as pd
from prefect import get_run_logger, task

from .utils import get_logger
from .xbrl import (
    fetch_company_cik,
    fetch_xbrl_document,
    parse_xbrl_fundamentals,
)

__all__ = [
    "get_fundamental_data",
    "calculate_financial_ratios",
    "analyze_portfolio_fundamentals",
]

logger = get_logger(__name__)


class FundamentalAnalyzer:
    """Analyze fundamental data for portfolio holdings."""

    def __init__(self, holdings_df: pd.DataFrame):
        """
        Initialize fundamental analyzer.

        Args:
            holdings_df: DataFrame with holdings
        """
        self.holdings_df = holdings_df
        self.fundamental_cache: Dict[str, Dict] = {}

    def get_ticker_fundamentals(self, ticker: str, company_name: str = "") -> Optional[Dict]:
        """
        Get fundamental data for a ticker.

        Args:
            ticker: Stock ticker symbol
            company_name: Company name (for CIK lookup)

        Returns:
            Dict with fundamental data or None
        """
        if ticker in self.fundamental_cache:
            return self.fundamental_cache[ticker]

        try:
            # Get CIK
            company_data = fetch_company_cik(ticker)
            if not company_data:
                logger.warning(f"Could not find CIK for {ticker}")
                return None

            cik = company_data.get("cik") if isinstance(company_data, dict) else company_data
            if not cik:
                return None

            # Fetch XBRL data using the CIK
            # Note: fetch_xbrl_document takes (cik, accession_number) but accession_number is not used
            xbrl_data = fetch_xbrl_document(cik, cik)
            
            if not xbrl_data:
                logger.warning(f"No XBRL data found for {ticker}")
                return None

            # Parse the XBRL data
            xbrl_parsed = parse_xbrl_fundamentals(xbrl_data, ticker)

            if xbrl_parsed:
                self.fundamental_cache[ticker] = xbrl_parsed
                return xbrl_parsed

            return None

        except Exception as e:
            logger.error(f"Error fetching fundamentals for {ticker}: {e}")
            return None

    @staticmethod
    def calculate_ratios(fundamentals: Dict) -> Dict[str, float]:
        """
        Calculate financial ratios from fundamental data.

        Args:
            fundamentals: Dict with fundamental data

        Returns:
            Dict with calculated ratios
        """
        ratios = {}

        # Revenue metrics
        if "revenue" in fundamentals and fundamentals["revenue"]:
            ratios["revenue"] = float(fundamentals["revenue"])

        # Profitability ratios
        if all(
            k in fundamentals and fundamentals[k]
            for k in ["net_income", "revenue"]
        ):
            try:
                ratios["net_margin"] = (
                    float(fundamentals["net_income"]) / float(fundamentals["revenue"])
                ) * 100
            except (ValueError, ZeroDivisionError):
                pass

        # Leverage ratios
        if all(
            k in fundamentals and fundamentals[k]
            for k in ["total_debt", "equity"]
        ):
            try:
                ratios["debt_to_equity"] = float(fundamentals["total_debt"]) / float(
                    fundamentals["equity"]
                )
            except (ValueError, ZeroDivisionError):
                pass

        # Liquidity ratios
        if all(
            k in fundamentals and fundamentals[k]
            for k in ["current_assets", "current_liabilities"]
        ):
            try:
                ratios["current_ratio"] = float(fundamentals["current_assets"]) / float(
                    fundamentals["current_liabilities"]
                )
            except (ValueError, ZeroDivisionError):
                pass

        # ROE (Return on Equity)
        if all(
            k in fundamentals and fundamentals[k]
            for k in ["net_income", "equity"]
        ):
            try:
                ratios["roe"] = (
                    float(fundamentals["net_income"]) / float(fundamentals["equity"])
                ) * 100
            except (ValueError, ZeroDivisionError):
                pass

        # ROA (Return on Assets)
        if all(
            k in fundamentals and fundamentals[k]
            for k in ["net_income", "total_assets"]
        ):
            try:
                ratios["roa"] = (
                    float(fundamentals["net_income"]) / float(fundamentals["total_assets"])
                ) * 100
            except (ValueError, ZeroDivisionError):
                pass

        return ratios

    def analyze_portfolio_fundamentals(self) -> pd.DataFrame:
        """
        Get fundamental analysis for all equities in portfolio.

        Returns:
            DataFrame with fundamental data for equities
        """
        # Filter to equities only
        equities = self.holdings_df[self.holdings_df["asset"] == "eq"].copy()

        if equities.empty:
            return pd.DataFrame()

        fundamental_data = []

        for _, holding in equities.iterrows():
            ticker = holding["sym"]
            company_name = holding.get("secname", "")

            # Get fundamentals
            fundamentals = self.get_ticker_fundamentals(ticker, company_name)

            if fundamentals:
                # Calculate ratios
                ratios = self.calculate_ratios(fundamentals)

                # Combine data
                record = {
                    "symbol": ticker,
                    "company": company_name,
                    "qty": holding["qty"],
                }

                record.update(fundamentals)
                record.update(ratios)

                fundamental_data.append(record)

        if not fundamental_data:
            return pd.DataFrame()

        return pd.DataFrame(fundamental_data)


@task
def get_fundamental_data(ticker: str, company_name: str = "") -> Optional[Dict]:
    """
    Get fundamental data for a security.

    Args:
        ticker: Stock ticker symbol
        company_name: Company name (for CIK lookup)

    Returns:
        Dict with fundamental data or None
    """
    logger_instance = get_run_logger()
    logger_instance.info(f"Fetching fundamental data for {ticker}")

    analyzer = FundamentalAnalyzer(pd.DataFrame())
    return analyzer.get_ticker_fundamentals(ticker, company_name)


@task
def calculate_financial_ratios(fundamentals: Dict) -> Dict[str, float]:
    """
    Calculate financial ratios.

    Args:
        fundamentals: Dict with fundamental data

    Returns:
        Dict with calculated ratios
    """
    logger_instance = get_run_logger()
    logger_instance.info("Calculating financial ratios")

    return FundamentalAnalyzer.calculate_ratios(fundamentals)


@task
def analyze_portfolio_fundamentals(holdings_df: pd.DataFrame) -> pd.DataFrame:
    """
    Analyze fundamentals for portfolio holdings.

    Args:
        holdings_df: DataFrame with holdings

    Returns:
        DataFrame with fundamental analysis
    """
    logger_instance = get_run_logger()
    logger_instance.info("Analyzing portfolio fundamentals")

    analyzer = FundamentalAnalyzer(holdings_df)
    fundamentals_df = analyzer.analyze_portfolio_fundamentals()

    logger_instance.info(f"Retrieved fundamentals for {len(fundamentals_df)} equities")

    return fundamentals_df
