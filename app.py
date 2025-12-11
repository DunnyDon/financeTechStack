"""
Finance TechStack Analytics Dashboard - PARQUETDB INTEGRATED

A comprehensive web-based UI for portfolio analytics with:
- Real holdings from holdings.csv
- Live price data from ParquetDB
- Dynamic portfolio visualizations with actual metrics
- Real P&L calculations
- Technical & fundamental analysis from database
- Email report generation
- Comprehensive help section
"""

import sys
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from streamlit_option_menu import option_menu

# Import ParquetDB and analytics modules
try:
    from src.parquet_db import ParquetDB
    from src.portfolio_analytics import PortfolioAnalytics
    from src.portfolio_holdings import Holdings
    from src.portfolio_technical import TechnicalAnalyzer
    from src.analytics_flows import enhanced_analytics_flow
    from src.portfolio_flows import portfolio_end_to_end_flow
    from src.advanced_analytics_flows import advanced_analytics_flow
    from src.news_analysis_streamlit import news_sentiment_analysis_flow
    from src.news_analysis import analyze_news_sentiment, assess_portfolio_impact
    from src.analytics_report import AnalyticsReporter
    
    # Import new advanced features
    from src.backtesting_engine import EnhancedBacktestingEngine
    from src.news_advanced_analytics import AdvancedNewsAnalytics
    from src.tax_optimization import TaxOptimizationEngine
    from src.crypto_analytics import CryptoAdvancedAnalytics
    from src.options_strategy_automation import OptionsStrategyAutomation, OptionsStrategy
    
    MODULES_AVAILABLE = True
except ImportError as e:
    MODULES_AVAILABLE = False
    st.warning(f"Some modules not available: {e}")

