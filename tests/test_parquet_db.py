"""
Comprehensive tests for Parquet Database Management Layer.

Tests all 7 tables:
- prices
- fx_rates
- pnl
- technical_analysis
- fundamental_analysis
- xbrl_filings
- sec_filings
"""

import os
import shutil
import tempfile
from datetime import datetime, timedelta

import pandas as pd
import pytest

from src.parquet_db import ParquetDB


@pytest.fixture
def temp_db():
    """Create temporary database directory."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # Cleanup
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)


@pytest.fixture
def db(temp_db):
    """Create ParquetDB instance with temp directory."""
    return ParquetDB(root_path=temp_db)


# ===== PRICES TABLE TESTS =====

def test_upsert_prices_insert(db):
    """Test inserting new price data."""
    now = pd.Timestamp(datetime.now())
    data = pd.DataFrame({
        'timestamp': [now],
        'symbol': ['AAPL'],
        'currency': ['USD'],
        'open_price': [150.0],
        'high_price': [152.0],
        'low_price': [149.5],
        'close_price': [151.5],
        'volume': [1000000],
        'frequency': ['DAILY'],
        'data_source': ['Yahoo Finance'],
        'created_at': [now],
        'updated_at': [now],
    })

    inserted, updated = db.upsert_prices(data)
    assert inserted == 1
    assert updated == 0

    # Verify data was written
    result = db.read_table('prices')
    assert result is not None
    assert len(result) == 1
    assert result.iloc[0]['symbol'] == 'AAPL'
    assert result.iloc[0]['close_price'] == 151.5


def test_upsert_prices_update(db):
    """Test updating existing price data."""
    now = pd.Timestamp(datetime.now())
    
    # Insert initial data
    data1 = pd.DataFrame({
        'timestamp': [now],
        'symbol': ['AAPL'],
        'currency': ['USD'],
        'open_price': [150.0],
        'high_price': [152.0],
        'low_price': [149.5],
        'close_price': [151.5],
        'volume': [1000000],
        'frequency': ['DAILY'],
        'data_source': ['Yahoo Finance'],
        'created_at': [now],
        'updated_at': [now],
    })
    inserted, _ = db.upsert_prices(data1)
    assert inserted == 1

    # Update with new price
    data2 = pd.DataFrame({
        'timestamp': [now],
        'symbol': ['AAPL'],
        'currency': ['USD'],
        'open_price': [150.0],
        'high_price': [153.0],  # Changed
        'low_price': [149.5],
        'close_price': [152.5],  # Changed
        'volume': [1100000],     # Changed
        'frequency': ['DAILY'],
        'data_source': ['Yahoo Finance'],
        'created_at': [now],
        'updated_at': [now],
    })
    inserted, updated = db.upsert_prices(data2)
    assert updated > 0  # Should be treated as update

    # Verify update
    result = db.read_table('prices')
    assert len(result) == 1
    assert result.iloc[0]['close_price'] == 152.5
    assert result.iloc[0]['volume'] == 1100000


def test_upsert_prices_multiple_symbols(db):
    """Test inserting multiple symbols."""
    now = pd.Timestamp(datetime.now())
    data = pd.DataFrame({
        'timestamp': [now, now, now],
        'symbol': ['AAPL', 'MSFT', 'GOOGL'],
        'currency': ['USD', 'USD', 'USD'],
        'open_price': [150.0, 310.0, 130.0],
        'high_price': [152.0, 312.0, 132.0],
        'low_price': [149.5, 309.5, 129.5],
        'close_price': [151.5, 311.5, 131.5],
        'volume': [1000000, 800000, 600000],
        'frequency': ['DAILY', 'DAILY', 'DAILY'],
        'data_source': ['Yahoo', 'Yahoo', 'Yahoo'],
        'created_at': [now, now, now],
        'updated_at': [now, now, now],
    })

    inserted, _ = db.upsert_prices(data)
    assert inserted == 3

    result = db.read_table('prices')
    assert len(result) == 3
    assert set(result['symbol'].unique()) == {'AAPL', 'MSFT', 'GOOGL'}


# ===== FX_RATES TABLE TESTS =====

def test_upsert_fx_rates(db):
    """Test inserting FX rates."""
    now = pd.Timestamp(datetime.now())
    data = pd.DataFrame({
        'timestamp': [now, now, now],
        'from_currency': ['USD', 'GBP', 'AUD'],
        'to_currency': ['EUR', 'EUR', 'EUR'],
        'rate': [0.92, 1.17, 0.61],
        'source': ['exchangerate-api', 'exchangerate-api', 'exchangerate-api'],
        'created_at': [now, now, now],
        'updated_at': [now, now, now],
    })

    inserted, _ = db.upsert_fx_rates(data)
    assert inserted == 3

    result = db.read_table('fx_rates')
    assert len(result) == 3
    assert result[result['from_currency'] == 'USD'].iloc[0]['rate'] == 0.92


# ===== PNL TABLE TESTS =====

def test_upsert_pnl(db):
    """Test inserting P&L data."""
    now = pd.Timestamp(datetime.now())
    data = pd.DataFrame({
        'timestamp': [now],
        'symbol': ['AAPL'],
        'portfolio_id': ['main'],
        'quantity': [100.0],
        'cost_basis_local': [15000.0],
        'cost_basis_eur': [13800.0],
        'current_price_local': [160.0],
        'current_price_eur': [147.2],
        'current_value_local': [16000.0],
        'current_value_eur': [14720.0],
        'unrealized_pnl_local': [1000.0],
        'unrealized_pnl_eur': [920.0],
        'pnl_percent': [6.67],
        'currency': ['USD'],
        'asset_type': ['STOCK'],
        'fx_rate': [0.92],
        'created_at': [now],
    })

    inserted, _ = db.upsert_pnl(data)
    assert inserted == 1

    result = db.read_table('pnl')
    assert len(result) == 1
    assert result.iloc[0]['unrealized_pnl_eur'] == 920.0


# ===== TECHNICAL_ANALYSIS TABLE TESTS =====

def test_upsert_technical_analysis(db):
    """Test inserting technical analysis data."""
    now = pd.Timestamp(datetime.now())
    data = pd.DataFrame({
        'timestamp': [now],
        'symbol': ['AAPL'],
        'frequency': ['DAILY'],
        'sma_20': [234.5],
        'sma_50': [230.0],
        'sma_200': [225.0],
        'ema_12': [233.0],
        'ema_26': [232.0],
        'rsi_14': [65.2],
        'macd': [2.1],
        'macd_signal': [1.8],
        'macd_histogram': [0.3],
        'bb_upper': [240.3],
        'bb_middle': [234.5],
        'bb_lower': [228.7],
        'bb_width': [11.6],
        'bb_pct': [0.65],
        'volume': [1000000],
        'volume_sma_20': [900000],
        'data_source': ['Alpha Vantage'],
        'created_at': [now],
        'updated_at': [now],
    })

    inserted, _ = db.upsert_technical_analysis(data)
    assert inserted == 1

    result = db.read_table('technical_analysis')
    assert len(result) == 1
    assert result.iloc[0]['rsi_14'] == 65.2
    assert result.iloc[0]['sma_20'] == 234.5


# ===== FUNDAMENTAL_ANALYSIS TABLE TESTS =====

def test_upsert_fundamental_analysis(db):
    """Test inserting fundamental analysis data."""
    now = pd.Timestamp(datetime.now())
    data = pd.DataFrame({
        'timestamp': [now],
        'symbol': ['AAPL'],
        'company_name': ['Apple Inc'],
        'sector': ['Technology'],
        'pe_ratio': [28.5],
        'pb_ratio': [42.1],
        'ps_ratio': [7.2],
        'peg_ratio': [2.1],
        'profit_margin': [25.5],
        'operating_margin': [30.1],
        'roe': [85.3],
        'roa': [16.2],
        'revenue_growth_yoy': [5.2],
        'earnings_growth_yoy': [8.1],
        'debt_to_equity': [2.1],
        'current_ratio': [1.2],
        'quick_ratio': [1.1],
        'dividend_yield': [0.42],
        'payout_ratio': [15.0],
        'eps': [6.05],
        'revenue_ttm': [383285000000],
        'net_income_ttm': [93736000000],
        'data_source': ['SEC XBRL'],
        'created_at': [now],
        'updated_at': [now],
    })

    inserted, _ = db.upsert_fundamental_analysis(data)
    assert inserted == 1

    result = db.read_table('fundamental_analysis')
    assert len(result) == 1
    assert result.iloc[0]['pe_ratio'] == 28.5
    assert result.iloc[0]['roe'] == 85.3


# ===== XBRL_FILINGS TABLE TESTS =====

def test_upsert_xbrl_filings(db):
    """Test inserting XBRL filing data."""
    filing_date = pd.Timestamp(datetime.now())
    period_end = pd.Timestamp(datetime.now()) - timedelta(days=30)
    
    data = pd.DataFrame({
        'filing_date': [filing_date],
        'period_end_date': [period_end],
        'ticker': ['AAPL'],
        'cik': ['0000320193'],
        'company_name': ['Apple Inc'],
        'filing_type': ['10-K'],
        'revenue': [383285000000.0],
        'cost_of_revenue': [214537000000.0],
        'gross_profit': [168748000000.0],
        'operating_income': [114318000000.0],
        'operating_expense': [54430000000.0],
        'net_income': [93736000000.0],
        'diluted_eps': [6.05],
        'total_assets': [352755000000.0],
        'total_liabilities': [302646000000.0],
        'total_equity': [50109000000.0],
        'current_assets': [143713000000.0],
        'current_liabilities': [106385000000.0],
        'cash_and_equivalents': [23646000000.0],
        'operating_cash_flow': [110543000000.0],
        'investing_cash_flow': [-42016000000.0],
        'financing_cash_flow': [-65520000000.0],
        'capital_expenditure': [13852000000.0],
        'shares_outstanding': [15506000000.0],
        'long_term_debt': [103769000000.0],
        'short_term_debt': [9848000000.0],
        'accession_number': ['0000320193-24-000077'],
        'form_type': ['10-K'],
        'created_at': [filing_date],
        'updated_at': [filing_date],
    })

    inserted, _ = db.upsert_xbrl_filings(data)
    assert inserted == 1

    result = db.read_table('xbrl_filings')
    assert len(result) == 1
    assert result.iloc[0]['revenue'] == 383285000000.0
    assert result.iloc[0]['net_income'] == 93736000000.0


# ===== SEC_FILINGS TABLE TESTS =====

def test_upsert_sec_filings(db):
    """Test inserting SEC filing metadata."""
    filing_date = pd.Timestamp(datetime.now())
    period_end = pd.Timestamp(datetime.now()) - timedelta(days=30)
    
    data = pd.DataFrame({
        'filing_date': [filing_date],
        'accession_number': ['0000320193-24-000077'],
        'ticker': ['AAPL'],
        'cik': ['0000320193'],
        'company_name': ['Apple Inc'],
        'filing_type': ['10-K'],
        'form_type': ['10-K'],
        'period_end_date': [period_end],
        'report_type': ['10-K'],
        'film_number': ['241234567'],
        'items': ['Part I, Part II, Part III, Part IV'],
        'filings_url': ['https://www.sec.gov/Archives/edgar/...'],
        'xbrl_processed': [True],
        'data_source': ['SEC EDGAR'],
        'created_at': [filing_date],
        'updated_at': [filing_date],
    })

    inserted, _ = db.upsert_sec_filings(data)
    assert inserted == 1

    result = db.read_table('sec_filings')
    assert len(result) == 1
    assert result.iloc[0]['xbrl_processed'] == True


# ===== PARTITIONING TESTS =====

def test_partitions_created_correctly(db):
    """Test that partitions are created in correct directory structure."""
    now = pd.Timestamp(datetime.now())
    data = pd.DataFrame({
        'timestamp': [now],
        'symbol': ['AAPL'],
        'currency': ['USD'],
        'open_price': [150.0],
        'high_price': [152.0],
        'low_price': [149.5],
        'close_price': [151.5],
        'volume': [1000000],
        'frequency': ['DAILY'],
        'data_source': ['Yahoo'],
        'created_at': [now],
        'updated_at': [now],
    })

    db.upsert_prices(data)

    # Verify partition structure
    year = now.year
    month = now.month
    day = now.day
    partition_path = os.path.join(db.root_path, 'prices', f'year={year}', f'month={month}', f'day={day}')
    assert os.path.exists(partition_path)
    assert os.path.exists(os.path.join(partition_path, '0.parquet'))


def test_multiple_partitions(db):
    """Test writing to multiple date partitions."""
    date1 = pd.Timestamp('2024-11-15')
    date2 = pd.Timestamp('2024-11-16')
    
    data = pd.DataFrame({
        'timestamp': [date1, date2],
        'symbol': ['AAPL', 'AAPL'],
        'currency': ['USD', 'USD'],
        'open_price': [150.0, 152.0],
        'high_price': [152.0, 154.0],
        'low_price': [149.5, 151.5],
        'close_price': [151.5, 153.5],
        'volume': [1000000, 1100000],
        'frequency': ['DAILY', 'DAILY'],
        'data_source': ['Yahoo', 'Yahoo'],
        'created_at': [date1, date2],
        'updated_at': [date1, date2],
    })

    inserted, _ = db.upsert_prices(data)
    assert inserted == 2

    # Verify both partitions exist
    path1 = os.path.join(db.root_path, 'prices', 'year=2024', 'month=11', 'day=15')
    path2 = os.path.join(db.root_path, 'prices', 'year=2024', 'month=11', 'day=16')
    assert os.path.exists(path1)
    assert os.path.exists(path2)


# ===== READ TESTS =====

def test_read_prices_with_columns(db):
    """Test reading specific columns."""
    now = pd.Timestamp(datetime.now())
    data = pd.DataFrame({
        'timestamp': [now],
        'symbol': ['AAPL'],
        'currency': ['USD'],
        'open_price': [150.0],
        'high_price': [152.0],
        'low_price': [149.5],
        'close_price': [151.5],
        'volume': [1000000],
        'frequency': ['DAILY'],
        'data_source': ['Yahoo'],
        'created_at': [now],
        'updated_at': [now],
    })

    db.upsert_prices(data)

    # Read only specific columns
    result = db.read_table('prices', columns=['symbol', 'close_price'])
    assert result is not None
    assert set(result.columns) == {'symbol', 'close_price'}


def test_read_with_date_range(db):
    """Test reading with date range filter."""
    date1 = pd.Timestamp('2024-11-10')
    date2 = pd.Timestamp('2024-11-15')
    date3 = pd.Timestamp('2024-11-20')
    
    data = pd.DataFrame({
        'timestamp': [date1, date2, date3],
        'symbol': ['AAPL', 'AAPL', 'AAPL'],
        'currency': ['USD', 'USD', 'USD'],
        'open_price': [150.0, 152.0, 155.0],
        'high_price': [152.0, 154.0, 157.0],
        'low_price': [149.5, 151.5, 154.5],
        'close_price': [151.5, 153.5, 156.5],
        'volume': [1000000, 1100000, 1200000],
        'frequency': ['DAILY', 'DAILY', 'DAILY'],
        'data_source': ['Yahoo', 'Yahoo', 'Yahoo'],
        'created_at': [date1, date2, date3],
        'updated_at': [date1, date2, date3],
    })

    db.upsert_prices(data)

    # Read with date range
    result = db.read_table('prices', start_date=date2, end_date=date2)
    assert result is not None
    assert len(result) == 1
    assert result.iloc[0]['close_price'] == 153.5


# ===== SCHEMA TESTS =====

def test_get_schema(db):
    """Test retrieving table schema."""
    schema = db.get_schema('prices')
    assert schema is not None
    assert 'timestamp' in schema.names
    assert 'symbol' in schema.names
    assert 'close_price' in schema.names


def test_get_tables(db):
    """Test listing all tables."""
    now = pd.Timestamp(datetime.now())
    prices_data = pd.DataFrame({
        'timestamp': [now],
        'symbol': ['AAPL'],
        'currency': ['USD'],
        'open_price': [150.0],
        'high_price': [152.0],
        'low_price': [149.5],
        'close_price': [151.5],
        'volume': [1000000],
        'frequency': ['DAILY'],
        'data_source': ['Yahoo'],
        'created_at': [now],
        'updated_at': [now],
    })
    db.upsert_prices(prices_data)

    fx_data = pd.DataFrame({
        'timestamp': [now],
        'from_currency': ['USD'],
        'to_currency': ['EUR'],
        'rate': [0.92],
        'source': ['exchangerate-api'],
        'created_at': [now],
        'updated_at': [now],
    })
    db.upsert_fx_rates(fx_data)

    tables = db.get_tables()
    assert 'prices' in tables
    assert 'fx_rates' in tables


# ===== ERROR HANDLING TESTS =====

def test_upsert_prices_missing_timestamp(db):
    """Test error when timestamp column is missing."""
    data = pd.DataFrame({
        'symbol': ['AAPL'],
        'close_price': [151.5],
    })

    with pytest.raises(ValueError, match="timestamp"):
        db.upsert_prices(data)


def test_read_nonexistent_table(db):
    """Test reading from table that doesn't exist."""
    result = db.read_table('nonexistent_table')
    assert result is None


