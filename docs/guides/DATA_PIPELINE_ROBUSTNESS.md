# Data Pipeline Robustness Guide

## Overview

Reliable, maintainable data pipelines with validation, automatic retries, error handling, and complete audit trails. Build production-grade data systems that recover from failures gracefully.

## Core Concepts

### 1. **Data Validation**
- Schema validation at pipeline boundaries
- Business rule validation (ranges, formats, relationships)
- Custom validation functions
- Severity levels (critical, warning, info)

### 2. **Automatic Retries**
- Exponential backoff strategy
- Linear backoff strategy
- Fixed delay strategy
- Jitter to prevent thundering herd

### 3. **Dead-Letter Queue (DLQ)**
- Capture failed records
- Automatic retry logic
- Persistent storage for investigation
- Manual recovery workflows

### 4. **Data Lineage**
- Track data transformations
- Record input/output hashes
- Audit trail for compliance
- End-to-end visibility

## Quick Start

### Schema Validation

```python
from src.data_pipeline_robustness import DataValidator, DataValidationRule, ValidationLevel
import pandas as pd

# Create validator
validator = DataValidator()

# Add rules
validator.add_rule(DataValidationRule(
    name='ticker_required',
    rule_type='required',
    column='ticker',
    level=ValidationLevel.CRITICAL
))

validator.add_rule(DataValidationRule(
    name='price_range',
    rule_type='range',
    column='price',
    parameters={'min': 0.01, 'max': 100000},
    level=ValidationLevel.CRITICAL
))

# Validate DataFrame
df = pd.DataFrame({
    'ticker': ['AAPL', 'MSFT', None],
    'price': [150.0, 300.0, 50.0]
})

result = validator.validate_dataframe(df, stage='data_ingestion')
print(f"Valid: {result.valid_records}/{result.total_records}")
print(f"Pass rate: {result.pass_rate:.1%}")

if not result.is_passed:
    print(f"Errors: {result.errors}")
    print(f"Failed rows: {result.failed_row_indices}")
```

### Automatic Retries

```python
from src.data_pipeline_robustness import RetryHandler, RetryPolicy, RetryStrategy
import time

# Configure retry policy
policy = RetryPolicy(
    max_attempts=3,
    strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
    initial_delay_seconds=1.0,
    max_delay_seconds=30.0,
    multiplier=2.0,
    jitter=True
)

handler = RetryHandler(policy)

# Function that might fail
call_count = [0]

def flaky_api_call():
    call_count[0] += 1
    if call_count[0] < 3:
        raise ConnectionError('Temporary network issue')
    return {'status': 'success', 'data': [1, 2, 3]}

# Execute with automatic retries
try:
    result = handler.execute_with_retry(flaky_api_call)
    print(f"Success after {call_count[0]} attempts: {result}")
except Exception as e:
    print(f"Failed after all retries: {e}")

# View retry history
for attempt in handler.retry_history:
    print(f"Attempt {attempt['attempt']}: {attempt['status']}")
```

### Dead-Letter Queue

```python
from src.data_pipeline_robustness import DeadLetterQueue, PipelineRecord
from datetime import datetime

# Create DLQ
dlq = DeadLetterQueue(name='sec_filings_dlq', max_retries=3)

# Create failed record
record = PipelineRecord(
    record_id='sec-123456',
    data={'ticker': 'AAPL', 'filing_date': '2024-01-15'},
    timestamp=datetime.now(),
    stage='sec_data_enrichment',
    error='Failed to fetch fundamental data'
)

# Enqueue failed record
dlq.enqueue(record)

# Process queue with handler function
def retry_handler(record):
    try:
        # Attempt to reprocess
        result = fetch_fundamentals(record.data['ticker'])
        return True  # Success
    except Exception as e:
        print(f"Retry failed: {e}")
        return False

stats = dlq.process_queue(retry_handler)
print(f"Processed: {stats['processed']}, Succeeded: {stats['succeeded']}")

# Export failed records for investigation
dlq.export_to_parquet('db/dead_letter_queues')
```

### Data Lineage Tracking

