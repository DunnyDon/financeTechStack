"""
Comprehensive Observability Module

Structured logging, distributed tracing, and performance monitoring:
- CloudWatch/ELK logging integration
- Jaeger distributed tracing
- Performance metrics and dashboards
- Prefect flow execution dashboards
- Alert conditions and thresholds
"""

import logging
import json
import time
from typing import Dict, Any, Optional, List, Callable
from functools import wraps
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
import uuid
from pathlib import Path
import pandas as pd
import numpy as np
from enum import Enum

logger = logging.getLogger(__name__)


class LogLevel(Enum):
    """Standard log levels."""
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL


class ServiceType(Enum):
    """Service/component types for tracing."""
    PREFECT_TASK = "prefect_task"
    DATA_FETCH = "data_fetch"
    ANALYTICS = "analytics"
    STORAGE = "storage"
    API_CALL = "api_call"
    PIPELINE = "pipeline"


@dataclass
class SpanContext:
    """Context for a distributed trace span."""
    
    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None
    service: ServiceType = ServiceType.PIPELINE
    operation: str = ""
    tags: Dict[str, Any] = field(default_factory=dict)
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    duration_ms: Optional[float] = None
    status: str = "running"  # 'running', 'success', 'error', 'timeout'
    error: Optional[str] = None
    
    def finish(self, status: str = 'success', error: Optional[str] = None):
        """Mark span as finished."""
        self.end_time = time.time()
        self.duration_ms = (self.end_time - self.start_time) * 1000
        self.status = status
        self.error = error


@dataclass
class StructuredLog:
    """Structured log entry for JSON-based logging."""
    
    timestamp: str
    level: str
    logger_name: str
    message: str
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    service: Optional[str] = None
    operation: Optional[str] = None
    duration_ms: Optional[float] = None
    error: Optional[str] = None
    stack_trace: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    tags: Dict[str, Any] = field(default_factory=dict)
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(asdict(self))


