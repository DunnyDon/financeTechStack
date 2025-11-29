"""
Application-wide constants for the TechStack financial data aggregation system.

This module defines all constant values used across the application to ensure
consistency and centralized management of configuration values.
"""

# SEC API Endpoints
SEC_BASE_URL: str = "https://data.sec.gov/submissions"
SEC_COMPANY_TICKERS_URL: str = "https://www.sec.gov/files/company_tickers.json"
SEC_FILINGS_URL: str = "https://www.sec.gov/cgi-bin/browse-edgar"

# Alpha Vantage API
ALPHA_VANTAGE_BASE_URL: str = "https://www.alphavantage.co/query"

# HTTP Configuration
DEFAULT_TIMEOUT: int = 10
REQUEST_MAX_RETRIES: int = 5
INITIAL_BACKOFF_DELAY: float = 2.0
RATE_LIMIT_DELAY: float = 1.0

# Backoff configuration for rate limiting
BACKOFF_FACTOR: float = 2.0  # Exponential backoff multiplier (2^attempt)
ALPHA_VANTAGE_RATE_LIMIT_DELAY: float = 12.0  # 5 requests/min = 1 request/12 sec

# File & Output Configuration
DEFAULT_OUTPUT_DIR: str = "db"
DEFAULT_COMPRESSION: str = "snappy"
PARQUET_EXTENSION: str = ".parquet"

# Prefect Configuration
PREFECT_TASK_RETRIES: int = 3
PREFECT_RETRY_DELAY_SECONDS: int = 5

# Filing Types
FILING_TYPE_10_K: str = "10-K"
FILING_TYPE_10_Q: str = "10-Q"
FILING_TYPE_8_K: str = "8-K"

# CIK Formatting
CIK_ZERO_PADDING: int = 10

# User Agents for HTTP requests
# SEC EDGAR requires proper User-Agent header with contact information
# Format: "Company Name (email@company.com)" or standard browser user agent
USER_AGENTS: list[str] = [
    "TechStack SEC Scraper (tech@techstack.com)",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (Safari/605.1.15)",
]

# SEC recommends maximum 10 requests per second
# We use conservative rate limiting of 1 request per 2 seconds
SEC_MAX_REQUESTS_PER_SECOND: float = 10.0
SEC_REQUEST_DELAY: float = 0.1  # Actual delay: 100ms between requests

# Error Messages
ERROR_CONFIG_FILE_NOT_FOUND: str = "Config file not found: {path}\nPlease create {path} from {template}"
ERROR_CONFIG_VALUE_PLACEHOLDER: str = "Config value for '{key}' is still placeholder 'your_api_key_here'. Please update config file with your actual API key."
ERROR_API_KEY_NOT_FOUND: str = "API key not found. Set {env_var} env var or add to config.csv"
ERROR_CIK_NOT_FOUND: str = "CIK not found for ticker: {ticker}"
ERROR_FILINGS_NOT_FOUND: str = "Failed to fetch filings for CIK {cik}"
ERROR_403_FORBIDDEN: str = "[Attempt {attempt}] 403 Forbidden. Waiting {wait_time}s before retry..."
ERROR_RETRY_FAILED: str = "[Final attempt] Failed after {max_retries} attempts"
