"""
Data Pipeline Robustness Integration

Integrates data validation, error handling, and retry logic into existing Prefect flows.
Provides decorators and utilities for adding robustness to pipeline tasks.
"""

import logging
from functools import wraps
from typing import Any, Callable, Dict, Optional, List
from datetime import datetime
import pandas as pd

from src.data_pipeline_robustness import (
    DataValidator,
    DataValidationRule,
    RetryHandler,
    RetryPolicy,
    RetryStrategy,
    DeadLetterQueue,
    DataLineageTracker,
    ValidationLevel,
    PipelineRecord,
    validate_schema,
)

logger = logging.getLogger(__name__)


class PipelineValidation:
    """Centralized validation configuration for pipeline stages."""

    # Price data schema
    PRICE_SCHEMA = {
        'timestamp': 'datetime64[ns]',
        'symbol': 'object',
        'open': 'float64',
        'high': 'float64',
        'low': 'float64',
        'close': 'float64',
        'volume': 'int64',
    }

    # Technical analysis schema
    TECHNICAL_SCHEMA = {
        'timestamp': 'datetime64[ns]',
        'symbol': 'object',
        'rsi': 'float64',
        'macd': 'float64',
        'bb_upper': 'float64',
        'bb_lower': 'float64',
    }

    # Fundamental analysis schema
    FUNDAMENTAL_SCHEMA = {
        'timestamp': 'datetime64[ns]',
        'symbol': 'object',
        'pe_ratio': 'float64',
        'dividend_yield': 'float64',
        'market_cap': 'float64',
    }

    # Portfolio schema
    PORTFOLIO_SCHEMA = {
        'symbol': 'object',
        'quantity': 'float64',
        'cost_basis': 'float64',
        'current_price': 'float64',
    }

    @staticmethod
    def get_price_validator() -> DataValidator:
        """Get validator for price data."""
        validator = DataValidator()

        # Required fields
        validator.add_rule(
            DataValidationRule(
                'symbol_required', 'required', 'symbol',
                level=ValidationLevel.CRITICAL
            )
        )
        validator.add_rule(
            DataValidationRule(
                'close_required', 'required', 'close',
                level=ValidationLevel.CRITICAL
            )
        )

        # Price ranges
        validator.add_rule(
            DataValidationRule(
                'price_positive', 'range', 'close',
                parameters={'min': 0.01, 'max': 1000000},
                level=ValidationLevel.CRITICAL
            )
        )

        # Volume validation
        validator.add_rule(
            DataValidationRule(
                'volume_non_negative', 'range', 'volume',
                parameters={'min': 0, 'max': 10000000000},
                level=ValidationLevel.WARNING
            )
        )

        return validator

    @staticmethod
    def get_technical_validator() -> DataValidator:
        """Get validator for technical analysis data."""
        validator = DataValidator()

        validator.add_rule(
            DataValidationRule(
                'symbol_required', 'required', 'symbol',
                level=ValidationLevel.CRITICAL
            )
        )

        # RSI should be 0-100
        validator.add_rule(
            DataValidationRule(
                'rsi_range', 'range', 'rsi',
                parameters={'min': 0, 'max': 100},
                level=ValidationLevel.WARNING
            )
        )

        return validator

    @staticmethod
    def get_fundamental_validator() -> DataValidator:
        """Get validator for fundamental analysis data."""
        validator = DataValidator()

        validator.add_rule(
            DataValidationRule(
                'symbol_required', 'required', 'symbol',
                level=ValidationLevel.CRITICAL
            )
        )

        # P/E ratio positive
        validator.add_rule(
            DataValidationRule(
                'pe_positive', 'custom', 'pe_ratio',
                parameters={'function': lambda x: pd.isna(x) or x > 0},
                message='P/E ratio must be positive or null',
                level=ValidationLevel.WARNING
            )
        )

        return validator


