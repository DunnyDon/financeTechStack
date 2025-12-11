# Comprehensive Observability Guide

## Overview

Production-grade observability with structured logging, distributed tracing, performance monitoring, and Prefect flow dashboards. Track system behavior, detect issues, and optimize performance.

## Components

### 1. **Structured Logging**
- JSON-based logging for CloudWatch/ELK ingestion
- Trace and span context propagation
- Structured fields and tags for filtering
- Multi-level logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)

### 2. **Distributed Tracing**
- Jaeger-compatible trace spans
- Parent-child span relationships
- Operation timing and error tracking
- Full request flow visibility

### 3. **Performance Monitoring**
- Real-time metrics collection
- Alert conditions and thresholds
- Metrics persistence to Parquet
- Performance trend analysis

### 4. **Prefect Dashboard Metrics**
- Flow execution tracking
- Task-level performance metrics
- Success/failure rates
- Throughput and latency analysis

## Quick Start

### Basic Structured Logging

```python
from src.observability import StructuredLogger, ServiceType

logger = StructuredLogger('my_application')

# Simple log
logger.info('Data fetch started')

# Log with context
logger.info(
    'User data loaded',
    context={'user_id': 123, 'records': 1000},
    tags={'environment': 'production'}
)

# Log errors with stack trace
try:
    result = fetch_data()
except Exception as e:
    logger.error(
        'Data fetch failed',
        error=e,
        context={'url': 'https://api.example.com/data'}
    )
```

### Distributed Tracing

```python
from src.observability import DistributedTracer, ServiceType

tracer = DistributedTracer(service_name='data-pipeline')

# Start trace span
span = tracer.start_span(
    operation='fetch_company_data',
    service=ServiceType.DATA_FETCH,
    tags={'ticker': 'AAPL', 'source': 'SEC'}
)

try:
    # Do work
    data = fetch_sec_filings('AAPL')
    tracer.finish_span(span, status='success')
except Exception as e:
    tracer.finish_span(span, status='error', error=str(e))
    raise

# Export traces
tracer.export_jaeger('db/tracing')
```

### Performance Monitoring

```python
from src.observability import PerformanceMonitor

monitor = PerformanceMonitor()

# Record metrics
monitor.record_metric(
    'api_latency_ms',
    response_time,
    tags={'endpoint': '/data', 'method': 'GET'}
)

# Check alerts
alerts = monitor.check_alert_conditions(
    'api_latency_ms',
    threshold=500.0,  # ms
    comparison='greater'
)

if alerts:
    print(f"⚠️  {len(alerts)} latency alerts triggered!")

# Save metrics
monitor.save_metrics_to_parquet('db/observability')
```

### Prefect Flow Monitoring

```python
from src.observability import PrefectDashboardMetrics
from datetime import datetime, timedelta

metrics = PrefectDashboardMetrics()

# Record flow execution
start = datetime.now()
# ... run flow ...
end = datetime.now()

metrics.record_flow_execution(
    flow_name='scrape_sec_filings',
    flow_run_id='run-123abc',
    start_time=start,
    end_time=end,
    status='Completed',
    num_tasks=5
)

# Record task execution
metrics.record_task_execution(
    task_name='fetch_company_data',
    flow_run_id='run-123abc',
    start_time=start + timedelta(seconds=1),
    end_time=end - timedelta(seconds=2),
    status='Completed',
    inputs_processed=1000,
    outputs_produced=950
)

# Analyze
health = metrics.get_flow_health()
print(f"Flow success rate: {health['success_rate']:.1%}")

performance = metrics.get_task_performance()
print(f"Avg task duration: {performance['avg_duration_seconds']:.2f}s")

# Save to Parquet
metrics.save_to_parquet('db/prefect_dashboards')
```

## Architecture

### Logging Flow

```
Application Code
    ↓
StructuredLogger (JSON format)
    ↓
Logging Handler (stdout, file, CloudWatch, ELK)
    ↓
Log Aggregation (CloudWatch Logs, ELK Stack)
    ↓
Dashboards & Alerts
```

### Tracing Flow

```
Request Start
    ↓
DistributedTracer.start_span()
    ├─ Create trace_id, span_id
    ├─ Set service type, operation name
    └─ Record start timestamp
    ↓
[ Nested spans for sub-operations ]
    ↓
DistributedTracer.finish_span()
    ├─ Calculate duration
    ├─ Record status/error
    └─ Save to trace storage
    ↓
Export (Jaeger, traces.json, etc.)
```

### Metrics Flow

