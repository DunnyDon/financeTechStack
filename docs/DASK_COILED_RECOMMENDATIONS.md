# Dask & Coiled Integration Research & Recommendations

**Date**: November 29, 2025  
**Status**: Strategic Planning  
**Target Phases**: Q1-Q2 2026 (if pursued)

---

## Executive Summary

Your Finance TechStack application is currently optimized for sequential processing of 1-10 companies using Prefect's single-worker orchestration. To support enterprise-scale analysis (hundreds to thousands of companies), this document provides strategic recommendations on integrating **Dask** for distributed computing and evaluating **Coiled** for managed infrastructure.

**Key Finding**: Your current bottleneck is **SEC API rate limits** (1 req/sec), not compute power. Adding Dask/Coiled makes sense only after addressing API constraints.

---

## Current Architecture Analysis

### Processing Pipeline Review

```
Current Flow (Single Worker):
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│  Ticker     │────→│ CIK Lookup   │────→│ SEC Fetch    │
│ List        │     │ (1 req/sec)  │     │ (1 req/sec)  │
└─────────────┘     └──────────────┘     └──────────────┘
                              ↓
                     ┌──────────────┐
                     │ XBRL Parse   │
                     │ (CPU-bound)  │
                     └──────────────┘
                              ↓
                     ┌──────────────┐
                     │ Alpha Vantage│
                     │ (5 req/min)  │
                     └──────────────┘
                              ↓
                     ┌──────────────┐
                     │ Data Merge   │
                     │ (I/O-bound)  │
                     └──────────────┘
                              ↓
                     ┌──────────────┐
                     │ Parquet Save │
                     │ (I/O-bound)  │
                     └──────────────┘
```

### Computational Characteristics

| Operation | Type | Duration | Parallelizable | Bottleneck |
|-----------|------|----------|-----------------|------------|
| CIK Lookup | I/O | 0.5-2s per ticker | ✓ API limit | SEC rate limit |
| SEC Filing Fetch | I/O | 1-3s per filing | ✓ API limit | SEC rate limit (1/sec) |
| XBRL Parse | CPU | 0.5-1s per filing | ✓ Yes | CPU if >100 files |
| Alpha Vantage | I/O | 0.2s per ticker | ✓ API limit | AV rate limit (5/min) |
| Data Merge | CPU/Mem | 0.1-0.5s | ✓ Yes | Memory for large datasets |
| Parquet Save | I/O | 0.1-0.5s | ✓ Yes | Disk I/O |

**Assessment**: Current implementation is **I/O-bound**, not CPU-bound. Dask shines with CPU-bound workloads.

### Current Limitations

1. **API Rate Limits** (Critical)
   - SEC: 1 request/second hard limit
   - Alpha Vantage Free: 5 API calls/minute
   - Cannot parallelize beyond these limits without multiple API keys

2. **Single Worker**
   - Prefect runs tasks sequentially on one worker
   - Network I/O is blocking
   - Processing 1000 companies takes ~1000 seconds minimum

3. **Memory Constraints**
   - Loading entire SEC company database in memory
   - Large XBRL documents parsed serially
   - Parquet files written to disk sequentially

---

## Dask Deep Dive

### What is Dask?

Dask is a flexible parallel computing library in Python that scales workloads across multiple cores/machines.

```python
# Sequential (current approach)
results = []
for ticker in tickers:
    result = process_ticker(ticker)
    results.append(result)

# Dask approach
import dask.bag as db
dask_tickers = db.from_sequence(tickers, npartitions=10)
results = dask_tickers.map(process_ticker).compute()
```

### Dask Components

1. **Dask Bag**: For processing sequences of objects
   - Perfect for: List of tickers → financial data
   - Example: Processing 1000 companies in parallel

2. **Dask DataFrame**: Pandas-like API with distribution
   - Perfect for: Large data transformations
   - Example: Merging SEC + XBRL + AV data across thousands of companies

3. **Dask Delayed**: For custom parallel workflows
   - Perfect for: Complex DAGs
   - Example: Your current Prefect flow structure

4. **Dask Distributed Scheduler**: Multiple machines
   - Perfect for: Scaling beyond single machine
   - Example: 10 worker nodes, each processing 100 companies

### Integration with Your Stack

#### Architecture Option 1: Dask within Prefect Tasks