# ===== MERGE/UPSERT BEHAVIOR TESTS =====

def test_upsert_merge_behavior(db):
    """Test that upsert correctly merges data."""
    now = pd.Timestamp(datetime.now())
    
    # First insert
    data1 = pd.DataFrame({
        'timestamp': [now, now],
        'symbol': ['AAPL', 'MSFT'],
        'currency': ['USD', 'USD'],
        'open_price': [150.0, 310.0],
        'high_price': [152.0, 312.0],
        'low_price': [149.5, 309.5],
        'close_price': [151.5, 311.5],
        'volume': [1000000, 800000],
        'frequency': ['DAILY', 'DAILY'],
        'data_source': ['Yahoo', 'Yahoo'],
        'created_at': [now, now],
        'updated_at': [now, now],
    })
    db.upsert_prices(data1)

    # Second insert with one update and one new
    data2 = pd.DataFrame({
        'timestamp': [now, now],
        'symbol': ['AAPL', 'GOOGL'],  # AAPL update, GOOGL new
        'currency': ['USD', 'USD'],
        'open_price': [151.0, 130.0],  # Changed
        'high_price': [153.0, 132.0],
        'low_price': [150.5, 129.5],
        'close_price': [152.5, 131.5],  # Changed
        'volume': [1100000, 600000],    # Changed
        'frequency': ['DAILY', 'DAILY'],
        'data_source': ['Yahoo', 'Yahoo'],
        'created_at': [now, now],
        'updated_at': [now, now],
    })
    db.upsert_prices(data2)

    # Verify final state: 3 rows with AAPL and GOOGL updated
    result = db.read_table('prices')
    assert len(result) == 3
    
    aapl = result[result['symbol'] == 'AAPL'].iloc[0]
    assert aapl['close_price'] == 152.5  # Updated
    
    googl = result[result['symbol'] == 'GOOGL'].iloc[0]
    assert googl['close_price'] == 131.5  # New


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