```
Code Execution
    ↓
PerformanceMonitor.record_metric()
    ├─ Store metric + timestamp
    ├─ Add tags for filtering
    └─ Queue for storage
    ↓
Check Alert Conditions
    ├─ Compare against thresholds
    ├─ Trigger alerts if breached
    └─ Log alert events
    ↓
Persist to Parquet
    ├─ Metrics files (metrics_*.parquet)
    └─ Alerts files (alerts_*.parquet)
```

## Instrumentation Decorators

### @trace_execution

Automatically trace function execution:

```python
from src.observability import trace_execution, DistributedTracer

tracer = DistributedTracer()

@trace_execution(tracer, service=ServiceType.ANALYTICS)
def calculate_portfolio_metrics(holdings):
    # Automatically traced
    return metrics

result = calculate_portfolio_metrics(portfolio)
# Span automatically recorded with duration, status, errors
```

### @monitor_performance

Automatically record performance metrics:

```python
from src.observability import monitor_performance, PerformanceMonitor

monitor = PerformanceMonitor()

@monitor_performance(monitor, metric_prefix='portfolio')
def fetch_prices(tickers):
    # Automatically timed
    return prices

prices = fetch_prices(['AAPL', 'MSFT'])
# Metric recorded: portfolio.fetch_prices = duration_ms
```

## Alert Configuration

### Alert Types

```python
monitor = PerformanceMonitor()

# Latency alerts
monitor.record_metric('request_latency_ms', 450)
alerts = monitor.check_alert_conditions(
    'request_latency_ms',
    threshold=500.0,
    comparison='greater'
)

# Throughput alerts
monitor.record_metric('records_per_second', 800)
alerts = monitor.check_alert_conditions(
    'records_per_second',
    threshold=1000,
    comparison='less'
)

# Error rate alerts
monitor.record_metric('error_rate', 0.05)
alerts = monitor.check_alert_conditions(
    'error_rate',
    threshold=0.01,
    comparison='greater'
)
```

### Alert Severity

- **warning:** Value slightly exceeds threshold (±10%)
- **high:** Value significantly exceeds threshold (>10%)

## Metrics Reference

### Application Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `request_latency_ms` | Gauge | HTTP request response time |
| `database_query_ms` | Gauge | Database query execution time |
| `cache_hit_rate` | Gauge | % of cache hits (0-100) |
| `error_rate` | Gauge | % of requests that error |
| `throughput_rps` | Gauge | Requests per second |

### Pipeline Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `records_processed` | Counter | Total records processed |
| `records_per_second` | Gauge | Processing throughput |
| `pipeline_duration_ms` | Gauge | End-to-end pipeline time |
| `data_quality_score` | Gauge | % of records passing validation |
| `dlq_size` | Gauge | Dead-letter queue depth |

### Prefect Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `flow_duration_seconds` | Gauge | Flow execution time |
| `task_duration_seconds` | Gauge | Task execution time |
| `flow_success_rate` | Gauge | % of flows completed (0-1) |
| `task_throughput` | Gauge | Records per second per task |
| `flow_failure_count` | Counter | Total failed flows |

## CloudWatch Integration

### Setup

```python
from src.observability import setup_logging_to_cloudwatch

setup_logging_to_cloudwatch(
    log_group='/aws/finance-techstack/app',
    log_stream='production'
)

logger.info('Application started')
# Now logs in CloudWatch
```

### CloudWatch Queries

```
# High latency requests
fields @timestamp, latency_ms, endpoint
| filter latency_ms > 1000
| stats count() by endpoint

# Error rate by service
fields @timestamp, service, status
| filter status = "error"
| stats count() as errors by service

# Throughput trend
fields @timestamp, @message
| stats count() as requests by bin(1m)
```

## ELK Stack Integration

### Setup

```python
from src.observability import setup_logging_to_elk

setup_logging_to_elk(
    elasticsearch_host='elasticsearch.example.com',
    elasticsearch_port=9200
)

logger.info('ELK logging configured')
```

### Kibana Dashboards

**Create dashboard with visualizations:**

1. Request Latency Heatmap
   - X-axis: Time
   - Y-axis: Response time buckets
   - Color: Request count

2. Error Rate Trend
   - X-axis: Time
   - Y-axis: Error %
   - Threshold line: Alert level

3. Service Performance
   - Service names: X-axis
   - Avg latency: Y-axis
   - Color by status

## Prefect Dashboard Features

### Flow Health Dashboard

```python
metrics = PrefectDashboardMetrics()

# Load historical data
import pandas as pd
flow_history = pd.read_parquet('db/prefect_dashboards/flow_executions_*.parquet')

# Calculate health metrics
health = metrics.get_flow_health()

# Visualize
import plotly.express as px

fig = px.pie(
    values=[health['success_count'], health['failure_count']],
    names=['Success', 'Failure'],
    title='Flow Success Rate'
)
fig.show()
```

### Task Performance Dashboard