```python
# src/main.py
from dask.distributed import Client
from prefect import flow, task

@task
def batch_process_tickers_with_dask(tickers: list, num_workers: int = 4):
    """Process multiple tickers using Dask for parallelization"""
    
    # Use local cluster for batch processing
    with LocalCluster(n_workers=num_workers, threads_per_worker=2) as cluster:
        with Client(cluster) as client:
            # Distribute CIK lookups
            cik_futures = client.map(fetch_company_cik, tickers)
            ciks = client.gather(cik_futures)
            
            # Distribute filing fetches (respecting SEC rate limit)
            filing_futures = client.map(fetch_sec_filings, ciks)
            filings = client.gather(filing_futures)
            
            # Distribute XBRL parsing (CPU-bound, benefits from parallelization)
            xbrl_futures = client.map(parse_xbrl_data, filings)
            xbrl_results = client.gather(xbrl_futures)
    
    return xbrl_results

@flow
def aggregate_financial_data_scaled(tickers: list):
    """Main flow with Dask scaling"""
    results = batch_process_tickers_with_dask(tickers, num_workers=4)
    merged_data = merge_all_results(results)
    save_data(merged_data)
    return merged_data
```

**Pros**:
- Seamless Prefect integration
- No vendor lock-in
- Local testing with docker-compose
- Fine-grained control

**Cons**:
- Must provision and maintain worker nodes
- Manual scaling decisions
- Monitoring complexity

#### Architecture Option 2: Dask Collections (DataFrame)

For large batch transformations:

```python
import dask.dataframe as dd
from prefect import task

@task
def bulk_calculate_financial_ratios(company_data_file: str):
    """Calculate ratios for thousands of companies"""
    
    # Load Parquet file as Dask DataFrame (lazy, partitioned)
    ddf = dd.read_parquet(company_data_file)
    
    # Distributed transformations
    ddf['debt_to_equity'] = ddf['total_debt'] / ddf['equity']
    ddf['current_ratio'] = ddf['current_assets'] / ddf['current_liabilities']
    ddf['roa'] = ddf['net_income'] / ddf['total_assets']
    
    # Write results back out
    ddf.to_parquet('db/ratios_*.parquet')
    
    return True
```

**Pros**:
- Familiar Pandas-like syntax
- Automatic optimization
- Handles larger-than-memory datasets
- Excellent for batch analytics

**Cons**:
- Less flexible than custom Dask Delayed
- Overhead for small datasets

### Dask Performance Projections

**Scenario**: Processing 1,000 companies' SEC filings

| Setup | Execution Time | Speedup | Cost |
|-------|----------------|---------|------|
| Current (1 worker) | ~2,000s (33 min) | 1x | Prefect server only |
| Dask Local (4 cores) | ~600s (10 min) | 3.3x | Laptop CPU |
| Dask 4-worker cluster | ~500s (8 min) | 4x | 4 EC2 t3.medium (~$0.50/hr) |
| Dask 10-worker cluster | ~200s (3 min) | 10x | 10 EC2 t3.medium (~$1.25/hr) |

**Reality Check**: These numbers assume **non-blocking I/O**. With SEC's 1 req/sec limit:
- Maximum throughput is ~60 companies/minute (~1000/sec ÷ 60)
- No parallelization helps until you have multiple API connections
- True speedup requires: API key pooling or SEC account upgrade

---

## Coiled Deep Dive

### What is Coiled?

Coiled is a managed Dask hosting platform on AWS that handles:
- Cluster provisioning and scaling
- Security and authentication
- Monitoring and dashboards
- Cost optimization (spot instances)

```python
import coiled

# Create a 10-worker cluster with 1 click
cluster = coiled.Cluster(
    n_workers=10,
    worker_memory="4GB",
    region="us-west-2"
)

# Your Dask code runs unchanged
with cluster.get_client() as client:
    result = distributed_computation(client)
```

### Key Coiled Features

| Feature | Benefit | Relevance |
|---------|---------|-----------|
| Auto-scaling | Scales to 50+ workers based on load | High - variable workloads |
| Spot instances | 70% cost savings | High - batch processing |
| Adaptive sizing | Workers right-size based on tasks | High - unknown task sizes |
| GPU support | ML/accelerated computing | Low - not needed yet |
| Multi-region | Global data processing | Medium - multi-geo data |
| Integrated security | SSO, encryption, audit logs | Medium - enterprise needs |
| Cost tracking | Detailed billing per cluster | High - cost management |

### Coiled Pricing Model

**Coiled Subscription**: $120-300/month for business tiers
**Cluster Costs**: Pay-per-use on AWS

**Example: Processing 5,000 companies**