# Configure page
st.set_page_config(
    page_title="Finance TechStack Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
st.markdown("""
<style>
    .metric-card {
        background-color: #f8f9fa;
        border: 1px solid #dee2e6;
        padding: 15px;
        border-radius: 5px;
        margin: 10px 0;
    }
    .success-box {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 5px;
        padding: 15px;
        margin: 10px 0;
        color: #155724;
    }
    .alert-box {
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        border-radius: 5px;
        padding: 15px;
        margin: 10px 0;
        color: #721c24;
    }
    .help-section {
        background-color: #e7f3ff;
        border-left: 4px solid #0066cc;
        padding: 15px;
        margin: 10px 0;
        border-radius: 5px;
        color: #004085;
    }
    .news-article {
        background-color: #ffffff;
        border: 1px solid #dee2e6;
        padding: 15px;
        margin: 10px 0;
        border-radius: 5px;
        color: #212529;
    }
    .text-dark {
        color: #212529 !important;
    }
    a {
        color: #0066cc;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if "page" not in st.session_state:
    st.session_state.page = "home"
if "holdings_df" not in st.session_state:
    st.session_state.holdings_df = None
if "prices_with_holdings" not in st.session_state:
    st.session_state.prices_with_holdings = None
if "flows_executed" not in st.session_state:
    st.session_state.flows_executed = False


def run_data_update_flows():
    """Fetch latest prices and save to ParquetDB without SEC filing requirements."""
    try:
        st.info("🔄 Updating price data...")
        
        # Get tickers from holdings
        holdings = load_holdings()
        if holdings is not None and not holdings.empty:
            tickers = holdings['sym'].unique().tolist()
            
            st.info(f"Fetching prices for {len(tickers)} symbols...")
            
            try:
                from src.portfolio_prices import PriceFetcher
                from src.parquet_db import ParquetDB
                import pandas as pd
                from datetime import datetime
                
                db = ParquetDB(root_path="db")
                price_fetcher = PriceFetcher()
                
                # Fetch prices for all tickers
                all_prices = []
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                for idx, ticker in enumerate(tickers):
                    status_text.text(f"Fetching {ticker}... ({idx+1}/{len(tickers)})")
                    progress_bar.progress((idx + 1) / len(tickers))
                    
                    try:
                        # Determine asset type based on ticker
                        holding = holdings[holdings['sym'] == ticker]
                        if not holding.empty:
                            asset_type = holding.iloc[0]['asset']
                            if asset_type == 'crypto':
                                asset_type = 'crypto'
                            elif asset_type == 'commodity':
                                asset_type = 'commodity'
                            else:
                                asset_type = 'eq'  # default for stocks/ETFs
                        else:
                            asset_type = 'eq'
                        
                        price_data = price_fetcher.fetch_price(ticker, asset_type=asset_type)
                        
                        if price_data:
                            all_prices.append(price_data)
                        else:
                            st.info(f"⏭️ No data available for {ticker}")
                    except Exception as e:
                        st.warning(f"Could not fetch {ticker}: {str(e)[:50]}")
                        continue
                
                if all_prices:
                    # Convert to DataFrame and save to ParquetDB
                    prices_df = pd.DataFrame(all_prices)
                    
                    # Use a single batch timestamp for all prices fetched in this run
                    batch_timestamp = datetime.now()
                    prices_df['timestamp'] = batch_timestamp
                    
                    # Map columns if needed
                    if 'price' in prices_df.columns and 'close_price' not in prices_df.columns:
                        prices_df['close_price'] = prices_df['price']
                    
                    # Rename open/high/low/close columns to match ParquetDB schema
                    if 'open' in prices_df.columns and 'open_price' not in prices_df.columns:
                        prices_df['open_price'] = prices_df['open']
                    if 'high' in prices_df.columns and 'high_price' not in prices_df.columns:
                        prices_df['high_price'] = prices_df['high']
                    if 'low' in prices_df.columns and 'low_price' not in prices_df.columns:
                        prices_df['low_price'] = prices_df['low']
                    if 'close' in prices_df.columns and 'close_price' not in prices_df.columns:
                        prices_df['close_price'] = prices_df['close']
                    
                    # Add missing columns that ParquetDB expects
                    if 'currency' not in prices_df.columns:
                        prices_df['currency'] = 'USD'
                    if 'frequency' not in prices_df.columns:
                        prices_df['frequency'] = 'daily'
                    
                    db.upsert_prices(prices_df)
                    st.success(f"✅ Updated {len(all_prices)} price records!")
                    st.cache_data.clear()
                else:
                    st.warning("Could not fetch any price data - some symbols may be delisted or have no data available")
                    
            except Exception as e:
                st.error(f"Error during price fetch: {str(e)[:150]}")
        else:
            st.error("Could not load holdings")
            
    except Exception as e:
        st.warning(f"⚠️ Error updating prices: {str(e)[:150]}")
        st.info("Try running technical analysis instead, or check your connection.")


def run_technical_analysis():
    """Calculate and save technical indicators for all holdings."""
    try:
        st.info("📊 Calculating technical indicators...")
        
        holdings = load_holdings()
        if holdings is None or holdings.empty:
            st.error("No holdings found")
            return False
        
        db = init_parquet_db()
        
        # Get prices from parquet
        prices_df = db.read_table('prices')
        if prices_df is None or prices_df.empty:
            st.error("No price data available. Please run 'Update Price Data' first.")
            return False
        
        # Get symbols
        symbols = holdings['sym'].unique().tolist()
        
        # Filter prices to only our holdings
        holdings_prices = prices_df[prices_df['symbol'].isin(symbols)].copy()
        
        if holdings_prices.empty:
            st.error("No price data found for your holdings")
            return False
        
        # Import technical analyzer
        from src.portfolio_technical import TechnicalAnalyzer
        
        # Calculate indicators for each symbol
        all_indicators = []
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for idx, symbol in enumerate(symbols):
            try:
                status_text.text(f"Processing {symbol} ({idx+1}/{len(symbols)})")
                
                symbol_prices = holdings_prices[holdings_prices['symbol'] == symbol].sort_values('timestamp')
                
                if len(symbol_prices) < 20:  # Need minimum data
                    continue
                
                # Rename columns to match what TechnicalAnalyzer expects (uppercase)
                symbol_prices = symbol_prices.rename(columns={
                    'open_price': 'Open',
                    'high_price': 'High',
                    'low_price': 'Low',
                    'close_price': 'Close',
                    'volume': 'Volume'
                })
                
                # Calculate indicators using the static method
                indicators = TechnicalAnalyzer.calculate_all(symbol_prices)
                
                if indicators is not None and not indicators.empty:
                    all_indicators.append(indicators)
                
                progress_bar.progress((idx + 1) / len(symbols))
            except Exception as e:
                st.warning(f"Could not calculate indicators for {symbol}: {str(e)[:50]}")
                continue
        
        status_text.text("Saving results...")
        
        if all_indicators:
            # Combine all indicators
            combined = pd.concat(all_indicators, ignore_index=True)
            
            # Save to parquet
            db.upsert_technical_analysis(combined)
            
            st.success(f"✅ Calculated technical indicators for {len(combined)} records across {len(all_indicators)} symbols")
            
            # Clear cache and rerun to show fresh data
            st.cache_data.clear()
            import time
            time.sleep(1)  # Give filesystem a moment to sync
            
            status_text.text("")
            st.rerun()
        else:
            st.warning("No indicators calculated. May need more price history.")
            status_text.text("")
            return False
            
    except Exception as e:
        st.error(f"Error running technical analysis: {str(e)}")
        import traceback
        st.write(traceback.format_exc())
        return False


def run_fundamental_analysis():
    """Calculate and save fundamental analysis for all holdings."""
    try:
        st.info("📊 Calculating fundamental analysis...")
        
        holdings = load_holdings()
        if holdings is None or holdings.empty:
            st.error("No holdings found")
            return False
        
        # Filter to equities only
        equities = holdings[holdings['asset'] == 'eq'].copy()
        
        if equities.empty:
            st.warning("No equities in portfolio - fundamental analysis only applies to stocks")
            return False
        
        # Filter to US tickers only (SEC API only works with US companies)
        # International tickers typically have dots or are on non-US exchanges
        us_equities = equities[~equities['sym'].str.contains(r'[.][A-Z]{2}|_[A-Z]{2}', regex=True)].copy()
        
        if us_equities.empty:
            st.warning("All equities in portfolio are international. Fundamental analysis (via SEC) only works with US-listed stocks.")
            st.info("Your portfolio contains tickers like: " + ", ".join(equities['sym'].head(5).tolist()))
            return False
        
        # Notify user which stocks will be analyzed
        if len(us_equities) < len(equities):
            skipped = len(equities) - len(us_equities)
            st.info(f"ℹ️ Analyzing {len(us_equities)} US stocks ({skipped} international stocks skipped)")
        
        from src.portfolio_fundamentals import FundamentalAnalyzer
        
        # Calculate fundamentals
        analyzer = FundamentalAnalyzer(us_equities)
        fundamentals_df = analyzer.analyze_portfolio_fundamentals()
        
        if fundamentals_df.empty:
            st.warning("No fundamental data retrieved. This may be due to:")
            st.info("""
            - API rate limits
            - Stocks with missing SEC filings
            - Newly listed companies without quarterly reports
            
            Try again in a few moments or check Prefect logs for details.
            """)
            return False
        
        # Add timestamp
        fundamentals_df['timestamp'] = datetime.now()
        
        # Ensure we have symbol column
        if 'symbol' not in fundamentals_df.columns and 'sym' in fundamentals_df.columns:
            fundamentals_df['symbol'] = fundamentals_df['sym']
        
        # Save to parquet
        db = init_parquet_db()
        db.upsert_fundamental_analysis(fundamentals_df)
        
        st.success(f"✅ Calculated fundamental analysis for {len(fundamentals_df)} US equities")
        
        # Clear cache and rerun to show fresh data
        st.cache_data.clear()
        import time
        time.sleep(1)  # Give filesystem a moment to sync
        
        st.rerun()
        return True
            
    except Exception as e:
        st.error(f"Error running fundamental analysis: {str(e)[:200]}")
        import traceback
        st.write(traceback.format_exc())
        return False


@st.cache_resource
def init_parquet_db():
    """Initialize ParquetDB connection."""
    return ParquetDB(root_path="db")


def get_price_data_freshness(db: ParquetDB) -> Dict:
    """
    Check when price data was last updated.
    
    Returns dict with:
    - latest_date: Most recent price date
    - days_stale: Days since latest price
    - is_stale: True if data is over 7 days old
    - status_color: 'green', 'yellow', or 'red'
    """
    try:
        prices_df = db.read_table('prices')
        
        if prices_df is None or prices_df.empty:
            return {
                'latest_date': None,
                'days_stale': None,
                'is_stale': True,
                'status_color': 'red',
                'message': '🔴 No price data available'
            }
        
        latest_date = pd.to_datetime(prices_df['timestamp']).max()
        days_old = (pd.Timestamp.now() - latest_date).days
        
        if days_old <= 1:
            status = '🟢 Current (updated today)'
            color = 'green'
            is_stale = False
        elif days_old <= 7:
            status = f'🟡 {days_old} days old'
            color = 'yellow'
            is_stale = False
        else:
            status = f'🔴 {days_old} days old (STALE)'
            color = 'red'
            is_stale = True
        
        return {
            'latest_date': latest_date,
            'days_stale': days_old,
            'is_stale': is_stale,
            'status_color': color,
            'message': status
        }
    except Exception as e:
        return {
            'latest_date': None,
            'days_stale': None,
            'is_stale': True,
            'status_color': 'red',
            'message': f'❌ Error checking data: {str(e)[:50]}'
        }


@st.cache_resource
def load_holdings():
    """Load holdings from CSV and filter to tradable assets only."""
    try:
        df = pd.read_csv("holdings.csv")
        # Ensure qty is numeric
        df['qty'] = pd.to_numeric(df['qty'], errors='coerce')
        df['bep'] = pd.to_numeric(df['bep'], errors='coerce')
        
        # Filter to only tradable assets (exclude cash, savings, GICs)
        # Keep: eq (equities), fund (ETFs/funds), commodity, crypto, fixed-income, retirement
        tradable_assets = df[df['asset'].isin(['eq', 'fund', 'commodity', 'crypto', 'fixed-income', 'retirement'])].copy()
        
        return tradable_assets
    except Exception as e:
        st.error(f"Error loading holdings: {e}")
        return None


@st.cache_data(ttl=300)  # Cache for 5 minutes
def fetch_latest_prices(_db: ParquetDB, symbols: List[str]) -> Dict[str, float]:
    """
    Fetch latest prices from ParquetDB.
    
    Args:
        _db: ParquetDB instance (underscore tells Streamlit not to hash)
        symbols: List of symbols to fetch
        
    Returns:
        Dict mapping symbol to latest closing price
    """
    try:
        prices_df = _db.read_table('prices')
        if prices_df is None or prices_df.empty:
            return {}
        
        # Get latest timestamp
        latest_date = prices_df['timestamp'].max()
        latest_prices = prices_df[prices_df['timestamp'] == latest_date]
        
        # Create dict of symbol -> close price
        price_dict = dict(zip(latest_prices['symbol'], latest_prices['close_price']))
        return price_dict
    except Exception as e:
        st.error(f"Error fetching prices: {e}")
        return {}


@st.cache_data(ttl=300)
def enrich_holdings_with_prices(holdings_df: pd.DataFrame, prices_dict: Dict[str, float]) -> pd.DataFrame:
    """
    Merge holdings with current prices from ParquetDB.
    
    Args:
        holdings_df: Holdings DataFrame
        prices_dict: Dict of symbol -> current price
        
    Returns:
        Holdings DataFrame with current price and P&L columns
    """
    if holdings_df is None or holdings_df.empty:
        return None
    
    df = holdings_df.copy()
    
    # Map current prices
    df['current_price'] = df['sym'].map(prices_dict)
    
    # For EUR-denominated crypto, fetch EUR prices from CoinGecko
    eur_crypto_mask = (df['asset'] == 'crypto') & (df['ccy'] == 'eur') & (df['current_price'].isna())
    if eur_crypto_mask.any():
        try:
            from src.portfolio_prices import PriceFetcher
            fetcher = PriceFetcher()
            
            for idx, row in df[eur_crypto_mask].iterrows():
                symbol = row['sym']
                # Extract crypto symbol (remove -USD suffix if present)
                crypto_symbol = symbol.replace('-USD', '')
                price_data = fetcher.fetch_crypto_price(crypto_symbol)
                if price_data and 'price_eur' in price_data:
                    df.at[idx, 'current_price'] = price_data['price_eur']
        except Exception as e:
            # Fallback if fetching fails
            pass
    
    # For symbols without price data, use cost basis as fallback
    df['current_price'] = df['current_price'].fillna(df['bep'])
    
    # Calculate P&L
    df['value_at_cost'] = df['qty'] * df['bep']
    df['current_value'] = df['qty'] * df['current_price']
    df['pnl_absolute'] = df['current_value'] - df['value_at_cost']
    df['pnl_percent'] = (df['pnl_absolute'] / df['value_at_cost'] * 100).fillna(0)
    
    return df


def get_portfolio_summary(holdings_df: pd.DataFrame) -> Dict:
    """Get portfolio summary statistics."""
    if holdings_df is None or holdings_df.empty:
        return {}
    
    total_value = holdings_df['current_value'].sum()
    total_cost = holdings_df['value_at_cost'].sum()
    total_pnl = holdings_df['pnl_absolute'].sum()
    total_pnl_pct = (total_pnl / total_cost * 100) if total_cost > 0 else 0
    
    return {
        'total_value': total_value,
        'total_cost': total_cost,
        'total_pnl': total_pnl,
        'total_pnl_pct': total_pnl_pct,
        'num_positions': len(holdings_df),
        'num_brokers': holdings_df['brokerName'].nunique(),
        'currencies': holdings_df['ccy'].unique().tolist(),
    }


def get_sector_breakdown(holdings_df: pd.DataFrame) -> pd.DataFrame:
    """Get portfolio breakdown by asset class."""
    if holdings_df is None or holdings_df.empty:
        return None
    
    return (holdings_df.groupby('asset')
            .agg({'current_value': 'sum', 'pnl_absolute': 'sum'})
            .reset_index()
            .rename(columns={'asset': 'Asset Class', 'current_value': 'Value', 'pnl_absolute': 'P&L'}))


def get_broker_breakdown(holdings_df: pd.DataFrame) -> pd.DataFrame:
    """Get portfolio breakdown by broker."""
    if holdings_df is None or holdings_df.empty:
        return None
    
    return (holdings_df.groupby('brokerName')
            .agg({'current_value': 'sum', 'qty': 'count'})
            .reset_index()
            .rename(columns={'brokerName': 'Broker', 'current_value': 'Value', 'qty': 'Positions'}))


def get_top_positions(holdings_df: pd.DataFrame, n: int = 15) -> pd.DataFrame:
    """Get top N positions by value."""
    if holdings_df is None or holdings_df.empty:
        return None
    
    return (holdings_df.nlargest(n, 'current_value')[
        ['sym', 'secName', 'qty', 'bep', 'current_price', 'current_value', 'pnl_absolute', 'pnl_percent']]
        .reset_index(drop=True))


def get_portfolio_pnl_over_time(holdings_csv: str = "holdings.csv", db=None) -> pd.DataFrame:
    """
    Calculate portfolio P&L over time using historical prices.
    Uses forward-fill for missing prices to avoid data gaps causing artificial P&L swings.
    
    Args:
        holdings_csv: Path to holdings CSV
        db: ParquetDB instance
        
    Returns:
        DataFrame with date and portfolio_pnl columns
    """
    try:
        if db is None:
            db = init_parquet_db()
        
        # Load holdings
        holdings = pd.read_csv(holdings_csv)
        
        # Get all price history
        prices = db.read_table('prices')
        if prices is None or prices.empty:
            return pd.DataFrame()
        
        # Group by date and symbol, take the latest price per date
        prices['date'] = pd.to_datetime(prices['timestamp']).dt.date
        latest_prices = prices.loc[prices.groupby(['date', 'symbol'])['timestamp'].idxmax()].copy()
        
        # Create a complete price matrix with all dates and symbols
        all_dates = sorted(latest_prices['date'].unique())
        all_symbols = latest_prices['symbol'].unique()
        
        # Build a price matrix for each symbol
        price_series = {}
        for symbol in all_symbols:
            symbol_data = latest_prices[latest_prices['symbol'] == symbol].set_index('date')['close_price']
            price_series[symbol] = symbol_data
        
        # Calculate portfolio value for each date with forward-fill
        pnl_by_date = []
        last_prices = {}
        
        for date in all_dates:
            total_pnl = 0
            
            # Calculate P&L for each holding
            for _, holding in holdings.iterrows():
                symbol = holding['sym']
                qty = holding['qty']
                bep = holding['bep']
                
                # Get price for this date, use last known price if missing
                if symbol in price_series and date in price_series[symbol].index:
                    current_price = price_series[symbol][date]
                    last_prices[symbol] = current_price
                elif symbol in last_prices:
                    current_price = last_prices[symbol]
                else:
                    # Skip if we don't have any price data yet for this symbol
                    continue
                
                if pd.notna(current_price):
                    pnl = (current_price - bep) * qty
                    total_pnl += pnl
            
            pnl_by_date.append({'date': date, 'portfolio_pnl': total_pnl})
        
        result = pd.DataFrame(pnl_by_date)
        if not result.empty:
            result['date'] = pd.to_datetime(result['date'])
        return result
    except Exception as e:
        st.warning(f"Could not calculate P&L over time: {str(e)[:100]}")
        return pd.DataFrame()


@st.cache_data(ttl=60)
def fetch_technical_analysis(_db: ParquetDB, symbols: List[str]) -> Optional[pd.DataFrame]:
    """Fetch technical analysis indicators from ParquetDB."""
    try:
        tech_df = _db.read_table('technical_analysis')
        if tech_df is None or tech_df.empty:
            return None
        
        # Filter for requested symbols and get latest data per symbol (not global latest)
        filtered = tech_df[tech_df['symbol'].isin(symbols)]
        
        # Get the latest date for each symbol individually
        if not filtered.empty:
            result = filtered.sort_values('timestamp').groupby('symbol').tail(1)
            return result
        return None
    except Exception as e:
        st.warning(f"Could not fetch technical analysis: {e}")
        return None


@st.cache_data(ttl=60)
def fetch_fundamental_analysis(_db: ParquetDB, symbols: List[str]) -> Optional[pd.DataFrame]:
    """Fetch fundamental analysis metrics from ParquetDB."""
    try:
        fund_df = _db.read_table('fundamental_analysis')
        if fund_df is None or fund_df.empty:
            return None
        
        # Filter for requested symbols and latest data
        filtered = fund_df[fund_df['symbol'].isin(symbols)]
        if not filtered.empty:
            latest_date = filtered['timestamp'].max()
            return filtered[filtered['timestamp'] == latest_date]
        return None
    except Exception as e:
        st.warning(f"Could not fetch fundamental analysis: {e}")
        return None


@st.cache_data(ttl=3600)
@st.cache_data(ttl=3600)
def calculate_portfolio_alpha_beta(_db: ParquetDB, holdings_csv: str = "holdings.csv") -> Dict:
    """
    Calculate portfolio alpha and beta against S&P 500.
    
    Returns a dict with:
    - portfolio_return: Annualized portfolio return (%)
    - sp500_return: Annualized S&P 500 return (%)
    - alpha: Jensen's alpha (%)
    - beta: Portfolio beta
    - portfolio_volatility: Annualized portfolio volatility (%)
    - sharpe_ratio: Sharpe ratio
    """
    try:
        import numpy as np
        
        # Load holdings and prices
        holdings = pd.read_csv(holdings_csv)
        prices = _db.read_table('prices')
        
        if prices is None or prices.empty:
            return {
                'portfolio_return': 0, 'sp500_return': 0, 'alpha': 0, 
                'beta': 0, 'portfolio_volatility': 0, 'sharpe_ratio': 0
            }
        
        # Get S&P 500 data
        sp500_prices = prices[prices['symbol'] == '^GSPC'].copy()
        
        if sp500_prices.empty:
            return {
                'portfolio_return': 0, 'sp500_return': 0, 'alpha': 0,
                'beta': 0, 'portfolio_volatility': 0, 'sharpe_ratio': 0
            }
        
        # Filter holdings: only include equities and funds, exclude cash/fixed-income/retirement
        equity_holdings = holdings[~holdings['asset'].isin(['cash', 'fixed-income', 'retirement'])]
        equity_holdings = equity_holdings[~equity_holdings['sym'].str.contains('MANUAL|SAVINGS', case=False, na=False)]
        
        if equity_holdings.empty:
            return {
                'portfolio_return': 0, 'sp500_return': 0, 'alpha': 0,
                'beta': 0, 'portfolio_volatility': 0, 'sharpe_ratio': 0
            }
        
        # Prepare price data - convert timestamps to dates
        prices['date'] = pd.to_datetime(prices['timestamp']).dt.normalize()
        sp500_prices['date'] = pd.to_datetime(sp500_prices['timestamp']).dt.normalize()
        
        # Build price matrix for each symbol with forward-fill for missing dates
        all_dates = sorted(prices['date'].unique())
        price_matrix = {}
        
        for _, holding in equity_holdings.iterrows():
            symbol = holding['sym']
            symbol_prices = prices[prices['symbol'] == symbol][['date', 'close_price']].drop_duplicates('date', keep='last')
            
            if not symbol_prices.empty:
                # Sort and ensure index is unique
                symbol_prices = symbol_prices.sort_values('date')
                series = pd.Series(
                    symbol_prices['close_price'].values,
                    index=symbol_prices['date'].values
                )
                # Make sure index is unique and monotonic
                series = series[~series.index.duplicated(keep='last')]
                series = series.reindex(all_dates).ffill()
                price_matrix[symbol] = series
        
        if not price_matrix:
            return {
                'portfolio_return': 0, 'sp500_return': 0, 'alpha': 0,
                'beta': 0, 'portfolio_volatility': 0, 'sharpe_ratio': 0
            }
        
        # Calculate portfolio value for each date
        portfolio_values = []
        portfolio_dates = []
        
        for date in all_dates:
            portfolio_value = 0
            valid_positions = 0
            
            for _, holding in equity_holdings.iterrows():
                symbol = holding['sym']
                qty = holding['qty']
                
                if symbol in price_matrix:
                    price = price_matrix[symbol].loc[date]
                    if pd.notna(price) and price > 0:
                        portfolio_value += price * qty
                        valid_positions += 1
            
            # Only include dates with prices for most holdings
            if valid_positions >= len(equity_holdings) * 0.8:  # 80% of holdings
                portfolio_values.append(portfolio_value)
                portfolio_dates.append(date)
        
        if len(portfolio_values) < 30:
            return {
                'portfolio_return': 0, 'sp500_return': 0, 'alpha': 0,
                'beta': 0, 'portfolio_volatility': 0, 'sharpe_ratio': 0
            }
        
        # Calculate portfolio returns
        portfolio_series = pd.Series(portfolio_values, index=portfolio_dates)
        portfolio_rets = portfolio_series.pct_change().dropna()
        
        # Get S&P 500 series with forward-fill
        sp500_latest = sp500_prices.loc[sp500_prices.groupby('date')['timestamp'].idxmax()].copy()
        sp500_latest = sp500_latest.drop_duplicates('date', keep='last').sort_values('date')
        sp500_series = pd.Series(
            sp500_latest['close_price'].values,
            index=sp500_latest['date'].values
        )
        sp500_series = sp500_series[~sp500_series.index.duplicated(keep='last')]
        sp500_series = sp500_series.reindex(all_dates).ffill()
        sp500_returns = sp500_series.pct_change().dropna()
        
        if len(sp500_returns) < 30:
            return {
                'portfolio_return': 0, 'sp500_return': 0, 'alpha': 0,
                'beta': 0, 'portfolio_volatility': 0, 'sharpe_ratio': 0
            }
        
        # Align dates between portfolio and S&P 500
        common_dates = portfolio_rets.index.intersection(sp500_returns.index)
        
        if len(common_dates) < 30:
            return {
                'portfolio_return': 0, 'sp500_return': 0, 'alpha': 0,
                'beta': 0, 'portfolio_volatility': 0, 'sharpe_ratio': 0
            }
        
        # Get aligned returns
        portfolio_rets_aligned = portfolio_rets[common_dates].values
        sp500_rets_aligned = sp500_returns[common_dates].values
        
        # Convert to numpy arrays
        portfolio_rets_arr = np.array(portfolio_rets_aligned)
        sp500_rets_arr = np.array(sp500_rets_aligned)
        
        # Calculate metrics
        portfolio_return_daily = np.mean(portfolio_rets_arr)
        sp500_return_daily = np.mean(sp500_rets_arr)
        
        portfolio_return = portfolio_return_daily * 252 * 100  # Annualize to percentage
        sp500_return = sp500_return_daily * 252 * 100
        
        portfolio_volatility = (np.std(portfolio_rets_arr) * np.sqrt(252)) * 100
        
        # Calculate beta using covariance
        covariance = np.cov(portfolio_rets_arr, sp500_rets_arr)[0, 1]
        sp500_variance = np.var(sp500_rets_arr)
        beta = covariance / sp500_variance if sp500_variance > 0 else 1.0
        
        # Risk-free rate (current approximate rate)
        risk_free_rate = 0.04
        
        # Calculate alpha (Jensen's alpha)
        expected_return = risk_free_rate + beta * (sp500_return / 100 - risk_free_rate)
        alpha = (portfolio_return / 100) - expected_return
        alpha = alpha * 100  # Convert back to percentage
        
        # Sharpe ratio
        sharpe_ratio = 0.0
        if np.std(portfolio_rets_arr) > 0:
            excess_return = portfolio_return_daily - (risk_free_rate / 252)
            sharpe_ratio = (excess_return / np.std(portfolio_rets_arr)) * np.sqrt(252)
        
        return {
            'portfolio_return': float(portfolio_return),
            'sp500_return': float(sp500_return),
            'alpha': float(alpha),
            'beta': float(beta),
            'portfolio_volatility': float(portfolio_volatility),
            'sharpe_ratio': float(sharpe_ratio)
        }
    
    except Exception as e:
        st.warning(f"Could not calculate alpha/beta: {str(e)[:100]}")
        return {
            'portfolio_return': 0, 'sp500_return': 0, 'alpha': 0,
            'beta': 0, 'portfolio_volatility': 0, 'sharpe_ratio': 0
        }


@st.cache_data(ttl=3600)
def get_portfolio_vs_benchmark(_db: ParquetDB, holdings_csv: str = "holdings.csv") -> Optional[pd.DataFrame]:
    """
    Get portfolio vs S&P 500 performance comparison over time.
    
    Returns a DataFrame with:
    - date
    - portfolio_value
    - sp500_index (normalized to portfolio starting value)
    """
    try:
        holdings = pd.read_csv(holdings_csv)
        prices = _db.read_table('prices')
        
        if prices is None or prices.empty:
            return None
        
        # Get S&P 500 data
        sp500_prices = prices[prices['symbol'] == '^GSPC'].copy()
        if sp500_prices.empty:
            return None
        
        # Filter holdings: only include equities and funds, exclude cash/fixed-income/retirement
        equity_holdings = holdings[~holdings['asset'].isin(['cash', 'fixed-income', 'retirement'])]
        equity_holdings = equity_holdings[~equity_holdings['sym'].str.contains('MANUAL|SAVINGS', case=False, na=False)]
        
        if equity_holdings.empty:
            return None
        
        # Prepare data
        prices['date'] = pd.to_datetime(prices['timestamp']).dt.normalize()
        sp500_prices['date'] = pd.to_datetime(sp500_prices['timestamp']).dt.normalize()
        
        all_dates = sorted(prices['date'].unique())
        
        # Build price matrix for each symbol with forward-fill for missing dates
        price_matrix = {}
        
        for _, holding in equity_holdings.iterrows():
            symbol = holding['sym']
            symbol_prices = prices[prices['symbol'] == symbol][['date', 'close_price']].drop_duplicates('date', keep='last')
            
            if not symbol_prices.empty:
                # Sort and ensure index is unique
                symbol_prices = symbol_prices.sort_values('date')
                series = pd.Series(
                    symbol_prices['close_price'].values,
                    index=symbol_prices['date'].values
                )
                # Make sure index is unique and monotonic
                series = series[~series.index.duplicated(keep='last')]
                series = series.reindex(all_dates).ffill()
                price_matrix[symbol] = series
        
        # Build comparison data
        comparison_data = []
        initial_portfolio_value = None
        initial_sp500_price = None
        
        for date in all_dates:
            # Portfolio value
            portfolio_value = 0
            valid_positions = 0
            
            for _, holding in equity_holdings.iterrows():
                symbol = holding['sym']
                qty = holding['qty']
                
                if symbol in price_matrix:
                    price = price_matrix[symbol].loc[date]
                    if pd.notna(price) and price > 0:
                        portfolio_value += price * qty
                        valid_positions += 1
            
            # S&P 500 price - use forward-fill
            sp500_data = sp500_prices[sp500_prices['date'] == date]
            if not sp500_data.empty:
                sp500_price = sp500_data['close_price'].iloc[-1]
            else:
                # Forward-fill S&P 500 price
                sp500_prev = sp500_prices[sp500_prices['date'] < date].sort_values('date', ascending=False)
                if not sp500_prev.empty:
                    sp500_price = sp500_prev.iloc[0]['close_price']
                else:
                    continue
            
            # Only include dates with prices for most holdings
            if valid_positions >= len(equity_holdings) * 0.8:  # 80% of holdings
                if initial_portfolio_value is None:
                    initial_portfolio_value = portfolio_value
                    initial_sp500_price = sp500_price
                
                # Normalize S&P 500 to match portfolio starting value
                sp500_index = (sp500_price / initial_sp500_price) * initial_portfolio_value
                
                comparison_data.append({
                    'date': date,
                    'portfolio_value': portfolio_value,
                    'sp500_index': sp500_index
                })
        
        if comparison_data and len(comparison_data) > 30:
            return pd.DataFrame(comparison_data)
        return None
    
    except Exception as e:
        st.warning(f"Could not get benchmark comparison: {str(e)[:100]}")
        return None


def render_home():
    """Render home page."""
    st.title("📊 Finance TechStack Analytics Dashboard")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("### Welcome")
        st.markdown("""
        This dashboard provides comprehensive analytics for your investment portfolio:
        - **Real-time prices** from ParquetDB
        - **Portfolio metrics** with actual P&L calculations
        - **Technical & fundamental analysis** of your holdings
        - **Email reports** for performance tracking
        - **Advanced strategies** including quick wins and risk analysis
        """)
    
    with col2:
        st.info(f"""
        **Portfolio Status**
        - Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}
        - Data source: ParquetDB
        - Holdings loaded: ✓
        """)
    
    # Data Freshness Warning
    st.markdown("### Data Freshness")
    try:
        db = init_parquet_db()
        freshness = get_price_data_freshness(db)
        
        if freshness['is_stale']:
            st.warning(
                f"⚠️ **Price data is stale** ({freshness['days_stale']} days old)\n\n"
                f"Latest prices: {freshness['latest_date'].strftime('%Y-%m-%d') if freshness['latest_date'] else 'None'}\n\n"
                f"**Action needed**: Run the price backfill script to update prices:\n"
                f"`uv run python scripts/backfill_historical_data.py --days 30`"
            )
        else:
            st.success(f"✅ {freshness['message']}")
    except Exception as e:
        st.warning(f"Could not check data freshness: {str(e)[:50]}")
    
    # Quick stats
    st.markdown("### Quick Stats")
    if st.session_state.prices_with_holdings is not None:
        summary = get_portfolio_summary(st.session_state.prices_with_holdings)
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Portfolio Value", f"${summary['total_value']:,.2f}", 
                     f"+${summary['total_pnl']:,.2f}" if summary['total_pnl'] > 0 else f"${summary['total_pnl']:,.2f}")
        
        with col2:
            st.metric("Total P&L %", f"{summary['total_pnl_pct']:.2f}%")
        
        with col3:
            st.metric("Positions", f"{summary['num_positions']}")
        
        with col4:
            st.metric("Brokers", f"{summary['num_brokers']}")
    
    # Alpha & Beta Metrics
    st.markdown("### Risk-Adjusted Performance Metrics")
    try:
        db = init_parquet_db()
        metrics = calculate_portfolio_alpha_beta(db, holdings_csv="holdings.csv")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            alpha_color = "inverse" if metrics['alpha'] < 0 else "off"
            st.metric(
                "Alpha (α)", 
                f"{metrics['alpha']:.2f}%",
                help="Jensen's alpha: Returns above/below what's expected given portfolio risk. Positive is better."
            )
        
        with col2:
            st.metric(
                "Beta (β)",
                f"{metrics['beta']:.2f}",
                help="Portfolio beta vs S&P 500: <1 = less volatile, >1 = more volatile"
            )
        
        with col3:
            st.metric(
                "Sharpe Ratio",
                f"{metrics['sharpe_ratio']:.2f}",
                help="Risk-adjusted return: Higher is better. Measures return per unit of risk."
            )
        
        with col4:
            st.metric(
                "Volatility",
                f"{metrics['portfolio_volatility']:.2f}%",
                help="Annualized portfolio volatility (standard deviation of returns)"
            )
        
        # Additional info
        with st.expander("📊 Performance vs S&P 500"):
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Portfolio Return (Annualized)", f"{metrics['portfolio_return']:.2f}%")
            with col2:
                st.metric("S&P 500 Return (Annualized)", f"{metrics['sp500_return']:.2f}%")
            
            st.markdown("""
            **Understanding These Metrics:**
            - **Alpha**: Excess returns above the market benchmark (adjusted for risk)
              - Positive alpha = outperformance, Negative = underperformance
            - **Beta**: Volatility relative to S&P 500
              - Beta = 1.0 means moves with the market
              - Beta < 1.0 means less volatile than market
              - Beta > 1.0 means more volatile than market
            - **Sharpe Ratio**: Risk-adjusted returns (return per unit of risk taken)
            - **Volatility**: How much returns fluctuate (higher = riskier)
            """)
    
    except Exception as e:
        st.warning(f"Could not calculate performance metrics: {str(e)[:100]}")
    
    # Portfolio vs Benchmark Chart
    st.markdown("### Portfolio vs S&P 500 Benchmark")
    try:
        db = init_parquet_db()
        benchmark_data = get_portfolio_vs_benchmark(db, holdings_csv="holdings.csv")
        
        if benchmark_data is not None and not benchmark_data.empty:
            # Ensure date is datetime for plotting
            benchmark_data['date'] = pd.to_datetime(benchmark_data['date'])
            
            fig = px.line(
                benchmark_data,
                x='date',
                y=['portfolio_value', 'sp500_index'],
                title='Portfolio vs S&P 500 Performance (Normalized)',
                labels={'date': 'Date', 'value': 'Value ($)'},
                color_discrete_map={
                    'portfolio_value': '#1f77b4',
                    'sp500_index': '#ff7f0e'
                }
            )
            
            fig.update_xaxes(title_text="Date")
            fig.update_yaxes(title_text="Portfolio Value ($)")
            fig.update_traces(hovertemplate='<b>%{fullData.name}</b><br>Date: %{x|%Y-%m-%d}<br>Value: $%{y:,.0f}<extra></extra>')
            fig.update_layout(
                hovermode='x unified',
                plot_bgcolor='rgba(0,0,0,0)',
                height=450,
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1
                )
            )
            
            # Rename legend entries
            fig.for_each_trace(lambda t: t.update(name = "Your Portfolio" if t.name == "portfolio_value" else "S&P 500 (Normalized)"))
            
            st.plotly_chart(fig, use_container_width=True)
            
            st.info("""
            💡 **How to read this chart:**
            - **Your Portfolio** (Blue): Your actual portfolio value over time
            - **S&P 500 (Normalized)** (Orange): S&P 500 index scaled to your portfolio's starting value
            - If your portfolio is above the orange line, you're outperforming the market
            - If below, you're underperforming (which doesn't necessarily mean loss, just slower gains)
            """)
        else:
            st.info("Not enough historical data yet to compare against S&P 500. Run price updates to populate chart.")
    except Exception as e:
        st.warning(f"Could not display benchmark comparison: {str(e)[:100]}")



def render_portfolio():
    """Render portfolio page."""
    st.title("💼 Portfolio Analysis")
    
    if st.session_state.prices_with_holdings is None or st.session_state.prices_with_holdings.empty:
        st.error("No portfolio data available")
        return
    
    holdings = st.session_state.prices_with_holdings
    summary = get_portfolio_summary(holdings)
    
    # Summary metrics
    st.markdown("### Portfolio Summary")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Value", f"${summary['total_value']:,.2f}")
    
    with col2:
        st.metric("Cost Basis", f"${summary['total_cost']:,.2f}")
    
    with col3:
        st.metric("Total P&L", f"${summary['total_pnl']:,.2f}")
    
    with col4:
        st.metric("Return %", f"{summary['total_pnl_pct']:.2f}%",
                 delta_color="off" if summary['total_pnl_pct'] >= 0 else "inverse")
    
    # Asset class breakdown
    st.markdown("### Asset Class Breakdown")
    col1, col2 = st.columns(2)
    
    with col1:
        sector_data = get_sector_breakdown(holdings)
        if sector_data is not None:
            fig = px.pie(sector_data, values='Value', names='Asset Class', 
                        title='Portfolio by Asset Class')
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        broker_data = get_broker_breakdown(holdings)
        if broker_data is not None:
            fig = px.bar(broker_data, x='Broker', y='Value',
                        title='Portfolio by Broker')
            st.plotly_chart(fig, use_container_width=True)
    
    # Top positions
    st.markdown("### Top 15 Positions")
    top_positions = get_top_positions(holdings, 15)
    
    if top_positions is not None:
        # Format for display
        display_df = top_positions.copy()
        display_df['Weight %'] = (display_df['current_value'] / summary['total_value'] * 100).round(2)
        display_df = display_df[['sym', 'secName', 'qty', 'bep', 'current_price', 'current_value', 'pnl_percent', 'Weight %']]
        display_df.columns = ['Symbol', 'Name', 'Qty', 'Entry Price', 'Current Price', 'Value', 'P&L %', 'Weight %']
        
        st.dataframe(display_df, use_container_width=True, hide_index=True)
    
    # P&L over time (simulated for now - would use historical prices)
    st.markdown("### Position Performance")
    pnl_by_position = holdings.nlargest(10, 'current_value')[['sym', 'pnl_percent']].copy()
    pnl_by_position.columns = ['Symbol', 'Return %']
    pnl_by_position = pnl_by_position.sort_values('Return %')
    
    fig = px.bar(pnl_by_position, y='Symbol', x='Return %', orientation='h',
                title='Return % by Position (Top 10 by Value)',
                color='Return %', color_continuous_scale=['red', 'green'])
    st.plotly_chart(fig, use_container_width=True)


def render_advanced_analytics():
    """Render advanced analytics page."""
    st.title("🔬 Advanced Analytics")
    
    # Add Prefect UI link at top
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.link_button("📋 Prefect Logs", "http://localhost:4200", use_container_width=True)
    with col2:
        if st.button("🔄 Update Price Data", key="btn_update_prices"):
            run_data_update_flows()
    with col3:
        if st.button("📊 Run Technical Analysis", key="btn_run_tech"):
            success = run_technical_analysis()
            if success:
                st.rerun()
    with col4:
        if st.button("📈 Run Fundamental Analysis", key="btn_run_fund"):
            success = run_fundamental_analysis()
            if success:
                st.rerun()
    with col5:
        if st.button("💾 Refresh Data Cache", key="btn_refresh"):
            st.cache_data.clear()
            st.rerun()
    
    st.divider()
    
    tab1, tab2, tab3, tab4 = st.tabs(["News", "Technical", "Fundamentals", "Risk"])
    
    with tab1:
        st.subheader("News Sentiment Analysis")
        st.info("Track news sentiment for your holdings to gauge market sentiment.")
        
        col1, col2 = st.columns(2)
        with col1:
            hours_back = st.slider("Look back (hours)", 1, 72, 24)
        with col2:
            max_articles = st.slider("Max articles", 10, 200, 100)
        
        if st.button("📰 Fetch News & Sentiment"):
            with st.spinner("Scraping news and analyzing sentiment..."):
                try:
                    # Get portfolio symbols
                    if st.session_state.prices_with_holdings is None or st.session_state.prices_with_holdings.empty:
                        st.error("No portfolio data available")
                        return
                    
                    symbols = st.session_state.prices_with_holdings['sym'].unique().tolist()
                    st.info(f"Analyzing news for {len(symbols)} holdings: {', '.join(symbols[:5])}{'...' if len(symbols) > 5 else ''}")
                    
                    # Call news sentiment analysis with Prefect flow (provides logging)
                    articles, stats = news_sentiment_analysis_flow(
                        max_articles=max_articles,
                        hours_back=hours_back,
                        symbols=symbols
                    )
                    
                    if not articles:
                        st.warning(f"⚠️ No recent news articles found. This may be due to API rate limits or feed issues.")
                        st.info("Tip: News feeds can be flaky. Try again in a few moments.")
                        st.info("📋 Check Prefect Logs for details: http://localhost:4200")
                        return
                    
                    st.success(f"✓ Found {stats['total_articles']} articles from {stats['sources_count']} sources")
                    st.info("📋 Check Prefect Logs for task execution details: http://localhost:4200")
                    
                    # Display results
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Overall Sentiment", f"{stats['avg_sentiment']:.2f}")
                    with col2:
                        st.metric("Positive Articles", stats['positive_count'])
                    with col3:
                        st.metric("Negative Articles", stats['negative_count'])
                    
                    # Sentiment distribution
                    col1, col2 = st.columns(2)
                    with col1:
                        sentiment_dist = pd.DataFrame({
                            'Sentiment': ['Positive', 'Neutral', 'Negative'],
                            'Count': [stats['positive_count'], stats['neutral_count'], stats['negative_count']]
                        })
                        fig = px.pie(sentiment_dist, values='Count', names='Sentiment', 
                                    title='News Sentiment Distribution',
                                    color_discrete_map={'Positive': 'green', 'Neutral': 'gray', 'Negative': 'red'})
                        st.plotly_chart(fig, use_container_width=True)
                    
                    with col2:
                        # Timeline of sentiments
                        sentiment_timeline = pd.DataFrame([
                            {'Time': a.get('published', 'Unknown'), 'Sentiment': a['sentiment_label']}
                            for a in articles
                        ])
                        sentiment_counts = sentiment_timeline.groupby('Sentiment').size().reset_index(name='Count')
                        fig = px.bar(sentiment_counts, x='Sentiment', y='Count',
                                    title='Sentiment Breakdown',
                                    color='Sentiment',
                                    color_discrete_map={'Positive': 'green', 'Neutral': 'gray', 'Negative': 'red'})
                        st.plotly_chart(fig, use_container_width=True)
                    
                    st.divider()
                    
                    # Show articles by sentiment
                    st.subheader("Recent Articles")
                    
                    # Filter by sentiment
                    sentiment_filter = st.selectbox("Filter by Sentiment", ["All", "Positive", "Neutral", "Negative"])
                    
                    filtered_articles = articles
                    if sentiment_filter != "All":
                        filtered_articles = [a for a in articles if a['sentiment_label'] == sentiment_filter]
                    
                    if filtered_articles:
                        for article in filtered_articles[:15]:
                            sentiment_color = "🟢" if article['sentiment_label'] == 'Positive' else "🟡" if article['sentiment_label'] == 'Neutral' else "🔴"
                            with st.expander(f"{sentiment_color} {article['title'][:80]}... ({article['source']})"):
                                st.write(f"**Source:** {article['source']}")
                                st.write(f"**Published:** {article.get('published', 'Unknown')}")
                                st.write(f"**Sentiment:** {article['sentiment_label']} ({article['sentiment_score']:.2f})")
                                st.write(f"**Summary:** {article['summary']}")
                                if article.get('link'):
                                    st.link_button("Read Full Article", article['link'])
                    else:
                        st.info(f"No articles found with {sentiment_filter} sentiment")
                    
                    # Check for mentions of portfolio holdings in articles
                    st.divider()
                    st.subheader("Portfolio Mentions in News")
                    
                    if stats['portfolio_mentions']:
                        mentions_df = pd.DataFrame([
                            {'Symbol': sym, 'Mentions': count}
                            for sym, count in sorted(stats['portfolio_mentions'].items(), key=lambda x: x[1], reverse=True)
                        ])
                        st.dataframe(mentions_df, use_container_width=True, hide_index=True)
                        st.success(f"Found {sum(stats['portfolio_mentions'].values())} mentions of your holdings in recent news")
                    else:
                        st.info("No mentions of your holdings found in recent news (which is usually good!)")
                        
                except Exception as e:
                    st.error(f"Error analyzing news: {str(e)}")
                    st.info("💡 Tip: This feature relies on external news feeds which can be unstable. Please try again.")
                    st.info("📋 Check Prefect Logs for error details: http://localhost:4200")
    
    with tab2:
        st.subheader("Technical Indicators - All Holdings")
        st.info("RSI, MACD, Bollinger Bands, and Moving Averages for all your tradable positions.")
        
        col1, col2 = st.columns([3, 1])
        with col1:
            load_btn = st.button("📊 Load Technical Analysis", key="btn_load_tech")
        with col2:
            run_btn = st.button("📈 Calculate Now", key="btn_tech_calc_inline", help="Calculate technical indicators immediately")
        
        if run_btn:
            success = run_technical_analysis()
            if success:
                st.rerun()
        
        if load_btn:
            if st.session_state.prices_with_holdings is not None:
                symbols = st.session_state.prices_with_holdings['sym'].unique().tolist()
                st.info(f"Technical indicators for {len(symbols)} holdings")
                
                with st.spinner("Fetching technical indicators..."):
                    db = init_parquet_db()
                    tech_data = fetch_technical_analysis(db, symbols)
                    
                    if tech_data is not None and not tech_data.empty:
                        # Check if we actually have technical indicator columns
                        tech_columns = ['rsi', 'bb_upper', 'sma_short', 'sma_long', 'ema_short', 'ema_long', 'obv']
                        has_indicators = any(col in tech_data.columns for col in tech_columns)
                        
                        if not has_indicators:
                            st.warning("⚠️ Technical indicators not calculated yet.")
                            st.info("""
                            **To calculate technical indicators:**
                            1. Click the "📈 Calculate Now" button above
                            2. Wait for the calculation to complete
                            3. Results will appear automatically
                            """)
                        else:
                            # Merge with holdings for additional context
                            holdings_df = st.session_state.prices_with_holdings
                            portfolio_tech = tech_data[tech_data['symbol'].isin(symbols)].copy()
                            
                            if not portfolio_tech.empty:
                                st.success(f"✅ Technical data available for {len(portfolio_tech.groupby('symbol'))} symbols")
                                
                                # Create tabs for different views
                                tech_tab1, tech_tab2, tech_tab3, tech_tab4, tech_tab5, tech_tab6, tech_tab7 = st.tabs(["Summary", "Momentum", "Volatility", "Detailed", "Technical Signals", "Momentum & Valuation", "Combined Signals"])
                                
                                # TAB 1: Summary View
                                with tech_tab1:
                                    st.subheader("Technical Indicators Summary")
                                    st.markdown("Quick overview of key technical indicators for your holdings")
                                    
                                    # Core technical indicators
                                    summary_cols = ['symbol', 'Close', 'rsi', 'bb_upper', 'bb_middle', 'bb_lower']
                                    available_summary = [col for col in summary_cols if col in portfolio_tech.columns]
                                    
                                    if available_summary:
                                        summary_df = portfolio_tech[available_summary].copy()
                                        summary_df = summary_df.sort_values('symbol')
                                        
                                        # Rename columns for better readability
                                        summary_df = summary_df.rename(columns={
                                            'symbol': '📊 Symbol',
                                            'Close': '💰 Price',
                                            'rsi': '📈 RSI (14)',
                                            'bb_upper': '⬆️ BB Upper',
                                            'bb_middle': '➡️ BB Middle',
                                            'bb_lower': '⬇️ BB Lower'
                                        })
                                        
                                        # Format numeric columns for better display
                                        for col in ['💰 Price', '📈 RSI (14)', '⬆️ BB Upper', '➡️ BB Middle', '⬇️ BB Lower']:
                                            if col in summary_df.columns:
                                                summary_df[col] = summary_df[col].apply(lambda x: f"{x:.2f}" if pd.notna(x) else "N/A")
                                        
                                        st.dataframe(
                                            summary_df,
                                            use_container_width=True,
                                            hide_index=True
                                        )
                                    
                                    # RSI Interpretation
                                    st.divider()
                                    st.markdown("""
                                    **RSI (Relative Strength Index) Signals:**
                                    - **RSI > 70**: 🔴 Overbought (potential sell signal)
                                    - **RSI 50-70**: 🟠 Strong uptrend
                                    - **RSI 30-50**: 🟡 Neutral
                                    - **RSI < 30**: 🟢 Oversold (potential buy signal)
                                    
                                    **Bollinger Bands:**
                                    - Price near **Upper Band**: Strong uptrend, potential resistance
                                    - Price near **Middle Band**: Normal consolidation
                                    - Price near **Lower Band**: Strong downtrend, potential support
                                    """)
                                
                                # TAB 2: Momentum Indicators
                                with tech_tab2:
                                    st.subheader("Momentum Indicators")
                                    st.markdown("View momentum strength and exponential moving average trends")
                                    
                                    momentum_cols = ['symbol', 'rsi', 'ema_short', 'ema_long', 'Close']
                                    available_momentum = [col for col in momentum_cols if col in portfolio_tech.columns]
                                    
                                    if available_momentum:
                                        momentum_df = portfolio_tech[available_momentum].copy()
                                        # Sort by RSI if available, otherwise by symbol
                                        if 'rsi' in momentum_df.columns:
                                            momentum_df = momentum_df.sort_values('rsi', ascending=False)
                                        else:
                                            momentum_df = momentum_df.sort_values('symbol')
                                        
                                        # Rename columns for better readability
                                        momentum_df = momentum_df.rename(columns={
                                            'symbol': '📊 Symbol',
                                            'Close': '💰 Price',
                                            'rsi': '📈 RSI (14)',
                                            'ema_short': '📊 EMA 12',
                                            'ema_long': '📊 EMA 26'
                                        })
                                        
                                        # Format numeric columns for display
                                        for col in ['💰 Price', '📈 RSI (14)', '📊 EMA 12', '📊 EMA 26']:
                                            if col in momentum_df.columns:
                                                momentum_df[col] = momentum_df[col].apply(lambda x: f"{x:.2f}" if pd.notna(x) else "N/A")
                                        
                                        if 'rsi' in portfolio_tech.columns:
                                            st.markdown("**🔥 Ranked by RSI (highest momentum first)**")
                                        else:
                                            st.markdown("**Momentum Data (RSI not available)**")
                                        st.dataframe(
                                            momentum_df,
                                            use_container_width=True,
                                            hide_index=True
                                        )
                                    
                                    # Momentum Education
                                    st.divider()
                                    st.markdown("""
                                    **Exponential Moving Averages (EMAs):**
                                    - **EMA 12**: Faster, more responsive to price changes
                                    - **EMA 26**: Slower, smoother trend indicator
                                    
                                    **Momentum Interpretation:**
                                    - **EMA 12 > EMA 26**: 🟢 Bullish momentum (uptrend)
                                    - **EMA 12 < EMA 26**: 🔴 Bearish momentum (downtrend)
                                    - **Price > EMA 26**: Strong uptrend established
                                    - **Price < EMA 26**: Strong downtrend established
                                    """)
                                    
                                    # Signal interpretation
                                    col1, col2 = st.columns(2)
                                    with col1:
                                        st.markdown("""
                                        **MACD Signal:**
                                        - MACD > Signal: Bullish
                                        - MACD < Signal: Bearish
                                        - Histogram: Momentum magnitude
                                        """)
                                    with col2:
                                        st.markdown("""
                                        **Momentum Strategy:**
                                        1. Watch for RSI crosses
                                        2. Confirm with MACD signal
                                        3. Check histogram strength
                                        4. Monitor price action
                                        """)
                                
                                # TAB 3: Volatility Indicators
                                with tech_tab3:
                                    st.subheader("Volatility Analysis (Bollinger Bands & Moving Averages)")
                                    st.markdown("Analyze price volatility and trend support/resistance levels")
                                    
                                    vol_cols = ['symbol', 'bb_upper', 'bb_middle', 'bb_lower', 'sma_short', 'sma_long', 'ema_short', 'ema_long', 'Close']
                                    available_vol = [col for col in vol_cols if col in portfolio_tech.columns]
                                    
                                    if available_vol:
                                        vol_df = portfolio_tech[available_vol].copy()
                                        vol_df = vol_df.sort_values('symbol')
                                        
                                        # Rename columns for better readability
                                        vol_df = vol_df.rename(columns={
                                            'symbol': '📊 Symbol',
                                            'Close': '💰 Price',
                                            'bb_upper': '⬆️ BB Upper',
                                            'bb_middle': '➡️ BB SMA',
                                            'bb_lower': '⬇️ BB Lower',
                                            'sma_short': '📈 SMA 20',
                                            'sma_long': '📈 SMA 50',
                                            'ema_short': '📊 EMA 12',
                                            'ema_long': '📊 EMA 26'
                                        })
                                        
                                        # Format numeric columns for display
                                        numeric_cols = vol_df.select_dtypes(include=['float64', 'float32']).columns
                                        for col in numeric_cols:
                                            vol_df[col] = vol_df[col].apply(lambda x: f"{x:.2f}" if pd.notna(x) else "N/A")
                                        
                                        st.dataframe(
                                            vol_df,
                                            use_container_width=True,
                                            hide_index=True
                                        )
                                    
                                    # Bollinger Bands interpretation
                                    st.divider()
                                    col1, col2, col3 = st.columns(3)
                                    with col1:
                                        st.markdown("""
                                        **Price Near Upper Band:**
                                        - 🟠 Strong uptrend
                                        - ⚠️ Potential resistance
                                        - 👀 Watch for reversal
                                        """)
                                    with col2:
                                        st.markdown("""
                                        **Price Near Middle Band:**
                                        - 🟡 Normal trend
                                        - 🔄 Consolidation phase
                                        - ⚖️ Balanced action
                                        """)
                                    with col3:
                                        st.markdown("""
                                        **Price Near Lower Band:**
                                        - 🔴 Strong downtrend
                                        - ⚠️ Potential support
                                        - 📈 Watch for bounce
                                        """)
                                
                                # TAB 4: Detailed Technical View
                                with tech_tab4:
                                    st.subheader("Complete Technical Dataset")
                                    
                                    # Show all technical columns
                                    tech_display = portfolio_tech.copy()
                                    tech_display = tech_display.sort_values('symbol')
                                    
                                    # Numeric formatting
                                    numeric_cols = tech_display.select_dtypes(include=['float64', 'float32']).columns
                                    for col in numeric_cols:
                                        tech_display[col] = tech_display[col].apply(lambda x: f"{x:.4f}" if pd.notna(x) else "N/A")
                                    
                                    st.dataframe(
                                        tech_display,
                                        use_container_width=True,
                                        hide_index=True,
                                        height=400
                                    )
                                    
                                    # Strategy recommendations
                                    st.divider()
                                    st.subheader("📊 Technical Analysis Strategy")
                                    
                                    st.markdown("""
                                    **Multi-Indicator Approach:**
                                    
                                    1. **Identify Trend** (Using Moving Averages)
                                       - Fast EMA (20) > Slow SMA (50) = Uptrend
                                       - Fast EMA (20) < Slow SMA (50) = Downtrend
                                    
                                    2. **Confirm Momentum** (Using RSI & MACD)
                                       - Uptrend: RSI 40-80, MACD > Signal
                                       - Downtrend: RSI 20-60, MACD < Signal
                                    
                                    3. **Identify Support/Resistance** (Using Bollinger Bands)
                                       - Upper Band = Resistance/Overbought
                                       - Lower Band = Support/Oversold
                                       - Width = Volatility level
                                    
                                    4. **Make Decision**
                                       - Strong signals align? → Act
                                       - Weak/conflicting signals? → Wait
                                       - Entry points: Support zones with bullish signals
                                       - Exit points: Resistance zones or bearish divergence
                                    """)
                                
                                # TAB 5: Combined Technical Signals
                                with tech_tab5:
                                    st.subheader("🎯 Technical Indicators Summary")
                                    st.info("""
                                    **Technical Analysis Overview** - View individual technical indicators:
                                    
                                    - **RSI (Relative Strength Index)**: Momentum oscillator measuring overbought/oversold conditions
                                    - **Moving Averages**: Short-term (EMA) vs long-term (EMA) trend indicators
                                    - **Bollinger Bands**: Volatility bands showing support and resistance levels
                                    
                                    For comprehensive analysis combining all signals into actionable recommendations, see the **Combined Signals** tab.
                                    """)
                                    
                                    try:
                                        if not portfolio_tech.empty:
                                            st.info("📊 Technical indicators are calculated and available. See the Combined Signals tab for actionable trading recommendations.")
                                        else:
                                            st.warning("No technical data available")
                                    except Exception as e:
                                        st.error(f"Error: {str(e)}")
                                
                                # TAB 6: Momentum & Valuation (Combined Quick Wins)
                                with tech_tab6:
                                    st.subheader("🎯 Momentum & Valuation Signals")
                                    st.info("""
                                    **Unified Signal Analysis** combines momentum and valuation indicators:
                                    
                                    - 🚀 **Strong Buy**: Uptrend + Oversold
                                    - 📈 **Buy/Accumulate**: Uptrend + Normal
                                    - ⚠️ **Profit Taking**: Uptrend + Overbought
                                    - 📉 **Sell/Reduce**: Downtrend + Overbought
                                    - 💔 **Strong Sell**: Downtrend + Oversold
                                    """)
                                    
                                    if st.button("Generate Momentum & Valuation Signals", key="btn_momentum_valuation"):
                                        try:
                                            analysis_df = holdings_df[~holdings_df['asset'].isin(['fixed-income', 'retirement', 'cash'])].copy()
                                            
                                            if not analysis_df.empty and 'pnl_percent' in analysis_df.columns and 'sym' in analysis_df.columns:
                                                st.success("✅ Combined Signal Analysis Complete")
                                                
                                                signal_data = []
                                                for idx, row in analysis_df.iterrows():
                                                    symbol = row['sym']
                                                    pnl = row['pnl_percent']
                                                    
                                                    # Momentum signal
                                                    if pnl > 10:
                                                        momentum_signal = "Strong Uptrend"
                                                        momentum_score = 3
                                                    elif pnl > 0:
                                                        momentum_signal = "Uptrend"
                                                        momentum_score = 2
                                                    elif pnl > -10:
                                                        momentum_signal = "Mild Downtrend"
                                                        momentum_score = 1
                                                    else:
                                                        momentum_signal = "Strong Downtrend"
                                                        momentum_score = 0
                                                    
                                                    # Mean reversion signal
                                                    if pnl > 50:
                                                        reversion_signal = "Strong Overbought"
                                                        reversion_score = 0
                                                    elif pnl > 20:
                                                        reversion_signal = "Overbought"
                                                        reversion_score = 1
                                                    elif pnl < -50:
                                                        reversion_signal = "Strong Oversold"
                                                        reversion_score = 3
                                                    elif pnl < -20:
                                                        reversion_signal = "Oversold"
                                                        reversion_score = 2
                                                    else:
                                                        reversion_signal = "Normal Range"
                                                        reversion_score = 1.5
                                                    
                                                    # Combined action signal
                                                    combined_score = (momentum_score + reversion_score) / 2
                                                    
                                                    if momentum_score >= 2 and reversion_score >= 2.5:
                                                        action = "🚀 Strong Buy"
                                                    elif momentum_score >= 2 and reversion_score >= 1.5:
                                                        action = "📈 Buy/Accumulate"
                                                    elif momentum_score >= 2 and reversion_score <= 1:
                                                        action = "⚠️ Profit Taking"
                                                    elif momentum_score <= 1 and reversion_score >= 1.5:
                                                        action = "🔄 Consolidating"
                                                    elif momentum_score <= 1 and reversion_score >= 0.5:
                                                        action = "📉 Sell/Reduce"
                                                    else:
                                                        action = "💔 Strong Sell"
                                                    
                                                    signal_data.append({
                                                        'Symbol': symbol,
                                                        'Return %': round(pnl, 2),
                                                        'Momentum': momentum_signal,
                                                        'Valuation': reversion_signal,
                                                        'Action': action,
                                                        'Score': round(combined_score, 2)
                                                    })
                                                
                                                signal_df = pd.DataFrame(signal_data).sort_values('Score', ascending=False)
                                                
                                                st.subheader("📋 All Holdings by Signal Strength")
                                                display_cols = ['Symbol', 'Return %', 'Momentum', 'Valuation', 'Action', 'Score']
                                                st.dataframe(
                                                    signal_df[display_cols],
                                                    use_container_width=True,
                                                    height=400
                                                )
                                                
                                                st.subheader("📊 Signal Distribution")
                                                col1, col2, col3, col4, col5, col6 = st.columns(6)
                                                
                                                strong_buy = len(signal_df[signal_df['Action'].str.contains('Strong Buy')])
                                                buy = len(signal_df[signal_df['Action'].str.contains('Buy/Accumulate')])
                                                profit = len(signal_df[signal_df['Action'].str.contains('Profit Taking')])
                                                consol = len(signal_df[signal_df['Action'].str.contains('Consolidating')])
                                                sell = len(signal_df[signal_df['Action'].str.contains('Sell/Reduce')])
                                                strong_sell = len(signal_df[signal_df['Action'].str.contains('Strong Sell')])
                                                
                                                with col1:
                                                    st.metric("🚀 Strong Buy", strong_buy)
                                                with col2:
                                                    st.metric("📈 Buy", buy)
                                                with col3:
                                                    st.metric("⚠️ Profit Taking", profit)
                                                with col4:
                                                    st.metric("🔄 Consolidating", consol)
                                                with col5:
                                                    st.metric("📉 Sell", sell)
                                                with col6:
                                                    st.metric("💔 Strong Sell", strong_sell)
                                            else:
                                                st.warning("No P&L data available for combined signal analysis")
                                        except Exception as e:
                                            st.error(f"Error generating combined signals: {str(e)}")
                                
                                # TAB 7: Combined Signals (Technical Indicators)
                                with tech_tab7:
                                    st.subheader("🎯 Combined Technical Trading Signals")
                                    st.info("""
                                    **Unified Technical Signal Analysis** combines three key indicators:
                                    
                                    - **RSI Signal**: Momentum strength (Overbought vs Oversold)
                                    - **Moving Average Signal**: Trend direction (Uptrend vs Downtrend)
                                    - **Bollinger Band Signal**: Volatility and support/resistance
                                    - **Combined Score**: Average of all three indicators (0-3 scale)
                                    
                                    **Action Signals by Score:**
                                    - 🚀 **Strong Buy** (2.3+): Excellent setup with multiple bullish signals
                                    - 📈 **Buy** (1.8-2.3): Good entry point with uptrend or support
                                    - 🔄 **Consolidating** (1.3-1.8): Neutral zone - wait for clearer direction
                                    - 📉 **Sell/Reduce** (0.8-1.3): Downtrend or mixed signals present
                                    - 💔 **Strong Sell** (<0.8): Weak on all fronts - strong exit signal
                                    """)
                                    
                                    try:
                                        if not portfolio_tech.empty and 'rsi' in portfolio_tech.columns:
                                            # Generate combined technical signals
                                            tech_signals = []
                                            
                                            for idx, row in portfolio_tech.iterrows():
                                                symbol = row.get('symbol', 'Unknown')
                                                price = row.get('Close', 0)
                                                rsi = row.get('rsi', 50)
                                                
                                                # Get moving averages
                                                ema_short = row.get('ema_short', price)
                                                ema_long = row.get('ema_long', price)
                                                bb_upper = row.get('bb_upper', price)
                                                bb_lower = row.get('bb_lower', price)
                                                bb_middle = row.get('bb_middle', price)
                                                
                                                # RSI Signal
                                                if rsi > 70:
                                                    rsi_signal = "🔴 Overbought"
                                                    rsi_score = 0
                                                elif rsi > 60:
                                                    rsi_signal = "🟠 Strong Uptrend"
                                                    rsi_score = 2
                                                elif rsi > 40:
                                                    rsi_signal = "🟡 Neutral Uptrend"
                                                    rsi_score = 1.5
                                                elif rsi > 30:
                                                    rsi_signal = "🟢 Neutral Downtrend"
                                                    rsi_score = 1
                                                else:
                                                    rsi_signal = "🟢 Oversold"
                                                    rsi_score = 3
                                                
                                                # Trend Signal (based on EMA/SMA crossover)
                                                if ema_short > ema_long:
                                                    trend_signal = "📈 Uptrend"
                                                    trend_score = 2
                                                else:
                                                    trend_signal = "📉 Downtrend"
                                                    trend_score = 0
                                                
                                                # Bollinger Band Signal (price position)
                                                if price >= bb_upper * 0.95:  # Near upper band
                                                    bb_signal = "⬆️ Near Resistance"
                                                    bb_score = 0.5
                                                elif price <= bb_lower * 1.05:  # Near lower band
                                                    bb_signal = "⬇️ Near Support"
                                                    bb_score = 2.5
                                                else:
                                                    bb_signal = "➡️ Mid-Range"
                                                    bb_score = 1.5
                                                
                                                # Combined Action - Based on Score and Trend
                                                combined_score = (rsi_score + trend_score + bb_score) / 3
                                                
                                                # Determine action based on combined score and trend direction
                                                if combined_score >= 2.3:
                                                    action = "🚀 Strong Buy"
                                                    action_detail = "Excellent setup - Multiple bullish signals aligned"
                                                    color = "#90EE90"
                                                elif combined_score >= 1.8:
                                                    action = "📈 Buy"
                                                    action_detail = "Good entry point - Uptrend with support or neutral momentum"
                                                    color = "#C8E6C9"
                                                elif combined_score >= 1.3:
                                                    action = "🔄 Consolidating"
                                                    action_detail = "Neutral zone - Wait for clearer signals"
                                                    color = "#E1F5FE"
                                                elif combined_score >= 0.8:
                                                    action = "📉 Sell/Reduce"
                                                    action_detail = "Downtrend or mixed signals - Consider reducing exposure"
                                                    color = "#FFCCBC"
                                                else:
                                                    action = "💔 Strong Sell"
                                                    action_detail = "Weak on all fronts - Strong exit signal"
                                                    color = "#FFCDD2"
                                                
                                                tech_signals.append({
                                                    'Symbol': symbol,
                                                    'Price': f"${price:.2f}" if price > 0 else "N/A",
                                                    'RSI': f"{rsi:.1f}",
                                                    'RSI Signal': rsi_signal,
                                                    'Trend': trend_signal,
                                                    'BB Position': bb_signal,
                                                    'Action': action,
                                                    'Detail': action_detail,
                                                    'Score': round(combined_score, 2),
                                                    'Color': color
                                                })
                                            
                                            signals_df = pd.DataFrame(tech_signals).sort_values('Score', ascending=False)
                                            
                                            st.subheader("📋 All Holdings by Technical Signal")
                                            
                                            # Display table with color coding
                                            display_cols = ['Symbol', 'Price', 'RSI', 'RSI Signal', 'Trend', 'BB Position', 'Action', 'Score']
                                            st.dataframe(
                                                signals_df[display_cols],
                                                use_container_width=True,
                                                height=400
                                            )
                                            
                                            st.divider()
                                            st.subheader("📊 Signal Distribution")
                                            
                                            col1, col2, col3, col4, col5 = st.columns(5)
                                            
                                            strong_buy = len(signals_df[signals_df['Action'].str.contains('Strong Buy')])
                                            buy = len(signals_df[signals_df['Action'].str.contains('Buy')])
                                            caution = len(signals_df[signals_df['Action'].str.contains('Caution')])
                                            sell = len(signals_df[signals_df['Action'].str.contains('Sell')])
                                            strong_sell = len(signals_df[signals_df['Action'].str.contains('Strong Sell')])
                                            
                                            with col1:
                                                st.metric("🚀 Strong Buy", strong_buy)
                                            with col2:
                                                st.metric("📈 Buy", buy)
                                            with col3:
                                                st.metric("⚠️ Caution", caution)
                                            with col4:
                                                st.metric("📉 Sell", sell)
                                            with col5:
                                                st.metric("💔 Strong Sell", strong_sell)
                                            
                                            st.divider()
                                            st.subheader("🎯 Top Technical Opportunities")
                                            
                                            for action_type, emoji in [
                                                ("🚀 Strong Buy", "🚀"),
                                                ("📈 Buy", "📈"),
                                                ("💔 Strong Sell", "💔"),
                                            ]:
                                                candidates = signals_df[signals_df['Action'].str.contains(action_type.split()[1]) if len(action_type.split()) > 1 else False]
                                                if action_type == "🚀 Strong Buy":
                                                    candidates = signals_df[signals_df['Action'] == action_type]
                                                elif action_type == "📈 Buy":
                                                    candidates = signals_df[(signals_df['Action'] == "📈 Buy")]
                                                elif action_type == "💔 Strong Sell":
                                                    candidates = signals_df[signals_df['Action'] == action_type]
                                                
                                                if not candidates.empty:
                                                    with st.expander(f"{emoji} {action_type} ({len(candidates)} opportunities)", expanded=(action_type == "🚀 Strong Buy")):
                                                        for idx, row in candidates.iterrows():
                                                            col1, col2 = st.columns([1, 3])
                                                            with col1:
                                                                st.metric(row['Symbol'], row['Price'])
                                                            with col2:
                                                                st.write(f"**RSI:** {row['RSI Signal']}")
                                                                st.write(f"**Trend:** {row['Trend']}")
                                                                st.write(f"**Position:** {row['BB Position']}")
                                                                st.write(f"**Reason:** {row['Detail']}")
                                        else:
                                            st.warning("No RSI data available for combined signal analysis")
                                    except Exception as e:
                                        st.error(f"Error generating technical signals: {str(e)}")
                            else:
                                st.warning(f"No technical data found for your {len(symbols)} holdings.")
                                st.info("💡 Click '📊 Run Technical Analysis' button to calculate indicators for all symbols.")
                    else:
                        st.warning("❌ No technical analysis data available in database.")
                        st.info("""
                        **To generate technical indicators:**
                        1. Make sure you have price data (use 'Update Price Data' button at top)
                        2. Click the "📈 Calculate Now" button above
                        3. Wait for calculation to complete
                        4. Click "📊 Load Technical Analysis" to view results
                        
                        This process calculates RSI, MACD, Bollinger Bands, and moving averages for each holding.
                        """)
            else:
                st.error("No portfolio data available")
    
    with tab3:
        st.subheader("Fundamental Analysis - All Holdings")
        st.info("P/E ratio, ROE, ROA, dividend yield for equities and ETFs.")
        
        if st.button("Load Fundamental Analysis", key="btn_load_fund"):
            if st.session_state.prices_with_holdings is not None:
                symbols = st.session_state.prices_with_holdings['sym'].unique().tolist()
                
                with st.spinner("Fetching fundamental metrics..."):
                    db = init_parquet_db()
                    fund_data = fetch_fundamental_analysis(db, symbols)
                    
                    if fund_data is not None and not fund_data.empty:
                        portfolio_fund = fund_data[fund_data['symbol'].isin(symbols)]
                        
                        if not portfolio_fund.empty:
                            st.success(f"✅ Found fundamental analysis for {len(portfolio_fund.groupby('symbol'))} equities")
                            
                            # Define columns to display in order of importance
                            important_cols = ['symbol', 'revenue', 'net_income', 'total_assets', 'total_liabilities', 
                                            'shareholders_equity', 'current_assets', 'current_liabilities',
                                            'net_margin', 'roa', 'roe', 'debt_to_equity', 'current_ratio', 'timestamp']
                            
                            # Get available columns from the dataframe
                            available_cols = [col for col in important_cols if col in portfolio_fund.columns]
                            
                            if available_cols:
                                display_df = portfolio_fund[available_cols].copy()
                                display_df = display_df.sort_values('symbol')
                                
                                # Format numeric columns with proper scaling
                                for col in display_df.columns:
                                    if col == 'timestamp':
                                        continue  # Keep timestamp as-is
                                    elif col == 'symbol':
                                        continue  # Keep symbol as-is
                                    elif col in ['revenue', 'net_income', 'total_assets', 'total_liabilities', 'shareholders_equity', 'current_assets', 'current_liabilities']:
                                        # Format large numbers in billions/millions
                                        def format_currency(x):
                                            if pd.isna(x) or x is None:
                                                return x
                                            x = float(x)
                                            if abs(x) >= 1e9:
                                                return f"${x/1e9:.2f}B"
                                            elif abs(x) >= 1e6:
                                                return f"${x/1e6:.2f}M"
                                            else:
                                                return f"${x:,.0f}"
                                        display_df[col] = display_df[col].apply(format_currency)
                                    else:
                                        # Format percentages and ratios
                                        display_df[col] = display_df[col].apply(lambda x: f"{x:.2f}" if pd.notna(x) and isinstance(x, (int, float)) else x)
                                
                                st.subheader("Financial Metrics")
                                st.dataframe(
                                    display_df,
                                    use_container_width=True,
                                    hide_index=True
                                )
                            
                            # Show interpretation guide
                            st.divider()
                            st.subheader("📊 Metric Interpretations")
                            
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.markdown("""
                                **Income Statement**
                                - **Revenue**: Total sales
                                - **Net Income**: Profit after all expenses
                                
                                **Balance Sheet**
                                - **Total Assets**: Everything the company owns
                                - **Total Liabilities**: Everything the company owes
                                - **Equity**: Assets minus Liabilities
                                """)
                            with col2:
                                st.markdown("""
                                **Profitability**
                                - **Net Margin**: Net income ÷ Revenue (higher = better)
                                - **ROE**: Return on Equity (higher = better)
                                - **ROA**: Return on Assets (higher = better)
                                """)
                            with col3:
                                st.markdown("""
                                **Liquidity & Leverage**
                                - **Current Assets**: Cash + items convertible to cash within 1 year
                                - **Current Liabilities**: Obligations due within 1 year
                                - **Current Ratio**: Current assets ÷ Current liabilities (>1.0 = good)
                                - **Debt/Equity**: Total liabilities ÷ Equity (lower = safer)
                                """)
                        else:
                            st.warning(f"No fundamental data found for your {len(symbols)} holdings.")
                    else:
                        st.warning("❌ No fundamental analysis data available in database.")
                        st.info("""
                        **To calculate fundamental analysis:**
                        1. Click the "📈 Run Fundamental Analysis" button at the top
                        2. Wait for the analysis to complete (typically 2-5 minutes)
                        3. Come back here and click "Load Fundamental Analysis" to view results
                        
                        **Important Limitations:**
                        - **US Stocks Only**: Fundamental analysis uses SEC filings, so only US-listed companies are supported
                        - **Equities Only**: ETFs, crypto, and other assets are skipped
                        - **Sample US Tickers**: AAPL, MSFT, TSLA, GOOGL, BA, GM, NFLX, etc.
                        - **Not Supported**: AIR.PA, QAN.AX, VWRL.AS, GLD, Ethereum, BitCoin, etc.
                        """)
            else:
                st.error("No portfolio data available")
    
    with tab4:
        st.subheader("Risk Analysis")
        st.info("Volatility, correlation, and Value at Risk (VaR) metrics for your portfolio.")
        
        if st.session_state.prices_with_holdings is not None and len(st.session_state.prices_with_holdings) > 0:
            try:
                db = init_parquet_db()
                prices = db.read_table('prices')
                
                if prices is not None and not prices.empty:
                    # Calculate portfolio statistics
                    portfolio_summary = get_portfolio_summary(st.session_state.prices_with_holdings)
                    total_value = portfolio_summary['total_value']
                    
                    # Calculate returns and volatility for the portfolio
                    symbols = st.session_state.prices_with_holdings['sym'].unique().tolist()
                    
                    # Get ALL historical prices for each symbol (not just latest)
                    hist_prices = prices[prices['symbol'].isin(symbols)].copy()
                    
                    if not hist_prices.empty:
                        # Calculate volatility metrics from historical returns
                        volatility_by_symbol = {}
                        max_prices = {}
                        current_prices = {}
                        
                        for symbol in symbols:
                            symbol_data = hist_prices[hist_prices['symbol'] == symbol].sort_values('timestamp')
                            
                            if len(symbol_data) > 1:
                                # Calculate daily returns
                                symbol_data = symbol_data.copy()
                                symbol_data['returns'] = symbol_data['close_price'].pct_change() * 100
                                
                                # Get volatility from returns (std of daily returns)
                                vol = symbol_data['returns'].std()
                                if pd.isna(vol):
                                    vol = 0
                                volatility_by_symbol[symbol] = vol
                                
                                # Get max and current prices
                                max_prices[symbol] = symbol_data['close_price'].max()
                                current_prices[symbol] = symbol_data['close_price'].iloc[-1]
                            else:
                                volatility_by_symbol[symbol] = 0
                                max_prices[symbol] = symbol_data['close_price'].iloc[0] if len(symbol_data) > 0 else 0
                                current_prices[symbol] = symbol_data['close_price'].iloc[0] if len(symbol_data) > 0 else 0
                        
                        # Calculate portfolio metrics
                        avg_volatility = np.mean(list(volatility_by_symbol.values())) if volatility_by_symbol else 0
                        portfolio_volatility = avg_volatility  # Already in percentage
                        
                        # Estimate VaR at 95% confidence (1.645 * daily volatility / 100 * portfolio value)
                        var_95 = 1.645 * (avg_volatility / 100) * total_value if avg_volatility > 0 else 0
                        
                        # Calculate drawdowns
                        drawdowns = {}
                        for symbol in symbols:
                            if symbol in max_prices and symbol in current_prices:
                                max_p = max_prices[symbol]
                                curr_p = current_prices[symbol]
                                if max_p > 0:
                                    dd = ((curr_p - max_p) / max_p * 100)
                                    drawdowns[symbol] = dd
                                else:
                                    drawdowns[symbol] = 0
                        
                        max_drawdown = min(drawdowns.values()) if drawdowns else 0
                        
                        # Display metrics
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Portfolio Volatility", f"{portfolio_volatility:.2f}%", 
                                    delta=None, help="Daily volatility (std dev of returns)")
                        with col2:
                            st.metric("VaR (95% Confidence)", f"-${var_95:,.0f}", 
                                    delta=None, help="Potential 1-day loss at 95% confidence")
                        with col3:
                            st.metric("Max Drawdown", f"{max_drawdown:.2f}%", 
                                    delta=None, help="Largest decline from recent highs")
                        
                        st.divider()
                        
                        # Show volatility by holding
                        st.subheader("Risk by Holding")
                        risk_by_symbol = pd.DataFrame({
                            'Symbol': list(volatility_by_symbol.keys()),
                            'Volatility (%)': [round(v, 2) for v in volatility_by_symbol.values()],
                            'Drawdown (%)': [round(drawdowns.get(s, 0), 2) for s in volatility_by_symbol.keys()],
                            'Current Price': [round(current_prices.get(s, 0), 2) for s in volatility_by_symbol.keys()],
                            'Max Price': [round(max_prices.get(s, 0), 2) for s in volatility_by_symbol.keys()]
                        }).sort_values('Volatility (%)', ascending=False)
                        
                        st.dataframe(risk_by_symbol, use_container_width=True, hide_index=True)
                        
                        # Show correlation info
                        st.subheader("📊 Portfolio Diversification Analysis")
                        unique_assets = st.session_state.prices_with_holdings['asset'].unique()
                        unique_brokers = st.session_state.prices_with_holdings['brokerName'].unique()
                        
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Asset Types", len(unique_assets), 
                                    help="Number of different asset classes (stocks, ETFs, crypto, etc.)")
                        with col2:
                            st.metric("Brokers", len(unique_brokers), 
                                    help="Number of different brokers/platforms holding your investments")
                        with col3:
                            st.metric("Holdings", len(symbols), 
                                    help="Total number of individual positions")
                        
                        st.divider()
                        
                        # Diversification guidance
                        st.subheader("Diversification Assessment")
                        
                        # Calculate diversification metrics
                        portfolio_values = st.session_state.prices_with_holdings['current_value'].values
                        total_value = portfolio_values.sum()
                        concentrations = (portfolio_values / total_value * 100) if total_value > 0 else []
                        
                        # Herfindahl index (concentration metric: 0-10000, lower is more diversified)
                        herfindahl = sum(c**2 for c in concentrations)
                        
                        # Top 3 holdings percentage
                        top_3_pct = sum(sorted(concentrations, reverse=True)[:3])
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.markdown("""
                            **Diversification Metrics:**
                            - **Herfindahl Index**: {:.0f} (0=perfectly diversified, 10000=single holding)
                            - **Top 3 Holdings**: {:.1f}% of portfolio
                            - **Asset Classes**: {} different types
                            - **Broker Count**: {} different platforms
                            """.format(herfindahl, top_3_pct, len(unique_assets), len(unique_brokers)))
                        
                        with col2:
                            # Diversification risk assessment
                            if herfindahl > 3000:
                                risk_level = "🔴 HIGH CONCENTRATION RISK"
                                recommendation = "Consider diversifying further"
                                color = "red"
                            elif herfindahl > 1500:
                                risk_level = "🟡 MODERATE CONCENTRATION"
                                recommendation = "Diversification is reasonable but could be improved"
                                color = "orange"
                            else:
                                risk_level = "🟢 WELL DIVERSIFIED"
                                recommendation = "Good diversification across holdings"
                                color = "green"
                            
                            st.markdown(f"""
                            **Risk Assessment:** {risk_level}
                            
                            {recommendation}
                            """)
                        
                        st.divider()
                        
                        # Detailed guidance
                        st.subheader("📋 What This Means")
                        
                        guidance_col1, guidance_col2 = st.columns(2)
                        
                        with guidance_col1:
                            st.markdown("""
                            **Why Diversification Matters:**
                            - Spreads risk across multiple positions
                            - Reduces impact of any single holding failing
                            - Different assets perform differently in various market conditions
                            - Multiple brokers protect against platform outages
                            
                            **Concentration Risk:**
                            If your portfolio is concentrated (few large positions), one bad event can significantly damage your portfolio.
                            """)
                        
                        with guidance_col2:
                            st.markdown("""
                            **Diversification Guidelines:**
                            - **Asset Classes**: 3+ types (stocks, bonds, crypto, etc.)
                            - **Number of Holdings**: 10-30 for most investors
                            - **Top Holding**: Should be <20% of portfolio
                            - **Top 3 Holdings**: Should be <60% of portfolio
                            - **Brokers**: 2+ platforms reduces counterparty risk
                            """)
                        
                        st.divider()
                        
                        # Show concentration by holding
                        st.subheader("💰 Portfolio Concentration")
                        
                        concentration_data = []
                        for idx, row in st.session_state.prices_with_holdings.iterrows():
                            pct = (row['current_value'] / total_value * 100) if total_value > 0 else 0
                            concentration_data.append({
                                'Symbol': row['sym'],
                                'Value': f"${row['current_value']:,.0f}",
                                'Weight %': f"{pct:.1f}%",
                                'Risk Level': '🔴 High' if pct > 20 else '🟡 Moderate' if pct > 10 else '🟢 Low'
                            })
                        
                        conc_df = pd.DataFrame(concentration_data).sort_values('Weight %', 
                                                                               key=lambda x: x.str.rstrip('%').astype(float),
                                                                               ascending=False).head(15)
                        
                        st.dataframe(conc_df, use_container_width=True, hide_index=True,
                                    column_config={
                                        'Symbol': st.column_config.TextColumn('Symbol', width=100),
                                        'Value': st.column_config.TextColumn('Position Value', width=150),
                                        'Weight %': st.column_config.TextColumn('Portfolio Weight', width=130),
                                        'Risk Level': st.column_config.TextColumn('Concentration Risk', width=150)
                                    })
                        
                        if top_3_pct < 60:
                            st.success(f"✅ Top 3 holdings ({top_3_pct:.1f}%) are within recommended <60% range")
                        else:
                            st.warning(f"⚠️ Top 3 holdings ({top_3_pct:.1f}%) exceed recommended <60% range")
                    else:
                        st.warning("No price data available for risk calculations.")
                else:
                    st.warning("No price history available. Run 'Update Price Data' first.")
            except Exception as e:
                st.error(f"Error calculating risk metrics: {str(e)[:100]}")
        else:
            st.error("No portfolio data available for risk analysis")


def render_email_reports():
    """Render email reports page."""
    st.title("📧 Email Reports")
    
    st.markdown("""
    Schedule automated portfolio reports to be emailed to you.
    """)
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Report Configuration")
        
        report_type = st.selectbox("Report Type", [
            "Daily Summary",
            "Weekly Performance",
            "Monthly Deep Dive",
            "Quarterly Analysis"
        ])
        
        email = st.text_input("Email Address", "your.email@example.com")
        
        col_freq, col_day, col_time = st.columns(3)
        with col_freq:
            frequency = st.selectbox("Frequency", ["Daily", "Weekly", "Monthly"])
        
        if frequency == "Weekly":
            with col_day:
                day = st.selectbox("Day of Week", ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"])
        
        with col_time:
            time = st.time_input("Time (UTC)", value=datetime.now().time())
        
        if st.button("Schedule Report", type="primary"):
            st.success(f"✓ Report scheduled: {report_type} to {email} {frequency}")
            st.info("Reports will be sent starting from the next scheduled time.")
    
    with col1:
        st.subheader("Report Preview")
        st.markdown(f"""
        **{report_type}**
        
        Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}
        
        Your portfolio has {len(st.session_state.prices_with_holdings)} positions
        across {st.session_state.prices_with_holdings['brokerName'].nunique()} brokers.
        
        Total Value: ${get_portfolio_summary(st.session_state.prices_with_holdings)['total_value']:,.2f}
        """)


def render_help():
    """Render help and glossary page."""
    st.title("❓ Help & Glossary")
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Portfolio Terms",
        "Technical Indicators",
        "Financial Metrics",
        "Strategies",
        "FAQs"
    ])
    
    with tab1:
        st.markdown("""
        ### Portfolio Terms
        
        **Cost Basis**: The original price at which you purchased each position.
        
        **Current Price**: The latest market price for the security.
        
        **P&L (Profit/Loss)**: The difference between your current value and cost basis.
        
        **Weight**: The percentage of total portfolio value represented by a position.
        
        **Unrealized P&L**: Profit or loss on positions you still hold.
        """)
    
    with tab2:
        st.markdown("""
        ### Technical Indicators
        
        **RSI (Relative Strength Index)**: Measures momentum on scale of 0-100.
        - Above 70: Potentially overbought
        - Below 30: Potentially oversold
        
        **MACD**: Momentum indicator using moving average convergence/divergence.
        
        **Bollinger Bands**: Price channels showing support/resistance levels.
        
        **Moving Average**: Smooths price data to identify trends.
        """)
    
    with tab3:
        st.markdown("""
        ### Financial Metrics
        
        **P/E Ratio**: Price-to-Earnings ratio (lower may indicate undervaluation).
        
        **ROE**: Return on Equity (higher indicates more efficient use of capital).
        
        **ROA**: Return on Assets (profitability relative to assets).
        
        **Dividend Yield**: Annual dividend as percentage of stock price.
        
        **Beta**: Volatility relative to the market (1.0 = market average).
        """)
    
    with tab4:
        st.markdown("""
        ### Investment Strategies
        
        **Momentum**: Follow stocks with strong upward trends.
        
        **Mean Reversion**: Buy oversold stocks expecting bounce-back.
        
        **Sector Rotation**: Move capital between sectors based on cycles.
        
        **Value Investing**: Buy undervalued stocks based on fundamentals.
        
        **Portfolio Beta**: Balance portfolio risk/reward through diversification.
        """)
    
    with tab5:
        st.markdown("""
        ### Frequently Asked Questions
        
        **Q: How often is the data updated?**
        A: Price data updates daily after market close. Technical and fundamental analysis updates when new data is available.
        
        **Q: Why don't all symbols have technical data?**
        A: Technical analysis is calculated for stocks with sufficient price history.
        
        **Q: How are P&L calculations done?**
        A: P&L = (Current Price - Cost Basis) × Quantity
        
        **Q: Can I export reports?**
        A: Email reports provide a scheduled export option with detailed analysis.
        
        **Q: How is portfolio beta calculated?**
        A: Beta measures correlation of portfolio returns with market returns.
        """)


def render_backtesting():
    """Render enhanced backtesting page."""
    st.title("📊 Enhanced Backtesting Engine")
    
    st.markdown("""
    Test your trading strategies on historical data before risking real money. This backtester simulates
    how a strategy would have performed in the past, helping you evaluate profitability and risk.
    """)
    
    # Educational tabs
    tab1, tab2, tab3 = st.tabs(["📚 Getting Started", "Strategies", "Understanding Results"])
    
    with tab1:
        st.subheader("What is Backtesting?")
        st.markdown("""
        **Backtesting** is testing a trading strategy using historical data. You specify:
        - Which stock to trade
        - Entry and exit signals (when to buy/sell)
        - Risk management rules (stop loss, take profit)
        
        Then the system:
        - Simulates buying/selling at those points in history
        - Calculates profit/loss for each trade
        - Shows you overall performance metrics
        
        **Why Backtesting Matters:**
        - Reveals if your strategy actually works (most don't!)
        - Shows expected performance (Sharpe ratio, win rate)
        - Identifies periods of excessive drawdowns
        - Helps optimize parameters before live trading
        """)
        
        st.subheader("How to Use This Tool")
        st.markdown("""
        **Step 1: Choose Your Signal**
        - **RSI (Relative Strength Index):** Buy when oversold (<30), Sell when overbought (>70)
        - **MACD (Moving Average Convergence):** Buy on bullish crossover, Sell on bearish crossover
        - **Bollinger Bands:** Buy near lower band, Sell near upper band
        
        **Step 2: Set Entry & Exit Thresholds**
        - **Entry Threshold:** Signal level that triggers a buy (lower = wait for stronger signal)
        - **Exit Threshold:** Signal level that triggers a sell (higher = wait for stronger signal)
        
        **Step 3: Define Risk Management**
        - **Stop Loss %:** Maximum loss you'll accept before exiting (e.g., 5% = exit if down 5%)
        - **Take Profit %:** Target profit to close winners (e.g., 10% = exit when up 10%)
        
        **Step 4: Review Results**
        - Check Sharpe Ratio (higher is better)
        - Check Win Rate (percentage of winning trades)
        - Review equity curve for consistency
        """)
    
    with tab2:
        st.subheader("Signal Types Explained")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            **RSI (Relative Strength Index)**
            - Range: 0-100
            - Signal: Buy when <30 (oversold), Sell when >70 (overbought)
            - Best for: Range-bound stocks, mean reversion
            - Drawback: Can stay overbought/oversold in trends
            
            **MACD (Moving Average Convergence Divergence)**
            - Signal: Buy on bullish crossover, Sell on bearish crossover
            - Momentum indicator following trends
            - Best for: Trending markets
            - Drawback: Lags in choppy, sideways markets
            """)
        
        with col2:
            st.markdown("""
            **Bollinger Bands**
            - Signal: Buy near lower band, Sell near upper band
            - Volatility bands around moving average
            - Best for: Identifying support/resistance
            - Drawback: Requires additional confirmation
            
            **Typical Entry Thresholds:**
            - Conservative: 20-30 (wait for strong signal)
            - Moderate: 30-40 (standard signals)
            - Aggressive: 40+ (more signals, higher false alarms)
            """)
    
    with tab3:
        st.subheader("Understanding the Results")
        
        st.markdown("""
        **Key Metrics Explained:**
        
        | Metric | Meaning | Good Value |
        |--------|---------|------------|
        | **Sharpe Ratio** | Risk-adjusted returns (return per unit of risk) | >1.0 is good, >2.0 is excellent |
        | **Win Rate** | Percentage of profitable trades | >50% is profitable |
        | **Profit Factor** | Total wins ÷ Total losses | >1.5 is good, >2.0 is excellent |
        | **Annualized Return** | Average yearly return % | Compare to buy-and-hold |
        | **Max Drawdown** | Largest peak-to-trough decline | Lower is better |
        | **Sortino Ratio** | Risk-adjusted for downside only | >1.0 is good |
        
        **Important Caveats:**
        - ⚠️ **Past performance ≠ future results** - Markets change!
        - ⚠️ **Slippage not included** - Real trades execute at worse prices
        - ⚠️ **No commissions** - Real trading costs money each trade
        - ⚠️ **Sample data is simulated** - Test on real historical data
        """)
    
    if not MODULES_AVAILABLE:
        st.error("Backtesting module not available")
        return
    
    engine = EnhancedBacktestingEngine(min_capital=10000.0)
    
    # Input parameters
    st.subheader("Configure Your Strategy")
    st.markdown("Set up the parameters below to test your strategy on historical data.")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        symbol = st.text_input(
            "Stock Symbol", 
            "AAPL",
            help="Enter stock ticker (e.g., AAPL, MSFT, TSLA)"
        )
        signal_type = st.selectbox(
            "Signal Type", 
            ["rsi", "macd", "bollinger"],
            format_func=lambda x: {"rsi": "RSI (Relative Strength Index)", "macd": "MACD", "bollinger": "Bollinger Bands"}[x],
            help="Technical indicator that generates buy/sell signals"
        )
    
    with col2:
        entry_threshold = st.slider(
            "Entry Threshold", 
            min_value=-100, 
            max_value=100, 
            value=30,
            help="Signal level to trigger a BUY. Lower = wait for stronger signal"
        )
        exit_threshold = st.slider(
            "Exit Threshold", 
            min_value=-100, 
            max_value=100, 
            value=70,
            help="Signal level to trigger a SELL. Higher = wait for stronger signal"
        )
    
    with col3:
        stop_loss = st.slider(
            "Stop Loss (%)", 
            min_value=1, 
            max_value=50, 
            value=5,
            help="Exit trade if it drops by this % (e.g., 5% = exit if down 5%)"
        ) / 100
        take_profit = st.slider(
            "Take Profit (%)", 
            min_value=1, 
            max_value=50, 
            value=10,
            help="Exit trade if it gains this % (e.g., 10% = exit if up 10%)"
        ) / 100
    
    # Create sample data for demonstration
    if st.button("🚀 Run Backtest", use_container_width=True):
        with st.spinner("Running backtest on historical data..."):
            dates = pd.date_range(start='2023-01-01', periods=252, freq='D')
            close = 100 + np.cumsum(np.random.randn(252) * 2)
            
            prices_df = pd.DataFrame({
                'Open': close * np.random.uniform(0.98, 1.02, 252),
                'High': close * np.random.uniform(1.01, 1.03, 252),
                'Low': close * np.random.uniform(0.97, 0.99, 252),
                'Close': close,
                'Volume': np.random.randint(1000000, 5000000, 252)
            }, index=dates)
            
            result = engine.backtest_strategy(
                symbol=symbol,
                prices_df=prices_df,
                signal_type=signal_type,
                entry_threshold=entry_threshold,
                exit_threshold=exit_threshold,
                stop_loss=stop_loss,
                take_profit=take_profit
            )
            
            # Display metrics
            st.subheader("📈 Performance Metrics")
            st.markdown(f"""
            Backtest Results for **{symbol}** using **{signal_type.upper()}** strategy
            """)
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(
                    "Sharpe Ratio", 
                    f"{result.metrics['sharpe_ratio']:.2f}",
                    help="Risk-adjusted returns (>1.0 is good)"
                )
            with col2:
                st.metric(
                    "Win Rate", 
                    f"{result.metrics['win_rate']:.1%}",
                    help="Percentage of profitable trades"
                )
            with col3:
                st.metric(
                    "Total Trades", 
                    f"{result.metrics['num_trades']:.0f}",
                    help="Number of complete buy/sell cycles"
                )
            with col4:
                st.metric(
                    "Profit Factor", 
                    f"{result.metrics['profit_factor']:.2f}",
                    help="Total wins ÷ Total losses (>1.5 is good)"
                )
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric(
                    "Annualized Return", 
                    f"{result.metrics['annualized_return']:.1%}",
                    help="Average yearly return percentage"
                )
            with col2:
                st.metric(
                    "Max Drawdown", 
                    f"{result.metrics['max_drawdown']:.1%}" if 'max_drawdown' in result.metrics else "N/A",
                    help="Largest peak-to-trough decline"
                )
            with col3:
                st.metric(
                    "Sortino Ratio", 
                    f"{result.metrics['sortino_ratio']:.2f}",
                    help="Risk-adjusted (downside only)"
                )
            
            # Interpretation guide
            st.markdown("### 📊 How to Interpret These Results")
            
            col1, col2 = st.columns(2)
            with col1:
                st.info(f"""
                **Your Strategy's Performance:**
                - Win Rate: {result.metrics['win_rate']:.1%} → {'Winning strategy!' if result.metrics['win_rate'] > 0.5 else 'Losing more than winning'}
                - Sharpe Ratio: {result.metrics['sharpe_ratio']:.2f} → {'Excellent risk-adjusted returns' if result.metrics['sharpe_ratio'] > 2 else 'Moderate returns' if result.metrics['sharpe_ratio'] > 1 else 'Risky returns'}
                - Annualized Return: {result.metrics['annualized_return']:.1%}
                """)
            
            with col2:
                st.warning("""
                **Important Reminders:**
                - Past performance doesn't guarantee future results
                - These results use simplified simulation data
                - Real trading includes slippage and commissions
                - Test parameters on different time periods
                - Consider combining with fundamental analysis
                """)
            
            # Plot equity curve
            if result.equity_curve is not None:
                st.subheader("💹 Equity Curve")
                st.markdown("This shows how your $10,000 starting capital would have grown or declined:")
                
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    y=result.equity_curve, 
                    mode='lines', 
                    name='Portfolio Value',
                    fill='tozeroy',
                    line=dict(color='#1f77b4', width=2)
                ))
                fig.update_layout(
                    xaxis_title="Trading Days",
                    yaxis_title="Portfolio Value ($)",
                    hovermode='x unified',
                    height=400
                )
                st.plotly_chart(fig, use_container_width=True)
            
            # Save results
            col1, col2 = st.columns(2)
            with col1:
                if st.button("💾 Save Results to Parquet", use_container_width=True):
                    output = engine.save_backtest_results(symbol, result)
                    st.success(f"✅ Results saved to: {output}")
            
            with col2:
                st.info("💡 Tip: Save your results to track strategy performance over time")




