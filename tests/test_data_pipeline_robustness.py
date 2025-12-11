"""
Tests for Data Pipeline Robustness Module

Coverage:
- Data validation at pipeline stages
- Automatic retries with exponential backoff
- Dead-letter queues for failed records
- Data lineage and audit trails
- Schema validation and error handling
- Retry policies and backoff strategies
"""

import pytest
import pandas as pd
import numpy as np
import time
from datetime import datetime
from pathlib import Path

from src.data_pipeline_robustness import (
    DataValidationRule, ValidationResult, RetryPolicy, RetryStrategy,
    PipelineRecord, DataLineageEntry, DataValidator, DeadLetterQueue,
    RetryHandler, DataLineageTracker, PipelineStage, ValidationLevel,
    validate_schema
)


class TestDataValidationRule:
    """Test data validation rules."""
    
    def test_required_rule(self):
        """Test required field validation."""
        rule = DataValidationRule(
            name='require_price',
            rule_type='required',
            column='price',
            level=ValidationLevel.CRITICAL
        )
        
        # Valid: has value
        is_valid, error = rule.validate(100.0)
        assert is_valid is True
        assert error is None
        
        # Invalid: None
        is_valid, error = rule.validate(None)
        assert is_valid is False
        assert 'required' in error.lower()
    
    def test_type_rule(self):
        """Test type validation."""
        rule = DataValidationRule(
            name='price_type',
            rule_type='type',
            column='price',
            parameters={'type': float}
        )
        
        # Valid
        is_valid, error = rule.validate(100.5)
        assert is_valid is True
        
        # Invalid
        is_valid, error = rule.validate("100.5")
        assert is_valid is False
    
    def test_range_rule(self):
        """Test range validation."""
        rule = DataValidationRule(
            name='price_range',
            rule_type='range',
            column='price',
            parameters={'min': 0.0, 'max': 1000.0}
        )
        
        # Valid
        is_valid, _ = rule.validate(500.0)
        assert is_valid is True
        
        # Too low
        is_valid, error = rule.validate(-10.0)
        assert is_valid is False
        
        # Too high
        is_valid, error = rule.validate(1500.0)
        assert is_valid is False
    
    def test_regex_rule(self):
        """Test regex validation."""
        rule = DataValidationRule(
            name='ticker_format',
            rule_type='regex',
            column='ticker',
            parameters={'pattern': r'^[A-Z]{1,5}$'}
        )
        
        # Valid
        is_valid, _ = rule.validate('AAPL')
        assert is_valid is True
        
        # Invalid
        is_valid, _ = rule.validate('aapl123')
        assert is_valid is False
    
    def test_custom_rule(self):
        """Test custom validation function."""
        rule = DataValidationRule(
            name='even_number',
            rule_type='custom',
            column='count',
            parameters={'function': lambda x: x % 2 == 0},
            message='Count must be even'
        )
        
        # Valid
        is_valid, _ = rule.validate(10)
        assert is_valid is True
        
        # Invalid
        is_valid, error = rule.validate(11)
        assert is_valid is False


class TestValidationResult:
    """Test ValidationResult tracking."""
    
    def test_pass_rate_calculation(self):
        """Test pass rate calculation."""
        result = ValidationResult(
            timestamp=datetime.now(),
            stage='data_fetch',
            total_records=100,
            valid_records=95,
            invalid_records=5
        )
        
        assert result.pass_rate == 0.95
        assert result.is_passed is False  # 5 invalid records
    
    def test_all_passed(self):
        """Test when all records pass."""
        result = ValidationResult(
            timestamp=datetime.now(),
            stage='data_fetch',
            total_records=100,
            valid_records=100,
            invalid_records=0
        )
        
        assert result.pass_rate == 1.0
        assert result.is_passed is True
    
    def test_all_failed(self):
        """Test when all records fail."""
        result = ValidationResult(
            timestamp=datetime.now(),
            stage='data_fetch',
            total_records=100,
            valid_records=0,
            invalid_records=100,
            errors=['Error 1', 'Error 2']
        )
        
        assert result.pass_rate == 0.0
        assert result.is_passed is False