class StructuredLogger:
    """Logging with structured output for ELK/CloudWatch."""
    
    def __init__(self, name: str, output_format: str = 'json'):
        """
        Initialize structured logger.
        
        Args:
            name: Logger name
            output_format: 'json' or 'text'
        """
        self.logger = logging.getLogger(name)
        self.output_format = output_format
        self.trace_context: Optional[SpanContext] = None
        
    def set_trace_context(self, context: SpanContext):
        """Set current trace context."""
        self.trace_context = context
    
    def _log(
        self,
        level: LogLevel,
        message: str,
        error: Optional[Exception] = None,
        context: Optional[Dict[str, Any]] = None,
        tags: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        """Internal logging method."""
        
        import traceback
        
        log_entry = StructuredLog(
            timestamp=datetime.utcnow().isoformat(),
            level=level.name,
            logger_name=self.logger.name,
            message=message,
            trace_id=self.trace_context.trace_id if self.trace_context else None,
            span_id=self.trace_context.span_id if self.trace_context else None,
            service=self.trace_context.service.value if self.trace_context else None,
            operation=self.trace_context.operation if self.trace_context else None,
            error=str(error) if error else None,
            stack_trace=traceback.format_exc() if error else None,
            context=context or {},
            tags=tags or {},
        )
        
        if self.output_format == 'json':
            self.logger.log(level.value, log_entry.to_json())
        else:
            self.logger.log(level.value, message, extra=asdict(log_entry))
    
    def info(self, message: str, context: Optional[Dict] = None, tags: Optional[Dict] = None, **kwargs):
        """Log info level."""
        self._log(LogLevel.INFO, message, context=context, tags=tags, **kwargs)
    
    def error(self, message: str, error: Optional[Exception] = None, context: Optional[Dict] = None, **kwargs):
        """Log error level."""
        self._log(LogLevel.ERROR, message, error=error, context=context, **kwargs)
    
    def warning(self, message: str, context: Optional[Dict] = None, **kwargs):
        """Log warning level."""
        self._log(LogLevel.WARNING, message, context=context, **kwargs)
    
    def debug(self, message: str, context: Optional[Dict] = None, **kwargs):
        """Log debug level."""
        self._log(LogLevel.DEBUG, message, context=context, **kwargs)


class DistributedTracer:
    """Jaeger-compatible distributed tracing."""
    
    def __init__(self, service_name: str = 'finance-techstack'):
        """
        Initialize distributed tracer.
        
        Args:
            service_name: Service name for traces
        """
        self.service_name = service_name
        self.spans: List[SpanContext] = []
        self.active_spans: Dict[str, SpanContext] = {}
    
    def start_span(
        self,
        operation: str,
        service: ServiceType = ServiceType.PIPELINE,
        parent_span_id: Optional[str] = None,
        tags: Optional[Dict[str, Any]] = None
    ) -> SpanContext:
        """
        Start a new distributed trace span.
        
        Args:
            operation: Operation name
            service: Service type
            parent_span_id: Parent span ID for nesting
            tags: Additional tags
        
        Returns:
            SpanContext for the span
        """
        trace_id = str(uuid.uuid4())
        span_id = str(uuid.uuid4())
        
        span = SpanContext(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id,
            service=service,
            operation=operation,
            tags=tags or {}
        )
        
        self.active_spans[span_id] = span
        return span
    
    def finish_span(self, span: SpanContext, status: str = 'success', error: Optional[str] = None):
        """
        Finish a span and record metrics.
        
        Args:
            span: SpanContext to finish
            status: Final status
            error: Error message if failed
        """
        span.finish(status=status, error=error)
        self.spans.append(span)
        if span.span_id in self.active_spans:
            del self.active_spans[span.span_id]
    
    def get_trace_summary(self) -> pd.DataFrame:
        """Get summary of all traces."""
        rows = []
        for span in self.spans:
            rows.append({
                'trace_id': span.trace_id,
                'span_id': span.span_id,
                'operation': span.operation,
                'service': span.service.value,
                'duration_ms': span.duration_ms,
                'status': span.status,
                'error': span.error,
                'timestamp': datetime.fromtimestamp(span.start_time),
            })
        return pd.DataFrame(rows)
    
    def export_jaeger(self, output_path: str = 'db/tracing'):
        """Export traces in Jaeger format."""
        output_dir = Path(output_path)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filepath = output_dir / f'traces_{timestamp}.json'
        
        traces = [asdict(span) for span in self.spans]
        with open(filepath, 'w') as f:
            json.dump(traces, f, indent=2, default=str)
        
        logger.info(f'Exported {len(self.spans)} spans to {filepath}')
        return str(filepath)


class PerformanceMonitor:
    """Monitor and track performance metrics."""
    
    def __init__(self):
        """Initialize performance monitor."""
        self.metrics: List[Dict[str, Any]] = []
        self.alerts: List[Dict[str, Any]] = []
    
    def record_metric(
        self,
        metric_name: str,
        value: float,
        tags: Optional[Dict[str, str]] = None,
        timestamp: Optional[datetime] = None
    ):
        """
        Record a metric value.
        
        Args:
            metric_name: Name of metric
            value: Metric value
            tags: Dimension tags
            timestamp: Timestamp (default: now)
        """
        self.metrics.append({
            'timestamp': timestamp or datetime.now(),
            'metric': metric_name,
            'value': value,
            'tags': tags or {},
        })
    
    def check_alert_conditions(
        self,
        metric_name: str,
        threshold: float,
        comparison: str = 'greater'  # 'greater', 'less', 'equal'
    ) -> List[Dict[str, Any]]:
        """
        Check if metric exceeds alert thresholds.
        
        Args:
            metric_name: Metric to check
            threshold: Alert threshold
            comparison: Comparison operator
        
        Returns:
            List of triggered alerts
        """
        triggered = []
        
        for metric in self.metrics:
            if metric['metric'] != metric_name:
                continue
            
            value = metric['value']
            is_alert = False
            
            if comparison == 'greater' and value > threshold:
                is_alert = True
            elif comparison == 'less' and value < threshold:
                is_alert = True
            elif comparison == 'equal' and value == threshold:
                is_alert = True
            
            if is_alert:
                alert = {
                    'timestamp': metric['timestamp'],
                    'metric': metric_name,
                    'value': value,
                    'threshold': threshold,
                    'severity': 'high' if abs(value - threshold) > threshold * 0.2 else 'warning',
                    'tags': metric['tags'],
                }
                triggered.append(alert)
                self.alerts.append(alert)
        
        return triggered
    
    def get_metrics_dataframe(self) -> pd.DataFrame:
        """Get all metrics as DataFrame."""
        return pd.DataFrame(self.metrics)
    
    def get_alerts_dataframe(self) -> pd.DataFrame:
        """Get all alerts as DataFrame."""
        return pd.DataFrame(self.alerts) if self.alerts else pd.DataFrame()
    
    def save_metrics_to_parquet(self, output_path: str = 'db/observability'):
        """Save metrics to Parquet."""
        output_dir = Path(output_path)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Save metrics
        metrics_df = self.get_metrics_dataframe()
        if not metrics_df.empty:
            metrics_df.to_parquet(
                output_dir / f'metrics_{timestamp}.parquet',
                compression='snappy'
            )
        
        # Save alerts
        alerts_df = self.get_alerts_dataframe()
        if not alerts_df.empty:
            alerts_df.to_parquet(
                output_dir / f'alerts_{timestamp}.parquet',
                compression='snappy'
            )


class PrefectDashboardMetrics:
    """Metrics for Prefect flow execution dashboards."""
    
    def __init__(self):
        """Initialize Prefect metrics."""
        self.flow_executions: List[Dict[str, Any]] = []
        self.task_executions: List[Dict[str, Any]] = []
    
    def record_flow_execution(
        self,
        flow_name: str,
        flow_run_id: str,
        start_time: datetime,
        end_time: datetime,
        status: str,
        num_tasks: int,
        error: Optional[str] = None
    ):
        """
        Record a Prefect flow execution.
        
        Args:
            flow_name: Name of flow
            flow_run_id: Unique flow run ID
            start_time: When flow started
            end_time: When flow ended
            status: 'Completed', 'Failed', 'Cancelled'
            num_tasks: Number of tasks in flow
            error: Error message if failed
        """
        duration = (end_time - start_time).total_seconds()
        
        self.flow_executions.append({
            'timestamp': datetime.now(),
            'flow_name': flow_name,
            'flow_run_id': flow_run_id,
            'start_time': start_time,
            'end_time': end_time,
            'duration_seconds': duration,
            'status': status,
            'num_tasks': num_tasks,
            'error': error,
        })
    
    def record_task_execution(
        self,
        task_name: str,
        flow_run_id: str,
        start_time: datetime,
        end_time: datetime,
        status: str,
        inputs_processed: int = 0,
        outputs_produced: int = 0,
        error: Optional[str] = None
    ):
        """
        Record a Prefect task execution.
        
        Args:
            task_name: Name of task
            flow_run_id: Parent flow run ID
            start_time: When task started
            end_time: When task ended
            status: 'Completed', 'Failed', 'Skipped'
            inputs_processed: Number of input records
            outputs_produced: Number of output records
            error: Error message if failed
        """
        duration = (end_time - start_time).total_seconds()
        throughput = inputs_processed / duration if duration > 0 else 0
        
        self.task_executions.append({
            'timestamp': datetime.now(),
            'task_name': task_name,
            'flow_run_id': flow_run_id,
            'start_time': start_time,
            'end_time': end_time,
            'duration_seconds': duration,
            'status': status,
            'inputs_processed': inputs_processed,
            'outputs_produced': outputs_produced,
            'throughput': throughput,
            'error': error,
        })
    
    def get_flow_summary(self) -> pd.DataFrame:
        """Get summary of all flow executions."""
        return pd.DataFrame(self.flow_executions)
    
    def get_task_summary(self) -> pd.DataFrame:
        """Get summary of all task executions."""
        return pd.DataFrame(self.task_executions)
    
    def get_flow_health(self) -> Dict[str, Any]:
        """Get overall flow health metrics."""
        if not self.flow_executions:
            return {}
        
        df = self.get_flow_summary()
        total = len(df)
        completed = len(df[df['status'] == 'Completed'])
        failed = len(df[df['status'] == 'Failed'])
        
        return {
            'total_flows': total,
            'success_count': completed,
            'failure_count': failed,
            'success_rate': completed / total if total > 0 else 0,
            'avg_duration_seconds': df['duration_seconds'].mean(),
            'max_duration_seconds': df['duration_seconds'].max(),
            'min_duration_seconds': df['duration_seconds'].min(),
        }
    
    def get_task_performance(self) -> Dict[str, Any]:
        """Get task performance metrics."""
        if not self.task_executions:
            return {}
        
        df = self.get_task_summary()
        
        return {
            'total_tasks': len(df),
            'avg_duration_seconds': df['duration_seconds'].mean(),
            'avg_throughput': df['throughput'].mean(),
            'total_records_processed': df['inputs_processed'].sum(),
            'total_records_produced': df['outputs_produced'].sum(),
            'slowest_task': df.loc[df['duration_seconds'].idxmax(), 'task_name'] if len(df) > 0 else None,
            'slowest_task_duration': df['duration_seconds'].max(),
        }
    
    def save_to_parquet(self, output_path: str = 'db/prefect_dashboards'):
        """Save metrics to Parquet."""
        output_dir = Path(output_path)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if self.flow_executions:
            self.get_flow_summary().to_parquet(
                output_dir / f'flow_executions_{timestamp}.parquet',
                compression='snappy'
            )
        
        if self.task_executions:
            self.get_task_summary().to_parquet(
                output_dir / f'task_executions_{timestamp}.parquet',
                compression='snappy'
            )


# Decorators for instrumentation

def trace_execution(tracer: DistributedTracer, service: ServiceType = ServiceType.PIPELINE):
    """
    Decorator to automatically trace function execution.
    
    Args:
        tracer: DistributedTracer instance
        service: ServiceType for the span
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            span = tracer.start_span(
                operation=func.__name__,
                service=service,
                tags={'args': str(args)[:100], 'kwargs': str(kwargs)[:100]}
            )
            try:
                result = func(*args, **kwargs)
                tracer.finish_span(span, status='success')
                return result
            except Exception as e:
                tracer.finish_span(span, status='error', error=str(e))
                raise
        return wrapper
    return decorator


def monitor_performance(monitor: PerformanceMonitor, metric_prefix: str = ''):
    """
    Decorator to automatically record performance metrics.
    
    Args:
        monitor: PerformanceMonitor instance
        metric_prefix: Prefix for metric names
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = func(*args, **kwargs)
                duration_ms = (time.time() - start) * 1000
                metric_name = f'{metric_prefix}.{func.__name__}' if metric_prefix else func.__name__
                monitor.record_metric(metric_name, duration_ms)
                return result
            except Exception as e:
                duration_ms = (time.time() - start) * 1000
                metric_name = f'{metric_prefix}.{func.__name__}.error' if metric_prefix else f'{func.__name__}.error'
                monitor.record_metric(metric_name, duration_ms)
                raise
        return wrapper
    return decorator


# Utility functions

def setup_logging_to_cloudwatch(log_group: str, log_stream: str):
    """
    Setup logging to AWS CloudWatch.
    
    Args:
        log_group: CloudWatch log group name
        log_stream: CloudWatch log stream name
    """
    try:
        import watchtower
        
        cloudwatch_handler = watchtower.CloudWatchLogHandler(
            log_group=log_group,
            stream_name=log_stream
        )
        logger.addHandler(cloudwatch_handler)
        logger.info(f'CloudWatch logging configured: {log_group}/{log_stream}')
    except ImportError:
        logger.warning('watchtower not installed, skipping CloudWatch setup')


def setup_logging_to_elk(elasticsearch_host: str, elasticsearch_port: int = 9200):
    """
    Setup logging to ELK stack.
    
    Args:
        elasticsearch_host: Elasticsearch host
        elasticsearch_port: Elasticsearch port
    """
    try:
        from elasticsearchpy import Elasticsearch
        from pythonjsonlogger import jsonlogger
        
        es = Elasticsearch(f'http://{elasticsearch_host}:{elasticsearch_port}')
        logger.info(f'ELK logging configured: {elasticsearch_host}:{elasticsearch_port}')
    except ImportError:
        logger.warning('ELK dependencies not installed, skipping ELK setup')
