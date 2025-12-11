"""
Streamlit-compatible quick wins analytics with Prefect flow integration.

Provides analysis functions for:
- Portfolio momentum signals
- Mean reversion opportunities
- Sector rotation strategies
- Portfolio beta calculation

Works both directly in Streamlit and with Prefect for logging.
"""

from typing import Dict, List, Optional, Tuple

import pandas as pd
import numpy as np

try:
    from prefect import flow, task, get_run_logger
    HAS_PREFECT = True
except ImportError:
    HAS_PREFECT = False


def calculate_momentum_analysis(holdings_df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict]:
    """
    Calculate momentum signals from holdings data.
    
    Args:
        holdings_df: DataFrame with holdings including returns data
    
    Returns:
        Tuple of (momentum_df with signals, statistics dict)
    """
    momentum_data = []
    
    for idx, row in holdings_df.iterrows():
        # Calculate return % from multiple sources
        return_pct = 0
        
        if 'pnl_percent' in holdings_df.columns and pd.notna(row.get('pnl_percent')):
            return_pct = float(row['pnl_percent'])
        elif 'current_price' in holdings_df.columns and 'bep' in holdings_df.columns:
            current = float(row.get('current_price', 0))
            entry = float(row.get('bep', 0))
            if entry > 0:
                return_pct = ((current - entry) / entry) * 100
        elif 'pnl_absolute' in holdings_df.columns and 'qty' in holdings_df.columns and 'bep' in holdings_df.columns:
            qty = float(row.get('qty', 0))
            entry = float(row.get('bep', 0))
            if qty > 0 and entry > 0:
                entry_value = qty * entry
                return_pct = (float(row.get('pnl_absolute', 0)) / entry_value) * 100 if entry_value > 0 else 0
        
        momentum_data.append({
            'Symbol': row['sym'],
            'Return %': round(return_pct, 2),
            'Current Price': row.get('current_price', 0),
            'Signal': 'Strong Uptrend' if return_pct > 10 else 'Uptrend' if return_pct > 0 else 'Downtrend'
        })
    
    momentum_df = pd.DataFrame(momentum_data).sort_values('Return %', ascending=False)
    
    uptrend_count = len(momentum_df[momentum_df['Signal'].str.contains('Uptrend')])
    downtrend_count = len(momentum_df[momentum_df['Signal'] == 'Downtrend'])
    avg_return = momentum_df['Return %'].mean()
    
    stats = {
        'total_symbols': len(momentum_df),
        'uptrend_count': uptrend_count,
        'downtrend_count': downtrend_count,
        'avg_return': float(avg_return),
        'best_performer': momentum_df.iloc[0]['Symbol'] if not momentum_df.empty else None,
        'worst_performer': momentum_df.iloc[-1]['Symbol'] if not momentum_df.empty else None,
    }
    
    return momentum_df, stats


def calculate_mean_reversion_analysis(holdings_df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict]:
    """
    Calculate mean reversion signals from holdings data.
    
    Args:
        holdings_df: DataFrame with holdings including P&L data
    
    Returns:
        Tuple of (reversion_df with signals, statistics dict)
    """
    if 'pnl_percent' not in holdings_df.columns:
        return pd.DataFrame(), {'error': 'No P&L data available'}
    
    reversion_data = []
    for idx, row in holdings_df.iterrows():
        pnl = row['pnl_percent']
        reversion_data.append({
            'Symbol': row['sym'],
            'P&L %': pnl,
            'Current Price': row.get('current_price', 0),
            'Signal': 'Strong Overbought' if pnl > 50 else 'Overbought' if pnl > 20 else 'Strong Oversold' if pnl < -50 else 'Oversold' if pnl < -20 else 'Normal Range'
        })
    
    reversion_df = pd.DataFrame(reversion_data).sort_values('P&L %', ascending=True)
    
    oversold_count = len(reversion_df[reversion_df['Signal'].str.contains('Oversold')])
    overbought_count = len(reversion_df[reversion_df['Signal'].str.contains('Overbought')])
    normal_count = len(reversion_df[reversion_df['Signal'] == 'Normal Range'])
    
    stats = {
        'total_symbols': len(reversion_df),
        'oversold_count': oversold_count,
        'overbought_count': overbought_count,
        'normal_count': normal_count,
        'avg_pnl': float(reversion_df['P&L %'].mean()),
        'max_gain': float(reversion_df['P&L %'].max()),
        'max_loss': float(reversion_df['P&L %'].min()),
    }
    
    return reversion_df, stats


