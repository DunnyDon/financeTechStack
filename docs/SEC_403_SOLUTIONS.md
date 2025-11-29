# SEC EDGAR 403 Forbidden Errors: Solutions & Best Practices

## Overview

The SEC implements rate limiting and bot detection using Akamai WAF to ensure fair access to EDGAR. 403 Forbidden errors occur when requests are identified as violating fair access policies or being part of a botnet.

**Current Status (2025):** SEC EDGAR is accessible but requires proper headers and rate limiting compliance.

---

## Top 5 Working GitHub Repositories

### 1. **sec-edgar/sec-edgar** ⭐⭐⭐⭐⭐
**Stars:** 400+ | **Language:** Python | **Active:** Yes

**Key Solutions for 403 Errors:**
- Implements mandatory `User-Agent` header with contact information
- **Header format:** `"User-Agent": "Name (email@domain.com)"`
- Exponential backoff with configurable retry count (default: 3 retries)
- Backoff factor for 429 rate limit errors
- Rate limiting: ≤10 requests/second
- Automatic retry with increasing delays on 403/429

**Critical Issue Fixes:**
- Fixed issue #296: "Filings blocked HTTP 403 missing user agent CIK lookup"
- Fixed issue #220: "NetworkClient throws 403s when saving filings due to misconfigured user agent"
- Issue #300: "Unauthorized response due to missing headers during cik lookup"

**Header Configuration:**
```python
headers = {
    "User-Agent": "YourCompany (contact@yourcompany.com)",
    "Accept": "application/json",
    "Accept-Encoding": "gzip, deflate"
}
```

**Rate Limiting:**
- Max: 10 requests/second
- Uses `urllib3.util.retry.Retry` with exponential backoff
- 429 error handling: 10-minute IP ban, automatic retry

### 2. **dgunning/edgartools** ⭐⭐⭐⭐
**Stars:** 250+ | **Language:** Python | **Active:** Yes

**Key Solutions:**
- Modern async/await support
- Proper header management for Akamai WAF
- Session pooling with connection limits
- JSON API endpoints (data.sec.gov) instead of HTML scraping
- Includes retry logic with exponential backoff

**Advantage:** Uses REST APIs for more reliable access

### 3. **jonathangreen/sec_filings_scraper** ⭐⭐⭐
**Language:** Python | **Active:** Maintained

**Key Solutions:**
- Simple, focused SEC scraper
- Proper header rotation
- Configurable delays between requests
- Error handling for 403/429/5xx errors

### 4. **edgar** (Archived but useful reference)
**Key Solutions:**
- CIK lookup caching
- Rate limiting with decorators
- Session management with retry adapters

### 5. **sec-api** (Python wrapper)
**Language:** Python

**Key Solutions:**
- High-level API wrapper
- Built-in rate limiting
- Error recovery patterns

---

## Common Causes of 403 Forbidden Errors

### 1. **Missing or Invalid User-Agent Header** (Most Common)
**Cause:** SEC requires identifying traffic for fair access monitoring
**Fix:** Include descriptive User-Agent header

### 2. **Akamai WAF Bot Detection**
**Triggers:**
- Suspicious request patterns
- No User-Agent or generic User-Agent ("python-requests")
- Too many requests too quickly
- Missing Accept-Encoding header

### 3. **Rate Limiting (HTTP 429 → 403)**
**Cause:** Exceeding 10 requests/second per SEC policy
**Duration:** 10-minute IP ban
**Fix:** Implement proper delays between requests

### 4. **Botnet Classification**
**Triggers:**
- Unclassified automated tools
- No identifying headers
- Aggressive scraping patterns

### 5. **Request Timing During SEC Maintenance**
**Times to Avoid:**
- 10:00 PM - 2:00 AM ET (daily index updates)
- Extended timeouts may occur

---

## Specific Headers That Work

### ✅ **Required Headers**

```python
headers = {
    "User-Agent": "YourCompanyName (your-email@company.com)",
    "Accept": "application/json, text/plain, */*",
    "Accept-Encoding": "gzip, deflate",
    "Accept-Language": "en-US,en;q=0.9",
    "Host": "www.sec.gov",
    "Connection": "keep-alive",
    "DNT": "1",
}
```

### ✅ **SEC's Official Recommended Headers**

From SEC documentation (sec.gov/os/accessing-edgar-data):
```
User-Agent: Sample Company Name AdminContact@<sample company domain>.com
Accept-Encoding: gzip, deflate
Host: www.sec.gov
```

### ✅ **Modern Browser-like Headers (Mimics Chrome)**

```python
headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 MyCompany (support@mycompany.com)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Encoding": "gzip, deflate",
    "Accept-Language": "en-US,en;q=0.9",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Cache-Control": "max-age=0",
    "Upgrade-Insecure-Requests": "1",
}
```

### ❌ **Headers That Cause 403 Blocking**