```python
from src.data_pipeline_robustness import DataLineageTracker
from datetime import datetime
import time

tracker = DataLineageTracker()

# Record transformation
start = time.time()
input_data = {'ticker': 'AAPL', 'price': 150.0}
output_data = {'ticker': 'AAPL', 'price': 150.0, 'pe_ratio': 28.5}
duration = (time.time() - start) * 1000

tracker.record_transformation(
    record_id='rec-123',
    source='raw_prices',
    destination='enriched_data',
    transformation='enrich_with_fundamentals',
    input_data=input_data,
    output_data=output_data,
    duration_ms=duration,
    status='success'
)

# Get lineage for record
lineage = tracker.get_record_lineage('rec-123')
for entry in lineage:
    print(f"{entry.source} → {entry.destination}: {entry.duration_ms:.1f}ms")

# Export lineage for audit trail
tracker.export_lineage('db/data_lineage')
```

## Validation Rules

### Rule Types

```python
# 1. Required field
DataValidationRule(
    name='ticker_required',
    rule_type='required',
    column='ticker'
)

# 2. Type validation
DataValidationRule(
    name='price_is_float',
    rule_type='type',
    column='price',
    parameters={'type': float}
)

# 3. Range validation
DataValidationRule(
    name='price_in_range',
    rule_type='range',
    column='price',
    parameters={'min': 0.01, 'max': 100000}
)

# 4. Regex pattern
DataValidationRule(
    name='ticker_format',
    rule_type='regex',
    column='ticker',
    parameters={'pattern': r'^[A-Z]{1,5}$'}
)

# 5. Custom function
def is_trading_day(date_str):
    # Check if not weekend
    from datetime import datetime
    date = datetime.strptime(date_str, '%Y-%m-%d')
    return date.weekday() < 5

DataValidationRule(
    name='trading_day',
    rule_type='custom',
    column='date',
    parameters={'function': is_trading_day},
    message='Date must be trading day'
)
```

### Validation Levels

```python
# Critical: Pipeline stops if this fails
DataValidationRule(
    'ticker_required',
    'required',
    'ticker',
    level=ValidationLevel.CRITICAL
)

# Warning: Log warning but continue
DataValidationRule(
    'price_reasonable',
    'range',
    'price',
    parameters={'min': 0, 'max': 10000},
    level=ValidationLevel.WARNING
)

# Info: Informational only
DataValidationRule(
    'future_price',
    'custom',
    'date',
    parameters={'function': lambda d: d > datetime.now()},
    level=ValidationLevel.INFO
)
```

## Retry Strategies

### Exponential Backoff

```python
from src.data_pipeline_robustness import RetryPolicy, RetryStrategy

policy = RetryPolicy(
    strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
    initial_delay_seconds=1.0,
    multiplier=2.0,
    max_delay_seconds=60.0
)

# Delays: 1s, 2s, 4s, 8s, 16s, 32s, 60s (capped)
```

**Use case:** Network calls, API requests (common transient failures)

### Linear Backoff

```python
policy = RetryPolicy(
    strategy=RetryStrategy.LINEAR_BACKOFF,
    initial_delay_seconds=2.0
)

# Delays: 2s, 4s, 6s, 8s, 10s...
```

**Use case:** Database locks, resource contention

### Fixed Delay

```python
policy = RetryPolicy(
    strategy=RetryStrategy.FIXED_DELAY,
    initial_delay_seconds=5.0
)

# Delays: 5s, 5s, 5s, 5s...
```

**Use case:** Rate-limited APIs, polling

## Pipeline Stages

### Custom Pipeline Stage

```python
from src.data_pipeline_robustness import PipelineStage
import pandas as pd

class DataEnrichmentStage(PipelineStage):
    """Enrich data with additional information."""
    
    def process(self, data):
        if not isinstance(data, pd.DataFrame):
            raise ValueError('Expected DataFrame')
        
        # Add fundamental metrics
        data['pe_ratio'] = fetch_pe_ratios(data['ticker'])
        data['dividend_yield'] = fetch_dividends(data['ticker'])
        
        return data

# Use stage
stage = DataEnrichmentStage(
    name='enrichment',
    validator=validator,
    retry_policy=policy,
    dlq=dlq
)

enriched = stage.execute(data)
```

## Schema Validation