def calculate_sector_rotation_analysis(holdings_df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict]:
    """
    Calculate sector rotation analysis from holdings data.
    
    Args:
        holdings_df: DataFrame with holdings including sector/asset class data
    
    Returns:
        Tuple of (sector_df with metrics, statistics dict)
    """
    if 'asset' not in holdings_df.columns:
        return pd.DataFrame(), {'error': 'No asset/sector data available'}
    
    sector_data = []
    
    for asset_class in holdings_df['asset'].unique():
        asset_holdings = holdings_df[holdings_df['asset'] == asset_class]
        
        total_value = asset_holdings['current_value'].sum()
        total_cost = asset_holdings['qty'].fillna(1) * asset_holdings['bep'].fillna(0)
        total_cost = total_cost.sum()
        total_pnl = asset_holdings['pnl_absolute'].sum() if 'pnl_absolute' in asset_holdings.columns else total_value - total_cost
        
        num_positions = len(asset_holdings)
        
        sector_data.append({
            'Asset Class': asset_class,
            'Value': total_value,
            'Cost': total_cost,
            'P&L': total_pnl,
            'Positions': num_positions,
            'Avg Position Size': total_value / num_positions if num_positions > 0 else 0,
        })
    
    sector_df = pd.DataFrame(sector_data).sort_values('Value', ascending=False)
    
    total_portfolio_value = sector_df['Value'].sum()
    
    stats = {
        'total_value': float(total_portfolio_value),
        'num_sectors': len(sector_df),
        'top_sector': sector_df.iloc[0]['Asset Class'] if not sector_df.empty else None,
        'top_sector_value': float(sector_df.iloc[0]['Value']) if not sector_df.empty else 0,
        'top_sector_pct': float((sector_df.iloc[0]['Value'] / total_portfolio_value * 100)) if not sector_df.empty and total_portfolio_value > 0 else 0,
        'total_pnl': float(sector_df['P&L'].sum()),
    }
    
    return sector_df, stats


def calculate_portfolio_beta_analysis(holdings_df: pd.DataFrame) -> Dict:
    """
    Calculate portfolio beta from holdings data.
    
    Args:
        holdings_df: DataFrame with holdings including returns data
    
    Returns:
        Dictionary with beta metrics and risk classification
    """
    total_value = holdings_df['current_value'].sum()
    
    # Calculate returns for each holding
    holding_returns = []
    for idx, row in holdings_df.iterrows():
        return_pct = 0
        
        if 'pnl_percent' in holdings_df.columns and pd.notna(row.get('pnl_percent')):
            return_pct = float(row['pnl_percent'])
        elif 'current_price' in holdings_df.columns and 'bep' in holdings_df.columns:
            current = float(row.get('current_price', 0))
            entry = float(row.get('bep', 0))
            if entry > 0:
                return_pct = ((current - entry) / entry) * 100
        elif 'pnl_absolute' in holdings_df.columns and 'qty' in holdings_df.columns and 'bep' in holdings_df.columns:
            qty = float(row.get('qty', 0))
            entry = float(row.get('bep', 0))
            if qty > 0 and entry > 0:
                entry_value = qty * entry
                return_pct = (float(row.get('pnl_absolute', 0)) / entry_value) * 100 if entry_value > 0 else 0
        
        holding_returns.append(return_pct)
    
    holding_returns = np.array(holding_returns)
    
    # Calculate metrics
    portfolio_return = np.average(holding_returns, weights=holdings_df['current_value'].values) if total_value > 0 else 0
    returns_volatility = np.std(holding_returns)
    market_return = np.mean(holding_returns)
    market_volatility = np.std(holding_returns)
    
    # Calculate beta
    if market_volatility > 0:
        portfolio_beta = returns_volatility / market_volatility if market_volatility > 0 else 1.0
        
        if market_return != 0:
            performance_ratio = portfolio_return / market_return
            portfolio_beta = portfolio_beta * performance_ratio
    else:
        portfolio_beta = 1.0
    
    # Ensure beta is positive and reasonable
    portfolio_beta = max(0.1, min(portfolio_beta, 3.0))
    
    # Calculate Sharpe ratio (simplified: excess return / volatility)
    sharpe_ratio = portfolio_return / returns_volatility if returns_volatility > 0 else 0
    
    # Classify risk profile
    if portfolio_beta > 1.2:
        risk_profile = "Aggressive"
    elif portfolio_beta > 0.8:
        risk_profile = "Moderate"
    elif portfolio_beta >= 0.5:
        risk_profile = "Conservative"
    else:
        risk_profile = "Very Conservative / Hedged"
    
    return {
        'beta': float(portfolio_beta),
        'volatility': float(returns_volatility),
        'portfolio_return': float(portfolio_return),
        'sharpe_ratio': float(sharpe_ratio),
        'risk_profile': risk_profile,
        'num_holdings': len(holdings_df),
        'avg_return': float(np.mean(holding_returns)),
        'std_dev': float(np.std(holding_returns)),
    }