```python
# BAD: Generic Python user agent (immediately blocked)
"User-Agent": "python-requests/2.31.0"

# BAD: No user agent
headers = {}

# BAD: Obviously a bot
"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit Bot/1.0"

# BAD: Missing Accept-Encoding
"Accept-Encoding": ""
```

---

## Timeout & Delay Strategies That Solve 403 Issues

### 1. **Exponential Backoff with Jitter**

```python
import time
import random

def make_request_with_backoff(url, max_retries=5):
    base_delay = 2.0  # seconds
    
    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                return response
            elif response.status_code == 403:
                delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                print(f"403 Forbidden. Attempt {attempt + 1}/{max_retries}. Waiting {delay:.1f}s...")
                time.sleep(delay)
            elif response.status_code == 429:
                print("429 Rate Limited. IP banned for 10 minutes.")
                time.sleep(600)  # 10 minutes
            else:
                response.raise_for_status()
                
        except requests.RequestException as e:
            delay = base_delay * (2 ** attempt)
            print(f"Request error: {e}. Attempt {attempt + 1}/{max_retries}. Waiting {delay:.1f}s...")
            time.sleep(delay)
    
    raise Exception(f"Failed after {max_retries} attempts")
```

**Pattern:** 2s → 4s → 8s → 16s → 32s (with ±1s jitter)

### 2. **SEC Compliance Rate Limiting**

```python
import time
from collections import deque

class RateLimiter:
    def __init__(self, max_requests_per_second=10):
        self.max_rps = max_requests_per_second
        self.min_interval = 1.0 / max_requests_per_second
        self.request_times = deque()
    
    def wait(self):
        """Block until we can make the next request."""
        now = time.time()
        
        # Remove old requests outside the 1-second window
        while self.request_times and self.request_times[0] < now - 1:
            self.request_times.popleft()
        
        # If we're at the limit, wait
        if len(self.request_times) >= self.max_rps:
            sleep_time = 1 - (now - self.request_times[0])
            if sleep_time > 0:
                time.sleep(sleep_time)
        
        self.request_times.append(time.time())

# Usage
limiter = RateLimiter(max_requests_per_second=8)  # Conservative: 8/sec (below 10/sec limit)

for cik in cik_list:
    limiter.wait()
    response = requests.get(url, headers=headers)
```

### 3. **Adaptive Delay Based on Response**

```python
class AdaptiveDelayer:
    def __init__(self):
        self.current_delay = 1.0  # Start with 1 second
        self.min_delay = 0.5
        self.max_delay = 30.0
    
    def handle_response(self, status_code):
        """Adjust delay based on response."""
        if status_code == 200:
            # Success: reduce delay slightly
            self.current_delay = max(self.min_delay, self.current_delay * 0.9)
        elif status_code == 403:
            # Forbidden: increase delay significantly
            self.current_delay = min(self.max_delay, self.current_delay * 4.0)
        elif status_code == 429:
            # Rate limited: maximum delay
            self.current_delay = self.max_delay
        elif status_code >= 500:
            # Server error: increase delay moderately
            self.current_delay = min(self.max_delay, self.current_delay * 2.0)
        
        return self.current_delay
```

### 4. **Recommended Default Configuration**

```python
# RECOMMENDED SETTINGS FOR SEC EDGAR
SEC_CONFIG = {
    "max_requests_per_second": 8,  # Under SEC's 10/sec limit
    "timeout": 15,  # seconds
    "retry_count": 5,
    "initial_backoff": 2.0,  # seconds
    "backoff_multiplier": 2.0,
    "rate_limit_ban_duration": 600,  # 10 minutes (SEC standard)
    "min_request_interval": 0.125,  # 1/8 second = 8 requests/second
}
```

---

## Best Practices for SEC API Scraping

### 1. **Always Declare Your Traffic**

✅ Good:
```python
user_agent = "MyFinanceApp/1.0 (contact: developer@mycompany.com)"
```

### 2. **Use data.sec.gov REST API When Possible**

The JSON API is more reliable than HTML scraping:

```python
# ✅ Prefer this (JSON API)
url = "https://data.sec.gov/submissions/CIK0000000000.json"
response = requests.get(url, headers=headers)

# Avoid this (HTML scraping)
url = "https://www.sec.gov/cgi-bin/browse-edgar?..."
```

### 3. **Implement Graceful Degradation**

```python
def get_filing_data(cik):
    endpoints = [
        f"https://data.sec.gov/submissions/CIK{cik.zfill(10)}.json",  # Try JSON first
        f"https://www.sec.gov/cgi-bin/browse-edgar?CIK={cik}",        # Fallback to HTML
    ]
    
    for endpoint in endpoints:
        try:
            response = requests.get(endpoint, headers=headers, timeout=10)
            if response.status_code == 200:
                return response
        except requests.RequestException:
            continue
    
    raise Exception(f"Failed to fetch filing for CIK {cik}")
```

