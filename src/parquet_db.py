"""
Parquet Database Management Layer

Provides unified interface for reading/writing/upserting data across 7 partitioned Parquet tables:
1. prices - Historical stock prices (OHLCV)
2. fx_rates - Currency conversion rates
3. pnl - Portfolio profit/loss
4. technical_analysis - Technical indicators
5. fundamental_analysis - Fundamental ratios
6. xbrl_filings - SEC XBRL financial statements
7. sec_filings - SEC EDGAR filing metadata

All tables use hierarchical partitioning: year/month/day
"""

import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from prefect import get_run_logger, task

from .constants import DEFAULT_OUTPUT_DIR
from .utils import get_logger

# Import data pipeline robustness components
try:
    from .pipeline_robustness_integration import (
        PRICE_VALIDATOR,
        TECHNICAL_VALIDATOR,
        FUNDAMENTAL_VALIDATOR,
    )
    ROBUSTNESS_AVAILABLE = True
except ImportError:
    ROBUSTNESS_AVAILABLE = False

__all__ = [
    "ParquetDB",
    "upsert_prices",
    "upsert_fx_rates",
    "upsert_pnl",
    "upsert_technical_analysis",
    "upsert_fundamental_analysis",
    "upsert_xbrl_filings",
    "upsert_sec_filings",
    "read_prices",
    "read_fx_rates",
    "read_pnl",
    "read_technical_analysis",
    "read_fundamental_analysis",
    "read_xbrl_filings",
    "read_sec_filings",
]

logger = get_logger(__name__)