```
Setup: 20-worker cluster, 4GB RAM each, us-west-2
Duration: 30 minutes (3,000 sec from 500s base above)
EC2 Costs: 20 workers × 0.5 hours × $0.042/hr = $0.42
Coiled Fee: $100/month (amortized per job)
Total: ~$0.50-1.50 per run
```

**Cost Comparison**

| Scale | Setup | Monthly Cost | Per-Run | Preferred |
|-------|-------|--------------|---------|-----------|
| 100 companies | Prefect only | $0 | $0 | Prefect |
| 500 companies | Dask local | $50-100 | $0 | Local Dask |
| 1000 companies | Dask cluster | $200-300 | $2-5 | Self-managed |
| 5000 companies | Coiled | $300-400 | $5-20 | Coiled |
| Real-time 24/7 | Coiled always-on | $1500+ | - | Coiled |

---

## API Constraint Analysis

### SEC EDGAR Rate Limiting

**Current Implementation**:
```python
# In src/utils.py - add 1-second delay between requests
time.sleep(1)  # Hard limit: 1 request per second
```

**Workaround Strategies**:

1. **Multiple API Connections** (Not recommended)
   - Opens multiple connections from same IP
   - SEC blocks IPs that attempt to circumvent rate limits
   - Violation of SEC Terms of Service

2. **SEC Commercial Service** (Recommended)
   - SEC offers higher-rate access through Edgar Online
   - Cost: $$$$ (enterprise pricing)
   - Unlimited concurrent connections

3. **Data Caching** (Immediate improvement)
   - Current: No caching of CIK lookups
   - Improvement: Cache company_tickers.json locally
   - Impact: Save ~100-500ms per duplicate ticker

4. **Distributed API Tokens** (Medium-term)
   - Use different AWS accounts/IP addresses
   - Blend requests across multiple sources
   - Risk: Complex, not recommended

### Alpha Vantage API Scaling

**Current Tier**: Free (5 calls/minute, 500/day)

**Options**:

| Tier | Price | Rate Limit | Monthly Cost |
|------|-------|-----------|--------------|
| Free | $0 | 5/min, 500/day | $0 |
| Premium | $29.99 | 120/min, 24k/day | $30 |
| Premium+ | $79.99 | 600/min, 120k/day | $80 |

**Analysis**:
- To process 1000 companies: Need minimum 6 days with free tier
- Premium tier: ~8-10 minutes for 1000 companies

**Recommendation**: Upgrade to Premium ($30/month) as prerequisite before Dask parallelization

---

## Implementation Recommendations

### Phase 1: Optimization (Weeks 1-4) - RECOMMENDED START

**Goal**: Maximize current single-worker efficiency

**Tasks**:

1. **Add SEC Data Caching** (2 days)
   ```python
   # Cache company_tickers.json locally
   # Benefits: 500ms saved per duplicate ticker
   # Impact: 10-20% improvement for typical runs
   ```

2. **Implement Local Dask Testing** (3 days)
   ```python
   # Create test suite: dask vs prefect performance
   # Benchmark XBRL parsing (CPU-bound opportunity)
   # Measure actual speedup on your data
   ```

3. **Upgrade Alpha Vantage** (1 hour)
   - Purchase Premium tier ($30/month)
   - Enables parallel AV calls (120/min)
   - Immediate 10x throughput improvement

4. **Async SEC Calls** (3 days)
   ```python
   # Use aiohttp for concurrent-but-rate-limited calls
   # Maintains SEC rate compliance while reducing wall time
   # Expected: 2-3x improvement
   ```

**Estimated Cost**: $30/month (AV) + dev time  
**Expected Gain**: 3-5x throughput improvement  
**Payoff**: Worth it before spending on Dask infrastructure

---

### Phase 2: Local Dask Implementation (Weeks 5-8) - IF PHASE 1 SUCCESSFUL

**Goal**: Enable multi-machine processing for batch workloads

**Prerequisites**:
- Phase 1 complete (caching, async, Premium AV)
- Workload requires >500 companies per run
- Available infrastructure to run worker nodes

**Architecture**:

```yaml
# Enhanced docker-compose.yml
services:
  dask-scheduler:
    image: "dask/dask:latest"
    ports:
      - "8786:8786"
      - "8787:8787"
    command: dask-scheduler

  dask-worker-1:
    image: "dask/dask:latest"
    command: dask-worker tcp://dask-scheduler:8786
    depends_on:
      - dask-scheduler
    environment:
      PYTHONUNBUFFERED: 1

  dask-worker-2:
    image: "dask/dask:latest"
    command: dask-worker tcp://dask-scheduler:8786
    depends_on:
      - dask-scheduler
```

