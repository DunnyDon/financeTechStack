"""
Tests for Observability Module

Coverage:
- Structured logging and JSON output
- Distributed tracing with Jaeger
- Performance monitoring and metrics
- Prefect flow execution dashboards
- Alert condition checking
- Export and persistence
"""

import pytest
import pandas as pd
import json
from datetime import datetime, timedelta
from pathlib import Path
import time

from src.observability import (
    SpanContext, StructuredLog, StructuredLogger, DistributedTracer,
    PerformanceMonitor, PrefectDashboardMetrics, ServiceType, LogLevel,
    trace_execution, monitor_performance
)


class TestSpanContext:
    """Test SpanContext for distributed tracing."""
    
    def test_span_creation(self):
        """Test creating a span context."""
        span = SpanContext(
            trace_id='trace-123',
            span_id='span-456',
            service=ServiceType.DATA_FETCH,
            operation='fetch_data'
        )
        
        assert span.trace_id == 'trace-123'
        assert span.span_id == 'span-456'
        assert span.status == 'running'
        assert span.duration_ms is None
    
    def test_span_finish(self):
        """Test finishing a span."""
        span = SpanContext(
            trace_id='trace-123',
            span_id='span-456',
            service=ServiceType.DATA_FETCH,
            operation='fetch_data'
        )
        
        initial_time = span.start_time
        time.sleep(0.1)
        span.finish(status='success')
        
        assert span.status == 'success'
        assert span.end_time > initial_time
        assert span.duration_ms > 100
        assert span.error is None
    
    def test_span_with_error(self):
        """Test span with error."""
        span = SpanContext(
            trace_id='trace-123',
            span_id='span-456'
        )
        
        span.finish(status='error', error='Connection timeout')
        
        assert span.status == 'error'
        assert span.error == 'Connection timeout'


class TestStructuredLog:
    """Test StructuredLog entries."""
    
    def test_structured_log_creation(self):
        """Test creating structured log entry."""
        log = StructuredLog(
            timestamp=datetime.now().isoformat(),
            level='INFO',
            logger_name='test.module',
            message='Test message',
            trace_id='trace-123',
            span_id='span-456'
        )
        
        assert log.level == 'INFO'
        assert log.message == 'Test message'
        assert log.trace_id == 'trace-123'
    
    def test_structured_log_to_json(self):
        """Test converting log to JSON."""
        log = StructuredLog(
            timestamp=datetime.now().isoformat(),
            level='ERROR',
            logger_name='test.module',
            message='Error occurred',
            error='Connection failed'
        )
        
        json_str = log.to_json()
        parsed = json.loads(json_str)
        
        assert parsed['level'] == 'ERROR'
        assert parsed['message'] == 'Error occurred'
        assert parsed['error'] == 'Connection failed'


class TestStructuredLogger:
    """Test StructuredLogger."""
    
    @pytest.fixture
    def logger(self):
        """Create structured logger instance."""
        return StructuredLogger('test.logger', output_format='json')
    
    def test_logger_creation(self, logger):
        """Test creating logger."""
        assert logger.logger.name == 'test.logger'
        assert logger.output_format == 'json'
    
    def test_set_trace_context(self, logger):
        """Test setting trace context."""
        span = SpanContext(
            trace_id='trace-123',
            span_id='span-456',
            service=ServiceType.ANALYTICS
        )
        
        logger.set_trace_context(span)
        assert logger.trace_context == span
    
    def test_log_with_context(self, logger):
        """Test logging with context."""
        logger.info(
            'Test message',
            context={'user_id': 123, 'action': 'fetch'},
            tags={'env': 'test'}
        )
        # Should not raise