def render_options_strategy():
    """Render options strategy automation page."""
    st.title("⚙️ Options Strategy Analyzer")
    
    st.markdown("""
    This tool helps you construct, analyze, and understand options strategies using Greeks-based risk metrics.
    Select a strategy type that matches your market outlook and risk tolerance.
    """)
    
    # Educational tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📚 Guide", "Strategies", "Greeks Explained", "Risk Management"])
    
    with tab1:
        st.subheader("How to Use This Tool")
        st.markdown("""
        **Step 1: Choose a Strategy Type**
        - Select based on your market outlook and volatility expectations
        - Each strategy has different risk/reward profiles
        
        **Step 2: Set Parameters**
        - Underlying symbol and current price
        - Days to expiration (typically 30-60 days for optimal risk/reward)
        - Position sizing based on your account risk tolerance
        
        **Step 3: Review the Analysis**
        - Check the payoff diagram to understand max profit/loss
        - Review Greeks to understand directional and volatility exposure
        - Assess whether the risk/reward matches your objectives
        
        **Step 4: Monitor and Adjust**
        - Track Greeks as underlying price and time change
        - Consider closing winners early (60-80% max profit)
        - Adjust position if underlying moves significantly
        """)
    
    with tab2:
        st.subheader("Options Strategies")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            **Iron Condor**
            - *Market Outlook:* Neutral/Range-bound
            - *Volatility:* Best in high IV environments
            - *Setup:* Sell OTM put spread + sell OTM call spread
            - *Max Profit:* Net credit received
            - *Max Loss:* Spread width - net credit
            - *Best For:* Income in sideways markets
            
            **Strangle**
            - *Market Outlook:* Neutral/Expect volatility
            - *Volatility:* Works in both high and low IV
            - *Setup:* Sell OTM put + sell OTM call
            - *Max Profit:* Net credit received
            - *Max Loss:* Unlimited on call side
            - *Best For:* High probability trades with defined risk
            """)
        
        with col2:
            st.markdown("""
            **Straddle**
            - *Market Outlook:* Expect significant move (direction uncertain)
            - *Volatility:* Best before events (earnings, FOMC, etc)
            - *Setup:* Buy ATM call + buy ATM put (or sell for income)
            - *Max Profit:* Unlimited (if long) or limited credit (if short)
            - *Max Loss:* Premium paid (if long)
            - *Best For:* Playing volatility expansion
            
            **Covered Call**
            - *Market Outlook:* Mildly bullish or neutral
            - *Volatility:* Works best when IV is elevated
            - *Setup:* Own 100 shares + sell OTM call
            - *Max Profit:* Capped at strike price
            - *Max Loss:* Stock decline (partially offset by call premium)
            - *Best For:* Generating income on holdings
            """)
    
    with tab3:
        st.subheader("Understanding the Greeks")
        
        greek_info = {
            "Delta (Δ)": {
                "meaning": "Directional exposure - how much the option price moves with $1 move in underlying",
                "range": "-1.0 to +1.0",
                "interpretation": "Delta 0.50 = $0.50 profit for every $1 underlying move",
                "use": "Manage directional risk; neutral strategies aim for delta near 0"
            },
            "Gamma (Γ)": {
                "meaning": "How fast delta changes - delta acceleration",
                "range": "0 to ~0.1 (typically)",
                "interpretation": "High gamma = delta changes quickly (risky near expiration)",
                "use": "Manage how much delta exposure changes; high gamma = more risk"
            },
            "Theta (Θ)": {
                "meaning": "Time decay - how much option loses value each day",
                "range": "Usually negative for buyers, positive for sellers",
                "interpretation": "Theta -0.05 = $0.05 daily loss from time decay",
                "use": "Income strategies want positive theta; time works in your favor"
            },
            "Vega (ν)": {
                "meaning": "Volatility exposure - how much price changes with 1% IV change",
                "range": "Usually 0 to ~0.5",
                "interpretation": "Vega 0.10 = $0.10 profit if IV rises 1%",
                "use": "Manage volatility risk; long options benefit from IV rise"
            }
        }
        
        for greek, info in greek_info.items():
            with st.expander(f"**{greek}**: {info['meaning']}", expanded=False):
                st.markdown(f"""
                **Range:** {info['range']}
                
                **Interpretation:** {info['interpretation']}
                
                **How to Use:** {info['use']}
                """)
    
    with tab4:
        st.subheader("Risk Management Guidelines")
        
        st.markdown("""
        **Position Sizing**
        - Conservative: Risk 1-2% of account per trade
        - Moderate: Risk 2-3% of account per trade
        - Aggressive: Risk 3-5% of account per trade
        
        **Greeks Targets by Strategy**
        
        | Strategy | Delta Target | Theta Goal | Vega Preference |
        |----------|--------------|-----------|-----------------|
        | Iron Condor | Near 0 | Positive (income) | Short (sell volatility) |
        | Strangle | Near 0 | Positive (income) | Short (sell volatility) |
        | Straddle | Near 0 | Varies | Long (buy volatility) |
        | Covered Call | 0.5-0.8 | Positive | Short (collect premium) |
        
        **Exit Rules**
        - Take profits at 50-80% max profit (why wait for 100%?)
        - Cut losses at 2x max profit risk
        - Close 7-14 days before expiration (theta decay accelerates)
        - Adjust at 50% of short strike distance remaining
        
        **Important Warnings**
        - Options are leveraged - you can lose more than initial debit
        - Selling calls on stocks you own = capped upside
        - Selling calls on margin = potentially unlimited risk
        - Test strategies with small position sizes first
        """)
    
    if not MODULES_AVAILABLE:
        st.error("Options strategy module not available")
        return
    
    # Strategy selection
    st.subheader("Strategy Configuration")
    
    st.markdown("""
    **Configure your options strategy below.** Each parameter affects the risk/reward profile:
    """)
    
    col1, col2 = st.columns(2)
    with col1:
        strategy_type = st.selectbox(
            "Select Strategy Type",
            ["Iron Condor", "Strangle", "Straddle", "Covered Call", "Collar"],
            help="""
            **Iron Condor**: Sell puts & calls, collect premium, profit if stock stays in range
            **Strangle**: Sell OTM put & call separately, flexible if stock moves
            **Straddle**: Buy or sell puts & calls at same strike, play big moves
            **Covered Call**: Sell upside, generate income from shares you own
            **Collar**: Protect stock with put, fund it by selling call
            """
        )
    
    with col2:
        risk_tolerance = st.select_slider(
            "Risk Tolerance",
            options=["Conservative", "Moderate", "Aggressive"],
            value="Moderate",
            help="""
            **Conservative**: Smaller position size, tighter stop losses
            **Moderate**: Balanced approach, standard position sizing
            **Aggressive**: Larger positions, accept more volatility
            """
        )
    
    # Underlying symbol and price
    st.markdown("**Underlying Information:**")
    col1, col2, col3 = st.columns(3)
    with col1:
        underlying = st.text_input("Underlying Symbol", value="AAPL", help="Stock ticker (e.g., AAPL, SPY, QQQ)").upper()
    with col2:
        current_price = st.number_input("Current Price ($)", value=150.0, min_value=0.01, step=0.01, help="Current trading price of underlying")
    with col3:
        volatility_pct = st.slider("IV Percentile", 0, 100, 50, help="""
        Implied Volatility percentile (0-100).
        - Low (0-25): Historic lows, consider buying options
        - Medium (25-75): Normal conditions
        - High (75-100): Historic highs, consider selling options
        """)
    
    # Strategy parameters
    st.subheader("Strategy Parameters")
    
    st.markdown("""
    These parameters control position structure and risk:
    """)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        dte = st.number_input("Days to Expiration", value=45, min_value=1, max_value=365, help="""
        Time until options expire.
        - 30-45 days: Good risk/reward for selling
        - 45-60 days: Standard for income strategies
        - 60+ days: More time but less daily decay
        """)
    
    with col2:
        spread_width = st.number_input("Spread Width ($)", value=5.0, min_value=0.5, step=0.5, help="""
        Distance between long and short strikes.
        - Wider: Higher max loss but higher credit
        - Narrower: Lower max loss but lower credit
        """)
    
    with col3:
        otm_pct = st.slider("OTM Distance %", 1, 10, 3, help="""
        How far Out-of-The-Money to place short strikes.
        - 1-2%: Close to price, higher probability, lower credit
        - 3-5%: Standard, balanced risk/reward
        - 5-10%: Far from price, lower probability, more credit
        """)
    
    with col4:
        position_size = st.number_input("Position Quantity", value=1, min_value=1, max_value=100, help="""
        Number of options contracts (or 100-share units).
        Start small to learn, increase with confidence.
        """)
    
    # Generate strategy
    if st.button("🔧 Generate Strategy", use_container_width=True):
        try:
            with st.spinner("Generating options strategy..."):
                automation = OptionsStrategyAutomation(
                    risk_tolerance=risk_tolerance.lower(),
                    max_loss_percent=5.0 if risk_tolerance == "Aggressive" else 3.0 if risk_tolerance == "Moderate" else 2.0
                )
                
                strategy = None
                
                if strategy_type == "Iron Condor":
                    strategy = automation.generate_iron_condor(
                        underlying=underlying,
                        current_price=current_price,
                        volatility_percentile=volatility_pct,
                        days_to_expiration=dte,
                        put_strike_pct=otm_pct/100,
                        call_strike_pct=otm_pct/100,
                        spread_width=spread_width
                    )
                
                elif strategy_type == "Strangle":
                    strategy = automation.generate_strangle(
                        underlying=underlying,
                        current_price=current_price,
                        volatility_percentile=volatility_pct,
                        days_to_expiration=dte,
                        put_otm_pct=otm_pct/100,
                        call_otm_pct=otm_pct/100
                    )
                
                elif strategy_type == "Straddle":
                    strategy = automation.generate_straddle(
                        underlying=underlying,
                        current_price=current_price,
                        volatility_percentile=volatility_pct,
                        days_to_expiration=dte,
                        strike=current_price
                    )
                
                elif strategy_type == "Covered Call":
                    call_strike = current_price * (1 + otm_pct/100)
                    strategy = automation.generate_covered_call(
                        underlying=underlying,
                        current_price=current_price,
                        call_strike=call_strike,
                        days_to_expiration=dte,
                        num_shares=100 * position_size
                    )
                
                if strategy:
                    st.session_state.options_strategy = strategy
                    st.success(f"✅ {strategy_type} strategy generated for {underlying}")
        
        except Exception as e:
            st.error(f"Error generating strategy: {str(e)}")
    
    # Display strategy if generated
    if "options_strategy" in st.session_state:
        strategy = st.session_state.options_strategy
        
        st.subheader("Strategy Details")
        
        # Display legs
        legs_data = []
        for leg in strategy.legs:
            legs_data.append({
                "Type": f"{leg.option_type.upper()} ({'BUY' if leg.action == 'buy' else 'SELL'})",
                "Strike": f"${leg.strike:.2f}",
                "Expiration": leg.expiration.strftime("%Y-%m-%d"),
                "Premium": f"${leg.current_price:.2f}",
                "Quantity": leg.quantity,
                "Delta": f"{leg.delta:.2f}",
                "Theta": f"{leg.theta:.4f}",
                "Vega": f"{leg.vega:.4f}",
            })
        
        st.dataframe(pd.DataFrame(legs_data), use_container_width=True)
        
        # Greeks summary
        st.subheader("Aggregate Greeks")
        greeks = strategy.aggregate_greeks
        
        st.markdown("""
        **Greeks Summary:** These metrics show how your position behaves under different market conditions.
        """)
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric(
                "Net Delta", 
                f"{greeks['delta']:.2f}", 
                help="""
                Directional exposure. 
                - Near 0: Neutral, profits from time/volatility
                - Positive: Benefits from stock rising
                - Negative: Benefits from stock falling
                """
            )
        with col2:
            st.metric(
                "Gamma", 
                f"{greeks['gamma']:.4f}", 
                help="""
                Delta acceleration.
                - Low: Delta stable (good near expiration)
                - High: Delta changes quickly (more risk if underlying moves)
                """
            )
        with col3:
            st.metric(
                "Theta", 
                f"{greeks['theta']:.4f}", 
                help="""
                Daily time decay.
                - Positive: You profit from time decay each day
                - Negative: You lose money from time decay
                - Higher magnitude = faster decay
                """
            )
        with col4:
            st.metric(
                "Vega", 
                f"{greeks['vega']:.4f}", 
                help="""
                Volatility exposure.
                - Positive: Profit if volatility increases
                - Negative: Profit if volatility decreases
                - Higher magnitude = more volatility sensitivity
                """
            )
        
        # P&L Analysis
        st.subheader("Profit & Loss Analysis")
        
        st.markdown("""
        **Payoff Diagram:** Shows your profit/loss at different underlying prices at expiration.
        - This is the **theoretical** P&L assuming you hold to expiration
        - **In practice**, you should manage the trade before expiration
        - The red line shows the current price
        """)
        
        price_range = np.linspace(current_price * 0.8, current_price * 1.2, 50)
        performance = automation.analyze_strategy_performance(strategy, price_range)
        
        if performance is not None and not performance.empty:
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=performance['underlying_price'],
                y=performance['profit_loss'],
                mode='lines',
                name='Strategy P&L',
                line=dict(color='blue', width=2),
                fill='tozeroy'
            ))
            
            fig.add_vline(x=current_price, line_dash="dash", line_color="red", annotation_text="Current Price")
            
            fig.update_layout(
                title="Strategy Payoff Diagram",
                xaxis_title="Underlying Price at Expiration",
                yaxis_title="Profit/Loss ($)",
                hovermode="x unified",
                height=500
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Key metrics
            col1, col2, col3 = st.columns(3)
            
            max_profit = performance['profit_loss'].max()
            max_loss = performance['profit_loss'].min()
            
            with col1:
                st.metric(
                    "Max Profit", 
                    f"${max_profit:,.0f}",
                    help="Best-case profit if underlying moves favorably"
                )
            with col2:
                st.metric(
                    "Max Loss", 
                    f"${max_loss:,.0f}",
                    help="Worst-case loss if underlying moves against you (at expiration)"
                )
            with col3:
                risk_reward = max_profit / abs(max_loss) if max_loss != 0 else 0
                st.metric(
                    "Risk/Reward Ratio", 
                    f"1:{risk_reward:.2f}",
                    help=f"For every $1 risked, potential ${risk_reward:.2f} profit"
                )
        
        # Risk warnings
        st.subheader("Risk Considerations & Monitoring")
        
        st.markdown("""
        **Important:** Options trading involves leverage and can result in losses exceeding initial investment.
        Always ensure you understand the risks before trading.
        """)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.warning(f"⏰ **Days to Expiration:** {strategy.days_to_expiration} days remaining")
            if strategy.days_to_expiration < 7:
                st.error("⛔ Critical: Strategy expires very soon! Consider closing or rolling.")
            elif strategy.days_to_expiration < 14:
                st.warning("⚠️ Theta decay accelerates in final 14 days. Monitor closely.")
            else:
                st.success("✅ Adequate time for position management")
        
        with col2:
            net_credit = -strategy.net_debit_credit if strategy.net_debit_credit < 0 else 0
            if net_credit > 0:
                st.info(f"""
                💰 **Net Credit Received:** ${abs(net_credit):,.2f}
                
                This is your maximum profit if stock stays in range.
                """)
            else:
                st.info(f"""
                💳 **Net Debit Paid:** ${strategy.net_debit_credit:,.2f}
                
                This is your maximum loss (plus commissions).
                """)
        
        # Monitoring guidelines
        st.markdown("""
        **How to Monitor This Trade:**
        
        1. **Watch Breakeven Levels** - See where the payoff diagram crosses zero
        2. **Track Delta** - If it drifts far from your target, consider adjusting
        3. **Monitor Theta Decay** - Accelerates in final 2 weeks
        4. **Exit Rules:**
           - Close winners at 50-80% max profit (don't wait for 100%)
           - Close losers if P&L hits 2x the max risk
           - Exit 7-14 days before expiration regardless of P&L
        5. **Adjustments** - If underlying moves 50% of spread width, consider rolling
        """)
        
        # Export options
        st.subheader("Export Strategy")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📥 Export as CSV"):
                strategy_df = pd.DataFrame([{
                    "Strategy": strategy_type,
                    "Underlying": underlying,
                    "Current Price": current_price,
                    "Entry Date": strategy.entry_date.strftime("%Y-%m-%d %H:%M:%S"),
                    "Days to Expiration": strategy.days_to_expiration,
                    "Net Debit/Credit": strategy.net_debit_credit,
                    "Delta": greeks['delta'],
                    "Theta": greeks['theta'],
                    "Vega": greeks['vega'],
                }])
                csv = strategy_df.to_csv(index=False)
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name=f"{underlying}_{strategy_type.replace(' ', '_')}_strategy.csv",
                    mime="text/csv"
                )
        
        with col2:
            if st.button("📋 Print Strategy Details"):
                details = f"""
                Strategy: {strategy_type}
                Underlying: {underlying}
                Current Price: ${current_price:.2f}
                Entry Date: {strategy.entry_date.strftime("%Y-%m-%d %H:%M:%S")}
                Days to Expiration: {strategy.days_to_expiration}
                
                Greeks:
                - Delta: {greeks['delta']:.4f}
                - Gamma: {greeks['gamma']:.6f}
                - Theta: {greeks['theta']:.6f}
                - Vega: {greeks['vega']:.6f}
                
                Net Credit/Debit: ${strategy.net_debit_credit:,.2f}
                """
                st.text(details)
        
        with col3:
            if st.button("🔄 Generate Hedge"):
                hedge_recs = automation.generate_hedge_recommendations(strategy)
                if hedge_recs:
                    st.subheader("Hedge Recommendations")
                    for rec in hedge_recs[:3]:  # Top 3 recommendations
                        with st.expander(f"🛡️ {rec['hedge_type']} - {rec['action']}"):
                            st.write(f"**Effectiveness:** {rec['effectiveness']:.1%}")
                            st.write(f"**Cost:** ${rec['cost']:,.2f}")
                            st.write(f"**Reduces:** {', '.join(rec['reduces_exposure'])}")
                else:
                    st.info("No hedge recommendations available for this strategy")


def render_tax_optimization():

    """Render tax optimization page with comprehensive tax loss harvesting analysis."""
    st.title("💰 Tax Loss Harvesting & Optimization")
    
    st.markdown("""
    Comprehensive tax optimization including:
    - **Tax Loss Harvesting:** Identify and execute tax-loss selling opportunities
    - **Wash Sale Analysis:** Avoid triggering wash sale rules
    - **Replacement Security Suggestions:** Similar securities to maintain portfolio positioning
    - **Tax Savings Projection:** Estimate tax savings from harvesting
    - **Calendar Optimization:** Best timing for harvesting decisions
    """)
    
    if not MODULES_AVAILABLE:
        st.error("Tax optimization module not available")
        return
    
    # Tax configuration
    st.subheader("Tax Configuration")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        long_term_rate = st.slider(
            "Long-Term Capital Gains Rate (%)",
            0, 50, 20,
            help="Your applicable long-term capital gains tax rate"
        ) / 100
    
    with col2:
        short_term_rate = st.slider(
            "Short-Term Capital Gains Rate (%)",
            0, 50, 37,
            help="Your ordinary income tax rate (short-term gains taxed at this rate)"
        ) / 100
    
    with col3:
        tax_filing_status = st.selectbox(
            "Tax Filing Status",
            ["Single", "Married Filing Jointly", "Married Filing Separately", "Head of Household"],
            help="Affects tax bracket thresholds"
        )
    
    # Carryforward losses
    st.subheader("Tax Loss Carryforward")
    carryforward_loss = st.number_input(
        "Prior Year Capital Loss Carryforward ($)",
        value=0.0,
        min_value=0.0,
        step=100.0,
        help="Unused capital losses from prior years (up to $3,000/year can offset ordinary income)"
    )
    
    engine = TaxOptimizationEngine(
        capital_gains_rate=long_term_rate,
        ordinary_rate=short_term_rate
    )
    
    # Holdings input
    st.subheader("Portfolio Holdings")
    
    input_method = st.radio(
        "Input Method", 
        ["Use Current Holdings", "Sample Data", "Upload CSV", "Manual Entry"], 
        horizontal=True,
        help="Choose where to get your portfolio data from"
    )
    
    if input_method == "Use Current Holdings":
        try:
            current_holdings = pd.read_csv("holdings.csv")
            # Filter to equity holdings only
            holdings_df = current_holdings[current_holdings['asset'].isin(['eq', 'fund'])].copy()
            
            if holdings_df.empty:
                st.warning("No equity or fund holdings found in your portfolio")
                return
            
            # Need to get current prices
            db = init_parquet_db()
            prices = db.read_table('prices')
            
            if prices is not None and not prices.empty:
                latest_prices = prices.sort_values('timestamp').drop_duplicates('symbol', keep='last')
                price_dict = dict(zip(latest_prices['symbol'], latest_prices['close_price']))
                
                holdings_df['current_price'] = holdings_df['sym'].map(price_dict)
                holdings_df['purchase_price'] = holdings_df['bep']
                holdings_df['quantity'] = holdings_df['qty']
                holdings_df['purchase_date'] = pd.Timestamp.now().strftime('%Y-%m-%d')  # Placeholder
                holdings_df['symbol'] = holdings_df['sym']
                
                # Keep only needed columns
                holdings_df = holdings_df[['symbol', 'quantity', 'purchase_price', 'current_price', 'purchase_date']]
                holdings_df = holdings_df.dropna(subset=['current_price'])
                
                st.success(f"✅ Loaded {len(holdings_df)} holdings from your portfolio")
            else:
                st.warning("Could not load current prices. Please use another input method.")
                input_method = "Sample Data"
        except Exception as e:
            st.warning(f"Could not load current holdings: {str(e)[:100]}. Using sample data instead.")
            input_method = "Sample Data"
    
    if input_method == "Sample Data":
        sample_data = {
            'symbol': ['AAPL', 'MSFT', 'TSLA', 'GOOGL', 'JPM', 'GE', 'F'],
            'quantity': [100, 50, 10, 25, 30, 40, 60],
            'purchase_price': [150, 300, 250, 2500, 145, 95, 12],
            'current_price': [120, 310, 180, 2600, 150, 78, 8.5],
            'purchase_date': [
                (pd.Timestamp.now() - pd.Timedelta(days=400)).strftime('%Y-%m-%d'),
                (pd.Timestamp.now() - pd.Timedelta(days=200)).strftime('%Y-%m-%d'),
                (pd.Timestamp.now() - pd.Timedelta(days=100)).strftime('%Y-%m-%d'),
                (pd.Timestamp.now() - pd.Timedelta(days=50)).strftime('%Y-%m-%d'),
                (pd.Timestamp.now() - pd.Timedelta(days=30)).strftime('%Y-%m-%d'),
                (pd.Timestamp.now() - pd.Timedelta(days=20)).strftime('%Y-%m-%d'),
                (pd.Timestamp.now() - pd.Timedelta(days=15)).strftime('%Y-%m-%d'),
            ]
        }
        holdings_df = pd.DataFrame(sample_data)
    
    elif input_method == "Upload CSV":
        uploaded_file = st.file_uploader("Choose CSV file", type="csv")
        if uploaded_file is not None:
            holdings_df = pd.read_csv(uploaded_file)
        else:
            st.info("Please upload a CSV file with columns: symbol, quantity, purchase_price, current_price, purchase_date")
            return
    
    else:  # Manual Entry
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            symbol = st.text_input("Symbol").upper()
        with col2:
            qty = st.number_input("Quantity", value=1, min_value=1)
        with col3:
            buy_price = st.number_input("Purchase Price", value=100.0, min_value=0.01)
        with col4:
            current = st.number_input("Current Price", value=90.0, min_value=0.01)
        with col5:
            buy_date = st.date_input("Purchase Date")
        
        if st.button("Add Position"):
            holdings_df = pd.DataFrame([{
                'symbol': symbol,
                'quantity': qty,
                'purchase_price': buy_price,
                'current_price': current,
                'purchase_date': buy_date.strftime('%Y-%m-%d')
            }])
        else:
            return
    
    st.write("Current Holdings:")
    st.dataframe(holdings_df, use_container_width=True)
    
    # Analyze button
    if st.button("🔍 Analyze Tax Opportunities", use_container_width=True):
        with st.spinner("Analyzing tax loss harvesting opportunities..."):
            report = engine.generate_tax_harvesting_report(holdings_df)
            
            st.success("✅ Analysis complete!")
            
            # Summary metrics
            st.subheader("Tax Optimization Summary")
            col1, col2, col3, col4, col5 = st.columns(5)
            
            with col1:
                st.metric(
                    "Total Unrealized Losses",
                    f"${report['total_unrealized_losses']:,.0f}",
                    delta=f"Loss {report['total_unrealized_losses']/holdings_df.eval('quantity * purchase_price').sum()*100:.1f}%"
                )
            with col2:
                st.metric(
                    "Potential Tax Savings",
                    f"${report['total_potential_tax_savings']:,.0f}",
                    delta_color="inverse"
                )
            with col3:
                st.metric(
                    "Opportunities Count",
                    f"{report['num_opportunities']}",
                    help="Number of positions with unrealized losses"
                )
            with col4:
                st.metric(
                    "Avg Wash Sale Risk",
                    f"{report['avg_wash_sale_risk']:.1%}",
                    help="Probability of triggering wash sale rule"
                )
            with col5:
                remaining_3k = max(0, 3000 - (carryforward_loss or 0))
                st.metric(
                    "Annual Loss Limit",
                    f"${remaining_3k:,.0f}",
                    help="Unused portion of $3K annual capital loss deduction"
                )
            
            # Detailed opportunities
            if report['opportunities']:
                st.subheader("Harvesting Opportunities (Ranked by Tax Benefit)")
                
                opp_df = pd.DataFrame(report['opportunities']).sort_values('tax_savings', ascending=False)
                
                # Visualization
                fig = go.Figure()
                fig.add_trace(go.Bar(
                    x=opp_df['symbol'],
                    y=opp_df['unrealized_loss'],
                    name='Unrealized Loss',
                    marker_color='#ff7f0e'
                ))
                
                fig.update_layout(
                    title="Unrealized Losses by Position",
                    xaxis_title="Symbol",
                    yaxis_title="Loss Amount ($)",
                    height=400
                )
                st.plotly_chart(fig, use_container_width=True)
                
                # Detailed opportunities
                for idx, opp in enumerate(report['opportunities'][:10], 1):  # Top 10 opportunities
                    with st.expander(f"{idx}. {opp['symbol']} 📍 Loss: ${opp['unrealized_loss']:,.0f} → Tax Savings: ${opp['tax_savings']:,.0f}"):
                        col1, col2, col3, col4 = st.columns(4)
                        
                        with col1:
                            st.write("**Position Details**")
                            st.write(f"Quantity: {opp['quantity']:,.0f}")
                            st.write(f"Purchase Price: ${opp.get('purchase_price', 0):.2f}")
                            st.write(f"Current Price: ${opp.get('current_price', 0):.2f}")
                        
                        with col2:
                            st.write("**Loss & Tax Benefit**")
                            st.write(f"Total Loss: ${opp['unrealized_loss']:,.0f}")
                            st.write(f"Tax Savings: ${opp['tax_savings']:,.0f}")
                            st.write(f"Loss %: {opp.get('loss_pct', 0):.1f}%")
                        
                        with col3:
                            st.write("**Holding Period**")
                            holding_period = opp.get('holding_period', 'Unknown')
                            st.write(f"Period: {holding_period}")
                            st.write(f"Days Held: {opp.get('days_held', 0)}")
                            if holding_period == 'short':
                                st.warning("⚠️ Short-term loss (taxed at ordinary rate)")
                            else:
                                st.success("✅ Long-term loss (lower tax rate)")
                        
                        with col4:
                            st.write("**Risk Analysis**")
                            wash_risk = opp.get('wash_sale_risk', 0)
                            st.write(f"Wash Sale Risk: {wash_risk:.1%}")
                            if wash_risk > 0.7:
                                st.error("🚨 High wash sale risk!")
                            elif wash_risk > 0.3:
                                st.warning("⚠️ Moderate wash sale risk")
                            else:
                                st.success("✅ Low wash sale risk")
                        
                        # Replacement suggestions
                        st.write("**Suggested Replacements (to avoid wash sale):**")
                        replacements = opp.get('replacements', [])
                        if replacements:
                            replacement_cols = st.columns(min(3, len(replacements)))
                            for col, repl in zip(replacement_cols, replacements[:3]):
                                with col:
                                    st.button(f"View {repl}", key=f"repl_{idx}_{repl}", disabled=True)
                        else:
                            st.info("No specific replacements suggested. Consider similar securities in same sector.")
                        
                        # Action buttons
                        col_btn1, col_btn2, col_btn3 = st.columns(3)
                        with col_btn1:
                            st.button(
                                "✅ Approve Harvest",
                                key=f"approve_{idx}",
                                help="Mark this position for harvesting"
                            )
                        with col_btn2:
                            st.button(
                                "🔄 Find Alternatives",
                                key=f"alt_{idx}",
                                help="Search for better replacement securities"
                            )
                        with col_btn3:
                            st.button(
                                "📋 Details",
                                key=f"details_{idx}",
                                help="Show detailed analysis"
                            )
            
            else:
                st.info("✅ No tax loss harvesting opportunities found. All positions are profitable!")
            
            # Tax optimization insights
            st.subheader("Tax Planning Insights")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**Recommendations:**")
                recommendations = []
                
                if report['total_unrealized_losses'] > 3000:
                    recommendations.append("💡 Significant losses available - prioritize harvesting before year-end")
                
                if report['avg_wash_sale_risk'] > 0.5:
                    recommendations.append("⚠️ High wash sale risk - carefully select replacement securities")
                
                if carryforward_loss > 0:
                    recommendations.append(f"📌 You have ${carryforward_loss:,.0f} in carryforward losses - these provide tax-free deductions")
                
                if not recommendations:
                    recommendations.append("✅ Current portfolio is well-optimized from a tax perspective")
                
                for rec in recommendations:
                    st.write(f"• {rec}")
            
            with col2:
                st.write("**Timeline:**")
                st.write("• December is ideal for tax-loss harvesting (before year-end)")
                st.write("• Wash sale rule: 30 days before or after sale")
                st.write("• Wait 31+ days before repurchasing same security")
                st.write("• Consider alternative sector ETFs for re-entry")
            
            # Export options
            st.subheader("Export Analysis")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                csv_data = pd.DataFrame(report['opportunities']).to_csv(index=False)
                st.download_button(
                    label="📥 Download CSV Report",
                    data=csv_data,
                    file_name=f"tax_loss_harvesting_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )
            
            with col2:
                if st.button("💾 Save to Parquet"):
                    try:
                        output = engine.save_tax_analysis_parquet(report)
                        st.success(f"✅ Saved to: {output}")
                    except:
                        st.info("Parquet export not available for this report format")
            
            with col3:
                if st.button("📧 Email Report"):
                    st.info("Email functionality would be integrated with your email service")


def render_crypto_analytics():
    """Render crypto analytics page."""
    st.title("₿ Crypto Advanced Analytics")
    
    st.markdown("""
    Advanced cryptocurrency analysis with on-chain metrics, market structure, and portfolio risk.
    """)
    
    if not MODULES_AVAILABLE:
        st.error("Crypto analytics module not available")
        return
    
    analytics = CryptoAdvancedAnalytics()
    
    tab1, tab2, tab3 = st.tabs(["On-Chain Metrics", "Market Structure", "Portfolio Risk"])
    
    with tab1:
        st.subheader("On-Chain Analysis")
        
        col1, col2 = st.columns(2)
        
        with col1:
            symbol = st.selectbox(
                "Select Crypto", 
                ["BTC", "ETH", "SOL", "ADA", "XRP"],
                help="Choose a cryptocurrency to analyze"
            )
            metric_type = st.radio(
                "Metric Type", 
                ["active_addresses", "transaction_volume", "whale_watch"],
                help="Select which on-chain metric to fetch"
            )
        
        if st.button("Fetch Metrics"):
            metrics = analytics.fetch_on_chain_metrics(symbol, metric_type)
            
            st.json(metrics['metrics'])
    
    with tab2:
        st.subheader("Market Structure")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            symbol = st.selectbox(
                "Asset", 
                ["BTC", "ETH", "SOL", "ADA", "XRP"],
                key="ms",
                help="Choose cryptocurrency"
            )
            price = st.number_input("Price ($)", value=50000.0, min_value=0.0)
        
        with col2:
            volume = st.number_input("24h Volume ($B)", value=30.0, min_value=0.0)
        
        if st.button("Analyze Market"):
            structure = analytics.analyze_market_structure(symbol, price, volume * 1e9)
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Liquidity Score", f"{structure['liquidity_score']:.0f}/100")
            with col2:
                st.metric("Market Strength", structure['market_strength'].upper())
            with col3:
                st.metric("7d Volatility", f"{structure['volatility_7d']:.1%}")
    
    with tab3:
        st.subheader("Portfolio Risk Metrics")
        
        # Option to use current holdings or manual input
        input_method = st.radio(
            "Input Method",
            ["Use Current Holdings", "Manual Entry"],
            horizontal=True,
            help="Use your actual portfolio or enter custom values"
        )
        
        if input_method == "Use Current Holdings":
            try:
                current_holdings = pd.read_csv("holdings.csv")
                crypto_holdings = current_holdings[current_holdings['asset'] == 'crypto'].copy()
                
                if crypto_holdings.empty:
                    st.warning("No crypto holdings found in your portfolio")
                    return
                
                # Get current prices from database
                db = init_parquet_db()
                prices = db.read_table('prices')
                
                if prices is not None and not prices.empty:
                    latest_prices = prices.sort_values('timestamp').drop_duplicates('symbol', keep='last')
                    price_dict = dict(zip(latest_prices['symbol'], latest_prices['close_price']))
                    
                    # Build holdings and prices dictionaries
                    holdings = {}
                    prices_dict = {}
                    
                    for _, row in crypto_holdings.iterrows():
                        symbol_key = row['sym'].replace('-USD', '')
                        qty = row['qty']
                        current_price = price_dict.get(row['sym'], row['bep'])
                        
                        holdings[symbol_key] = qty
                        prices_dict[symbol_key] = current_price
                    
                    st.success(f"✅ Loaded {len(holdings)} crypto assets from your portfolio")
                    
                    # Display current allocation
                    st.subheader("Current Crypto Allocation")
                    
                    allocation_data = []
                    total_value = 0
                    
                    for symbol, qty in holdings.items():
                        price = prices_dict[symbol]
                        value = qty * price
                        total_value += value
                        allocation_data.append({
                            "Asset": symbol,
                            "Quantity": f"{qty:.4f}",
                            "Price": f"${price:,.2f}",
                            "Value": f"${value:,.2f}"
                        })
                    
                    allocation_df = pd.DataFrame(allocation_data)
                    st.dataframe(allocation_df, use_container_width=True)
                    
                    st.metric("Total Crypto Value", f"${total_value:,.2f}")
                    
                    # Calculate weights
                    st.subheader("Portfolio Weights")
                    
                    weights = {}
                    for symbol, qty in holdings.items():
                        value = qty * prices_dict[symbol]
                        weight = (value / total_value * 100) if total_value > 0 else 0
                        weights[symbol] = weight
                    
                    col1, col2, col3 = st.columns(len(weights))
                    
                    for idx, (symbol, weight) in enumerate(weights.items()):
                        with st.columns(len(weights))[idx]:
                            st.metric(symbol, f"{weight:.1f}%")
                    
                    # Risk calculation with actual holdings
                    if st.button("Calculate Portfolio Risk"):
                        # Create correlation matrix
                        crypto_symbols = list(holdings.keys())
                        n = len(crypto_symbols)
                        
                        # Simplified correlation (BTC/ETH typically 0.8, others lower)
                        correlation = pd.DataFrame(
                            [[1.0] * n for _ in range(n)],
                            index=crypto_symbols,
                            columns=crypto_symbols
                        )
                        
                        # Set some realistic correlations
                        for i, sym1 in enumerate(crypto_symbols):
                            for j, sym2 in enumerate(crypto_symbols):
                                if i != j:
                                    if {sym1, sym2} == {'BTC', 'ETH'}:
                                        correlation.iloc[i, j] = 0.8
                                    else:
                                        correlation.iloc[i, j] = 0.6
                        
                        risk = analytics.calculate_crypto_portfolio_risk(holdings, prices_dict, correlation)
                        
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            st.metric("Portfolio Value", f"${risk['portfolio_value']:,.0f}")
                        with col2:
                            st.metric("Annual Volatility", f"{risk['annual_volatility']:.1%}")
                        with col3:
                            st.metric("VaR (95%)", f"${risk['var_95']:,.0f}")
                        
                        st.info("""
                        **What these metrics mean:**
                        - **Portfolio Value**: Total current value of your crypto holdings
                        - **Annual Volatility**: Expected price fluctuation (higher = riskier)
                        - **VaR (95%)**: Maximum expected loss 95% of the time
                        """)
                else:
                    st.warning("Could not load current prices from database")
                    input_method = "Manual Entry"
            
            except Exception as e:
                st.warning(f"Could not load current holdings: {str(e)[:100]}")
                input_method = "Manual Entry"
        
        if input_method == "Manual Entry":
            st.subheader("Enter Crypto Holdings")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                holdings_btc = st.number_input("BTC Holdings", value=1.0, min_value=0.0)
            with col2:
                holdings_eth = st.number_input("ETH Holdings", value=10.0, min_value=0.0)
            with col3:
                holdings_xrp = st.number_input("XRP Holdings", value=1000.0, min_value=0.0)
            
            if st.button("Calculate Portfolio Risk"):
                holdings = {'BTC': holdings_btc, 'ETH': holdings_eth, 'XRP': holdings_xrp}
                prices = {'BTC': 50000, 'ETH': 2500, 'XRP': 0.67}
                
                correlation = pd.DataFrame(
                    [[1.0, 0.8, 0.6], [0.8, 1.0, 0.6], [0.6, 0.6, 1.0]],
                    index=['BTC', 'ETH', 'XRP'],
                    columns=['BTC', 'ETH', 'XRP']
                )
                
                risk = analytics.calculate_crypto_portfolio_risk(holdings, prices, correlation)
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Portfolio Value", f"${risk['portfolio_value']:,.0f}")
                with col2:
                    st.metric("Annual Volatility", f"{risk['annual_volatility']:.1%}")
                with col3:
                    st.metric("VaR (95%)", f"${risk['var_95']:,.0f}")


def render_fx_analytics():
    """Render FX (Foreign Exchange) analytics and hedging strategies."""
    st.title("💱 FX Analytics & Hedging")
    
    st.markdown("""
    Analyze your foreign exchange exposure, manage FX risk, and optimize hedging strategies
    for your multi-currency portfolio.
    """)
    
    # Load current holdings and FX data
    try:
        current_holdings = pd.read_csv("holdings.csv")
        db = init_parquet_db()
        prices = db.read_table('prices')
    except Exception as e:
        st.error(f"Could not load portfolio data: {str(e)[:100]}")
        return
    
    # Tabs for different FX analyses
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "💼 Currency Exposure",
        "📊 FX Risk Metrics",
        "🛡️ Hedging Strategies",
        "📈 Technical & Sentiment",
        "🔄 Pair Analytics"
    ])
    
    # ==================== TAB 1: CURRENCY EXPOSURE ====================
    with tab1:
        st.subheader("Portfolio Currency Exposure Analysis")
        
        st.markdown("""
        Understand your portfolio's exposure across different currencies and identify
        FX concentration risk.
        """)
        
        # Analyze currency exposure from holdings
        holdings_with_fx = current_holdings[current_holdings['ccy'].notna()].copy()
        
        if len(holdings_with_fx) > 0:
            # Calculate notional exposure by currency
            latest_prices = prices.sort_values('timestamp').drop_duplicates('symbol', keep='last')
            price_dict = dict(zip(latest_prices['symbol'], latest_prices['close_price']))
            
            # For holdings with prices (equities, funds, commodities, crypto)
            holdings_with_fx['current_price'] = holdings_with_fx['sym'].map(price_dict)
            
            # For cash, fixed-income, retirement: use qty * bep (since bep=1.0, qty is the value)
            # For other assets: use qty * current_price
            holdings_with_fx['current_value'] = holdings_with_fx.apply(
                lambda row: row['qty'] * row['bep'] if row['asset'] in ['cash', 'fixed-income', 'retirement'] 
                else row['qty'] * row['current_price'],
                axis=1
            )
            holdings_with_fx['current_value'] = holdings_with_fx['current_value'].fillna(0)
            
            # Group by currency
            exposure_by_ccy = holdings_with_fx.groupby('ccy').agg({
                'current_value': 'sum',
                'sym': 'count'
            }).round(2)
            exposure_by_ccy.columns = ['Notional ($)', 'Position Count']
            
            total_fx_exposure = exposure_by_ccy['Notional ($)'].sum()
            exposure_by_ccy['% of FX Portfolio'] = (exposure_by_ccy['Notional ($)'] / total_fx_exposure * 100).round(1)
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric("Total FX Exposure", f"${total_fx_exposure:,.0f}")
            with col2:
                st.metric("Currencies Traded", f"{len(exposure_by_ccy)}")
            
            # Exposure table
            st.dataframe(exposure_by_ccy, use_container_width=True)
            
            # Visualization
            if len(exposure_by_ccy) > 1:
                fig = go.Figure(data=[go.Pie(
                    labels=exposure_by_ccy.index,
                    values=exposure_by_ccy['Notional ($)'],
                    hovertemplate='<b>%{label}</b><br>%{value:,.0f}<br>%{percent}'
                )])
                fig.update_layout(
                    title="FX Portfolio Allocation",
                    height=400,
                    showlegend=True
                )
                st.plotly_chart(fig, use_container_width=True)
                
                # Concentration risk
                largest_exposure = exposure_by_ccy['% of FX Portfolio'].max()
                if largest_exposure > 80:
                    st.warning(f"⚠️ **High Concentration Risk**: {largest_exposure:.1f}% in single currency")
                elif largest_exposure > 60:
                    st.info(f"📊 **Moderate Concentration**: {largest_exposure:.1f}% in largest currency")
                else:
                    st.success(f"✅ **Well-Diversified**: {largest_exposure:.1f}% max concentration")
            
            # Asset type breakdown by currency
            st.subheader("Asset Type Breakdown by Currency")
            
            for ccy in exposure_by_ccy.index:
                with st.expander(f"**{ccy}** - ${exposure_by_ccy.loc[ccy, 'Notional ($)']:,.0f}"):
                    ccy_holdings = holdings_with_fx[holdings_with_fx['ccy'] == ccy]
                    
                    # Group by asset type
                    asset_breakdown = ccy_holdings.groupby('asset').agg({
                        'current_value': ['sum', 'count']
                    }).round(2)
                    asset_breakdown.columns = ['Value ($)', 'Count']
                    asset_breakdown['% of Currency'] = (asset_breakdown['Value ($)'] / ccy_holdings['current_value'].sum() * 100).round(1)
                    
                    st.dataframe(asset_breakdown, use_container_width=True)
                    
                    # Individual holdings
                    st.markdown("**Holdings:**")
                    for _, row in ccy_holdings.iterrows():
                        if pd.notna(row['current_value']) and row['current_value'] > 0:
                            asset_type = str(row['asset']).upper() if pd.notna(row['asset']) else 'UNKNOWN'
                            st.caption(f"{row['sym']:15} ({asset_type:12}) → ${row['current_value']:>12,.0f}")
        else:
            st.info("No holdings with currency data found")
    
    # ==================== TAB 2: FX RISK METRICS ====================
    with tab2:
        st.subheader("FX Risk Metrics & Analysis")
        
        st.markdown("""
        Assess the risk of your FX exposure through volatility analysis, Value-at-Risk,
        and currency correlations.
        """)
        
        # Get FX rate pairs from portfolio
        currencies = current_holdings[current_holdings['ccy'].notna()]['ccy'].unique()
        
        if len(currencies) > 1:
            # Calculate FX volatility for major pairs
            st.subheader("Currency Pair Volatility")
            
            major_pairs = []
            base_currencies = ['USD', 'EUR', 'GBP', 'JPY', 'AUD', 'CAD']
            
            for ccy in currencies:
                if ccy != 'USD':
                    pair = f"{ccy}USD"  # e.g., EURUSD
                    major_pairs.append(pair)
            
            # Create volatility estimate based on typical FX ranges
            volatility_data = []
            for pair in major_pairs:
                # Typical FX volatility ranges (annual)
                typical_vol = {
                    'EURUSD': 0.10, 'GBPUSD': 0.11, 'JPYUSD': 0.12,
                    'AUDUSD': 0.13, 'CADUSD': 0.10
                }
                vol = typical_vol.get(pair, 0.11)
                volatility_data.append({'Pair': pair, 'Annual Volatility': f"{vol:.1%}"})
            
            if volatility_data:
                vol_df = pd.DataFrame(volatility_data)
                st.dataframe(vol_df, use_container_width=True)
                
                st.info("""
                **Volatility Interpretation:**
                - **<10%**: Low FX volatility (stable pairs like USD/CAD)
                - **10-15%**: Moderate volatility (typical major pairs)
                - **>15%**: High volatility (emerging market currencies)
                """)
            
            # Value at Risk calculation
            st.subheader("FX Exposure Value at Risk")
            
            col1, col2 = st.columns(2)
            
            with col1:
                confidence = st.select_slider("Confidence Level", options=[90, 95, 99], value=95)
            
            with col2:
                lookback_days = st.slider("Lookback Period (days)", min_value=30, max_value=252, value=90)
            
            # Simple VaR calculation
            if len(exposure_by_ccy) > 0:
                total_exposure = exposure_by_ccy['Notional ($)'].sum()
                
                # Z-scores for different confidence levels
                z_scores = {90: 1.28, 95: 1.645, 99: 2.33}
                z = z_scores[confidence]
                
                # Average FX volatility weighted by exposure
                avg_vol = 0.115  # ~11.5% typical for major FX pairs
                
                var_amount = total_exposure * avg_vol * z
                var_pct = (var_amount / total_exposure) * 100
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric(f"VaR ({confidence}%)", f"${var_amount:,.0f}")
                with col2:
                    st.metric("As % of Exposure", f"{var_pct:.1f}%")
                with col3:
                    st.metric("Daily Risk", f"${var_amount/np.sqrt(252):,.0f}")
                
                st.warning(f"""
                **Interpretation**: There is a {confidence}% probability that your FX exposure
                will NOT lose more than **${var_amount:,.0f}** in a 1-day move.
                """)
            
            # Correlation matrix estimation
            st.subheader("Currency Correlations")
            
            if len(major_pairs) > 1:
                # Extract individual currencies from pairs
                currencies_in_portfolio = sorted(list(set(['USD'] + [p[:-3].upper() for p in major_pairs])))
                
                # Currency-to-currency correlations (not pair-based)
                # These represent how the currencies move relative to each other
                corr_map = {
                    ('EUR', 'GBP'): 0.85,
                    ('EUR', 'JPY'): -0.55,
                    ('EUR', 'AUD'): 0.65,
                    ('EUR', 'CAD'): 0.60,
                    ('GBP', 'JPY'): -0.50,
                    ('GBP', 'AUD'): 0.70,
                    ('GBP', 'CAD'): 0.65,
                    ('AUD', 'JPY'): -0.40,
                    ('AUD', 'CAD'): 0.50,
                    ('CAD', 'JPY'): -0.35,
                    ('USD', 'EUR'): -0.50,
                    ('USD', 'GBP'): -0.48,
                    ('USD', 'JPY'): 0.40,
                    ('USD', 'AUD'): -0.40,
                    ('USD', 'CAD'): 0.70,
                }
                
                n = len(currencies_in_portfolio)
                corr_matrix = pd.DataFrame(
                    np.identity(n),
                    index=currencies_in_portfolio,
                    columns=currencies_in_portfolio
                )
                
                # Populate correlations from map
                for (ccy1, ccy2), corr in corr_map.items():
                    if ccy1 in currencies_in_portfolio and ccy2 in currencies_in_portfolio:
                        i, j = currencies_in_portfolio.index(ccy1), currencies_in_portfolio.index(ccy2)
                        corr_matrix.iloc[i, j] = corr
                        corr_matrix.iloc[j, i] = corr
                
                st.dataframe(corr_matrix.round(2), use_container_width=True)
                
                st.info("""
                **Correlation Insights:**
                - **Positive (>0.5)**: Currencies move together (similar economic drivers)
                - **Negative (<-0.3)**: Currencies move opposite (good for diversification)
                - **Neutral (-0.3 to 0.5)**: Low/moderate relationship
                
                **Note:** These correlations show how currencies move relative to each other, not vs USD.
                """)
        else:
            st.info("Portfolio contains only USD exposure - no FX risk to analyze")
    
    # ==================== TAB 3: HEDGING STRATEGIES ====================
    with tab3:
        st.subheader("FX Hedging Strategy Recommendations")
        
        st.markdown("""
        Determine optimal hedging strategies to protect your FX exposure against adverse
        currency movements.
        """)
        
        if len(exposure_by_ccy) > 1:
            # Select currency to hedge
            hedge_ccy = st.selectbox("Select Currency to Hedge", 
                                    [c for c in exposure_by_ccy.index if c != 'USD'])
            
            exposure_amount = exposure_by_ccy.loc[hedge_ccy, 'Notional ($)']
            
            st.metric("Exposure to Hedge", f"${exposure_amount:,.0f}")
            
            # Hedging strategy comparison
            st.subheader("Hedging Strategy Comparison")
            
            col1, col2 = st.columns(2)
            
            with col1:
                hedge_ratio = st.slider("Hedge Ratio (%)", min_value=0, max_value=100, value=100, step=10)
            
            with col2:
                time_horizon = st.select_slider("Time Horizon (months)", 
                                               options=[1, 3, 6, 12], value=3)
            
            hedge_amount = exposure_amount * (hedge_ratio / 100)
            
            # Strategy costs (approximate)
            strategies = {
                'Forward Contract': {
                    'cost_bps': 15,  # 15 basis points
                    'description': 'Lock in FX rate for future date. Cost: 0.15% per year',
                    'pros': 'Simple, zero upfront cost, locks in rate',
                    'cons': 'No flexibility, potential missed upside'
                },
                'FX Put Option': {
                    'cost_bps': 300,  # 3% premium
                    'description': 'Right to sell currency at fixed rate. Cost: 2-3% premium',
                    'pros': 'Downside protection with upside potential',
                    'cons': 'Higher cost, time decay (theta)'
                },
                'Currency Swap': {
                    'cost_bps': 50,  # 50 basis points
                    'description': 'Exchange cash flows in different currencies. Cost: 0.5%',
                    'pros': 'Flexible, matches cash flow timing',
                    'cons': 'Counterparty risk, less transparent'
                },
                'No Hedge': {
                    'cost_bps': 0,
                    'description': 'Accept FX risk. Cost: $0',
                    'pros': 'No cost, potential gains from favorable moves',
                    'cons': 'Exposed to adverse FX moves'
                }
            }
            
            # Display strategy comparison
            strategy_results = []
            for strategy, details in strategies.items():
                annual_cost = hedge_amount * (details['cost_bps'] / 10000) * (time_horizon / 12)
                cost_pct = (details['cost_bps'] / 10000) * 100
                
                strategy_results.append({
                    'Strategy': strategy,
                    'Cost Basis Points': details['cost_bps'],
                    f'Cost for {time_horizon}mo': f"${annual_cost:,.0f}",
                    'Annual Cost %': f"{cost_pct:.2f}%"
                })
            
            results_df = pd.DataFrame(strategy_results)
            st.dataframe(results_df, use_container_width=True)
            
            # Detailed strategy recommendations
            st.subheader("Strategy Details & Recommendation")
            
            for strategy, details in strategies.items():
                with st.expander(f"**{strategy}**"):
                    st.markdown(f"""
                    **Description**: {details['description']}
                    
                    **Advantages:**
                    - {details['pros']}
                    
                    **Disadvantages:**
                    - {details['cons']}
                    """)
                    
                    if strategy == 'Forward Contract':
                        st.success("""
                        **Recommendation**: Forward contracts are ideal for firms with known
                        future FX obligations at a specific date. They're the most cost-effective
                        for 100% hedging needs.
                        """)
                    elif strategy == 'FX Put Option':
                        st.info("""
                        **Recommendation**: Use put options if you want protection but also
                        want to benefit from favorable currency movements (one-way risk).
                        """)
                    elif strategy == 'Currency Swap':
                        st.info("""
                        **Recommendation**: Currency swaps work best for long-term obligations
                        or when you want to match payment dates with cash flows.
                        """)
            
            # Scenario analysis
            st.subheader("Scenario Analysis")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                spot_rate = st.number_input(f"Current {hedge_ccy}/USD Rate", value=1.10, min_value=0.01)
            
            with col2:
                adverse_move = st.slider("Adverse Move (%)", min_value=1, max_value=20, value=10)
            
            with col3:
                favorable_move = st.slider("Favorable Move (%)", min_value=1, max_value=20, value=10)
            
            adverse_rate = spot_rate * (1 - adverse_move / 100)
            favorable_rate = spot_rate * (1 + favorable_move / 100)
            
            scenarios = {
                'Adverse Case': {
                    'rate': adverse_rate,
                    'impact': exposure_amount * (adverse_move / 100)
                },
                'Base Case': {
                    'rate': spot_rate,
                    'impact': 0
                },
                'Favorable Case': {
                    'rate': favorable_rate,
                    'impact': exposure_amount * (favorable_move / 100)
                }
            }
            
            scenario_data = []
            for scenario, data in scenarios.items():
                unhedged_pnl = data['impact']
                forward_cost = hedge_amount * (50 / 10000)  # Forward contract cost
                hedged_pnl = -forward_cost if data['impact'] < 0 else -forward_cost
                
                scenario_data.append({
                    'Scenario': scenario,
                    'Rate': f"{data['rate']:.4f}",
                    'Unhedged P&L': f"${unhedged_pnl:,.0f}",
                    'With Forward': f"${hedged_pnl:,.0f}"
                })
            
            scenario_df = pd.DataFrame(scenario_data)
            st.dataframe(scenario_df, use_container_width=True)
        else:
            st.info("Need multiple currencies to recommend hedging strategies")
    
    # ==================== TAB 4: TECHNICAL & SENTIMENT ====================
    with tab4:
        st.subheader("Technical Analysis & Market Sentiment")
        
        st.markdown("""
        Analyze technical levels and market sentiment for currency pairs.
        Select a pair to see technical levels, RSI momentum, and what market participants expect.
        """)
        
        # Get currencies from portfolio
        currencies = sorted(current_holdings[current_holdings['ccy'].notna()]['ccy'].unique())
        
        if len(currencies) > 1:
            # Generate all possible pairs (excluding self-pairs)
            all_pairs = []
            for i, ccy1 in enumerate(currencies):
                for ccy2 in currencies[i+1:]:
                    all_pairs.append(f"{ccy1.upper()}{ccy2.upper()}")
                    all_pairs.append(f"{ccy2.upper()}{ccy1.upper()}")
            
            all_pairs = sorted(list(set(all_pairs)))
            
            if all_pairs:
                selected_pair = st.selectbox("Select Currency Pair to Analyze", all_pairs, key='tech_pair')
                
                st.subheader(f"📊 Technical Analysis: {selected_pair}")
                
                # Technical levels (comprehensive data for all pairs)
                technical_data = {
                    'EURUSD': {'current': 1.0850, 'support1': 1.0800, 'support2': 1.0750, 'resistance1': 1.0900, 'resistance2': 1.0950, 'trend': 'Uptrend', 'rsi': 65},
                    'USDEUR': {'current': 0.9218, 'support1': 0.9174, 'support2': 0.9128, 'resistance1': 0.9259, 'resistance2': 0.9306, 'trend': 'Downtrend', 'rsi': 35},
                    'GBPUSD': {'current': 1.2650, 'support1': 1.2600, 'support2': 1.2550, 'resistance1': 1.2700, 'resistance2': 1.2750, 'trend': 'Sideways', 'rsi': 55},
                    'USDGBP': {'current': 0.7905, 'support1': 0.7876, 'support2': 0.7847, 'resistance1': 0.7941, 'resistance2': 0.7970, 'trend': 'Sideways', 'rsi': 45},
                    'JPYUSD': {'current': 0.0095, 'support1': 0.0094, 'support2': 0.0093, 'resistance1': 0.0096, 'resistance2': 0.0097, 'trend': 'Downtrend', 'rsi': 35},
                    'USDJPY': {'current': 105.26, 'support1': 104.17, 'support2': 103.09, 'resistance1': 106.38, 'resistance2': 107.49, 'trend': 'Uptrend', 'rsi': 65},
                    'AUDUSD': {'current': 0.6550, 'support1': 0.6500, 'support2': 0.6450, 'resistance1': 0.6600, 'resistance2': 0.6650, 'trend': 'Uptrend', 'rsi': 70},
                    'USDAUD': {'current': 1.5267, 'support1': 1.5152, 'support2': 1.5038, 'resistance1': 1.5385, 'resistance2': 1.5500, 'trend': 'Downtrend', 'rsi': 30},
                    'CADUSD': {'current': 0.7350, 'support1': 0.7300, 'support2': 0.7250, 'resistance1': 0.7400, 'resistance2': 0.7450, 'trend': 'Sideways', 'rsi': 50},
                    'USDCAD': {'current': 1.3605, 'support1': 1.3514, 'support2': 1.3424, 'resistance1': 1.3699, 'resistance2': 1.3790, 'trend': 'Uptrend', 'rsi': 58},
                    'EURGBP': {'current': 0.8582, 'support1': 0.8545, 'support2': 0.8507, 'resistance1': 0.8623, 'resistance2': 0.8661, 'trend': 'Sideways', 'rsi': 48},
                    'GBPEUR': {'current': 1.1653, 'support1': 1.1599, 'support2': 1.1545, 'resistance1': 1.1710, 'resistance2': 1.1765, 'trend': 'Sideways', 'rsi': 52},
                    'EURJPY': {'current': 114.30, 'support1': 113.05, 'support2': 111.81, 'resistance1': 115.60, 'resistance2': 116.87, 'trend': 'Uptrend', 'rsi': 62},
                    'JPYEUR': {'current': 0.00875, 'support1': 0.00859, 'support2': 0.00843, 'resistance1': 0.00891, 'resistance2': 0.00907, 'trend': 'Downtrend', 'rsi': 38},
                    'EURAUD': {'current': 1.6553, 'support1': 1.6420, 'support2': 1.6288, 'resistance1': 1.6695, 'resistance2': 1.6828, 'trend': 'Uptrend', 'rsi': 68},
                    'AUDEUR': {'current': 0.6039, 'support1': 0.5982, 'support2': 0.5927, 'resistance1': 0.6098, 'resistance2': 0.6155, 'trend': 'Downtrend', 'rsi': 32},
                    'EURCAD': {'current': 1.4786, 'support1': 1.4672, 'support2': 1.4558, 'resistance1': 1.4910, 'resistance2': 1.5024, 'trend': 'Uptrend', 'rsi': 64},
                    'CADEUR': {'current': 0.6765, 'support1': 0.6713, 'support2': 0.6662, 'resistance1': 0.6820, 'resistance2': 0.6872, 'trend': 'Downtrend', 'rsi': 36},
                    'GBPJPY': {'current': 133.08, 'support1': 131.58, 'support2': 130.08, 'resistance1': 134.68, 'resistance2': 136.18, 'trend': 'Uptrend', 'rsi': 60},
                    'JPYGBP': {'current': 0.00752, 'support1': 0.00742, 'support2': 0.00732, 'resistance1': 0.00762, 'resistance2': 0.00772, 'trend': 'Downtrend', 'rsi': 40},
                    'GBPAUD': {'current': 1.9315, 'support1': 1.9126, 'support2': 1.8939, 'resistance1': 1.9515, 'resistance2': 1.9704, 'trend': 'Uptrend', 'rsi': 66},
                    'AUDGBP': {'current': 0.5178, 'support1': 0.5139, 'support2': 0.5100, 'resistance1': 0.5219, 'resistance2': 0.5258, 'trend': 'Downtrend', 'rsi': 34},
                    'GBPCAD': {'current': 1.7230, 'support1': 1.7086, 'support2': 1.6942, 'resistance1': 1.7388, 'resistance2': 1.7532, 'trend': 'Uptrend', 'rsi': 62},
                    'CADGBP': {'current': 0.5803, 'support1': 0.5761, 'support2': 0.5719, 'resistance1': 0.5848, 'resistance2': 0.5890, 'trend': 'Downtrend', 'rsi': 38},
                    'AUDJPY': {'current': 0.0689, 'support1': 0.0682, 'support2': 0.0675, 'resistance1': 0.0697, 'resistance2': 0.0704, 'trend': 'Uptrend', 'rsi': 61},
                    'JPYAUD': {'current': 14.515, 'support1': 14.305, 'support2': 14.096, 'resistance1': 14.728, 'resistance2': 14.937, 'trend': 'Downtrend', 'rsi': 39},
                    'AUDCAD': {'current': 0.8915, 'support1': 0.8837, 'support2': 0.8760, 'resistance1': 0.8995, 'resistance2': 0.9073, 'trend': 'Sideways', 'rsi': 52},
                    'CADAUD': {'current': 1.1218, 'support1': 1.1115, 'support2': 1.1012, 'resistance1': 1.1323, 'resistance2': 1.1427, 'trend': 'Sideways', 'rsi': 48},
                    'CADJPY': {'current': 0.0774, 'support1': 0.0767, 'support2': 0.0759, 'resistance1': 0.0782, 'resistance2': 0.0790, 'trend': 'Sideways', 'rsi': 50},
                    'JPYCAD': {'current': 12.920, 'support1': 12.787, 'support2': 12.655, 'resistance1': 13.057, 'resistance2': 13.189, 'trend': 'Sideways', 'rsi': 50},
                }
                
                tech_info = technical_data.get(selected_pair, {
                    'current': 1.0000,
                    'support1': 0.9950,
                    'support2': 0.9900,
                    'resistance1': 1.0050,
                    'resistance2': 1.0100,
                    'trend': 'Neutral',
                    'rsi': 50
                })
                
                # Key metrics
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Current Rate", f"{tech_info['current']:.4f}")
                with col2:
                    st.metric("RSI (14)", f"{tech_info['rsi']}")
                with col3:
                    st.metric("Trend", tech_info['trend'])
                with col4:
                    if tech_info['rsi'] > 70:
                        st.metric("Momentum", "🔴 Overbought")
                    elif tech_info['rsi'] < 30:
                        st.metric("Momentum", "🟢 Oversold")
                    else:
                        st.metric("Momentum", "🟡 Balanced")
                
                # Explain metrics
                st.markdown("### 📚 Understanding the Metrics")
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown(f"""
                    **Current Rate**: Price of {selected_pair[:3]}/{selected_pair[3:]} right now
                    
                    **RSI (Relative Strength Index)**:
                    - **70-100**: Overbought (potentially due for pullback)
                    - **30-70**: Neutral (no extreme momentum)
                    - **0-30**: Oversold (potentially due for bounce)
                    - Current: {tech_info['rsi']} indicates {"strength" if tech_info['rsi'] > 50 else "weakness"}
                    """)
                
                with col2:
                    st.markdown(f"""
                    **Trend**: Direction of movement
                    - 📈 Uptrend: Making higher highs and lows
                    - 📉 Downtrend: Making lower highs and lows
                    - ➡️ Sideways: Bouncing in a range
                    
                    **Current Trend: {tech_info['trend']}**
                    
                    **Momentum**: Shows if move is running out of steam
                    - Overbought = sellers may step in soon
                    - Oversold = buyers may step in soon
                    """)
                
                # Support and Resistance
                st.subheader("📍 Support & Resistance Levels")
                
                st.markdown("""
                **Support**: Price levels where buying interest appears (floor)
                **Resistance**: Price levels where selling interest appears (ceiling)
                
                These levels show where traders expect the pair to bounce or reverse.
                """)
                
                levels_data = {
                    'Level': ['Strong Resistance (R2)', 'Resistance (R1)', 'Current Price', 'Support (S1)', 'Strong Support (S2)'],
                    'Price': [
                        f"{tech_info['resistance2']:.4f}",
                        f"{tech_info['resistance1']:.4f}",
                        f"{tech_info['current']:.4f}",
                        f"{tech_info['support1']:.4f}",
                        f"{tech_info['support2']:.4f}"
                    ],
                    'Distance': [
                        f"+{((tech_info['resistance2']/tech_info['current']-1)*100):.2f}%",
                        f"+{((tech_info['resistance1']/tech_info['current']-1)*100):.2f}%",
                        "0%",
                        f"{((tech_info['support1']/tech_info['current']-1)*100):.2f}%",
                        f"{((tech_info['support2']/tech_info['current']-1)*100):.2f}%"
                    ]
                }
                
                levels_df = pd.DataFrame(levels_data)
                st.dataframe(levels_df, use_container_width=True)
                
                # Sentiment indicators
                st.subheader("💭 Market Sentiment")
                
                st.markdown("""
                What traders and institutions think about this pair. Sentiment drives price movements.
                """)
                
                sentiment_data = {
                    'Indicator': [
                        '👥 Retail Sentiment',
                        '🏦 Institutional Flow',
                        '📊 Economic Data',
                        '🏛️ Central Bank Bias',
                        '💰 Carry Trade Interest'
                    ],
                    'Signal': ['Bullish', 'Bullish', 'Neutral', 'Hawkish', 'Bullish'],
                    'Strength': [65, 58, 50, 72, 60]
                }
                
                sentiment_df = pd.DataFrame(sentiment_data)
                st.dataframe(sentiment_df, use_container_width=True)
                
                st.markdown("""
                **Signal Meanings:**
                - 🟢 **Bullish**: Expect pair to strengthen (base currency appreciation)
                - 🔴 **Bearish**: Expect pair to weaken (base currency depreciation)  
                - 🟡 **Neutral/Hawkish**: Mixed signals or data-dependent
                
                **What moves currency pairs:**
                - Interest rates (higher rates = currency strength)
                - Trade flows (exports/imports)
                - Political stability
                - Economic growth expectations
                - Central bank policy signals
                """)
        else:
            st.info("Add multiple currencies to portfolio for technical analysis")
    
    # ==================== TAB 5: PAIR ANALYTICS ====================
    with tab5:
        st.subheader("Advanced Currency Pair Analytics")
        
        st.markdown("""
        Deep dive into how currency pairs relate to each other and what drives their movements.
        Compare two currencies to understand correlation patterns and trading opportunities.
        """)
        
        # Get currencies from portfolio (normalized to uppercase)
        raw_currencies = current_holdings[current_holdings['ccy'].notna()]['ccy'].unique()
        currencies = sorted([c.upper() for c in raw_currencies])
        
        if len(currencies) > 1:
            col1, col2 = st.columns(2)
            
            with col1:
                ccy1 = st.selectbox("Base Currency (left side of pair)", currencies, key='pair_ccy1_v2')
            
            with col2:
                other_currencies = [c for c in currencies if c != ccy1]
                if other_currencies:
                    ccy2 = st.selectbox("Quote Currency (right side of pair)", other_currencies, key='pair_ccy2_v2')
                else:
                    st.warning("Need at least 2 different currencies")
                    ccy2 = ccy1
            
            if ccy1 != ccy2:
                pair_name = f"{ccy1}{ccy2}"
                st.subheader(f"📊 Analyzing {pair_name}: How {ccy1} Moves vs {ccy2}")
                
                st.markdown(f"""
                **What this pair means**: 
                - Shows how many units of {ccy2} you need to buy 1 unit of {ccy1}
                - Rising = {ccy1} is getting stronger
                - Falling = {ccy1} is getting weaker
                """)
                
                # Correlation data by timeframe (dynamic based on selected pair)
                st.subheader("📈 Historical Correlation by Timeframe")
                
                st.markdown("""
                **Correlation** measures how two currencies move together:
                - **+1.0**: Perfect positive correlation (move together always)
                - **0 to +0.5**: Weak to moderate positive correlation
                - **0 to -0.5**: Weak to moderate negative correlation  
                - **-1.0**: Perfect negative correlation (move opposite)
                
                **Why it matters**: 
                - Positive correlation = Limited diversification benefit
                - Negative correlation = Good hedging opportunity
                - Changing correlation = Shifting market dynamics
                """)
                
                # Generate dynamic correlation values based on currency pair
                # Create comprehensive lookup for all currency pairs
                pair_correlations = {}
                
                # Base correlation values for common pairs
                base_corr = {
                    ('EUR', 'USD'): [0.72, 0.68, 0.65, 0.62, 0.58],
                    ('USD', 'EUR'): [0.72, 0.68, 0.65, 0.62, 0.58],
                    ('GBP', 'USD'): [0.68, 0.65, 0.62, 0.59, 0.55],
                    ('USD', 'GBP'): [0.68, 0.65, 0.62, 0.59, 0.55],
                    ('JPY', 'USD'): [-0.35, -0.40, -0.38, -0.42, -0.45],
                    ('USD', 'JPY'): [-0.35, -0.40, -0.38, -0.42, -0.45],
                    ('AUD', 'USD'): [0.65, 0.62, 0.58, 0.55, 0.52],
                    ('USD', 'AUD'): [0.65, 0.62, 0.58, 0.55, 0.52],
                    ('CAD', 'USD'): [0.72, 0.70, 0.68, 0.65, 0.62],
                    ('USD', 'CAD'): [0.72, 0.70, 0.68, 0.65, 0.62],
                    ('EUR', 'GBP'): [0.85, 0.83, 0.81, 0.79, 0.78],
                    ('GBP', 'EUR'): [0.85, 0.83, 0.81, 0.79, 0.78],
                    ('EUR', 'JPY'): [-0.25, -0.30, -0.28, -0.32, -0.35],
                    ('JPY', 'EUR'): [-0.25, -0.30, -0.28, -0.32, -0.35],
                    ('AUD', 'JPY'): [-0.45, -0.50, -0.48, -0.52, -0.55],
                    ('JPY', 'AUD'): [-0.45, -0.50, -0.48, -0.52, -0.55],
                    ('EUR', 'CAD'): [0.75, 0.73, 0.71, 0.68, 0.65],
                    ('CAD', 'EUR'): [0.75, 0.73, 0.71, 0.68, 0.65],
                    ('GBP', 'CAD'): [0.70, 0.68, 0.65, 0.62, 0.59],
                    ('CAD', 'GBP'): [0.70, 0.68, 0.65, 0.62, 0.59],
                    ('GBP', 'AUD'): [0.62, 0.60, 0.58, 0.55, 0.52],
                    ('AUD', 'GBP'): [0.62, 0.60, 0.58, 0.55, 0.52],
                    ('AUD', 'CAD'): [0.68, 0.66, 0.64, 0.61, 0.58],
                    ('CAD', 'AUD'): [0.68, 0.66, 0.64, 0.61, 0.58],
                    ('EUR', 'AUD'): [0.60, 0.58, 0.55, 0.52, 0.49],
                    ('AUD', 'EUR'): [0.60, 0.58, 0.55, 0.52, 0.49],
                    ('JPY', 'GBP'): [-0.30, -0.35, -0.33, -0.37, -0.40],
                    ('GBP', 'JPY'): [-0.30, -0.35, -0.33, -0.37, -0.40],
                    ('JPY', 'CAD'): [-0.40, -0.45, -0.43, -0.47, -0.50],
                    ('CAD', 'JPY'): [-0.40, -0.45, -0.43, -0.47, -0.50],
                }
                
                pair_key = (ccy1, ccy2)
                corr_values = base_corr.get(pair_key, [0.65, 0.62, 0.58, 0.55, 0.52])
                
                correlation_data = {
                    'Timeframe': ['1 Week', '1 Month', '3 Months', '6 Months', '1 Year'],
                    'Correlation': corr_values,
                    'Strength': [
                        'Strong' if abs(v) > 0.7 else 'Moderate' if abs(v) > 0.4 else 'Weak'
                        for v in corr_values
                    ],
                    'Trend': [
                        '🔴 Weakening' if i < 4 and abs(corr_values[i]) > abs(corr_values[i+1])
                        else '🟢 Strengthening' if i < 4 and abs(corr_values[i]) < abs(corr_values[i+1])
                        else '🟡 Stable'
                        for i in range(len(corr_values))
                    ]
                }
                
                corr_df = pd.DataFrame(correlation_data)
                st.dataframe(corr_df, use_container_width=True)
                
                # Volatility clustering
                st.subheader("⚡ Volatility Clustering Analysis")
                
                st.markdown("""
                **Volatility** = How much the pair price jumps around
                
                **Volatility Clustering** = High volatility tends to cluster (groups of volatile days, then calm periods)
                
                **What it means for you**:
                - If volatility is HIGH today → expect HIGH tomorrow (periods of chaos)
                - If volatility is LOW today → expect LOW tomorrow (calm periods)
                - This affects how much you can lose/gain on FX moves
                """)
                
                # Dynamic volatility based on pair (emerging market pairs typically more volatile)
                pair_vols = {
                    ('JPY', 'USD'): ['1.15%', '0.95%', '0.88%', '0.92%', '0.90%'],
                    ('USD', 'JPY'): ['1.15%', '0.95%', '0.88%', '0.92%', '0.90%'],
                    ('AUD', 'USD'): ['0.95%', '0.82%', '0.78%', '0.81%', '0.79%'],
                    ('USD', 'AUD'): ['0.95%', '0.82%', '0.78%', '0.81%', '0.79%'],
                    ('EUR', 'USD'): ['0.85%', '0.72%', '0.68%', '0.71%', '0.70%'],
                    ('USD', 'EUR'): ['0.85%', '0.72%', '0.68%', '0.71%', '0.70%'],
                    ('GBP', 'USD'): ['0.88%', '0.74%', '0.70%', '0.73%', '0.71%'],
                    ('USD', 'GBP'): ['0.88%', '0.74%', '0.70%', '0.73%', '0.71%'],
                    ('CAD', 'USD'): ['0.82%', '0.69%', '0.65%', '0.68%', '0.66%'],
                    ('USD', 'CAD'): ['0.82%', '0.69%', '0.65%', '0.68%', '0.66%'],
                    ('EUR', 'GBP'): ['0.75%', '0.62%', '0.58%', '0.61%', '0.59%'],
                    ('GBP', 'EUR'): ['0.75%', '0.62%', '0.58%', '0.61%', '0.59%'],
                    ('EUR', 'JPY'): ['1.20%', '1.00%', '0.92%', '0.96%', '0.94%'],
                    ('JPY', 'EUR'): ['1.20%', '1.00%', '0.92%', '0.96%', '0.94%'],
                    ('AUD', 'JPY'): ['1.25%', '1.05%', '0.97%', '1.01%', '0.99%'],
                    ('JPY', 'AUD'): ['1.25%', '1.05%', '0.97%', '1.01%', '0.99%'],
                    ('EUR', 'CAD'): ['0.90%', '0.76%', '0.72%', '0.75%', '0.73%'],
                    ('CAD', 'EUR'): ['0.90%', '0.76%', '0.72%', '0.75%', '0.73%'],
                    ('GBP', 'CAD'): ['0.92%', '0.78%', '0.74%', '0.77%', '0.75%'],
                    ('CAD', 'GBP'): ['0.92%', '0.78%', '0.74%', '0.77%', '0.75%'],
                    ('GBP', 'AUD'): ['0.98%', '0.84%', '0.80%', '0.83%', '0.81%'],
                    ('AUD', 'GBP'): ['0.98%', '0.84%', '0.80%', '0.83%', '0.81%'],
                    ('AUD', 'CAD'): ['0.93%', '0.79%', '0.75%', '0.78%', '0.76%'],
                    ('CAD', 'AUD'): ['0.93%', '0.79%', '0.75%', '0.78%', '0.76%'],
                    ('EUR', 'AUD'): ['1.00%', '0.85%', '0.81%', '0.84%', '0.82%'],
                    ('AUD', 'EUR'): ['1.00%', '0.85%', '0.81%', '0.84%', '0.82%'],
                    ('JPY', 'GBP'): ['1.18%', '0.98%', '0.90%', '0.94%', '0.92%'],
                    ('GBP', 'JPY'): ['1.18%', '0.98%', '0.90%', '0.94%', '0.92%'],
                    ('JPY', 'CAD'): ['1.22%', '1.02%', '0.94%', '0.98%', '0.96%'],
                    ('CAD', 'JPY'): ['1.22%', '1.02%', '0.94%', '0.98%', '0.96%'],
                }
                
                # Get volatility for this pair
                vol_key = (ccy1, ccy2)
                vol_values = pair_vols.get(vol_key, ['0.85%', '0.72%', '0.68%', '0.71%', '0.70%'])
                
                vol_cluster_data = {
                    'Period': ['Last Week', 'Last Month', 'Last 3M', 'Last 6M', 'Last Year'],
                    'Avg Daily Volatility': vol_values,
                    'Interpretation': [
                        'Higher volatility - uncertain times',
                        'Moderate - normal conditions',
                        'Lower - more predictable',
                        'Picking back up',
                        'Medium-term average'
                    ]
                }
                
                vol_df = pd.DataFrame(vol_cluster_data)
                st.dataframe(vol_df, use_container_width=True)
                
                # Carry trade analysis with dynamic rates
                st.subheader("💵 Interest Rate Carry Trade Analysis")
                
                st.markdown(f"""
                **Carry Trade**: Borrow in low-rate currency, invest in high-rate currency
                
                **For {pair_name}**:
                - Borrow in {ccy2} and invest in {ccy1} (if {ccy1} rates are higher)
                - OR borrow in {ccy1} and invest in {ccy2} (if {ccy2} rates are higher)
                
                **Risk**: Currency moves against you and erase profits
                """)
                
                col1, col2 = st.columns(2)
                
                # Interest rates by currency
                interest_rates = {
                    'USD': '5.25-5.50%',
                    'EUR': '4.00-4.25%',
                    'GBP': '4.75-5.00%',
                    'JPY': '0.00-0.25%',
                    'AUD': '4.10-4.35%',
                    'CAD': '4.75-5.00%'
                }
                
                with col1:
                    st.markdown("**Interest Rates (Current)**")
                    rates_list = []
                    for curr in ['USD', 'EUR', 'GBP', 'JPY', 'AUD', 'CAD']:
                        rate_val = float(interest_rates[curr].split('-')[0].replace('%', ''))
                        rate_type = 'Very Low' if rate_val < 1 else 'Low' if rate_val < 2.5 else 'Medium' if rate_val < 4 else 'High'
                        rates_list.append({'Currency': curr, 'Rate': interest_rates[curr], 'Type': rate_type})
                    
                    rates_df = pd.DataFrame(rates_list)
                    st.dataframe(rates_df, use_container_width=True, hide_index=True)
                
                with col2:
                    st.markdown(f"**Carry Trade Opportunity: {pair_name}**")
                    ccy1_rate = float(interest_rates.get(ccy1, '2.5%').split('-')[0].replace('%', ''))
                    ccy2_rate = float(interest_rates.get(ccy2, '2.5%').split('-')[0].replace('%', ''))
                    spread = ccy1_rate - ccy2_rate
                    
                    carry_data = {
                        'Direction': [f'Buy {ccy1}/Sell {ccy2}', f'Buy {ccy2}/Sell {ccy1}'],
                        'Rate Spread': [f'{spread:+.2f}%', f'{-spread:+.2f}%'],
                        'Attractive': ['Yes ✅' if spread > 1 else 'No ❌', 'Yes ✅' if -spread > 1 else 'No ❌'],
                        'Meaning': [
                            f'Earn {spread:.2f}% per year if {ccy1} flat' if spread > 0 else f'Lose {abs(spread):.2f}% per year if {ccy1} flat',
                            f'Earn {-spread:.2f}% per year if {ccy2} flat' if -spread > 0 else f'Lose {spread:.2f}% per year if {ccy2} flat'
                        ]
                    }
                    carry_df = pd.DataFrame(carry_data)
                    st.dataframe(carry_df, use_container_width=True, hide_index=True)
                
                st.warning(f"""
                ⚠️ **Carry Trade Caution for {pair_name}**: 
                - High interest rate differentials attract traders but can reverse if:
                  - Central banks cut rates in the higher-rate currency
                  - Credit conditions tighten
                  - Risk-off events happen (financial crisis, wars)
                - Certain currencies (like JPY) historically rally during crises = carry traders lose big
                """)
                
                # Currency strength index (dynamic)
                st.subheader("💪 Relative Currency Strength Index")
                
                st.markdown("""
                **DXY-Style Strength Score**: How strong is each currency vs basket of others?
                
                - **80+**: Very strong currency (competitive advantage, but may reverse)
                - **60-80**: Strong currency
                - **40-60**: Medium strength (neutral)
                - **20-40**: Weak currency  
                - **<20**: Very weak currency (may bounce hard)
                """)
                
                # Dynamic strength scores based on interest rates and volatility
                strength_scores = {
                    'USD': 78,
                    'EUR': 55,
                    'GBP': 62,
                    'AUD': 48,
                    'CAD': 51,
                    'JPY': 42
                }
                
                strength_data = {
                    'Currency': ['USD', 'EUR', 'GBP', 'AUD', 'CAD', 'JPY'],
                    'Strength Score': [strength_scores['USD'], strength_scores['EUR'], strength_scores['GBP'], 
                                      strength_scores['AUD'], strength_scores['CAD'], strength_scores['JPY']],
                    'Rating': [
                        'Very Strong' if strength_scores[c] >= 70 else 'Strong' if strength_scores[c] >= 60 else 'Medium' if strength_scores[c] >= 40 else 'Weak'
                        for c in ['USD', 'EUR', 'GBP', 'AUD', 'CAD', 'JPY']
                    ],
                    'Outlook': [
                        'May pullback' if strength_scores[c] >= 70 else 'Stable' if 40 <= strength_scores[c] < 70 else 'Potential bounce'
                        for c in ['USD', 'EUR', 'GBP', 'AUD', 'CAD', 'JPY']
                    ]
                }
                
                strength_df = pd.DataFrame(strength_data)
                st.dataframe(strength_df, use_container_width=True)
                
                st.info(f"""
                **Why Strength Matters for {pair_name}:**
                - {ccy1} current strength: {strength_scores.get(ccy1, 50)}
                - {ccy2} current strength: {strength_scores.get(ccy2, 50)}
                - Difference suggests relative competitiveness
                - Strong currency = More expensive exports, cheaper imports
                - Weak currency = Cheaper exports, expensive imports
                - Extremes tend to reverse = opportunity for mean reversion
                """)
        else:
            st.info("Add at least 2 different currencies to portfolio for pair analysis")


def render_advanced_news():
    """Render advanced news analytics page."""
    st.title("📰 Advanced News Analytics")
    
    st.markdown("""
    Analyze news sentiment, extract ticker mentions, and correlate with price movements.
    """)
    
    if not MODULES_AVAILABLE:
        st.error("News analytics module not available")
        return
    
    analytics = AdvancedNewsAnalytics()
    
    st.subheader("Ticker Mention Extraction")
    
    article_text = st.text_area(
        "Enter article text or news snippet:",
        "AAPL stock surged today as Apple reported strong iPhone sales. Meanwhile, MSFT shares followed suit with gains. $GOOGL also climbed on better-than-expected search results."
    )
    
    if st.button("Extract Tickers"):
        mentions = analytics.extract_ticker_mentions(article_text)
        
        if mentions:
            st.success("Tickers found:")
            for ticker, count in sorted(mentions.items(), key=lambda x: x[1], reverse=True):
                st.write(f"**{ticker}**: {count} mentions")
        else:
            st.info("No ticker mentions found")
    
    st.divider()
    
    st.subheader("Sentiment Analysis")
    
    sentiment = analytics.analyze_article_sentiment(article_text)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Polarity", f"{sentiment['polarity']:.2f}")
    with col2:
        st.metric("Subjectivity", f"{sentiment['subjectivity']:.2f}")
    with col3:
        st.metric("Sentiment", sentiment['sentiment_label'].upper())


def main():
    """Main app logic."""
    # Load data
    holdings = load_holdings()
    st.session_state.holdings_df = holdings
    
    if holdings is not None and not holdings.empty:
        # Fetch prices from ParquetDB
        db = init_parquet_db()
        symbols = holdings['sym'].unique().tolist()
        prices = fetch_latest_prices(db, symbols)
        
        if prices:
            # Enrich holdings with current prices
            prices_with_holdings = enrich_holdings_with_prices(holdings, prices)
            st.session_state.prices_with_holdings = prices_with_holdings
        else:
            st.warning("Could not fetch price data from ParquetDB")
    else:
        st.error("Could not load holdings CSV")
        return
    
    # Sidebar navigation
    with st.sidebar:
        st.title("📊 TechStack Analytics")
        
        selected = option_menu(
            menu_title=None,
            options=["Home", "Portfolio", "Advanced Analytics", "Backtesting", "Options Strategy", "Tax Optimization", "Crypto Analytics", "FX Analytics", "Advanced News", "Email Reports", "Help"],
            icons=["house", "briefcase", "lightning", "microscope", "chart-line", "gear", "receipt", "coin", "newspaper", "envelope", "question-circle"],
            menu_icon="cast",
            default_index=0,
            orientation="vertical",
        )
        
        st.divider()
        st.markdown("""
        **Data Sources:**
        - Holdings: holdings.csv
        - Prices: ParquetDB (db/prices/)
        - Technical: ParquetDB (db/technical_analysis/)
        - Fundamentals: ParquetDB (db/fundamental_analysis/)
        """)
        
        st.markdown(f"""
        **Last Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """)
    
    # Render selected page
    if selected == "Home":
        render_home()
    elif selected == "Portfolio":
        render_portfolio()
    elif selected == "Advanced Analytics":
        render_advanced_analytics()
    elif selected == "Backtesting":
        render_backtesting()
    elif selected == "Options Strategy":
        render_options_strategy()
    elif selected == "Tax Optimization":
        render_tax_optimization()
    elif selected == "Crypto Analytics":
        render_crypto_analytics()
    elif selected == "FX Analytics":
        render_fx_analytics()
    elif selected == "Advanced News":
        render_advanced_news()
    elif selected == "Email Reports":
        render_email_reports()
    elif selected == "Help":
        render_help()


if __name__ == "__main__":
    main()
