"""
Data Pipeline Robustness Module

Reliable, maintainable data pipelines:
- Data validation at each pipeline stage
- Automatic retries with exponential backoff
- Dead-letter queues for failed records
- Data lineage and audit trails
- Schema validation and evolution
"""

import logging
from typing import Dict, List, Any, Optional, Callable, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
import json
import hashlib
from pathlib import Path
import pandas as pd
import uuid
from abc import ABC, abstractmethod
import time

logger = logging.getLogger(__name__)


class ValidationLevel(Enum):
    """Validation severity levels."""
    CRITICAL = "critical"  # Must pass
    WARNING = "warning"    # Log warning but continue
    INFO = "info"         # Informational


class RetryStrategy(Enum):
    """Retry strategies."""
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"
    FIXED_DELAY = "fixed_delay"


@dataclass
class DataValidationRule:
    """A single data validation rule."""
    
    name: str
    rule_type: str  # 'required', 'type', 'range', 'regex', 'custom'
    column: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    level: ValidationLevel = ValidationLevel.CRITICAL
    message: str = ""
    
    def validate(self, value: Any) -> Tuple[bool, Optional[str]]:
        """
        Apply validation rule.
        
        Args:
            value: Value to validate
        
        Returns:
            (is_valid, error_message)
        """
        if self.rule_type == 'required':
            is_valid = value is not None and str(value).strip() != ''
            error = None if is_valid else f'{self.column} is required'
        
        elif self.rule_type == 'type':
            expected_type = self.parameters.get('type', type(None))
            is_valid = isinstance(value, expected_type)
            error = None if is_valid else f'{self.column} must be {expected_type.__name__}'
        
        elif self.rule_type == 'range':
            min_val = self.parameters.get('min')
            max_val = self.parameters.get('max')
            is_valid = True
            error = None
            
            if min_val is not None and value < min_val:
                is_valid = False
                error = f'{self.column} must be >= {min_val}'
            elif max_val is not None and value > max_val:
                is_valid = False
                error = f'{self.column} must be <= {max_val}'
        
        elif self.rule_type == 'regex':
            import re
            pattern = self.parameters.get('pattern', '')
            is_valid = bool(re.match(pattern, str(value)))
            error = None if is_valid else f'{self.column} format invalid'
        
        elif self.rule_type == 'custom':
            func = self.parameters.get('function')
            is_valid = func(value) if func else True
            error = None if is_valid else self.message or f'{self.column} failed custom validation'
        
        else:
            is_valid = True
            error = None
        
        return is_valid, error


@dataclass
class ValidationResult:
    """Result of a validation check."""
    
    timestamp: datetime
    stage: str  # Pipeline stage name
    total_records: int
    valid_records: int
    invalid_records: int
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    failed_row_indices: List[int] = field(default_factory=list)
    
    @property
    def pass_rate(self) -> float:
        """Percentage of records that passed validation."""
        return self.valid_records / self.total_records if self.total_records > 0 else 0
    
    @property
    def is_passed(self) -> bool:
        """Whether validation passed overall."""
        return self.invalid_records == 0


@dataclass
class RetryPolicy:
    """Configuration for automatic retries."""
    
    max_attempts: int = 3
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF
    initial_delay_seconds: float = 1.0
    max_delay_seconds: float = 60.0
    multiplier: float = 2.0
    jitter: bool = True
    
    def get_delay(self, attempt: int) -> float:
        """
        Get delay for a specific attempt number.
        
        Args:
            attempt: 0-indexed attempt number
        
        Returns:
            Delay in seconds
        """
        if self.strategy == RetryStrategy.FIXED_DELAY:
            delay = self.initial_delay_seconds
        
        elif self.strategy == RetryStrategy.LINEAR_BACKOFF:
            delay = self.initial_delay_seconds * (attempt + 1)
        
        elif self.strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            delay = self.initial_delay_seconds * (self.multiplier ** attempt)
        
        else:
            delay = self.initial_delay_seconds
        
        # Cap at max delay
        delay = min(delay, self.max_delay_seconds)
        
        # Add jitter
        if self.jitter:
            import random
            jitter_amount = delay * 0.1
            delay += random.uniform(-jitter_amount, jitter_amount)
        
        return max(0, delay)


