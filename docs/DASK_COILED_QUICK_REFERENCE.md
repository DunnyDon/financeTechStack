# Dask & Coiled Quick Reference

**Document**: Companion to [docs/DASK_COILED_RECOMMENDATIONS.md](docs/DASK_COILED_RECOMMENDATIONS.md)  
**Last Updated**: November 29, 2025

---

## TL;DR - Should You Use Dask/Coiled?

| Volume | Answer | Why |
|--------|--------|-----|
| <100 companies | ❌ No | Prefect alone is optimal |
| 100-1000 companies | ⚠️ Maybe | Optimize Phase 1 first |
| 1000-5000 companies | ✅ Consider | Phase 2 (Local Dask) makes sense |
| 5000-50000 companies | ✅ Yes | Phase 2 or Phase 3 (Coiled) |
| Real-time, always-on | ✅ Yes | Phase 3 (Coiled) essential |

---

## Current Project Assessment

### ✓ Strengths
- Clean Prefect architecture
- Well-tested (33 tests, all passing)
- Containerized and cloud-ready
- Good error handling and retries
- Excellent logging and monitoring

### ⚠️ Bottlenecks
- **SEC API**: 1 request/second hard limit
- **Single worker**: Sequential processing
- **Memory**: All companies loaded into RAM
- **Blocking I/O**: Network calls block execution

### 🎯 Real Constraint
**You're I/O-bound, not CPU-bound.** Dask helps with CPU-bound work.

**Current bottleneck**: SEC API rate limit (1 req/sec) = ~60 companies/minute maximum

---

## Decision Matrix

### Phase 1 Optimization (RECOMMENDED NOW)
✓ Low cost, high impact, do immediately

```python
# Quick wins:
1. Cache SEC company_tickers.json locally (-500ms/duplicate)
2. Upgrade Alpha Vantage Premium ($30/month, +10x throughput)
3. Async SEC requests with rate-limiting (+2-3x throughput)
4. Profile and optimize hot paths (+10-20% improvement)
```

**Expected**: 3-5x throughput, $30/month, 3-4 weeks development

---

### Phase 2: Local Dask (EVALUATE AFTER PHASE 1)
⚠️ Medium cost, measurable benefit, do if workload justifies

**Prerequisites**:
- Phase 1 complete and proven beneficial
- Processing >500 companies per batch regularly
- Infrastructure budget available ($50-200/month)

```python
# Local Dask cluster:
dask_workers = 4-10 nodes
expected_speedup = 4-10x (depends on CPU-bound % of work)
cost = $50-200/month infrastructure
effort = 3-4 weeks implementation
roi_breakeven = When batch time matters more than cost
```

**When**: Implement when Phase 1 benefits plateau

---

### Phase 3: Coiled (ENTERPRISE SCALE)
❌ High cost, significant benefit, do only if volume huge

**Prerequisites**:
- Phase 2 proven successful and valuable
- Volume regularly exceeds 10,000 companies
- Real-time/low-latency requirements
- Managed infrastructure preferred over self-hosted

```python
# Managed Dask on AWS:
auto_scaling = 5-50 workers based on load
spot_instances = 70% cost savings
expected_speedup = 10-50x (but still capped by SEC rate limit)
cost = $300-400/month + AWS usage ($0.50-5 per run)
effort = 1-2 weeks integration (after Phase 2)
roi_breakeven = High-volume, time-sensitive workloads
```

**When**: Implement only for mission-critical workloads

---

## Performance Expectations

### SEC API Rate Limit Reality Check

```
SEC Hard Limit: 1 request/second

Current Throughput:
- Companies: 60/minute = 3600/hour = 86k/day
- With sequential flow: ~1 min per company
- With Dask (4 workers): ~0.25 min per company still bottlenecked by SEC

Key Insight: Even with Dask, you can't exceed SEC's 1 req/sec
Solution: Upgrade to SEC commercial service or use multiple API tokens
```

### Realistic Speedups

