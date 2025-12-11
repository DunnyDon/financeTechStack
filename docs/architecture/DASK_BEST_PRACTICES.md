# Dask Parallelization Best Practices

**Preventing Race Conditions in Database Operations**

---

## The Problem We Fixed

When using Dask to parallelize operations that write to a shared database (like ParquetDB), you can get race conditions if multiple tasks try to write to the same files simultaneously.

### Bad Pattern ❌

```python
from dask import delayed

@delayed
def process_and_save_ticker(ticker):
    # Fetch data
    data = fetch_data(ticker)
    
    # PROBLEM: Each task creates its own DB connection and tries to write
    db = ParquetDB()
    db.upsert_prices(data)  # RACE CONDITION if multiple tasks do this
    
    return {"ticker": ticker, "status": "done"}

# All tasks run in parallel, causing concurrent writes
tasks = [process_and_save_ticker(t) for t in tickers]
results = dask.compute(*tasks, scheduler="threads")  # ⚠️ CRASHES
```

**Why it fails:**
- Thread 1 reads partition file
- Thread 2 reads SAME partition file (no lock)
- Thread 1 modifies and writes back
- Thread 2 modifies and overwrites Thread 1's changes
- File becomes corrupted

---

## Good Pattern ✅ (What We Implemented)

### Architecture: Separate Fetch from Write

```python
from dask import delayed
import dask

# PHASE 1: Fetch data in parallel (safe - no I/O conflicts)
@delayed
def fetch_ticker_data(ticker):
    """Fetch only - return data, don't write"""
    data = fetch_data(ticker)
    return {
        "ticker": ticker,
        "data": data,
        "status": "fetched"
    }

# Create parallel tasks for fetching
tasks = [fetch_ticker_data(t) for t in tickers]

# Execute all fetches in parallel
results_list = dask.compute(*tasks, scheduler="threads")
results = {r["ticker"]: r for r in results_list}

# PHASE 2: Write sequentially (safe - single thread)
db = ParquetDB()
for ticker, result in results.items():
    if result.get("data") is not None:
        db.upsert_prices(result["data"])
```

**Why it works:**
- PHASE 1: All threads fetch independently (no file conflicts)
- PHASE 2: Single thread writes (no race conditions)
- Still fast: 30x speedup from parallel fetches
- Always safe: Sequential writes guarantee correctness

---

## When Different Parallelization Strategies Are Safe

### ✅ SAFE: Read-Only Operations

```python
# This is always safe - multiple threads reading
@delayed
def fetch_price(ticker):
    return price_fetcher.fetch_price(ticker)

tasks = [fetch_price(t) for t in tickers]
results = dask.compute(*tasks, scheduler="threads")  # ✅ OK
```

### ✅ SAFE: Distributed Client with Proper Scheduler

```python
# Dask's distributed client handles concurrency
from dask.distributed import Client

client = Client("tcp://localhost:8786")

# Each worker runs independently on separate machines
futures = [client.submit(compute_fn, item) for item in items]
results = [f.result() for f in futures]  # ✅ OK
```

### ✅ SAFE: Consolidate Before Write

```python
# Fetch in parallel, combine, then write once
results = dask.compute(*fetch_tasks)
combined_df = pd.concat([r["data"] for r in results])

# Single write - no race conditions
db.upsert_prices(combined_df)  # ✅ OK
```

### ❌ UNSAFE: Concurrent DB Writes

```python
# This causes race conditions
@delayed
def fetch_and_write(ticker):
    data = fetch(ticker)
    db.upsert_prices(data)  # ❌ RACE CONDITION
    return result

results = dask.compute(*tasks, scheduler="threads")
```

### ❌ UNSAFE: Shared File Writes

```python
# Writing to same file from multiple threads
def write_log(message):
    with open("log.txt", "a") as f:
        f.write(message)  # ❌ Can corrupt file

tasks = [delayed(write_log)(msg) for msg in messages]
dask.compute(*tasks, scheduler="threads")
```

---

## Implementation Checklist