# Prefect task wrappers (optional, if Prefect available)
if HAS_PREFECT:
    @task(name="momentum_analysis_task")
    def momentum_analysis_task(holdings_df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict]:
        """Prefect task for momentum analysis."""
        return calculate_momentum_analysis(holdings_df)
    
    @task(name="mean_reversion_task")
    def mean_reversion_task(holdings_df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict]:
        """Prefect task for mean reversion analysis."""
        return calculate_mean_reversion_analysis(holdings_df)
    
    @task(name="sector_rotation_task")
    def sector_rotation_task(holdings_df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict]:
        """Prefect task for sector rotation analysis."""
        return calculate_sector_rotation_analysis(holdings_df)
    
    @task(name="portfolio_beta_task")
    def portfolio_beta_task(holdings_df: pd.DataFrame) -> Dict:
        """Prefect task for portfolio beta analysis."""
        return calculate_portfolio_beta_analysis(holdings_df)
    
    # Flow wrappers that work in/out of Prefect context
    @flow(name="momentum_analysis_flow")
    def momentum_analysis_flow(holdings_df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict]:
        """Streamlit-compatible momentum analysis flow."""
        flow_logger = get_run_logger()
        flow_logger.info(f"Starting momentum analysis for {len(holdings_df)} holdings")
        momentum_df, stats = momentum_analysis_task(holdings_df)
        flow_logger.info(f"Momentum analysis complete: {stats['uptrend_count']} uptrend, {stats['downtrend_count']} downtrend")
        return momentum_df, stats
    
    @flow(name="mean_reversion_flow")
    def mean_reversion_flow(holdings_df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict]:
        """Streamlit-compatible mean reversion flow."""
        flow_logger = get_run_logger()
        flow_logger.info(f"Starting mean reversion analysis for {len(holdings_df)} holdings")
        reversion_df, stats = mean_reversion_task(holdings_df)
        flow_logger.info(f"Mean reversion analysis complete: {stats['oversold_count']} oversold, {stats['overbought_count']} overbought")
        return reversion_df, stats
    
    @flow(name="sector_rotation_flow")
    def sector_rotation_flow(holdings_df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict]:
        """Streamlit-compatible sector rotation flow."""
        flow_logger = get_run_logger()
        flow_logger.info(f"Starting sector rotation analysis for {len(holdings_df)} holdings")
        sector_df, stats = sector_rotation_task(holdings_df)
        flow_logger.info(f"Sector analysis complete: {stats['num_sectors']} sectors analyzed")
        return sector_df, stats
    
    @flow(name="portfolio_beta_flow")
    def portfolio_beta_flow(holdings_df: pd.DataFrame) -> Dict:
        """Streamlit-compatible portfolio beta flow."""
        flow_logger = get_run_logger()
        flow_logger.info(f"Starting portfolio beta analysis")
        beta_metrics = portfolio_beta_task(holdings_df)
        flow_logger.info(f"Portfolio beta: {beta_metrics['beta']:.2f}, Risk: {beta_metrics['risk_profile']}")
        return beta_metrics

else:
    # Fallback if Prefect not available
    def momentum_analysis_flow(holdings_df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict]:
        """Fallback momentum analysis without Prefect."""
        return calculate_momentum_analysis(holdings_df)
    
    def mean_reversion_flow(holdings_df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict]:
        """Fallback mean reversion without Prefect."""
        return calculate_mean_reversion_analysis(holdings_df)
    
    def sector_rotation_flow(holdings_df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict]:
        """Fallback sector rotation without Prefect."""
        return calculate_sector_rotation_analysis(holdings_df)
    
    def portfolio_beta_flow(holdings_df: pd.DataFrame) -> Dict:
        """Fallback portfolio beta without Prefect."""
        return calculate_portfolio_beta_analysis(holdings_df)