class TestDistributedTracer:
    """Test DistributedTracer."""
    
    @pytest.fixture
    def tracer(self):
        """Create tracer instance."""
        return DistributedTracer(service_name='test-service')
    
    def test_start_span(self, tracer):
        """Test starting a span."""
        span = tracer.start_span(
            operation='test_operation',
            service=ServiceType.DATA_FETCH
        )
        
        assert span.operation == 'test_operation'
        assert span.service == ServiceType.DATA_FETCH
        assert span.span_id in tracer.active_spans
    
    def test_finish_span(self, tracer):
        """Test finishing a span."""
        span = tracer.start_span('test_op')
        tracer.finish_span(span, status='success')
        
        assert span.status == 'success'
        assert len(tracer.spans) == 1
        assert span.span_id not in tracer.active_spans
    
    def test_nested_spans(self, tracer):
        """Test nested trace spans."""
        parent = tracer.start_span('parent_op')
        child = tracer.start_span('child_op', parent_span_id=parent.span_id)
        
        assert child.parent_span_id == parent.span_id
        assert len(tracer.active_spans) == 2
    
    def test_get_trace_summary(self, tracer):
        """Test getting trace summary."""
        tracer.start_span('op1')
        span2 = tracer.start_span('op2')
        tracer.finish_span(span2, status='success')
        
        summary = tracer.get_trace_summary()
        
        assert len(summary) >= 1
        assert 'operation' in summary.columns
        assert 'status' in summary.columns
    
    def test_export_jaeger(self, tracer, tmp_path):
        """Test exporting traces in Jaeger format."""
        span1 = tracer.start_span('op1')
        tracer.finish_span(span1)
        
        span2 = tracer.start_span('op2')
        tracer.finish_span(span2)
        
        # Override path for test
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = tracer.export_jaeger(tmpdir)
            
            assert Path(filepath).exists()
            
            with open(filepath) as f:
                data = json.load(f)
                assert len(data) >= 2


class TestPerformanceMonitor:
    """Test PerformanceMonitor."""
    
    @pytest.fixture
    def monitor(self):
        """Create monitor instance."""
        return PerformanceMonitor()
    
    def test_record_metric(self, monitor):
        """Test recording a metric."""
        monitor.record_metric('request_latency', 42.5, tags={'endpoint': '/api/data'})
        
        assert len(monitor.metrics) == 1
        assert monitor.metrics[0]['metric'] == 'request_latency'
        assert monitor.metrics[0]['value'] == 42.5
    
    def test_check_alert_greater_than(self, monitor):
        """Test alert condition: value > threshold."""
        monitor.record_metric('cpu_usage', 85.0, tags={'host': 'server1'})
        monitor.record_metric('cpu_usage', 92.0, tags={'host': 'server2'})
        
        alerts = monitor.check_alert_conditions('cpu_usage', threshold=90.0, comparison='greater')
        
        assert len(alerts) == 1
        assert alerts[0]['value'] == 92.0
    
    def test_check_alert_less_than(self, monitor):
        """Test alert condition: value < threshold."""
        monitor.record_metric('data_quality', 95.0)
        monitor.record_metric('data_quality', 88.0)
        
        alerts = monitor.check_alert_conditions('data_quality', threshold=90.0, comparison='less')
        
        assert len(alerts) == 1
        assert alerts[0]['value'] == 88.0
    
    def test_multiple_metrics(self, monitor):
        """Test tracking multiple metrics."""
        monitor.record_metric('latency_ms', 100.0)
        monitor.record_metric('throughput_rps', 500.0)
        monitor.record_metric('error_rate', 0.02)
        
        df = monitor.get_metrics_dataframe()
        assert len(df) == 3
        assert 'metric' in df.columns
        assert 'value' in df.columns
    
    def test_alerts_dataframe(self, monitor):
        """Test getting alerts as DataFrame."""
        monitor.record_metric('latency', 200.0)
        monitor.check_alert_conditions('latency', threshold=150.0, comparison='greater')
        
        alerts_df = monitor.get_alerts_dataframe()
        
        assert len(alerts_df) == 1
        assert 'metric' in alerts_df.columns
        assert 'threshold' in alerts_df.columns
    
    def test_save_metrics_to_parquet(self, monitor):
        """Test saving metrics to Parquet."""
        monitor.record_metric('latency', 100.0)
        monitor.record_metric('throughput', 500.0)
        monitor.check_alert_conditions('latency', 150.0, 'greater')
        
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            monitor.save_metrics_to_parquet(tmpdir)
            
            # Verify files created
            metrics_file = list(Path(tmpdir).glob('metrics_*.parquet'))
            alerts_file = list(Path(tmpdir).glob('alerts_*.parquet'))
            
            assert len(metrics_file) > 0
            assert len(alerts_file) > 0