When adding Dask parallelization:

- [ ] **Identify the bottleneck** - What operation is slow?
  - Fetching data? → Can parallelize
  - Writing? → Keep sequential
  
- [ ] **Separate concerns**
  - Extract fetch-only function
  - Keep DB writes outside Dask tasks
  
- [ ] **Use appropriate scheduler**
  - Distributed reads → `scheduler="threads"` ✅
  - Database writes → Single thread ✅
  - CPU-intensive work → `scheduler="processes"` ✅
  
- [ ] **Verify thread-safety**
  - No concurrent file writes to same location
  - No concurrent DB operations on same partition
  - No shared mutable state
  
- [ ] **Test with data**
  - Run multiple times
  - Verify output is consistent
  - Check all files are readable after completion

---

## Code Template: Two-Phase Pattern

```python
from typing import List, Dict, Optional
from dask import delayed
import dask
from src.parquet_db import ParquetDB

@delayed
def fetch_only(ticker: str) -> Dict:
    """
    PHASE 1: Fetch data (can run in parallel)
    
    Returns data without writing to DB
    """
    try:
        fetcher = MyFetcher()
        data = fetcher.fetch(ticker)
        return {
            "ticker": ticker,
            "status": "success",
            "data": data,
        }
    except Exception as e:
        return {
            "ticker": ticker,
            "status": "error",
            "error": str(e),
        }

def fetch_and_write(
    tickers: List[str],
    n_workers: Optional[int] = None
) -> Dict:
    """
    Main orchestration: Fetch parallel, write sequential
    """
    
    # PHASE 1: Parallel fetch
    print(f"Fetching {len(tickers)} items in parallel...")
    tasks = [fetch_only(ticker) for ticker in tickers]
    results_list = dask.compute(*tasks, scheduler="threads", num_workers=n_workers)
    results = {r["ticker"]: r for r in results_list}
    
    # PHASE 2: Sequential write
    print(f"Writing {len(results)} items sequentially...")
    db = ParquetDB()
    written = 0
    
    for ticker, result in results.items():
        if result.get("status") == "success" and result.get("data") is not None:
            try:
                db.upsert_prices(result["data"])
                written += 1
            except Exception as e:
                print(f"Error writing {ticker}: {e}")
    
    return {
        "total": len(tickers),
        "written": written,
        "failed": len(tickers) - written,
    }
```

---

## Monitoring & Validation

### After Running Backfill

```python
import pyarrow.parquet as pq
from pathlib import Path

# Verify all files are readable
parquet_files = list(Path('db/prices').rglob('*.parquet'))
print(f"Total files: {len(parquet_files)}")

valid = 0
for f in parquet_files:
    try:
        table = pq.read_table(str(f))
        valid += 1
    except Exception as e:
        print(f"ERROR: {f} - {e}")

print(f"Valid files: {valid}/{len(parquet_files)}")
```

### Dashboard Integration

Show data freshness to users:
```python
def get_price_data_freshness(db: ParquetDB) -> Dict:
    prices_df = db.read_table('prices')
    latest_date = pd.to_datetime(prices_df['timestamp']).max()
    days_old = (datetime.now() - latest_date).days
    
    if days_old <= 1:
        return {"status": "🟢 Fresh", "is_stale": False}
    elif days_old <= 7:
        return {"status": f"🟡 {days_old} days old", "is_stale": False}
    else:
        return {"status": f"🔴 STALE ({days_old} days)", "is_stale": True}
```

---

## Key Takeaways

1. **Never write to shared database from parallel tasks** ❌
2. **Separate fetch (parallel) from write (sequential)** ✅
3. **Use Distributed Client for true parallel writes** ✅
4. **Consolidate then write once** ✅
5. **Verify output integrity after execution** ✅

---

## References

- Dask Distributed: https://distributed.dask.org/
- Dask Delayed: https://docs.dask.org/en/latest/delayed.html
- Thread Safety in Python: https://realpython.com/intro-to-python-threading/
- ParquetDB Partitioning: See `src/parquet_db.py`
