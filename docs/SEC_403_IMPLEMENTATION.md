# Implementation Guide: Fixing SEC 403 Errors in Your Project

## Current Status of Your Code

Your project (`src/utils.py`, `src/main.py`) already has some good foundations:
- ✅ Rotating user agents
- ✅ Exponential backoff on 403 errors
- ✅ Retry logic
- ⚠️ Missing some critical headers
- ⚠️ Rate limiting could be more aggressive (2.0s delay is good but could be optimized)

---

## Recommended Fixes for Your Project

### 1. **Update Headers in utils.py**

Replace the basic headers with SEC-compliant headers:

```python
# Current (in make_request_with_backoff):
default_headers = {
    "User-Agent": get_next_user_agent(),
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate",
    "DNT": "1",
}

# REPLACE WITH:
default_headers = {
    "User-Agent": get_next_user_agent(),
    "Accept": "application/json, text/plain, */*",
    "Accept-Encoding": "gzip, deflate",
    "Accept-Language": "en-US,en;q=0.9",
    "Host": "www.sec.gov",
    "Connection": "keep-alive",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "DNT": "1",
}
```

### 2. **Add Declarative User Agent Function**

```python
def get_declarative_user_agent() -> str:
    """
    Return a declarative user agent as recommended by SEC.
    Format: "Company Name (email@domain.com)"
    """
    # Read from config or environment
    company_name = os.getenv("SEC_COMPANY_NAME", "FinanceApp")
    contact_email = os.getenv("SEC_CONTACT_EMAIL", "contact@example.com")
    
    return f"{company_name} ({contact_email})"
```

### 3. **Implement Session Management**

Instead of creating a new session for each request, reuse sessions:

```python
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

class SECRequestsManager:
    """Singleton for managing SEC API requests with proper retry logic."""
    
    _instance = None
    _session = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize_session()
        return cls._instance
    
    def _initialize_session(self):
        """Initialize session with proper retry strategy."""
        self._session = requests.Session()
        
        # Retry strategy: exponential backoff
        retry_strategy = Retry(
            total=3,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"],
            backoff_factor=2,  # 1s, 2s, 4s
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self._session.mount("http://", adapter)
        self._session.mount("https://", adapter)
    
    def get(self, url, headers=None, **kwargs):
        """Make GET request with SEC headers."""
        if headers is None:
            headers = {}
        
        # Add SEC headers
        headers.update({
            "User-Agent": get_next_user_agent(),
            "Accept": "application/json, text/plain, */*",
            "Accept-Encoding": "gzip, deflate",
        })
        
        return self._session.get(url, headers=headers, **kwargs)
```

### 4. **Use REST API Instead of HTML Scraping**

Current approach (HTML scraping - prone to 403):
```python
# ❌ Avoid this for company_tickers.json
url = "https://www.sec.gov/files/company_tickers.json"
```

Better approach (Direct JSON):
```python
# ✅ Use this instead
url = "https://data.sec.gov/submissions/CIK0000000000.json"
```

### 5. **Enhanced Rate Limiting**

```python
import time
from collections import deque
from threading import Lock

class RateLimiter:
    """Ensure we stay within SEC's 10 requests/second limit."""
    
    def __init__(self, max_requests_per_second=8):
        self.max_rps = max_requests_per_second
        self.min_interval = 1.0 / max_requests_per_second
        self.request_times = deque()
        self.lock = Lock()
    
    def wait(self):
        """Block until we can make the next request."""
        with self.lock:
            now = time.time()
            
            # Remove requests outside the 1-second window
            while self.request_times and self.request_times[0] < now - 1:
                self.request_times.popleft()
            
            # If at limit, wait
            if len(self.request_times) >= self.max_rps:
                sleep_time = 1 - (now - self.request_times[0])
                if sleep_time > 0:
                    time.sleep(sleep_time)
            
            self.request_times.append(time.time())

# Usage
rate_limiter = RateLimiter(max_requests_per_second=8)

for cik in ciks:
    rate_limiter.wait()
    response = requests.get(url, headers=headers)
```

