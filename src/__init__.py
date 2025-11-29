"""
TechStack - Financial data aggregation and analysis system.

A production-ready Python application that scrapes SEC filings from EDGAR,
fetches fundamental data from Alpha Vantage, and analyzes financial information
using Prefect workflow orchestration.
"""

__version__ = "0.1.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"
__license__ = "MIT"

from .alpha_vantage import fetch_fundamental_data, fetch_fundamentals
from .config import config
from .data_merge import (
    compare_tickers,
    enrich_with_calculated_metrics,
    get_ticker_analysis,
    merge_fundamental_data,
    read_alpha_vantage_data,
    read_xbrl_data,
    save_merged_data_to_parquet,
)
from .exceptions import (
    APIKeyError,
    CIKNotFoundError,
    ConfigurationError,
    DataParseError,
    FilingNotFoundError,
    ValidationError,
)
from .main import (
    aggregate_financial_data,
    fetch_alpha_vantage_data,
    fetch_company_cik,
    fetch_filing_metadata,
    fetch_xbrl_data,
    merge_financial_data,
    save_aggregated_data,
)
from .xbrl import (
    fetch_sec_filing_index,
    fetch_xbrl_document,
    fetch_xbrl_filings,
    parse_xbrl_fundamentals,
    save_xbrl_data_to_parquet,
)

__all__ = [
    # Version
    "__version__",
    "__author__",
    "__email__",
    "__license__",
    # Config
    "config",
    # Main financial data aggregation
    "aggregate_financial_data",
    "fetch_company_cik",
    "fetch_filing_metadata",
    "fetch_xbrl_data",
    "fetch_alpha_vantage_data",
    "merge_financial_data",
    "save_aggregated_data",
    # Alpha Vantage functions
    "fetch_fundamental_data",
    "fetch_fundamentals",
    # XBRL functions
    "fetch_sec_filing_index",
    "fetch_xbrl_document",
    "parse_xbrl_fundamentals",
    "save_xbrl_data_to_parquet",
    "fetch_xbrl_filings",
    # Data merge functions
    "read_alpha_vantage_data",
    "read_xbrl_data",
    "merge_fundamental_data",
    "enrich_with_calculated_metrics",
    "save_merged_data_to_parquet",
    "get_ticker_analysis",
    "compare_tickers",
    # Exceptions
    "ConfigurationError",
    "APIKeyError",
    "CIKNotFoundError",
    "FilingNotFoundError",
    "DataParseError",
    "ValidationError",
]