class TestDataValidator:
    """Test DataValidator class."""
    
    @pytest.fixture
    def validator(self):
        """Create validator instance."""
        validator = DataValidator()
        validator.add_rule(DataValidationRule(
            'require_ticker', 'required', 'ticker'
        ))
        validator.add_rule(DataValidationRule(
            'price_range', 'range', 'price',
            parameters={'min': 0, 'max': 10000}
        ))
        return validator
    
    def test_validate_valid_record(self, validator):
        """Test validating a valid record."""
        record = {'ticker': 'AAPL', 'price': 150.0}
        is_valid, errors = validator.validate_record(record)
        
        assert is_valid is True
        assert len(errors) == 0
    
    def test_validate_invalid_record(self, validator):
        """Test validating an invalid record."""
        record = {'ticker': None, 'price': 150.0}
        is_valid, errors = validator.validate_record(record)
        
        assert is_valid is False
        assert len(errors) > 0
    
    def test_validate_dataframe(self, validator):
        """Test validating entire DataFrame."""
        df = pd.DataFrame({
            'ticker': ['AAPL', 'MSFT', None],
            'price': [150.0, 300.0, 50.0]
        })
        
        result = validator.validate_dataframe(df, 'test_stage')
        
        assert result.total_records == 3
        assert result.valid_records == 2
        assert result.invalid_records == 1
        assert 3 in result.failed_row_indices  # Row with None ticker
    
    def test_validation_on_failure_raise(self, validator):
        """Test raising on validation failure."""
        df = pd.DataFrame({
            'ticker': [None],
            'price': [150.0]
        })
        
        with pytest.raises(ValueError):
            validator.validate_dataframe(df, 'test', on_failure='raise')
    
    def test_validation_on_failure_log(self, validator):
        """Test logging on validation failure."""
        df = pd.DataFrame({
            'ticker': [None],
            'price': [150.0]
        })
        
        result = validator.validate_dataframe(df, 'test', on_failure='log')
        assert result.invalid_records > 0


class TestRetryPolicy:
    """Test RetryPolicy configurations."""
    
    def test_exponential_backoff(self):
        """Test exponential backoff strategy."""
        policy = RetryPolicy(
            max_attempts=3,
            strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
            initial_delay_seconds=1.0,
            multiplier=2.0,
            jitter=False
        )
        
        delay0 = policy.get_delay(0)
        delay1 = policy.get_delay(1)
        delay2 = policy.get_delay(2)
        
        assert delay0 == 1.0
        assert delay1 == 2.0
        assert delay2 == 4.0
    
    def test_linear_backoff(self):
        """Test linear backoff strategy."""
        policy = RetryPolicy(
            strategy=RetryStrategy.LINEAR_BACKOFF,
            initial_delay_seconds=1.0,
            jitter=False
        )
        
        delay0 = policy.get_delay(0)
        delay1 = policy.get_delay(1)
        delay2 = policy.get_delay(2)
        
        assert delay0 == 1.0
        assert delay1 == 2.0
        assert delay2 == 3.0
    
    def test_fixed_delay(self):
        """Test fixed delay strategy."""
        policy = RetryPolicy(
            strategy=RetryStrategy.FIXED_DELAY,
            initial_delay_seconds=2.0,
            jitter=False
        )
        
        assert policy.get_delay(0) == 2.0
        assert policy.get_delay(5) == 2.0
    
    def test_max_delay_cap(self):
        """Test max delay capping."""
        policy = RetryPolicy(
            strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
            initial_delay_seconds=10.0,
            max_delay_seconds=30.0,
            multiplier=3.0,
            jitter=False
        )
        
        # Without cap: 10 * 3^3 = 270
        # With cap: 30
        assert policy.get_delay(3) == 30.0


class TestRetryHandler:
    """Test RetryHandler with automatic retries."""
    
    def test_successful_first_attempt(self):
        """Test function that succeeds on first attempt."""
        handler = RetryHandler()
        
        def simple_func():
            return 'success'
        
        result = handler.execute_with_retry(simple_func)
        assert result == 'success'
        assert len(handler.retry_history) == 0
    
    def test_eventual_success_after_retries(self):
        """Test function that succeeds after retries."""
        handler = RetryHandler(RetryPolicy(
            max_attempts=3,
            strategy=RetryStrategy.FIXED_DELAY,
            initial_delay_seconds=0.01
        ))
        
        call_count = [0]
        
        def flaky_func():
            call_count[0] += 1
            if call_count[0] < 3:
                raise ValueError('Not ready yet')
            return 'success'
        
        result = handler.execute_with_retry(flaky_func)
        
        assert result == 'success'
        assert call_count[0] == 3
        assert len(handler.retry_history) == 2  # 2 retries before success
    
    def test_exhausted_retries(self):
        """Test function that fails all retries."""
        handler = RetryHandler(RetryPolicy(
            max_attempts=2,
            strategy=RetryStrategy.FIXED_DELAY,
            initial_delay_seconds=0.01
        ))
        
        def always_fails():
            raise RuntimeError('Always fails')
        
        with pytest.raises(RuntimeError):
            handler.execute_with_retry(always_fails)
        
        assert len(handler.retry_history) == 1