```python
from src.data_pipeline_robustness import validate_schema

schema = {
    'ticker': 'object',
    'price': 'float64',
    'volume': 'int64',
    'date': 'object'
}

df = pd.DataFrame({
    'ticker': ['AAPL'],
    'price': [150.0],
    'volume': [1000000],
    'date': ['2024-01-15']
})

is_valid, errors = validate_schema(df, schema)

if not is_valid:
    print(f"Schema errors: {errors}")
```

## Complete Pipeline Example

```python
from src.data_pipeline_robustness import (
    DataValidator, DataValidationRule, RetryHandler, RetryPolicy,
    DeadLetterQueue, DataLineageTracker, PipelineStage, ValidationLevel
)
from datetime import datetime
import pandas as pd

# 1. Setup components
validator = DataValidator()
validator.add_rule(DataValidationRule(
    'ticker_required', 'required', 'ticker', level=ValidationLevel.CRITICAL
))
validator.add_rule(DataValidationRule(
    'price_range', 'range', 'price',
    parameters={'min': 0.01, 'max': 100000}, level=ValidationLevel.CRITICAL
))

retry_policy = RetryPolicy(max_attempts=3)
dlq = DeadLetterQueue('price_pipeline', max_retries=3)
lineage = DataLineageTracker()

# 2. Create pipeline stages
class FetchStage(PipelineStage):
    def process(self, tickers):
        # Fetch prices (with retry)
        prices = fetch_prices_from_api(tickers)
        return pd.DataFrame(prices)

class ValidateStage(PipelineStage):
    def process(self, df):
        # Data already validated by stage.execute()
        return df

class EnrichStage(PipelineStage):
    def process(self, df):
        df['pe_ratio'] = [get_pe_ratio(t) for t in df['ticker']]
        return df

# 3. Execute pipeline
fetch = FetchStage('fetch', validator, retry_policy, dlq)
validate = ValidateStage('validate', validator, retry_policy, dlq)
enrich = EnrichStage('enrich', validator, retry_policy, dlq)

try:
    # Fetch prices
    prices_df = fetch.execute(['AAPL', 'MSFT'])
    
    # Validate
    validated_df = validate.execute(prices_df)
    
    # Enrich
    enriched_df = enrich.execute(validated_df)
    
    # Record success lineage
    lineage.record_transformation(
        'batch-001',
        'price_api',
        'enriched_prices',
        'complete_pipeline',
        {'count': 2},
        {'count': 2, 'enriched': True},
        100.0,
        'success'
    )
    
except Exception as e:
    # Record failure lineage
    lineage.record_transformation(
        'batch-001',
        'price_api',
        'enriched_prices',
        'complete_pipeline',
        {},
        None,
        50.0,
        'failure',
        str(e)
    )

# 4. Cleanup
dlq.export_to_parquet('db/dlq')
lineage.export_lineage('db/lineage')
```

## Error Handling Patterns

### Pattern 1: Fail Fast

```python
result = validator.validate_dataframe(df, 'ingestion', on_failure='raise')
# Raises if validation fails
```

### Pattern 2: Graceful Degradation

```python
result = validator.validate_dataframe(df, 'ingestion', on_failure='log')
# Logs warnings but continues with valid records
# Access invalid records via result.failed_row_indices
```

### Pattern 3: Dead-Letter Queue

```python
for _, row in df.iterrows():
    try:
        result = process_record(row)
    except Exception as e:
        dlq.enqueue(PipelineRecord(
            record_id=row['id'],
            data=row.to_dict(),
            timestamp=datetime.now(),
            stage='processing',
            error=str(e)
        ))
```

## Monitoring & Alerting

### Key Metrics

```python
# Track validation metrics
validation_result = validator.validate_dataframe(df, 'ingestion')
print(f"Pass rate: {validation_result.pass_rate:.1%}")
print(f"Failed records: {validation_result.invalid_records}")

# Track retry metrics
print(f"Retry attempts: {len(handler.retry_history)}")
successful_retries = sum(
    1 for h in handler.retry_history if h['status'] == 'success'
)
print(f"Successful retries: {successful_retries}")

# Track DLQ metrics
print(f"DLQ depth: {dlq.get_size()}")
print(f"DLQ failures: {len(dlq.failed)}")

# Track lineage metrics
lineage_df = lineage.get_lineage_dataframe()
print(f"Avg transformation time: {lineage_df['duration_ms'].mean():.1f}ms")
print(f"Failure rate: {(lineage_df['status'] == 'failure').sum() / len(lineage_df):.1%}")
```