| Scenario | Speedup Factor | Reason |
|----------|---|---------|
| Dask local (4 cores) XBRL parsing | 3-4x | CPU-bound work parallels |
| Dask local (4 cores) full pipeline | 1.5-2x | I/O blocking still present |
| Dask + async SEC | 2-3x | Better network utilization |
| Coiled cluster (20 workers) | 5-10x | Network parallelization + CPU |
| Coiled + SEC upgrade | 15-30x | Removes API rate limit |

**Conclusion**: Expect 2-3x improvement without SEC upgrade. 15-30x with SEC upgrade.

---

## Quick Implementation Guide

### Start Here: Phase 1 (This Week)

```bash
# 1. Enable data caching
cat > src/cache.py << 'EOF'
import json
import os
from datetime import datetime, timedelta

CACHE_DIR = ".cache"
CACHE_EXPIRY_DAYS = 7

def cache_get(key):
    cache_file = f"{CACHE_DIR}/{key}.json"
    if os.path.exists(cache_file):
        age = datetime.now() - datetime.fromtimestamp(os.path.getmtime(cache_file))
        if age.days < CACHE_EXPIRY_DAYS:
            with open(cache_file) as f:
                return json.load(f)
    return None

def cache_set(key, value):
    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(f"{CACHE_DIR}/{key}.json", "w") as f:
        json.dump(value, f)
EOF

# 2. Update CIK lookup to use cache
# In src/xbrl.py:
# company_data = cache_get('company_tickers')
# if not company_data:
#     company_data = fetch_company_tickers()
#     cache_set('company_tickers', company_data)

# 3. Upgrade Alpha Vantage
# Visit: https://www.alphavantage.co/premium
# Cost: $29.99/month
# Benefit: 120 calls/min instead of 5 calls/min

# 4. Measure improvement
python -m timeit -n 1 -r 1 'from src.main import aggregate_financial_data; aggregate_financial_data(["AAPL", "MSFT", "GOOGL"])'

# 5. Profile code
python -m cProfile -s cumtime -m src.main > profile.txt
# Review profile.txt for bottlenecks
```

---

### If Volume Justifies: Phase 2 (Month 2-3)

```python
# docker-compose.yml addition
dask-scheduler:
  image: dask/dask:latest
  ports:
    - "8786:8786"
  command: dask-scheduler

dask-worker:
  image: dask/dask:latest
  command: dask-worker tcp://dask-scheduler:8786
  deploy:
    replicas: 4  # Scale this number

# src/dask_tasks.py
from dask.distributed import Client
from prefect import task

@task
def batch_xbrl_parse(filings_list):
    with Client("tcp://dask-scheduler:8786") as client:
        futures = client.map(parse_xbrl, filings_list)
        return client.gather(futures)
```

---

### If Enterprise Scale: Phase 3 (Month 3-4)

```python
# pip install coiled

import coiled

@task
def process_with_coiled(df, n_workers=20):
    with coiled.Cluster(
        n_workers=n_workers,
        region="us-west-2",
        spot_instances=True  # 70% savings
    ) as cluster:
        with cluster.get_client() as client:
            # Distributed work here
            pass
```

---

## Cost Breakdown

### Current Setup
- Prefect: $0 (self-hosted)
- Alpha Vantage: $0 (free tier) 
- **Total**: $0/month

### After Phase 1
- Prefect: $0
- Alpha Vantage: $30 (premium tier)
- Infrastructure: $0 (laptop)
- **Total**: $30/month | **Speedup**: 3-5x

### After Phase 2 (Local Dask)
- Prefect: $0
- Alpha Vantage: $30
- Infrastructure: $50-200 (EC2/GCP)
- **Total**: $80-230/month | **Speedup**: 4-10x

### After Phase 3 (Coiled)
- Prefect: $0
- Alpha Vantage: $30 (or $80 premium)
- Coiled: $300/month (business tier)
- AWS: $0.50-5 per run
- **Total**: $330-415/month | **Speedup**: 10-50x