class TestDeadLetterQueue:
    """Test DeadLetterQueue for failed records."""
    
    @pytest.fixture
    def dlq(self):
        """Create DLQ instance."""
        return DeadLetterQueue(name='test_dlq', max_retries=3)
    
    def test_enqueue_record(self, dlq):
        """Test enqueuing a failed record."""
        record = PipelineRecord(
            record_id='rec-1',
            data={'ticker': 'AAPL', 'price': 150.0},
            timestamp=datetime.now(),
            stage='enrichment',
            error='API timeout'
        )
        
        dlq.enqueue(record)
        
        assert dlq.get_size() == 1
        assert dlq.queue[0].record_id == 'rec-1'
    
    def test_process_queue_success(self, dlq):
        """Test processing records that succeed."""
        record = PipelineRecord(
            record_id='rec-1',
            data={'value': 100},
            timestamp=datetime.now(),
            stage='processing'
        )
        dlq.enqueue(record)
        
        def handler(rec):
            return True  # Success
        
        stats = dlq.process_queue(handler)
        
        assert stats['processed'] == 1
        assert stats['succeeded'] == 1
        assert stats['failed'] == 0
        assert dlq.get_size() == 0
    
    def test_process_queue_with_retries(self, dlq):
        """Test processing with multiple retries."""
        record = PipelineRecord(
            record_id='rec-1',
            data={'value': 100},
            timestamp=datetime.now(),
            stage='processing'
        )
        dlq.enqueue(record)
        
        call_count = [0]
        
        def handler(rec):
            call_count[0] += 1
            return call_count[0] > 2  # Succeed on 3rd call
        
        dlq.process_queue(handler)
        
        # Should be re-queued
        assert dlq.get_size() > 0 or len(dlq.failed) == 0
    
    def test_export_failed_records(self, dlq):
        """Test exporting failed records to Parquet."""
        record = PipelineRecord(
            record_id='rec-1',
            data={'value': 100},
            timestamp=datetime.now(),
            stage='processing',
            error='Max retries exceeded'
        )
        dlq.failed.append(record)
        
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = dlq.export_to_parquet(tmpdir)
            
            assert filepath is not None
            df = pd.read_parquet(filepath)
            assert len(df) >= 1


class TestDataLineageTracker:
    """Test DataLineageTracker."""
    
    @pytest.fixture
    def tracker(self):
        """Create lineage tracker."""
        return DataLineageTracker()
    
    def test_record_transformation(self, tracker):
        """Test recording a transformation."""
        tracker.record_transformation(
            record_id='rec-1',
            source='raw_data',
            destination='enriched_data',
            transformation='enrich_with_fundamentals',
            input_data={'ticker': 'AAPL'},
            output_data={'ticker': 'AAPL', 'pe_ratio': 28.5},
            duration_ms=150.0
        )
        
        assert len(tracker.entries) == 1
        entry = tracker.entries[0]
        assert entry.record_id == 'rec-1'
        assert entry.source == 'raw_data'
        assert entry.status == 'success'
    
    def test_record_failed_transformation(self, tracker):
        """Test recording a failed transformation."""
        tracker.record_transformation(
            record_id='rec-1',
            source='raw_data',
            destination='enriched_data',
            transformation='enrich_with_fundamentals',
            input_data={'ticker': 'INVALID'},
            output_data=None,
            duration_ms=45.0,
            status='failure',
            error='Unknown ticker'
        )
        
        entry = tracker.entries[0]
        assert entry.status == 'failure'
        assert entry.error == 'Unknown ticker'
    
    def test_get_record_lineage(self, tracker):
        """Test getting lineage for specific record."""
        tracker.record_transformation('rec-1', 'stage1', 'stage2', 'transform1', {}, {}, 10)
        tracker.record_transformation('rec-1', 'stage2', 'stage3', 'transform2', {}, {}, 15)
        tracker.record_transformation('rec-2', 'stage1', 'stage2', 'transform1', {}, {}, 12)
        
        lineage = tracker.get_record_lineage('rec-1')
        
        assert len(lineage) == 2
        assert all(e.record_id == 'rec-1' for e in lineage)
    
    def test_lineage_dataframe(self, tracker):
        """Test getting lineage as DataFrame."""
        tracker.record_transformation('rec-1', 'stage1', 'stage2', 'transform', {}, {}, 10)
        tracker.record_transformation('rec-2', 'stage1', 'stage2', 'transform', {}, {}, 15)
        
        df = tracker.get_lineage_dataframe()
        
        assert len(df) == 2
        assert 'record_id' in df.columns
        assert 'duration_ms' in df.columns
    
    def test_export_lineage(self, tracker):
        """Test exporting lineage to Parquet."""
        tracker.record_transformation('rec-1', 'stage1', 'stage2', 'transform', {}, {}, 10)
        
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = tracker.export_lineage(tmpdir)
            
            assert filepath is not None
            df = pd.read_parquet(filepath)
            assert len(df) >= 1


