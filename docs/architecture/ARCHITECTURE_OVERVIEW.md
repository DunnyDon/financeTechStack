# System Architecture Overview

High-level architecture of Finance TechStack.

---

## System Components

```
┌─────────────────────────────────────────────────────────────┐
│                    FINANCE TECHSTACK                         │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────────┐  ┌──────────────────┐                 │
│  │  FRONTEND LAYER  │  │  DATA SOURCES    │                 │
│  ├──────────────────┤  ├──────────────────┤                 │
│  │ Streamlit App    │  │ SEC EDGAR        │                 │
│  │ - Dashboard      │  │ NewsAPI          │                 │
│  │ - Analytics      │  │ Finnhub          │                 │
│  │ - Backtesting    │  │ Alpha Vantage    │                 │
│  │ - Visualization  │  │ Yahoo Finance    │                 │
│  │                  │  │ CoinGecko        │                 │
│  │ Port: 8501       │  │ Open-Meteo       │                 │
│  └──────────────────┘  └──────────────────┘                 │
│         │                      │                             │
│         └──────────┬───────────┘                             │
│                    │                                         │
│  ┌─────────────────▼─────────────────┐                      │
│  │   ORCHESTRATION & FLOWS (Prefect)  │                      │
│  ├────────────────────────────────────┤                      │
│  │ Portfolio Flows:                    │                      │
│  │ - aggregate_financial_data_flow     │                      │
│  │ - portfolio_analysis_flow           │                      │
│  │ - portfolio_end_to_end_flow         │                      │
│  │                                      │                      │
│  │ Analytics Flows:                    │                      │
│  │ - enhanced_analytics_flow           │                      │
│  │ - advanced_analytics_flow           │                      │
│  │ - news_informed_analytics_flow      │                      │
│  │                                      │                      │
│  │ Dask Flows:                         │                      │
│  │ - dask_aggregate_financial_data     │                      │
│  │ - dask_batch_security_analysis      │                      │
│  │                                      │                      │
│  │ Email Flows:                        │                      │
│  │ - send_report_email_flow            │                      │
│  └────────────────────────────────────┘                      │
│         │         │         │         │                      │
│         ▼         ▼         ▼         ▼                      │
│  ┌─────────────────────────────────────┐                     │
│  │    CORE ANALYTICS MODULES           │                     │
│  ├─────────────────────────────────────┤                     │
│  │ Price Fetcher      (multi-source)   │                     │
│  │ Technical Analyzer (RSI, BB, EMA)   │                     │
│  │ Fundamental Analyzer (SEC XBRL)     │                     │
│  │ FX Rates           (currency conv)  │                     │
│  │ Portfolio Analytics (P&L, metrics)  │                     │
│  │ News Sentiment     (NLP scoring)    │                     │
│  │ Options Analysis   (Greeks, IV)     │                     │
│  │ Fixed Income       (duration)       │                     │
│  │ Quick Wins         (signals)        │                     │
│  └─────────────────────────────────────┘                     │
│         │                                                    │
│  ┌──────▼───────────────────────────────┐                   │
│  │   PERFORMANCE LAYER (Dask)           │                   │
│  ├───────────────────────────────────────┤                   │
│  │ Parallel Processing:                  │                   │
│  │ - Data backfill (6x faster)           │                   │
│  │ - Batch analysis                      │                   │
│  │ - Distributed calculations            │                   │
│  │                                        │                   │
│  │ 4-8 worker processes                  │                   │
│  └───────────────────────────────────────┘                   │
│         │                                                    │
│  ┌──────▼──────────────────────────────┐                    │
│  │   DATA STORAGE LAYER                 │                   │
│  ├───────────────────────────────────────┤                   │
│  │ ParquetDB (Apache Parquet):           │                   │
│  │ ├─ prices/                            │                   │
│  │ ├─ technical_analysis/                │                   │
│  │ ├─ fundamental_analysis/              │                   │
│  │ ├─ sec_filings/                       │                   │
│  │ ├─ xbrl_filings/                      │                   │
│  │ ├─ fx_rates/                          │                   │
│  │ ├─ cache/                             │                   │
│  │ └─ backtesting/                       │                   │
│  │                                        │                   │
│  │ Features:                             │                   │
│  │ - Snappy compression                  │                   │
│  │ - Partitioned by timestamp            │                   │
│  │ - Time-series optimized               │                   │
│  │ - Python/Arrow native                 │                   │
│  └───────────────────────────────────────┘                   │
│         │                                                    │
│  ┌──────▼──────────────────────────────┐                    │
│  │   CACHING LAYER                      │                   │
│  ├───────────────────────────────────────┤                   │
│  │ In-Memory Cache:                      │                   │
│  │ - 60-second TTL for prices            │                   │
│  │ - Configurable per module             │                   │
│  │ - Thread-safe operations              │                   │
│  └───────────────────────────────────────┘                   │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

---

## Data Flow Diagram

```
Holdings.csv → Portfolio Holdings Module
                    ↓
            [Load positions]
                    ↓
    ┌───────────────┼───────────────┐
    ▼               ▼               ▼
 Price Fetch   SEC CIK Lookup   FX Rates
    ▼               ▼               ▼