### 4. **Cache Aggressively**

```python
import json
from pathlib import Path

cache_dir = Path("./sec_cache")

def get_filing_with_cache(cik):
    cache_file = cache_dir / f"{cik}.json"
    
    # Return cached version if available
    if cache_file.exists():
        return json.loads(cache_file.read_text())
    
    # Fetch and cache
    data = requests.get(...).json()
    cache_file.write_text(json.dumps(data))
    return data
```

### 5. **Batch Requests Efficiently**

```python
# ❌ Bad: 100 individual requests with overhead
for cik in ciks:
    response = requests.get(f"https://data.sec.gov/submissions/CIK{cik}.json")

# ✅ Good: Group with minimal overhead
ciks_batch = [list(ciks)[i:i+5] for i in range(0, len(ciks), 5)]
for batch in ciks_batch:
    for cik in batch:
        response = requests.get(f"https://data.sec.gov/submissions/CIK{cik}.json")
        time.sleep(0.15)  # 8 requests/second = 0.125s minimum
```

### 6. **Monitor and Adapt**

```python
class RequestMonitor:
    def __init__(self):
        self.requests_count = 0
        self.errors_count = 0
        self.start_time = time.time()
    
    def log_request(self, status_code):
        self.requests_count += 1
        if status_code >= 400:
            self.errors_count += 1
        
        elapsed = time.time() - self.start_time
        rps = self.requests_count / elapsed
        error_rate = self.errors_count / self.requests_count if self.requests_count > 0 else 0
        
        print(f"Requests: {self.requests_count}, RPS: {rps:.1f}, Error Rate: {error_rate:.1%}")
        
        if error_rate > 0.1:  # More than 10% errors
            print("WARNING: High error rate detected. Consider slowing down.")
```

---

## Alternative SEC Data Sources

### 1. **SEC REST API (data.sec.gov)** ⭐ Recommended

**Advantages:**
- JSON format (easier to parse than HTML)
- More reliable than HTML scraping
- Officially supported

**Endpoints:**
```
https://data.sec.gov/submissions/CIK0000000000.json
https://data.sec.gov/api/xbrl/companyconcept/CIK0000000000/us-gaap/Assets.json
https://data.sec.gov/api/xbrl/companyfacts/CIK0000000000.json
https://data.sec.gov/api/xbrl/frames/us-gaap/Assets/CY2023Q4I.json
```

### 2. **EDGAR Index Files** (XML/JSON)

**More efficient than individual requests:**
```
https://www.sec.gov/Archives/edgar/daily-index/
https://www.sec.gov/Archives/edgar/full-index/
```

### 3. **Company Tickers JSON**

**For CIK lookup (recommended over search):**
```
https://www.sec.gov/files/company_tickers.json
```

### 4. **RSS Feeds**

**Real-time filing updates:**
```
https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=10-k&output=atom
```

### 5. **Third-Party Services**

- **Edgar Online** (S&P Capital IQ)
- **Bloomberg Terminal**
- **FactSet**
- **eSpeed**

---

## Quick Fix Checklist

When getting 403 errors:

- [ ] **Add User-Agent header** with your company/email
- [ ] **Include Accept-Encoding** header (gzip, deflate)
- [ ] **Add 2+ second delays** between requests
- [ ] **Limit to 8-10 requests/second** max
- [ ] **Implement exponential backoff** (2s, 4s, 8s...)
- [ ] **Rotate user agents** if making many requests
- [ ] **Use data.sec.gov REST API** instead of HTML scraping
- [ ] **Cache responses** to avoid repeat requests
- [ ] **Monitor 429 errors** and pause for 10 minutes
- [ ] **Check SEC maintenance windows** (10pm-2am ET)
- [ ] **Use session pooling** to reuse connections
- [ ] **Add DNT: 1 header** (Do Not Track - respects privacy)

---

## Current SEC API Status

| Endpoint | Status | Recommended |
|----------|--------|-------------|
| data.sec.gov (JSON API) | ✅ Working | YES |
| company_tickers.json | ✅ Working | YES |
| Daily/Full Indexes | ✅ Working | YES |
| RSS Feeds | ✅ Working | YES |
| XBRL API | ✅ Working | YES |
| HTML Scraping (EDGAR) | ⚠️ Working | NO (use API) |
| Archives Download | ✅ Working | YES |

**Last Verified:** November 2025

---

## References

- **SEC Official:** https://www.sec.gov/os/accessing-edgar-data
- **SEC Developer:** https://www.sec.gov/developer
- **Fair Access Policy:** https://www.sec.gov/privacy.htm#security
- **GitHub sec-edgar:** https://github.com/sec-edgar/sec-edgar
- **Data.sec.gov API:** https://data.sec.gov/submissions/