### Alert Conditions

```python
# Set up alerts
if validation_result.pass_rate < 0.95:
    send_alert(f"Validation pass rate {validation_result.pass_rate:.1%} below 95%")

if dlq.get_size() > 100:
    send_alert(f"DLQ depth: {dlq.get_size()} records")

if lineage_df['duration_ms'].max() > 5000:
    send_alert(f"Slow transformation: {lineage_df['duration_ms'].max():.0f}ms")
```

## Best Practices

### 1. **Validate Early and Often**

```python
# ✅ Validate at pipeline entry
df = pd.read_csv('data.csv')
result = validator.validate_dataframe(df, 'ingestion')

# Validate after transformation
df_transformed = transform(df)
result = validator.validate_dataframe(df_transformed, 'transformation')
```

### 2. **Use Appropriate Retry Strategy**

```python
# ✅ Exponential for transient network issues
policy = RetryPolicy(strategy=RetryStrategy.EXPONENTIAL_BACKOFF)
result = handler.execute_with_retry(api_call)

# Fixed delay for rate-limited APIs
policy = RetryPolicy(strategy=RetryStrategy.FIXED_DELAY)
result = handler.execute_with_retry(rate_limited_api)
```

### 3. **Capture Complete Context**

```python
# ✅ Rich error information
record = PipelineRecord(
    record_id=f'{ticker}_{date}',
    data=row.to_dict(),
    timestamp=datetime.now(),
    stage='enrichment',
    attempt=attempt_num,
    error=f'API timeout after {timeout}ms',
    validation_errors=validation_errors
)
dlq.enqueue(record)
```

### 4. **Monitor Pipeline Health**

```python
# ✅ Track key metrics
lineage_df = lineage.get_lineage_dataframe()
success_rate = (lineage_df['status'] == 'success').sum() / len(lineage_df)
avg_duration = lineage_df['duration_ms'].mean()

if success_rate < 0.95:
    logger.warning(f"Pipeline health: {success_rate:.1%}")
```

## Troubleshooting

### Issue: Validation too strict
- **Solution:** Use WARNING level instead of CRITICAL, or adjust thresholds

### Issue: Retry delays too long
- **Solution:** Reduce initial_delay_seconds or max_delay_seconds

### Issue: DLQ growing too fast
- **Solution:** Investigate underlying issue, increase max_retries, or improve handler

### Issue: Slow lineage tracking
- **Solution:** Sample records, batch exports, or use async tracking

## Advanced Patterns

### Pattern: Conditional Retry

```python
def smart_retry(func, data):
    handler = RetryHandler(RetryPolicy(max_attempts=3))
    
    try:
        return handler.execute_with_retry(func, data)
    except ConnectionError:
        # Retry connection errors
        return handler.execute_with_retry(func, data)
    except ValueError:
        # Don't retry validation errors
        raise
```

### Pattern: Batch Processing with DLQ

```python
dlq = DeadLetterQueue()

for batch in batches:
    for record in batch:
        try:
            result = process(record)
        except Exception as e:
            dlq.enqueue(PipelineRecord(
                record_id=record['id'],
                data=record,
                timestamp=datetime.now(),
                stage='processing',
                error=str(e)
            ))

# Reprocess failed records
dlq.process_queue(lambda r: process(r.data))
```

## Testing

Comprehensive test coverage (50+ tests):

```bash
pytest tests/test_data_pipeline_robustness.py -v
```

## API Reference

- `DataValidator` - Validate against rules
- `DataValidationRule` - Define validation rules
- `RetryHandler` - Automatic retries with backoff
- `RetryPolicy` - Configure retry behavior
- `DeadLetterQueue` - Manage failed records
- `DataLineageTracker` - Track transformations
- `PipelineStage` - Base class for pipeline stages
- `validate_schema` - Quick schema validation

## See Also

- Observability Guide
- Error Handling Best Practices
- Production Deployment Checklist