[Fetch prices] [Fetch XBRL]   [Convert]
    │               │               │
    └───────────────┼───────────────┘
                    ▼
            [Cache & Store]
                    ▼
            ParquetDB (Prices, Fundamentals, FX)
                    ▼
        [Dask: Parallel Processing]
                    ▼
    ┌──────────────┬──────────────┐
    ▼              ▼              ▼
Technical     Fundamental    Risk Analysis
Analysis      Analysis       (VaR, Beta, HHI)
    │              │              │
    └──────────────┼──────────────┘
                   ▼
            [Portfolio Analytics]
                   ▼
    ┌──────────────┬──────────────┐
    ▼              ▼              ▼
Dashboard   Email Report    Backtesting
```

---

## Technology Stack

### Backend
- **Python 3.13** - Core language
- **Prefect 3.x** - Workflow orchestration with retries
- **Dask** - Parallel processing (6x speedup)
- **Pandas/NumPy** - Data manipulation
- **SciPy/scikit-learn** - Scientific computing
- **PyArrow** - Parquet support

### Frontend
- **Streamlit** - Interactive UI framework
- **Plotly** - Interactive charts
- **Custom CSS** - Styling

### Data Storage
- **Apache Parquet** - Columnar storage
- **Snappy** - Compression codec
- **Partitioned** - By timestamp for efficiency

### External APIs
- **SEC EDGAR** - Company filings
- **NewsAPI** - News aggregation
- **Finnhub** - Real-time quotes
- **Alpha Vantage** - Historical prices
- **CoinGecko** - Crypto prices
- **Open-Meteo** - FX rates

---

## Request Flow

### Portfolio Analytics Request (typical)

1. **User initiates** (Dashboard or command line)
2. **Prefect Flow starts** with task graph
3. **Load Holdings** from CSV
4. **Fetch Data in Parallel** (Dask):
   - Price data from multiple sources
   - SEC CIK and XBRL fundamentals
   - FX rates for conversions
   - News sentiment
5. **Cache Results** (60-second TTL)
6. **Calculate Analytics**:
   - Technical indicators
   - Risk metrics (VaR, beta, HHI)
   - Portfolio optimization
   - Trading signals
7. **Store Results** to ParquetDB
8. **Generate Report**:
   - Dashboard visualization
   - Email with HTML formatting
   - Backtesting results
9. **Return to User**

**Total Time:** 2-10 seconds depending on data freshness

---

## Scaling Architecture

### Horizontal Scaling
- **Dask Cluster** - Multiple worker nodes
- **Kubernetes** - Container orchestration
- **AWS ECS** - Container service

### Vertical Scaling
- **More Dask workers** - Parallelism increase
- **Larger instances** - More memory/CPU
- **TimescaleDB** - Time-series database for large datasets

### Current Performance
- Dashboard load: <2 seconds
- Backfill speed: 0.5 seconds/6 tickers (4 workers)
- Data freshness: 60-second cache
- Supports: 50+ portfolio holdings

---

## Deployment Options

### Local Development
```bash
uv sync
uv run streamlit run app.py
```

### Docker
```bash
docker build -t techstack:latest .
docker run -p 8501:8501 techstack:latest
```

### Kubernetes
```bash
kubectl apply -f deploy/kubernetes/
```

### AWS ECS
```bash
./deploy/aws-ecs-deploy.sh
```

---

## Monitoring & Observability

### Current
- ✅ Prefect flow dashboards
- ✅ Test coverage (21+ test files)
- ✅ Application logging

### Planned
- [ ] Structured logging (CloudWatch)
- [ ] Distributed tracing (Jaeger)
- [ ] Performance monitoring (Datadog)
- [ ] Custom alerts

---

## Error Handling

### Built-in Features
- Task retries (3x with backoff)
- Fallback data sources
- Rate limiting compliance
- Graceful degradation

### Recovery
- Dead-letter queues for failed tasks
- Data validation at each stage
- Automatic backfill of missing data
- Historical data archives

---

## Future Enhancements

1. **Real-time Database** - TimescaleDB for large-scale
2. **API Gateway** - FastAPI for external integrations
3. **Message Queue** - RabbitMQ for reliability
4. **Caching Layer** - Redis for performance
5. **ML Integration** - Adaptive signals and predictions
6. **Distributed Dask** - Multi-node clusters

See `docs/FUTURE_WORK.md` for roadmap details.