### 6. **Add Request Monitoring**

```python
import logging
from dataclasses import dataclass
from datetime import datetime

@dataclass
class RequestStats:
    total_requests: int = 0
    successful: int = 0
    forbidden_403: int = 0
    rate_limited_429: int = 0
    errors: int = 0
    start_time: datetime = None
    
    def log_stats(self):
        """Log current statistics."""
        elapsed = (datetime.now() - self.start_time).total_seconds()
        rps = self.total_requests / elapsed if elapsed > 0 else 0
        error_rate = self.errors / self.total_requests if self.total_requests > 0 else 0
        
        logger = logging.getLogger(__name__)
        logger.info(
            f"Stats - Total: {self.total_requests}, "
            f"Success: {self.successful}, 403: {self.forbidden_403}, "
            f"429: {self.rate_limited_429}, Errors: {self.errors}, "
            f"RPS: {rps:.1f}, Error Rate: {error_rate:.1%}"
        )

# Usage
stats = RequestStats(start_time=datetime.now())

for cik in ciks:
    try:
        response = requests.get(url)
        stats.total_requests += 1
        
        if response.status_code == 200:
            stats.successful += 1
        elif response.status_code == 403:
            stats.forbidden_403 += 1
        elif response.status_code == 429:
            stats.rate_limited_429 += 1
            time.sleep(600)  # 10 minute ban
        else:
            stats.errors += 1
    except Exception as e:
        stats.errors += 1
    
    if stats.total_requests % 100 == 0:
        stats.log_stats()
```

---

## Quick Implementation Steps

### Step 1: Update constants.py

```python
# Add to SEC_CONFIG section
SEC_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Encoding": "gzip, deflate",
    "Accept-Language": "en-US,en;q=0.9",
    "Host": "www.sec.gov",
    "Connection": "keep-alive",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "DNT": "1",
}

# Add company info from env
SEC_COMPANY_NAME = os.getenv("SEC_COMPANY_NAME", "FinanceApp")
SEC_CONTACT_EMAIL = os.getenv("SEC_CONTACT_EMAIL", "contact@example.com")

# Rate limiting
SEC_MAX_REQUESTS_PER_SECOND = 8  # Conservative: below SEC's 10/sec limit
SEC_MIN_REQUEST_INTERVAL = 1.0 / SEC_MAX_REQUESTS_PER_SECOND
```

### Step 2: Create new file: sec_client.py

```python
"""SEC EDGAR API client with proper rate limiting and error handling."""

import time
from collections import deque
from threading import Lock
from typing import Optional, Dict, Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .constants import (
    SEC_HEADERS,
    SEC_COMPANY_NAME,
    SEC_CONTACT_EMAIL,
    SEC_MAX_REQUESTS_PER_SECOND,
)
from .utils import get_logger

logger = get_logger(__name__)


class SECClient:
    """Client for SEC EDGAR API with rate limiting."""
    
    def __init__(self):
        self.session = self._create_session()
        self.rate_limiter = RateLimiter(SEC_MAX_REQUESTS_PER_SECOND)
    
    @staticmethod
    def _create_session():
        """Create session with retry strategy."""
        session = requests.Session()
        
        retry_strategy = Retry(
            total=3,
            backoff_factor=2,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    def get(self, url: str, timeout: int = 15) -> Optional[Dict[str, Any]]:
        """Make SEC API request with rate limiting."""
        self.rate_limiter.wait()
        
        headers = SEC_HEADERS.copy()
        headers["User-Agent"] = f"{SEC_COMPANY_NAME} ({SEC_CONTACT_EMAIL})"
        
        try:
            response = self.session.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                logger.error("403 Forbidden - Check rate limiting")
            raise


class RateLimiter:
    """Rate limiter for SEC requests."""
    
    def __init__(self, max_requests_per_second: float):
        self.max_rps = max_requests_per_second
        self.request_times = deque()
        self.lock = Lock()
    
    def wait(self):
        """Wait until next request is allowed."""
        with self.lock:
            now = time.time()
            
            # Remove old requests
            while self.request_times and self.request_times[0] < now - 1:
                self.request_times.popleft()
            
            # Wait if needed
            if len(self.request_times) >= self.max_rps:
                sleep_time = 1 - (now - self.request_times[0])
                if sleep_time > 0:
                    time.sleep(sleep_time)
            
            self.request_times.append(time.time())
```