class TestPrefectDashboardMetrics:
    """Test PrefectDashboardMetrics."""
    
    @pytest.fixture
    def metrics(self):
        """Create Prefect metrics instance."""
        return PrefectDashboardMetrics()
    
    def test_record_flow_execution(self, metrics):
        """Test recording flow execution."""
        start = datetime.now()
        end = start + timedelta(seconds=30)
        
        metrics.record_flow_execution(
            flow_name='scrape_sec_filings',
            flow_run_id='run-123',
            start_time=start,
            end_time=end,
            status='Completed',
            num_tasks=5
        )
        
        assert len(metrics.flow_executions) == 1
        assert metrics.flow_executions[0]['flow_name'] == 'scrape_sec_filings'
        assert metrics.flow_executions[0]['status'] == 'Completed'
    
    def test_record_task_execution(self, metrics):
        """Test recording task execution."""
        start = datetime.now()
        end = start + timedelta(seconds=5)
        
        metrics.record_task_execution(
            task_name='fetch_data',
            flow_run_id='run-123',
            start_time=start,
            end_time=end,
            status='Completed',
            inputs_processed=1000,
            outputs_produced=950
        )
        
        assert len(metrics.task_executions) == 1
        assert metrics.task_executions[0]['task_name'] == 'fetch_data'
        assert metrics.task_executions[0]['inputs_processed'] == 1000
    
    def test_flow_summary(self, metrics):
        """Test flow summary."""
        start = datetime.now()
        
        metrics.record_flow_execution(
            'flow1', 'run-1', start, start + timedelta(seconds=10), 'Completed', 3
        )
        metrics.record_flow_execution(
            'flow2', 'run-2', start, start + timedelta(seconds=20), 'Failed', 2
        )
        
        summary = metrics.get_flow_summary()
        
        assert len(summary) == 2
        assert 'duration_seconds' in summary.columns
    
    def test_task_summary(self, metrics):
        """Test task summary."""
        start = datetime.now()
        
        metrics.record_task_execution(
            'task1', 'run-1', start, start + timedelta(seconds=5),
            'Completed', 100, 95
        )
        metrics.record_task_execution(
            'task2', 'run-1', start, start + timedelta(seconds=8),
            'Completed', 200, 190
        )
        
        summary = metrics.get_task_summary()
        
        assert len(summary) == 2
        assert 'throughput' in summary.columns
    
    def test_flow_health(self, metrics):
        """Test flow health metrics."""
        start = datetime.now()
        
        metrics.record_flow_execution('f1', 'r1', start, start + timedelta(seconds=10), 'Completed', 3)
        metrics.record_flow_execution('f2', 'r2', start, start + timedelta(seconds=15), 'Completed', 3)
        metrics.record_flow_execution('f3', 'r3', start, start + timedelta(seconds=20), 'Failed', 2)
        
        health = metrics.get_flow_health()
        
        assert health['total_flows'] == 3
        assert health['success_count'] == 2
        assert health['failure_count'] == 1
        assert health['success_rate'] == 2/3
    
    def test_task_performance(self, metrics):
        """Test task performance metrics."""
        start = datetime.now()
        
        metrics.record_task_execution(
            'task1', 'run-1', start, start + timedelta(seconds=5),
            'Completed', 1000, 950
        )
        
        perf = metrics.get_task_performance()
        
        assert perf['total_tasks'] == 1
        assert perf['total_records_processed'] == 1000
        assert perf['total_records_produced'] == 950
    
    def test_save_to_parquet(self, metrics):
        """Test saving Prefect metrics to Parquet."""
        start = datetime.now()
        
        metrics.record_flow_execution(
            'test_flow', 'run-1', start, start + timedelta(seconds=10), 'Completed', 2
        )
        metrics.record_task_execution(
            'test_task', 'run-1', start, start + timedelta(seconds=5), 'Completed', 100, 95
        )
        
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            metrics.save_to_parquet(tmpdir)
            
            files = list(Path(tmpdir).glob('*.parquet'))
            assert len(files) >= 2