**Implementation Steps**:

1. Create `/src/dask_tasks.py`
   - Wrapper functions for Dask execution
   - Rate-limit-aware batch processing
   - Monitoring and logging

2. Modify `/src/main.py`
   - Add `--use-dask` flag
   - Scale XBRL parsing across workers
   - Monitor cluster health

3. Add `/deploy/kubernetes/dask-deployment.yaml`
   - Kubernetes DaemonSet for workers
   - Auto-scaling based on CPU
   - Persistent storage for results

4. Document in `/docs/DASK_SETUP.md`
   - Cluster configuration guide
   - Performance tuning parameters
   - Cost optimization strategies

**Timeline**: 3-4 weeks  
**Cost**: Infrastructure costs (depends on deployment)
- Self-hosted: $50-200/month (2-4 EC2 instances)
- Kubernetes: $0-100/month (shared cluster)

**Expected Gains**:
- 4-core local Dask: 2-3x faster
- 10-worker cluster: 8-10x faster
- Bottleneck: Still SEC rate limit (1 req/sec)

---

### Phase 3: Coiled Managed Service (Weeks 9-12) - IF PHASE 2 SUCCESSFUL

**Goal**: Enterprise-scale distributed processing with minimal ops overhead

**Prerequisites**:
- Phase 2 successful (Dask working locally)
- Volume justifies managed service cost
- AWS account with proper permissions

**Setup**:

```python
# src/coiled_tasks.py
import coiled
from prefect import task

@task
def process_with_coiled(companies_df, n_workers=20):
    """Auto-scaling Dask cluster on AWS"""
    
    cluster = coiled.Cluster(
        name="finance-techstack",
        n_workers=n_workers,
        worker_memory="4GB",
        scheduler_memory="8GB",
        region="us-west-2",
        spot_instances=True,  # 70% cost savings
        auto_shutdown=True,   # Stop after idle period
    )
    
    with cluster.get_client() as client:
        # Your distributed work here
        results = bulk_process(companies_df, client)
    
    return results
```

**Implementation Steps**:

1. Create Coiled account (~$300/month business tier)
2. Set up AWS IAM credentials
3. Test with pilot batch (1000 companies)
4. Create Prefect deployment that auto-selects Coiled for large runs
5. Document ops procedures

**Deployment Pattern**:
```python
@flow
def aggregate_financial_data(tickers: list):
    if len(tickers) > 1000:
        # Auto-select Coiled for large batches
        return process_with_coiled(tickers)
    else:
        # Use local Prefect for small batches
        return process_locally(tickers)
```

**Cost Analysis**:
- Coiled subscription: $100-300/month (business tier)
- AWS EC2 spot instances: $0.50-2 per run
- Total: $200-400/month + usage

**Expected Gains**:
- Auto-scaling 5-50 workers based on load
- Spot instances: 70% AWS cost savings
- Fully managed: No ops overhead
- Integrated monitoring/dashboards

---

## Recommendation Summary

### For Current Project (100-1000 companies annually):

✓ **NOT RECOMMENDED** to implement Dask/Coiled yet

**Reasons**:
1. Single Prefect worker is sufficient
2. SEC API rate limit is the real constraint
3. Infrastructure cost not justified
4. Complexity overhead not worth it

**Instead, invest in**:
1. ✓ SEC data caching (500ms savings)
2. ✓ Alpha Vantage Premium upgrade ($30/month)
3. ✓ Async SEC requests (2-3x improvement)
4. ✓ Code optimization (10-20% improvements)

**Expected**: 3-5x current throughput at $30/month cost

---

### For Growth Scenarios (5,000+ companies annually):

✓ **CONSIDER** Phase 1 + Phase 2 (Local Dask)

**When to implement**:
- Processing >500 companies per batch
- Running scheduled jobs weekly+
- Infrastructure budget available ($50-200/month)
- Team has DevOps capacity

**Timeline**: 6-8 weeks  
**Cost**: $30/month (AV) + $50-200/month (infrastructure)  
**Gain**: 4-10x throughput improvement

---

### For Enterprise Scale (100,000+ companies, real-time):

✓ **IMPLEMENT** All three phases

**When to implement**:
- Need <5 minute latency for 10k companies
- Real-time analysis requirements
- Dedicated ML/analytics team
- Annual analysis budget >$10k

**Timeline**: 3-4 months (all phases)  
**Cost**: $300-400/month (Coiled) + AWS usage  
**Gain**: On-demand 50-200x throughput with auto-scaling