@dataclass
class PipelineRecord:
    """A record flowing through the pipeline."""
    
    record_id: str
    data: Dict[str, Any]
    timestamp: datetime
    stage: str
    attempt: int = 1
    error: Optional[str] = None
    validation_errors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'record_id': self.record_id,
            'data': self.data,
            'timestamp': self.timestamp.isoformat(),
            'stage': self.stage,
            'attempt': self.attempt,
            'error': self.error,
            'validation_errors': self.validation_errors,
        }


@dataclass
class DataLineageEntry:
    """Entry in the data lineage audit trail."""
    
    timestamp: datetime
    record_id: str
    source: str
    destination: str
    transformation: str
    input_hash: str
    output_hash: str
    status: str  # 'success', 'failure', 'skipped'
    duration_ms: float
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class DataValidator:
    """Validates data against rules at pipeline stages."""
    
    def __init__(self):
        """Initialize data validator."""
        self.rules: List[DataValidationRule] = []
        self.results: List[ValidationResult] = []
    
    def add_rule(self, rule: DataValidationRule):
        """Add a validation rule."""
        self.rules.append(rule)
    
    def validate_record(self, record: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate a single record.
        
        Args:
            record: Record to validate
        
        Returns:
            (is_valid, errors)
        """
        errors = []
        
        for rule in self.rules:
            if rule.column is None:
                continue
            
            value = record.get(rule.column)
            is_valid, error = rule.validate(value)
            
            if not is_valid:
                errors.append(error)
        
        return len(errors) == 0, errors
    
    def validate_dataframe(
        self,
        df: pd.DataFrame,
        stage: str,
        on_failure: str = 'log'  # 'log', 'raise', 'collect'
    ) -> ValidationResult:
        """
        Validate an entire DataFrame.
        
        Args:
            df: DataFrame to validate
            stage: Pipeline stage name
            on_failure: How to handle failures
        
        Returns:
            ValidationResult
        """
        result = ValidationResult(
            timestamp=datetime.now(),
            stage=stage,
            total_records=len(df),
            valid_records=0,
            invalid_records=0,
        )
        
        for idx, row in df.iterrows():
            record = row.to_dict()
            is_valid, errors = self.validate_record(record)
            
            if is_valid:
                result.valid_records += 1
            else:
                result.invalid_records += 1
                result.failed_row_indices.append(idx)
                result.errors.extend(errors)
        
        self.results.append(result)
        
        if on_failure == 'raise' and not result.is_passed:
            raise ValueError(f'Validation failed at {stage}: {result.errors}')
        elif on_failure == 'log' and not result.is_passed:
            logger.warning(f'Validation warnings at {stage}: {len(result.errors)} issues')
        
        return result


class DeadLetterQueue:
    """Queue for handling failed records."""
    
    def __init__(self, name: str = 'default_dlq', max_retries: int = 3):
        """
        Initialize dead-letter queue.
        
        Args:
            name: Queue name
            max_retries: Max retries before final failure
        """
        self.name = name
        self.max_retries = max_retries
        self.queue: List[PipelineRecord] = []
        self.failed: List[PipelineRecord] = []
    
    def enqueue(self, record: PipelineRecord):
        """Add record to dead-letter queue."""
        self.queue.append(record)
        logger.warning(f'Record {record.record_id} enqueued to DLQ: {record.error}')
    
    def process_queue(
        self,
        handler: Callable[[PipelineRecord], bool]
    ) -> Dict[str, int]:
        """
        Process queued records with handler function.
        
        Args:
            handler: Function to process record, returns True if success
        
        Returns:
            Statistics: {'processed': int, 'succeeded': int, 'failed': int}
        """
        stats = {'processed': 0, 'succeeded': 0, 'failed': 0}
        
        while self.queue:
            record = self.queue.pop(0)
            stats['processed'] += 1
            
            try:
                success = handler(record)
                if success:
                    stats['succeeded'] += 1
                else:
                    record.attempt += 1
                    if record.attempt >= self.max_retries:
                        self.failed.append(record)
                    else:
                        self.queue.append(record)
            except Exception as e:
                record.error = str(e)
                record.attempt += 1
                if record.attempt >= self.max_retries:
                    self.failed.append(record)
                    stats['failed'] += 1
                else:
                    self.queue.append(record)
        
        return stats
    
    def get_size(self) -> int:
        """Get current queue size."""
        return len(self.queue)
    
    def export_to_parquet(self, output_path: str = 'db/dead_letter_queues'):
        """Export failed records to Parquet."""
        if not self.failed:
            return None
        
        output_dir = Path(output_path)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        df = pd.DataFrame([record.to_dict() for record in self.failed])
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filepath = output_dir / f'dlq_{self.name}_{timestamp}.parquet'
        
        df.to_parquet(filepath, compression='snappy')
        logger.info(f'Exported {len(self.failed)} failed records to {filepath}')
        
        return str(filepath)


class RetryHandler:
    """Handles automatic retries with configurable backoff."""
    
    def __init__(self, policy: RetryPolicy = None):
        """
        Initialize retry handler.
        
        Args:
            policy: RetryPolicy configuration
        """
        self.policy = policy or RetryPolicy()
        self.retry_history: List[Dict[str, Any]] = []
    
    def execute_with_retry(
        self,
        func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute function with automatic retries.
        
        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
        
        Returns:
            Function result
        
        Raises:
            Exception: If all retries exhausted
        """
        last_error = None
        
        for attempt in range(self.policy.max_attempts):
            try:
                result = func(*args, **kwargs)
                
                if attempt > 0:
                    self.retry_history.append({
                        'function': func.__name__,
                        'attempt': attempt,
                        'status': 'success',
                        'timestamp': datetime.now(),
                    })
                
                return result
            
            except Exception as e:
                last_error = e
                
                if attempt < self.policy.max_attempts - 1:
                    delay = self.policy.get_delay(attempt)
                    logger.warning(
                        f'Retry {attempt + 1}/{self.policy.max_attempts} for {func.__name__} '
                        f'after {delay:.2f}s: {str(e)}'
                    )
                    
                    self.retry_history.append({
                        'function': func.__name__,
                        'attempt': attempt,
                        'status': 'retry',
                        'delay_seconds': delay,
                        'error': str(e),
                        'timestamp': datetime.now(),
                    })
                    
                    time.sleep(delay)
        
        raise last_error


class DataLineageTracker:
    """Track data lineage and transformations."""
    
    def __init__(self):
        """Initialize lineage tracker."""
        self.entries: List[DataLineageEntry] = []
    
    def _hash_data(self, data: Any) -> str:
        """Generate hash of data for comparison."""
        if isinstance(data, dict):
            data_str = json.dumps(data, sort_keys=True)
        else:
            data_str = str(data)
        
        return hashlib.sha256(data_str.encode()).hexdigest()
    
    def record_transformation(
        self,
        record_id: str,
        source: str,
        destination: str,
        transformation: str,
        input_data: Any,
        output_data: Any,
        duration_ms: float,
        status: str = 'success',
        error: Optional[str] = None
    ):
        """
        Record a data transformation in lineage trail.
        
        Args:
            record_id: Unique record identifier
            source: Source system/stage
            destination: Destination system/stage
            transformation: Transformation name/description
            input_data: Input data
            output_data: Output data
            duration_ms: Processing time in milliseconds
            status: 'success', 'failure', 'skipped'
            error: Error message if failed
        """
        entry = DataLineageEntry(
            timestamp=datetime.now(),
            record_id=record_id,
            source=source,
            destination=destination,
            transformation=transformation,
            input_hash=self._hash_data(input_data),
            output_hash=self._hash_data(output_data),
            status=status,
            duration_ms=duration_ms,
            error=error,
        )
        
        self.entries.append(entry)
    
    def get_record_lineage(self, record_id: str) -> List[DataLineageEntry]:
        """Get lineage for a specific record."""
        return [e for e in self.entries if e.record_id == record_id]
    
    def get_lineage_dataframe(self) -> pd.DataFrame:
        """Get all lineage entries as DataFrame."""
        if not self.entries:
            return pd.DataFrame()
        
        return pd.DataFrame([entry.to_dict() for entry in self.entries])
    
    def export_lineage(self, output_path: str = 'db/data_lineage'):
        """Export data lineage to Parquet."""
        if not self.entries:
            return None
        
        output_dir = Path(output_path)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        df = self.get_lineage_dataframe()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filepath = output_dir / f'lineage_{timestamp}.parquet'
        
        df.to_parquet(filepath, compression='snappy')
        logger.info(f'Exported {len(self.entries)} lineage entries to {filepath}')
        
        return str(filepath)


class PipelineStage(ABC):
    """Abstract base class for pipeline stages."""
    
    def __init__(
        self,
        name: str,
        validator: DataValidator = None,
        retry_policy: RetryPolicy = None,
        dlq: DeadLetterQueue = None
    ):
        """
        Initialize pipeline stage.
        
        Args:
            name: Stage name
            validator: Data validator
            retry_policy: Retry configuration
            dlq: Dead-letter queue
        """
        self.name = name
        self.validator = validator or DataValidator()
        self.retry_handler = RetryHandler(retry_policy)
        self.dlq = dlq
        self.lineage_tracker = DataLineageTracker()
    
    @abstractmethod
    def process(self, data: Any) -> Any:
        """Process data through this stage."""
        pass
    
    def execute(
        self,
        data: Any,
        record_id: str = None,
        validate: bool = True
    ) -> Any:
        """
        Execute stage with validation and retry logic.
        
        Args:
            data: Input data
            record_id: Record identifier for lineage
            validate: Whether to validate input
        
        Returns:
            Processed data
        """
        if record_id is None:
            record_id = str(uuid.uuid4())
        
        start_time = time.time()
        
        try:
            # Validate input if DataFrame
            if validate and isinstance(data, pd.DataFrame):
                validation = self.validator.validate_dataframe(data, self.name)
                if not validation.is_passed:
                    logger.warning(f'Validation warnings in {self.name}: {validation.errors}')
            
            # Process with retry
            result = self.retry_handler.execute_with_retry(self.process, data)
            
            duration_ms = (time.time() - start_time) * 1000
            
            # Record lineage
            self.lineage_tracker.record_transformation(
                record_id=record_id,
                source='input',
                destination=self.name,
                transformation=f'{self.name}_process',
                input_data=data,
                output_data=result,
                duration_ms=duration_ms,
                status='success'
            )
            
            return result
        
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            
            # Record failure lineage
            self.lineage_tracker.record_transformation(
                record_id=record_id,
                source='input',
                destination=self.name,
                transformation=f'{self.name}_process',
                input_data=data,
                output_data=None,
                duration_ms=duration_ms,
                status='failure',
                error=str(e)
            )
            
            # Send to DLQ if available
            if self.dlq:
                record = PipelineRecord(
                    record_id=record_id,
                    data=data if isinstance(data, dict) else {'raw': str(data)},
                    timestamp=datetime.now(),
                    stage=self.name,
                    error=str(e)
                )
                self.dlq.enqueue(record)
            
            raise


# Utility functions

def validate_schema(df: pd.DataFrame, schema: Dict[str, str]) -> Tuple[bool, List[str]]:
    """
    Validate DataFrame against expected schema.
    
    Args:
        df: DataFrame to validate
        schema: Expected schema {'column_name': 'dtype'}
    
    Returns:
        (is_valid, errors)
    """
    errors = []
    
    # Check required columns exist
    missing_cols = set(schema.keys()) - set(df.columns)
    if missing_cols:
        errors.append(f'Missing columns: {missing_cols}')
    
    # Check column types
    for col, expected_dtype in schema.items():
        if col in df.columns:
            actual_dtype = str(df[col].dtype)
            if expected_dtype not in actual_dtype:
                errors.append(f'Column {col}: expected {expected_dtype}, got {actual_dtype}')
    
    return len(errors) == 0, errors