class TestPipelineStage:
    """Test PipelineStage abstract class."""
    
    class SimplePipelineStage(PipelineStage):
        """Concrete implementation for testing."""
        
        def process(self, data):
            if isinstance(data, dict) and data.get('fail'):
                raise ValueError('Processing failed')
            return data
    
    def test_execute_stage_success(self):
        """Test successful stage execution."""
        stage = self.SimplePipelineStage('test_stage')
        
        result = stage.execute({'value': 100}, validate=False)
        
        assert result == {'value': 100}
        assert len(stage.lineage_tracker.entries) == 1
    
    def test_execute_stage_with_failure(self):
        """Test stage execution with failure."""
        stage = self.SimplePipelineStage('test_stage')
        dlq = DeadLetterQueue()
        stage.dlq = dlq
        
        with pytest.raises(ValueError):
            stage.execute({'fail': True}, validate=False)
        
        # Should be in DLQ
        assert dlq.get_size() > 0


class TestSchemaValidation:
    """Test schema validation."""
    
    def test_valid_schema(self):
        """Test DataFrame that matches schema."""
        df = pd.DataFrame({
            'ticker': ['AAPL', 'MSFT'],
            'price': [150.0, 300.0]
        })
        
        schema = {'ticker': 'object', 'price': 'float64'}
        is_valid, errors = validate_schema(df, schema)
        
        assert is_valid is True
        assert len(errors) == 0
    
    def test_missing_columns(self):
        """Test DataFrame with missing columns."""
        df = pd.DataFrame({
            'ticker': ['AAPL'],
        })
        
        schema = {'ticker': 'object', 'price': 'float64'}
        is_valid, errors = validate_schema(df, schema)
        
        assert is_valid is False
        assert any('Missing' in error for error in errors)
    
    def test_wrong_dtype(self):
        """Test DataFrame with wrong data type."""
        df = pd.DataFrame({
            'ticker': ['AAPL'],
            'price': ['150.0']  # String instead of float
        })
        
        schema = {'ticker': 'object', 'price': 'float64'}
        is_valid, errors = validate_schema(df, schema)
        
        assert is_valid is False


class TestPipelineRecord:
    """Test PipelineRecord data structure."""
    
    def test_record_creation(self):
        """Test creating a pipeline record."""
        record = PipelineRecord(
            record_id='rec-1',
            data={'value': 100},
            timestamp=datetime.now(),
            stage='processing'
        )
        
        assert record.record_id == 'rec-1'
        assert record.data == {'value': 100}
        assert record.attempt == 1
    
    def test_record_to_dict(self):
        """Test converting record to dict."""
        record = PipelineRecord(
            record_id='rec-1',
            data={'value': 100},
            timestamp=datetime.now(),
            stage='processing',
            error='Test error'
        )
        
        record_dict = record.to_dict()
        
        assert record_dict['record_id'] == 'rec-1'
        assert record_dict['error'] == 'Test error'


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_empty_dataframe_validation(self):
        """Test validating empty DataFrame."""
        validator = DataValidator()
        validator.add_rule(DataValidationRule('req', 'required', 'col'))
        
        df = pd.DataFrame({'col': []})
        result = validator.validate_dataframe(df, 'test')
        
        assert result.total_records == 0
    
    def test_single_record_retry(self):
        """Test retry with single record."""
        handler = RetryHandler(RetryPolicy(max_attempts=1))
        
        def func():
            return 'ok'
        
        result = handler.execute_with_retry(func)
        assert result == 'ok'
    
    def test_large_batch_processing(self):
        """Test processing large batch."""
        validator = DataValidator()
        
        # Create large DataFrame
        df = pd.DataFrame({
            'ticker': ['AAPL'] * 1000,
            'price': np.random.rand(1000) * 100
        })
        
        result = validator.validate_dataframe(df, 'large_batch')
        assert result.total_records == 1000


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