```python
task_summary = metrics.get_task_summary()

# Slowest tasks
slowest = task_summary.nlargest(5, 'duration_seconds')[['task_name', 'duration_seconds']]

# Highest throughput
fastest = task_summary.nlargest(5, 'throughput')[['task_name', 'throughput']]

# Bottlenecks
bottlenecks = task_summary[task_summary['duration_seconds'] > 30]
```

## Best Practices

### 1. **Logging Guidelines**

```python
# ✅ Good: Structured, contextual
logger.info(
    'User authentication successful',
    context={'user_id': 123, 'method': 'oauth'},
    tags={'service': 'auth', 'environment': 'production'}
)

# ❌ Bad: String concatenation, no context
logger.info(f'User {user_id} logged in')
```

### 2. **Tracing Guidelines**

```python
# ✅ Good: Proper error handling
span = tracer.start_span('fetch_data')
try:
    data = api.fetch()
    tracer.finish_span(span, status='success')
except Exception as e:
    tracer.finish_span(span, status='error', error=str(e))
    raise

# ❌ Bad: Silent failures
span = tracer.start_span('fetch_data')
data = api.fetch()  # Exception silently fails span
```

### 3. **Metrics Guidelines**

```python
# ✅ Good: Rich tags for filtering
monitor.record_metric(
    'api_latency_ms',
    time_ms,
    tags={
        'endpoint': '/api/data',
        'method': 'GET',
        'status': 200
    }
)

# ❌ Bad: No context
monitor.record_metric('latency', time_ms)
```

### 4. **Performance Tuning**

```python
# Batch log writes
logger = StructuredLogger('app', output_format='json')

# Use sampling for high-frequency metrics
if random.random() < 0.1:  # Sample 10%
    monitor.record_metric('request_latency', time_ms)

# Archive old traces
tracer.export_jaeger('db/tracing')
# Then delete local memory: tracer.spans = []
```

## Troubleshooting

### Issue: Missing spans in traces
- **Solution:** Ensure tracer.export_jaeger() called after spans finish

### Issue: High memory usage
- **Solution:** Archive traces/metrics periodically, use sampling

### Issue: Slow logging
- **Solution:** Use async handlers, batch writes, sample high-frequency logs

### Issue: Alert fatigue
- **Solution:** Adjust thresholds, add hysteresis, group related alerts

## Example: Complete Observability Setup

```python
from src.observability import (
    StructuredLogger, DistributedTracer, PerformanceMonitor,
    PrefectDashboardMetrics, trace_execution, monitor_performance,
    ServiceType
)
from datetime import datetime, timedelta

# Initialize observability stack
logger = StructuredLogger('data_pipeline')
tracer = DistributedTracer(service_name='finance-pipeline')
monitor = PerformanceMonitor()
prefect_metrics = PrefectDashboardMetrics()

# Instrument pipeline
@trace_execution(tracer, service=ServiceType.PIPELINE)
@monitor_performance(monitor, metric_prefix='pipeline')
def process_data(data):
    logger.info('Starting data processing', context={'records': len(data)})
    
    try:
        # Process data
        result = transform(data)
        
        logger.info(
            'Data processing complete',
            context={'input_records': len(data), 'output_records': len(result)}
        )
        return result
    
    except Exception as e:
        logger.error('Processing failed', error=e)
        raise

# Log flow execution
flow_start = datetime.now()
try:
    data = fetch_data()
    processed = process_data(data)
    flow_end = datetime.now()
    
    prefect_metrics.record_flow_execution(
        flow_name='data_pipeline',
        flow_run_id='run-001',
        start_time=flow_start,
        end_time=flow_end,
        status='Completed',
        num_tasks=2
    )
except Exception as e:
    flow_end = datetime.now()
    prefect_metrics.record_flow_execution(
        flow_name='data_pipeline',
        flow_run_id='run-001',
        start_time=flow_start,
        end_time=flow_end,
        status='Failed',
        num_tasks=2,
        error=str(e)
    )

# Save everything
tracer.export_jaeger('db/tracing')
monitor.save_metrics_to_parquet('db/observability')
prefect_metrics.save_to_parquet('db/prefect_dashboards')
```

## Testing

Comprehensive test coverage (50+ tests):

```bash
pytest tests/test_observability.py -v
```

## API Reference

- `StructuredLogger` - JSON logging
- `DistributedTracer` - Distributed tracing (Jaeger)
- `PerformanceMonitor` - Metrics collection
- `PrefectDashboardMetrics` - Prefect flow tracking
- `@trace_execution` - Decorator for tracing
- `@monitor_performance` - Decorator for metrics

## See Also

- Data Pipeline Robustness Guide
- Monitoring and Alerting
- Production Deployment Guide