---

## Common Mistakes to Avoid

❌ **Don't**: Add Dask before optimizing Phase 1  
✓ **Do**: Implement caching, async, and profiling first

❌ **Don't**: Try to exceed SEC API rate limit  
✓ **Do**: Accept 60 companies/minute unless SEC account upgraded

❌ **Don't**: Use Coiled without Phase 2 validation  
✓ **Do**: Prove Dask benefits in docker-compose first

❌ **Don't**: Allocate unlimited workers  
✓ **Do**: Right-size workers based on data (4-20 typical)

❌ **Don't**: Store Parquet results directly from workers  
✓ **Do**: Aggregate results in driver, then save

---

## Success Criteria by Phase

### Phase 1: Optimization
- ✓ Data caching implemented
- ✓ Alpha Vantage upgraded
- ✓ Async SEC requests working
- ✓ 3-5x improvement demonstrated
- ✓ Profiling shows CPU time reduced

### Phase 2: Local Dask
- ✓ docker-compose includes Dask services
- ✓ 4-10 core benchmark proves 2-3x improvement
- ✓ Error handling and retries working
- ✓ Test suite passes with Dask enabled
- ✓ Production deployment tested

### Phase 3: Coiled
- ✓ Coiled account created and working
- ✓ Pilot run (1000 companies) successful
- ✓ Auto-scaling works (5-50 worker range)
- ✓ Cost tracking implemented
- ✓ Production monitoring in place

---

## Testing Your Changes

```bash
# Phase 1 validation
time python -m pytest tests/ -v
# Should show same tests passing, faster execution

# Phase 2 validation
docker-compose up -d
docker-compose run --rm techstack python -c "
from src.dask_tasks import batch_process
results = batch_process(['AAPL', 'MSFT', 'GOOGL'])
print(f'✓ Processed {len(results)} companies with Dask')
"

# Phase 3 validation
python -c "
import coiled
cluster = coiled.Cluster(n_workers=5)
print(f'✓ Coiled cluster created: {cluster}')
cluster.close()
"
```

---

## References

- **Full Research**: [docs/DASK_COILED_RECOMMENDATIONS.md](docs/DASK_COILED_RECOMMENDATIONS.md)
- **Dask Docs**: https://docs.dask.org/
- **Coiled Docs**: https://coiled.io/docs/
- **Prefect Docs**: https://docs.prefect.io/
- **SEC API**: https://www.sec.gov/developer

---

## Decision Flowchart

```
Are you processing 100+ companies regularly?
├─ NO → Stop. Current setup is optimal.
└─ YES → Is SEC API rate limit your bottleneck?
    ├─ NO → Implement Phase 1 (caching, async)
    │       └─ Does 3-5x improvement solve problem?
    │           ├─ YES → Done! Maintain Phase 1.
    │           └─ NO → Proceed to Phase 2
    └─ YES → Upgrade SEC API access
             └─ Does that solve problem?
                 ├─ YES → Done! Use upgraded API.
                 └─ NO → Proceed to Phase 2
```

---

## When to Revisit This Decision

✓ **Revisit in 6 months** - Check actual volume patterns  
✓ **Revisit if batch time exceeds 30 min** - Phase 2 time-to-value high  
✓ **Revisit if volume doubles** - Scaling requirements change  
✓ **Revisit annually** - Cost/benefit analysis

---

## Next Action

**What to do now**:

1. Read [docs/DASK_COILED_RECOMMENDATIONS.md](docs/DASK_COILED_RECOMMENDATIONS.md) for full context
2. Assess current workload (how many companies/month?)
3. If <1000/month: Implement Phase 1 optimization
4. If 1000-10000/month: Plan Phase 2 after Phase 1
5. If 10000+/month: Evaluate Phase 3 (Coiled)

**Questions**?

- Check the full recommendations document
- Review SEC API documentation
- Benchmark locally before investing in infrastructure
