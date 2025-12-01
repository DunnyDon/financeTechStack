"""
TechStack - Financial data aggregation and analysis system.

A production-ready Python application that combines portfolio analytics,
SEC EDGAR integration, XBRL fundamentals, and technical analysis
using Prefect workflow orchestration.
"""

__version__ = "0.1.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"
__license__ = "MIT"

from .analytics_flows import enhanced_analytics_flow, send_report_email_flow
from .analytics_report import AnalyticsReporter, generate_analytics_report, send_analytics_email
from .config import config
from .exceptions import (
    APIKeyError,
    CIKNotFoundError,
    ConfigurationError,
    DataParseError,
    FilingNotFoundError,
    ValidationError,
)
from .parquet_db import ParquetDB
from .portfolio_analytics import PortfolioAnalytics
from .portfolio_fundamentals import FundamentalAnalyzer
from .portfolio_holdings import Holdings
from .portfolio_prices import PriceFetcher
from .portfolio_technical import TechnicalAnalyzer
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
    # Main analytics flows
    "enhanced_analytics_flow",
    "send_report_email_flow",
    # Analytics and reporting
    "AnalyticsReporter",
    "generate_analytics_report",
    "send_analytics_email",
    # Portfolio analysis
    "PortfolioAnalytics",
    "FundamentalAnalyzer",
    "TechnicalAnalyzer",
    "Holdings",
    "PriceFetcher",
    # Data storage
    "ParquetDB",
    # Config
    "config",
    # XBRL functions
    "fetch_sec_filing_index",
    "fetch_xbrl_document",
    "parse_xbrl_fundamentals",
    "save_xbrl_data_to_parquet",
    "fetch_xbrl_filings",
    # Exceptions
    "ConfigurationError",
    "APIKeyError",
    "CIKNotFoundError",
    "FilingNotFoundError",
    "DataParseError",
    "ValidationError",
]