class RobustPipelineTask:
    """Wrapper for robust pipeline tasks with validation and retries."""

    def __init__(
        self,
        task_name: str,
        validator: Optional[DataValidator] = None,
        retry_policy: Optional[RetryPolicy] = None,
        dlq: Optional[DeadLetterQueue] = None,
        lineage_tracker: Optional[DataLineageTracker] = None,
    ):
        """
        Initialize robust task.

        Args:
            task_name: Name of task for logging
            validator: Data validator instance
            retry_policy: Retry configuration
            dlq: Dead-letter queue for failed records
            lineage_tracker: Data lineage tracker
        """
        self.task_name = task_name
        self.validator = validator
        self.retry_policy = retry_policy or RetryPolicy(
            max_attempts=3,
            strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
            initial_delay_seconds=1.0,
        )
        self.retry_handler = RetryHandler(self.retry_policy)
        self.dlq = dlq or DeadLetterQueue(name=task_name)
        self.lineage_tracker = lineage_tracker or DataLineageTracker()

    def execute(
        self,
        func: Callable,
        *args,
        validate: bool = True,
        schema: Optional[Dict[str, str]] = None,
        **kwargs,
    ) -> Any:
        """
        Execute task with validation and retry logic.

        Args:
            func: Function to execute
            *args: Function arguments
            validate: Whether to validate output
            schema: Expected schema for validation
            **kwargs: Function keyword arguments

        Returns:
            Function result
        """
        import time
        start_time = time.time()

        try:
            # Execute with retry
            result = self.retry_handler.execute_with_retry(func, *args, **kwargs)

            # Validate output
            if validate and isinstance(result, pd.DataFrame):
                if schema:
                    is_valid, errors = validate_schema(result, schema)
                    if not is_valid:
                        logger.warning(f'Schema validation warnings: {errors}')
                
                if self.validator:
                    validation = self.validator.validate_dataframe(result, self.task_name)
                    logger.info(
                        f'Validation: {validation.valid_records}/{validation.total_records} records passed'
                    )

            # Record success lineage
            duration = (time.time() - start_time) * 1000
            self.lineage_tracker.record_transformation(
                record_id=f'{self.task_name}_{datetime.now().timestamp()}',
                source='input',
                destination=self.task_name,
                transformation=func.__name__,
                input_data={'args': len(args), 'kwargs': len(kwargs)},
                output_data={'type': type(result).__name__, 'size': len(result) if hasattr(result, '__len__') else 0},
                duration_ms=duration,
                status='success',
            )

            return result

        except Exception as e:
            duration = (time.time() - start_time) * 1000

            # Record failure lineage
            self.lineage_tracker.record_transformation(
                record_id=f'{self.task_name}_{datetime.now().timestamp()}',
                source='input',
                destination=self.task_name,
                transformation=func.__name__,
                input_data={},
                output_data=None,
                duration_ms=duration,
                status='failure',
                error=str(e),
            )

            logger.error(f'Task {self.task_name} failed: {e}')
            raise

    def get_lineage_summary(self) -> pd.DataFrame:
        """Get lineage summary as DataFrame."""
        return self.lineage_tracker.get_lineage_dataframe()


def robust_task(
    validator: Optional[DataValidator] = None,
    retry_policy: Optional[RetryPolicy] = None,
    schema: Optional[Dict[str, str]] = None,
):
    """
    Decorator to add robustness to Prefect tasks.

    Args:
        validator: Data validator
        retry_policy: Retry configuration
        schema: Expected output schema
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            task_wrapper = RobustPipelineTask(
                task_name=func.__name__,
                validator=validator,
                retry_policy=retry_policy,
            )
            return task_wrapper.execute(
                func,
                *args,
                validate=True,
                schema=schema,
                **kwargs,
            )
        return wrapper
    return decorator


# Global pipeline instances for use across modules
PRICE_VALIDATOR = PipelineValidation.get_price_validator()
TECHNICAL_VALIDATOR = PipelineValidation.get_technical_validator()
FUNDAMENTAL_VALIDATOR = PipelineValidation.get_fundamental_validator()

PRICE_RETRY_POLICY = RetryPolicy(
    max_attempts=3,
    strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
    initial_delay_seconds=2.0,
    max_delay_seconds=30.0,
)

TECHNICAL_RETRY_POLICY = RetryPolicy(
    max_attempts=2,
    strategy=RetryStrategy.FIXED_DELAY,
    initial_delay_seconds=5.0,
)

FUNDAMENTAL_RETRY_POLICY = RetryPolicy(
    max_attempts=2,
    strategy=RetryStrategy.LINEAR_BACKOFF,
    initial_delay_seconds=3.0,
)


def validate_and_save_prices(df: pd.DataFrame) -> pd.DataFrame:
    """
    Validate and process price data before saving.

    Args:
        df: Price DataFrame

    Returns:
        Validated DataFrame
    """
    # Remove invalid rows
    validation = PRICE_VALIDATOR.validate_dataframe(df, 'price_processing')

    if not validation.is_passed:
        logger.warning(
            f'Price validation: {validation.invalid_records} invalid records removed'
        )
        # Remove failed rows
        df = df.drop(df.index[validation.failed_row_indices])

    return df


def validate_and_save_technical(df: pd.DataFrame) -> pd.DataFrame:
    """
    Validate and process technical analysis data.

    Args:
        df: Technical DataFrame

    Returns:
        Validated DataFrame
    """
    validation = TECHNICAL_VALIDATOR.validate_dataframe(df, 'technical_processing')

    if validation.invalid_records > 0:
        logger.warning(f'Technical validation: {validation.invalid_records} warnings')

    return df


def validate_and_save_fundamental(df: pd.DataFrame) -> pd.DataFrame:
    """
    Validate and process fundamental analysis data.

    Args:
        df: Fundamental DataFrame

    Returns:
        Validated DataFrame
    """
    validation = FUNDAMENTAL_VALIDATOR.validate_dataframe(df, 'fundamental_processing')

    if validation.invalid_records > 0:
        logger.warning(f'Fundamental validation: {validation.invalid_records} warnings')

    return df


__all__ = [
    'PipelineValidation',
    'RobustPipelineTask',
    'robust_task',
    'PRICE_VALIDATOR',
    'TECHNICAL_VALIDATOR',
    'FUNDAMENTAL_VALIDATOR',
    'PRICE_RETRY_POLICY',
    'TECHNICAL_RETRY_POLICY',
    'FUNDAMENTAL_RETRY_POLICY',
    'validate_and_save_prices',
    'validate_and_save_technical',
    'validate_and_save_fundamental',
]