class ParquetDB:
    """
    Unified Parquet database manager for partitioned dataset.

    Handles upsert, read, and query operations across 7 tables with
    hierarchical year/month/day partitioning.
    """

    # Table schemas
    PRICES_SCHEMA = pa.schema([
        ('timestamp', pa.timestamp('us')),
        ('symbol', pa.dictionary(pa.int32(), pa.string())),
        ('currency', pa.dictionary(pa.int32(), pa.string())),
        ('open_price', pa.float64()),
        ('high_price', pa.float64()),
        ('low_price', pa.float64()),
        ('close_price', pa.float64()),
        ('volume', pa.int64()),
        ('frequency', pa.dictionary(pa.int32(), pa.string())),
        ('data_source', pa.string()),
        ('created_at', pa.timestamp('us')),
        ('updated_at', pa.timestamp('us')),
    ])

    FX_RATES_SCHEMA = pa.schema([
        ('timestamp', pa.timestamp('us')),
        ('from_currency', pa.dictionary(pa.int32(), pa.string())),
        ('to_currency', pa.dictionary(pa.int32(), pa.string())),
        ('rate', pa.float64()),
        ('source', pa.string()),
        ('created_at', pa.timestamp('us')),
        ('updated_at', pa.timestamp('us')),
    ])

    PNL_SCHEMA = pa.schema([
        ('timestamp', pa.timestamp('us')),
        ('symbol', pa.dictionary(pa.int32(), pa.string())),
        ('portfolio_id', pa.string()),
        ('quantity', pa.float64()),
        ('cost_basis_local', pa.float64()),
        ('cost_basis_eur', pa.float64()),
        ('current_price_local', pa.float64()),
        ('current_price_eur', pa.float64()),
        ('current_value_local', pa.float64()),
        ('current_value_eur', pa.float64()),
        ('unrealized_pnl_local', pa.float64()),
        ('unrealized_pnl_eur', pa.float64()),
        ('pnl_percent', pa.float64()),
        ('currency', pa.dictionary(pa.int32(), pa.string())),
        ('asset_type', pa.dictionary(pa.int32(), pa.string())),
        ('fx_rate', pa.float64()),
        ('created_at', pa.timestamp('us')),
    ])

    TECHNICAL_ANALYSIS_SCHEMA = pa.schema([
        ('timestamp', pa.timestamp('us')),
        ('symbol', pa.dictionary(pa.int32(), pa.string())),
        ('frequency', pa.dictionary(pa.int32(), pa.string())),
        ('sma_20', pa.float64()),
        ('sma_50', pa.float64()),
        ('sma_200', pa.float64()),
        ('ema_12', pa.float64()),
        ('ema_26', pa.float64()),
        ('rsi_14', pa.float64()),
        ('macd', pa.float64()),
        ('macd_signal', pa.float64()),
        ('macd_histogram', pa.float64()),
        ('bb_upper', pa.float64()),
        ('bb_middle', pa.float64()),
        ('bb_lower', pa.float64()),
        ('bb_width', pa.float64()),
        ('bb_pct', pa.float64()),
        ('volume', pa.int64()),
        ('volume_sma_20', pa.int64()),
        ('data_source', pa.string()),
        ('created_at', pa.timestamp('us')),
        ('updated_at', pa.timestamp('us')),
    ])

    FUNDAMENTAL_ANALYSIS_SCHEMA = pa.schema([
        ('timestamp', pa.timestamp('us')),
        ('symbol', pa.dictionary(pa.int32(), pa.string())),
        ('company_name', pa.string()),
        ('sector', pa.dictionary(pa.int32(), pa.string())),
        ('pe_ratio', pa.float64()),
        ('pb_ratio', pa.float64()),
        ('ps_ratio', pa.float64()),
        ('peg_ratio', pa.float64()),
        ('profit_margin', pa.float64()),
        ('operating_margin', pa.float64()),
        ('roe', pa.float64()),
        ('roa', pa.float64()),
        ('revenue_growth_yoy', pa.float64()),
        ('earnings_growth_yoy', pa.float64()),
        ('debt_to_equity', pa.float64()),
        ('current_ratio', pa.float64()),
        ('quick_ratio', pa.float64()),
        ('dividend_yield', pa.float64()),
        ('payout_ratio', pa.float64()),
        ('eps', pa.float64()),
        ('revenue_ttm', pa.float64()),
        ('net_income_ttm', pa.float64()),
        ('data_source', pa.string()),
        ('created_at', pa.timestamp('us')),
        ('updated_at', pa.timestamp('us')),
    ])

    XBRL_FILINGS_SCHEMA = pa.schema([
        ('filing_date', pa.timestamp('us')),
        ('period_end_date', pa.timestamp('us')),
        ('ticker', pa.dictionary(pa.int32(), pa.string())),
        ('cik', pa.string()),
        ('company_name', pa.string()),
        ('filing_type', pa.dictionary(pa.int32(), pa.string())),
        ('revenue', pa.float64()),
        ('cost_of_revenue', pa.float64()),
        ('gross_profit', pa.float64()),
        ('operating_income', pa.float64()),
        ('operating_expense', pa.float64()),
        ('net_income', pa.float64()),
        ('diluted_eps', pa.float64()),
        ('total_assets', pa.float64()),
        ('total_liabilities', pa.float64()),
        ('total_equity', pa.float64()),
        ('current_assets', pa.float64()),
        ('current_liabilities', pa.float64()),
        ('cash_and_equivalents', pa.float64()),
        ('operating_cash_flow', pa.float64()),
        ('investing_cash_flow', pa.float64()),
        ('financing_cash_flow', pa.float64()),
        ('capital_expenditure', pa.float64()),
        ('shares_outstanding', pa.float64()),
        ('long_term_debt', pa.float64()),
        ('short_term_debt', pa.float64()),
        ('accession_number', pa.string()),
        ('form_type', pa.string()),
        ('created_at', pa.timestamp('us')),
        ('updated_at', pa.timestamp('us')),
    ])

    SEC_FILINGS_SCHEMA = pa.schema([
        ('filing_date', pa.timestamp('us')),
        ('accession_number', pa.string()),
        ('ticker', pa.dictionary(pa.int32(), pa.string())),
        ('cik', pa.string()),
        ('company_name', pa.string()),
        ('filing_type', pa.dictionary(pa.int32(), pa.string())),
        ('form_type', pa.string()),
        ('period_end_date', pa.timestamp('us')),
        ('report_type', pa.string()),
        ('film_number', pa.string()),
        ('items', pa.string()),
        ('filings_url', pa.string()),
        ('xbrl_processed', pa.bool_()),
        ('data_source', pa.string()),
        ('created_at', pa.timestamp('us')),
        ('updated_at', pa.timestamp('us')),
    ])

    SCHEMAS = {
        'prices': PRICES_SCHEMA,
        'fx_rates': FX_RATES_SCHEMA,
        'pnl': PNL_SCHEMA,
        'technical_analysis': TECHNICAL_ANALYSIS_SCHEMA,
        'fundamental_analysis': FUNDAMENTAL_ANALYSIS_SCHEMA,
        'xbrl_filings': XBRL_FILINGS_SCHEMA,
        'sec_filings': SEC_FILINGS_SCHEMA,
    }

    def __init__(self, root_path: str = DEFAULT_OUTPUT_DIR):
        """Initialize database manager."""
        self.root_path = root_path
        os.makedirs(root_path, exist_ok=True)

    def _get_partition_path(self, table: str, timestamp: pd.Timestamp) -> str:
        """Get partition path for a timestamp."""
        year = timestamp.year
        month = timestamp.month
        day = timestamp.day
        return os.path.join(
            self.root_path,
            table,
            f"year={year}",
            f"month={month}",
            f"day={day}"
        )

    def _upsert_partition(
        self,
        table: str,
        new_data: pd.DataFrame,
        timestamp_col: str,
        key_cols: List[str],
        dictionary_cols: Optional[List[str]] = None
    ) -> Tuple[int, int]:
        """
        Upsert data into a single partition (merge-on-read pattern).

        Args:
            table: Table name
            new_data: New/updated records
            timestamp_col: Name of timestamp column
            key_cols: Columns that uniquely identify a record
            dictionary_cols: Columns to use dictionary encoding

        Returns:
            Tuple of (rows_inserted, rows_updated)
        """
        if new_data.empty:
            return 0, 0

        dictionary_cols = dictionary_cols or []
        rows_inserted = 0
        rows_updated = 0

        # Make a copy to avoid modifying original
        new_data = new_data.copy()

        # Group by partition (year/month/day)
        partition_groups = []
        for idx, row in new_data.iterrows():
            ts = row[timestamp_col]
            year = ts.year
            month = ts.month
            day = ts.day
            partition_groups.append((year, month, day, row.to_dict()))

        # Process each partition
        from collections import defaultdict
        partitions = defaultdict(list)
        for year, month, day, row_dict in partition_groups:
            partitions[(year, month, day)].append(row_dict)

        for (year, month, day), rows in partitions.items():
            partition_data = pd.DataFrame(rows)
            partition_path = os.path.join(
                self.root_path,
                table,
                f"year={year}",
                f"month={month}",
                f"day={day}"
            )
            os.makedirs(partition_path, exist_ok=True)

            # Check if partition exists
            existing_files = [f for f in os.listdir(partition_path) if f.endswith('.parquet')]

            if existing_files:
                # Read existing data
                existing_file = os.path.join(partition_path, existing_files[0])
                existing_df = pd.read_parquet(existing_file)

                # Merge: new data overwrites old by key
                combined = pd.concat([existing_df, partition_data], ignore_index=True)
                combined = combined.drop_duplicates(subset=key_cols, keep='last')

                rows_updated += len(partition_data)
                new_table = pa.Table.from_pandas(combined, preserve_index=False)
            else:
                # First write to partition
                rows_inserted += len(partition_data)
                new_table = pa.Table.from_pandas(partition_data, preserve_index=False)

            # Write with compression and dictionary encoding
            output_file = os.path.join(partition_path, "0.parquet")
            pq.write_table(
                new_table,
                output_file,
                compression='snappy',
                use_dictionary=dictionary_cols,
                version='1.0',
                coerce_timestamps='us'
            )

        return rows_inserted, rows_updated

    def upsert_prices(self, data: pd.DataFrame) -> Tuple[int, int]:
        """Upsert price data with validation."""
        if 'timestamp' not in data.columns:
            raise ValueError("Data must contain 'timestamp' column")
        
        # Validate data if robustness available
        if ROBUSTNESS_AVAILABLE:
            logger.debug(f"Validating {len(data)} price records before upsert")
            invalid_count = 0
            for idx, row in data.iterrows():
                try:
                    PRICE_VALIDATOR.validate({
                        'timestamp': str(row.get('timestamp', datetime.now())),
                        'symbol': row.get('symbol', 'UNKNOWN'),
                        'open': float(row.get('open', 0)),
                        'high': float(row.get('high', 0)),
                        'low': float(row.get('low', 0)),
                        'close': float(row.get('close', 0)),
                        'volume': float(row.get('volume', 0))
                    })
                except Exception as e:
                    invalid_count += 1
                    logger.warning(f"Price validation failed for row {idx}: {e}")
            
            if invalid_count > 0:
                logger.warning(f"Price validation: {invalid_count}/{len(data)} records failed")
        
        return self._upsert_partition(
            'prices', data, 'timestamp',
            key_cols=['symbol', 'timestamp'],
            dictionary_cols=['symbol', 'currency', 'frequency']
        )

    def upsert_fx_rates(self, data: pd.DataFrame) -> Tuple[int, int]:
        """Upsert FX rates data."""
        if 'timestamp' not in data.columns:
            raise ValueError("Data must contain 'timestamp' column")
        return self._upsert_partition(
            'fx_rates', data, 'timestamp',
            key_cols=['from_currency', 'to_currency', 'timestamp'],
            dictionary_cols=['from_currency', 'to_currency']
        )

    def upsert_pnl(self, data: pd.DataFrame) -> Tuple[int, int]:
        """Upsert P&L data."""
        if 'timestamp' not in data.columns:
            raise ValueError("Data must contain 'timestamp' column")
        return self._upsert_partition(
            'pnl', data, 'timestamp',
            key_cols=['symbol', 'timestamp'],
            dictionary_cols=['symbol', 'currency', 'asset_type']
        )

    def upsert_technical_analysis(self, data: pd.DataFrame) -> Tuple[int, int]:
        """Upsert technical analysis data with validation."""
        if 'timestamp' not in data.columns:
            raise ValueError("Data must contain 'timestamp' column")
        
        # Validate data if robustness available
        if ROBUSTNESS_AVAILABLE:
            logger.debug(f"Validating {len(data)} technical records before upsert")
            invalid_count = 0
            for idx, row in data.iterrows():
                try:
                    TECHNICAL_VALIDATOR.validate({
                        'timestamp': str(row.get('timestamp', datetime.now())),
                        'symbol': row.get('symbol', 'UNKNOWN'),
                        'rsi': float(row.get('rsi', 50)),
                        'macd': float(row.get('macd', 0)),
                        'bollinger_upper': float(row.get('bollinger_upper', 0)),
                        'bollinger_lower': float(row.get('bollinger_lower', 0))
                    })
                except Exception as e:
                    invalid_count += 1
                    logger.warning(f"Technical validation failed for row {idx}: {e}")
            
            if invalid_count > 0:
                logger.warning(f"Technical validation: {invalid_count}/{len(data)} records failed")
        
        return self._upsert_partition(
            'technical_analysis', data, 'timestamp',
            key_cols=['symbol', 'frequency', 'timestamp'],
            dictionary_cols=['symbol', 'frequency']
        )

    def upsert_fundamental_analysis(self, data: pd.DataFrame) -> Tuple[int, int]:
        """Upsert fundamental analysis data with validation."""
        if 'timestamp' not in data.columns:
            raise ValueError("Data must contain 'timestamp' column")
        
        # Validate data if robustness available
        if ROBUSTNESS_AVAILABLE:
            logger.debug(f"Validating {len(data)} fundamental records before upsert")
            invalid_count = 0
            for idx, row in data.iterrows():
                try:
                    FUNDAMENTAL_VALIDATOR.validate({
                        'timestamp': str(row.get('timestamp', datetime.now())),
                        'symbol': row.get('symbol', 'UNKNOWN'),
                        'pe_ratio': float(row.get('pe_ratio', 0)),
                        'dividend_yield': float(row.get('dividend_yield', 0)),
                        'market_cap': float(row.get('market_cap', 0))
                    })
                except Exception as e:
                    invalid_count += 1
                    logger.warning(f"Fundamental validation failed for row {idx}: {e}")
            
            if invalid_count > 0:
                logger.warning(f"Fundamental validation: {invalid_count}/{len(data)} records failed")
        
        return self._upsert_partition(
            'fundamental_analysis', data, 'timestamp',
            key_cols=['symbol', 'timestamp'],
            dictionary_cols=['symbol', 'sector']
        )

    def upsert_xbrl_filings(self, data: pd.DataFrame) -> Tuple[int, int]:
        """Upsert XBRL filings data."""
        if 'filing_date' not in data.columns:
            raise ValueError("Data must contain 'filing_date' column")
        return self._upsert_partition(
            'xbrl_filings', data, 'filing_date',
            key_cols=['ticker', 'accession_number'],
            dictionary_cols=['ticker', 'filing_type', 'form_type']
        )

    def upsert_sec_filings(self, data: pd.DataFrame) -> Tuple[int, int]:
        """Upsert SEC filings metadata."""
        if 'filing_date' not in data.columns:
            raise ValueError("Data must contain 'filing_date' column")
        return self._upsert_partition(
            'sec_filings', data, 'filing_date',
            key_cols=['accession_number'],
            dictionary_cols=['ticker', 'filing_type']
        )

    def read_table(
        self,
        table: str,
        columns: Optional[List[str]] = None,
        filters: Optional[List[Tuple]] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Optional[pd.DataFrame]:
        """
        Read data from table with optional filtering.

        Args:
            table: Table name
            columns: Specific columns to read
            filters: Row filters
            start_date: Filter by date (inclusive)
            end_date: Filter by date (inclusive)

        Returns:
            DataFrame or None if no data
        """
        table_path = os.path.join(self.root_path, table)

        if not os.path.exists(table_path):
            return None

        try:
            # Read entire dataset - note: PyArrow may add partition columns
            data = pq.read_table(
                table_path,
                columns=columns,
                filters=filters
            ).to_pandas()

            # Remove partition columns if they were auto-added
            partition_cols = ['year', 'month', 'day']
            data = data.drop(columns=[c for c in partition_cols if c in data.columns], errors='ignore')

            # Apply date filters if provided
            if start_date or end_date:
                timestamp_col = 'filing_date' if table in ['xbrl_filings', 'sec_filings'] else 'timestamp'
                if timestamp_col in data.columns:
                    if start_date:
                        data = data[data[timestamp_col] >= pd.Timestamp(start_date)]
                    if end_date:
                        data = data[data[timestamp_col] <= pd.Timestamp(end_date)]

            return data if not data.empty else None

        except Exception as e:
            logger.error(f"Error reading {table}: {e}")
            return None

    def get_schema(self, table: str) -> Optional[pa.Schema]:
        """Get schema for a table."""
        return self.SCHEMAS.get(table)

    def get_tables(self) -> List[str]:
        """Get list of all tables in database."""
        tables = []
        for name in self.SCHEMAS.keys():
            table_path = os.path.join(self.root_path, name)
            if os.path.exists(table_path):
                tables.append(name)
        return sorted(tables)

    def get_partitions(self, table: str) -> List[str]:
        """Get list of all partitions for a table."""
        table_path = os.path.join(self.root_path, table)
        if not os.path.exists(table_path):
            return []

        partitions = []
        for year_dir in os.listdir(table_path):
            if year_dir.startswith('year='):
                year_path = os.path.join(table_path, year_dir)
                for month_dir in os.listdir(year_path):
                    if month_dir.startswith('month='):
                        month_path = os.path.join(year_path, month_dir)
                        for day_dir in os.listdir(month_path):
                            if day_dir.startswith('day='):
                                partitions.append(f"{year_dir}/{month_dir}/{day_dir}")

        return sorted(partitions)


# Convenience functions for Prefect tasks
@task
def upsert_prices(data: pd.DataFrame, root_path: str = DEFAULT_OUTPUT_DIR) -> Tuple[int, int]:
    """Upsert prices task."""
    db = ParquetDB(root_path)
    return db.upsert_prices(data)


@task
def upsert_fx_rates(data: pd.DataFrame, root_path: str = DEFAULT_OUTPUT_DIR) -> Tuple[int, int]:
    """Upsert FX rates task."""
    db = ParquetDB(root_path)
    return db.upsert_fx_rates(data)


@task
def upsert_pnl(data: pd.DataFrame, root_path: str = DEFAULT_OUTPUT_DIR) -> Tuple[int, int]:
    """Upsert P&L task."""
    db = ParquetDB(root_path)
    return db.upsert_pnl(data)


@task
def upsert_technical_analysis(data: pd.DataFrame, root_path: str = DEFAULT_OUTPUT_DIR) -> Tuple[int, int]:
    """Upsert technical analysis task."""
    db = ParquetDB(root_path)
    return db.upsert_technical_analysis(data)


@task
def upsert_fundamental_analysis(data: pd.DataFrame, root_path: str = DEFAULT_OUTPUT_DIR) -> Tuple[int, int]:
    """Upsert fundamental analysis task."""
    db = ParquetDB(root_path)
    return db.upsert_fundamental_analysis(data)


@task
def upsert_xbrl_filings(data: pd.DataFrame, root_path: str = DEFAULT_OUTPUT_DIR) -> Tuple[int, int]:
    """Upsert XBRL filings task."""
    db = ParquetDB(root_path)
    return db.upsert_xbrl_filings(data)


@task
def upsert_sec_filings(data: pd.DataFrame, root_path: str = DEFAULT_OUTPUT_DIR) -> Tuple[int, int]:
    """Upsert SEC filings task."""
    db = ParquetDB(root_path)
    return db.upsert_sec_filings(data)


@task
def read_prices(
    columns: Optional[List[str]] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    root_path: str = DEFAULT_OUTPUT_DIR,
) -> Optional[pd.DataFrame]:
    """Read prices task."""
    db = ParquetDB(root_path)
    return db.read_table('prices', columns=columns, start_date=start_date, end_date=end_date)


@task
def read_fx_rates(
    columns: Optional[List[str]] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    root_path: str = DEFAULT_OUTPUT_DIR,
) -> Optional[pd.DataFrame]:
    """Read FX rates task."""
    db = ParquetDB(root_path)
    return db.read_table('fx_rates', columns=columns, start_date=start_date, end_date=end_date)


@task
def read_pnl(
    columns: Optional[List[str]] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    root_path: str = DEFAULT_OUTPUT_DIR,
) -> Optional[pd.DataFrame]:
    """Read P&L task."""
    db = ParquetDB(root_path)
    return db.read_table('pnl', columns=columns, start_date=start_date, end_date=end_date)


@task
def read_technical_analysis(
    columns: Optional[List[str]] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    root_path: str = DEFAULT_OUTPUT_DIR,
) -> Optional[pd.DataFrame]:
    """Read technical analysis task."""
    db = ParquetDB(root_path)
    return db.read_table('technical_analysis', columns=columns, start_date=start_date, end_date=end_date)


@task
def read_fundamental_analysis(
    columns: Optional[List[str]] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    root_path: str = DEFAULT_OUTPUT_DIR,
) -> Optional[pd.DataFrame]:
    """Read fundamental analysis task."""
    db = ParquetDB(root_path)
    return db.read_table('fundamental_analysis', columns=columns, start_date=start_date, end_date=end_date)


@task
def read_xbrl_filings(
    columns: Optional[List[str]] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    root_path: str = DEFAULT_OUTPUT_DIR,
) -> Optional[pd.DataFrame]:
    """Read XBRL filings task."""
    db = ParquetDB(root_path)
    return db.read_table('xbrl_filings', columns=columns, start_date=start_date, end_date=end_date)


@task
def read_sec_filings(
    columns: Optional[List[str]] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    root_path: str = DEFAULT_OUTPUT_DIR,
) -> Optional[pd.DataFrame]:
    """Read SEC filings task."""
    db = ParquetDB(root_path)
    return db.read_table('sec_filings', columns=columns, start_date=start_date, end_date=end_date)