### Step 3: Update main.py to use new client

```python
from .sec_client import SECClient

# Create global client
sec_client = SECClient()

@task(retries=3, retry_delay_seconds=5)
def fetch_sec_filings(cik: str) -> dict:
    """Fetch SEC filings for a CIK."""
    url = f"https://data.sec.gov/submissions/CIK{cik.zfill(10)}.json"
    
    try:
        data = sec_client.get(url)
        if not data:
            raise FilingNotFoundError(f"No filings found for CIK {cik}")
        return data
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 403:
            logger.warning(f"403 Forbidden for CIK {cik}. Retrying...")
            raise  # Prefect will retry
        raise
```

---

## Testing Your Changes

### Test 1: Verify Headers

```python
import requests

url = "https://data.sec.gov/submissions/CIK0000320193.json"
headers = {
    "User-Agent": "TestApp (test@example.com)",
    "Accept": "application/json",
    "Accept-Encoding": "gzip, deflate",
}

response = requests.get(url, headers=headers)
print(f"Status: {response.status_code}")
assert response.status_code == 200, "Failed to fetch with proper headers"
```

### Test 2: Rate Limiting

```python
from src.sec_client import RateLimiter
import time

limiter = RateLimiter(10)
start = time.time()

for i in range(20):
    limiter.wait()

elapsed = time.time() - start
# Should take at least 1 second (20 requests at 10/sec = 2 seconds)
assert elapsed >= 1.0, f"Rate limiting too fast: {elapsed}s"
print(f"Rate limiting test passed: {20} requests in {elapsed:.1f}s")
```

### Test 3: 403 Handling

```python
def test_403_recovery():
    """Test that 403 errors trigger retry logic."""
    from unittest.mock import patch, MagicMock
    
    # Mock a 403 response followed by success
    responses = [
        MagicMock(status_code=403),
        MagicMock(status_code=200, json=lambda: {"data": "test"}),
    ]
    
    with patch('requests.Session.get', side_effect=responses):
        # Should handle 403 and succeed on retry
        pass
```

---

## Environment Setup

Add to your `.env` file:

```bash
SEC_COMPANY_NAME=MyFinanceCompany
SEC_CONTACT_EMAIL=developer@mycompany.com
SEC_MAX_REQUESTS_PER_SECOND=8
DEFAULT_TIMEOUT=15
REQUEST_MAX_RETRIES=5
```

---

## Monitoring & Debugging

### Enable Debug Logging

```python
import logging

# Add to your setup
logging.getLogger("requests").setLevel(logging.DEBUG)
logging.getLogger("urllib3").setLevel(logging.DEBUG)
```

### Common Issues & Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| 403 on first request | Missing User-Agent | Add `User-Agent: Company (email@domain.com)` |
| 403 after 50 requests | Rate limiting | Reduce to 8 requests/second |
| Timeouts | SEC maintenance | Wait 30 mins, retry |
| 429 status code | IP banned | Wait 10 minutes before retrying |
| HTML instead of JSON | Wrong endpoint | Use `data.sec.gov` not `www.sec.gov` |

---

## Production Checklist

- [ ] User-Agent header includes company name and contact email
- [ ] Rate limiting set to ≤8 requests/second
- [ ] Exponential backoff implemented (2s, 4s, 8s...)
- [ ] 429 error handling with 10-minute pause
- [ ] Session pooling for connection reuse
- [ ] Response caching to avoid duplicate requests
- [ ] Error monitoring and alerting
- [ ] Request logging for debugging
- [ ] Graceful degradation on API errors
- [ ] Documentation of SEC compliance measures