---

## Technical Debt Considerations

### Before Adding Dask, Address:

1. **API Resilience** (Critical)
   - Current: Basic retry logic
   - Needed: Circuit breakers, exponential backoff
   - Dask amplifies failures if API handling poor

2. **Error Propagation** (Critical)
   - Current: Logs errors, continues
   - Needed: Structured error tracking
   - Dask requires clear success/failure semantics

3. **Memory Management** (High)
   - Current: Loads all company tickers in RAM
   - Needed: Streaming/chunked processing
   - Dask workers need bounded memory usage

4. **Data Consistency** (High)
   - Current: Single-writer model
   - Needed: Distributed write coordination
   - Multiple workers writing Parquet files requires careful handling

5. **Monitoring** (Medium)
   - Current: Prefect server logs
   - Needed: Cluster-wide metrics, dashboards
   - Dask requires distributed tracing

### Suggested Improvements (Pre-Dask):

```python
# 1. Circuit breaker for SEC API
from circuitbreaker import circuit

@circuit(failure_threshold=5, recovery_timeout=300)
def fetch_sec_filing_safe(cik, form_type):
    return fetch_sec_filing(cik, form_type)

# 2. Structured error tracking
from prefect import get_run_logger

logger = get_run_logger()
try:
    result = process_ticker(ticker)
except APIError as e:
    logger.error("API error", extra={
        "ticker": ticker,
        "error_code": e.code,
        "retry_after": e.retry_after
    })

# 3. Generator-based chunking
def process_companies_chunked(tickers, chunk_size=100):
    for i in range(0, len(tickers), chunk_size):
        yield tickers[i:i+chunk_size]

# 4. Distributed write coordination
import pyarrow.parquet as pq

def save_distributed_parquet(df, base_path):
    # Use partition columns to avoid conflicts
    df.to_parquet(
        base_path,
        partition_cols=['date'],
        flavor='pyarrow'
    )
```

---

## Next Steps

### Immediate (This Week):

1. ✓ Share this document with team
2. ✓ Decide on Phase 1 investment ($30/month AV upgrade)
3. ✓ Plan async SEC implementation (2-3 days)

### Short-term (Next 30 days):

1. Implement Phase 1 improvements
2. Measure actual improvements with profiling
3. Assess if Phase 2 is justified by volume

### Medium-term (Q1 2026):

1. Revisit decision based on usage patterns
2. If volume justifies, start Phase 2 planning
3. Create Dask testing suite in docker-compose

### Long-term (Q2+ 2026):

1. Evaluate Coiled when Dask proven beneficial
2. Build auto-scaling deployment patterns
3. Migrate to managed service if ROI clear

---

## Conclusion

Your current architecture is well-designed for small-to-medium scale financial data aggregation. Dask and Coiled are powerful tools, but they add significant complexity and cost.

**Strategic Guidance**:

1. **First**: Optimize the single-worker path (Phase 1)
   - Low cost ($30/month)
   - 3-5x improvement
   - Foundation for future scaling

2. **Second**: Monitor usage patterns for 6+ months
   - Understand true workload characteristics
   - Identify real bottlenecks
   - Build business case for scaling

3. **Third**: If volume justifies, implement Dask incrementally
   - Start with local testing (Phase 2)
   - Move to managed service only if proven beneficial
   - Don't overengineer early

The "right" architecture depends on your actual usage patterns, which will become clear after Phase 1 optimization and 6 months of production operation.

---

## References & Resources

### Official Documentation
- [Dask Documentation](https://docs.dask.org/)
- [Coiled Documentation](https://coiled.io/docs/)
- [Prefect Documentation](https://docs.prefect.io/)
- [SEC EDGAR API](https://www.sec.gov/developer)

### Useful Libraries
- `dask[distributed]` - Distributed computing
- `coiled` - Managed Dask hosting
- `aiohttp` - Async HTTP client
- `circuitbreaker` - Resilience pattern
- `pyarrow` - Parquet support

### Performance Tools
- `dask.diagnostics.ProgressBar` - Progress tracking
- `dask.base.visualize()` - Task graph visualization
- `coiled.diagnostics` - Cluster monitoring
- `cProfile` - CPU profiling

### Similar Projects
- [Pangeo](https://pangeo.io/) - Dask for climate science
- [Prefect Cloud](https://www.prefect.io/) - Managed Prefect
- [Apache Spark (PySpark)](https://spark.apache.org/) - Alternative distributed framework