class TestDecorators:
    """Test instrumentation decorators."""
    
    def test_trace_execution_decorator(self):
        """Test trace_execution decorator."""
        tracer = DistributedTracer()
        
        @trace_execution(tracer, service=ServiceType.ANALYTICS)
        def sample_function(x, y):
            return x + y
        
        result = sample_function(5, 10)
        
        assert result == 15
        assert len(tracer.spans) == 1
        assert tracer.spans[0].operation == 'sample_function'
    
    def test_trace_execution_with_error(self):
        """Test trace_execution with exception."""
        tracer = DistributedTracer()
        
        @trace_execution(tracer)
        def failing_function():
            raise ValueError('Test error')
        
        with pytest.raises(ValueError):
            failing_function()
        
        assert len(tracer.spans) == 1
        assert tracer.spans[0].status == 'error'
    
    def test_monitor_performance_decorator(self):
        """Test monitor_performance decorator."""
        monitor = PerformanceMonitor()
        
        @monitor_performance(monitor, metric_prefix='test')
        def sample_function(x):
            time.sleep(0.01)
            return x * 2
        
        result = sample_function(5)
        
        assert result == 10
        assert len(monitor.metrics) == 1
        assert 'test.sample_function' in monitor.metrics[0]['metric']


class TestAlertSeverity:
    """Test alert severity levels."""
    
    def test_alert_severity_determination(self):
        """Test how alert severity is determined."""
        monitor = PerformanceMonitor()
        
        # Slightly above threshold = warning
        monitor.record_metric('cpu', 95.0)
        alerts = monitor.check_alert_conditions('cpu', 90.0, 'greater')
        assert alerts[0]['severity'] == 'warning'
        
        # Well above threshold = high
        monitor.record_metric('cpu', 110.0)
        alerts = monitor.check_alert_conditions('cpu', 90.0, 'greater')
        assert alerts[-1]['severity'] == 'high'


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_empty_metrics_export(self):
        """Test exporting with no metrics."""
        monitor = PerformanceMonitor()
        df = monitor.get_metrics_dataframe()
        assert df.empty
    
    def test_span_with_tags(self):
        """Test span with custom tags."""
        tracer = DistributedTracer()
        
        span = tracer.start_span(
            'operation',
            tags={'region': 'us-west', 'environment': 'production'}
        )
        
        assert span.tags['region'] == 'us-west'
        assert span.tags['environment'] == 'production'
    
    def test_zero_duration_task(self):
        """Test recording task with zero duration."""
        metrics = PrefectDashboardMetrics()
        
        now = datetime.now()
        metrics.record_task_execution(
            'instant_task',
            'run-1',
            now,
            now,  # Same time
            'Completed',
            0,
            0
        )
        
        summary = metrics.get_task_summary()
        assert summary[summary['task_name'] == 'instant_task']['duration_seconds'].iloc[0] == 0.0
    
    def test_alert_with_custom_tags(self):
        """Test alert with custom tags."""
        monitor = PerformanceMonitor()
        
        monitor.record_metric(
            'request_latency',
            250.0,
            tags={'endpoint': '/api/data', 'method': 'POST'}
        )
        
        alerts = monitor.check_alert_conditions('request_latency', 200.0, 'greater')
        
        assert alerts[0]['tags']['endpoint'] == '/api/data'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
