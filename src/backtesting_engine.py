"""
Enhanced Backtesting Engine

Provides comprehensive backtesting with:
- Parameter optimization
- Monte Carlo simulation
- Drawdown analysis
- Strategy performance metrics
- Dask-accelerated calculations
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
import logging
from pathlib import Path

import dask
import dask.dataframe as dd
from scipy import stats
from src.parquet_db import ParquetDB
from src.portfolio_technical import TechnicalAnalyzer
from src.utils import get_logger

logger = get_logger(__name__)


class BacktestResult:
    """Container for backtest results."""
    
    def __init__(self):
        self.trades = []
        self.equity_curve = None
        self.returns = None
        self.metrics = {}
        self.drawdowns = None
        self.signals = None


class EnhancedBacktestingEngine:
    """
    Enhanced backtesting engine with optimization and analysis.
    
    Features:
    - Technical indicator parameter optimization
    - Monte Carlo simulation for risk assessment
    - Maximum drawdown and recovery analysis
    - Sharpe ratio, Sortino, Calmar calculations
    - Win rate and profit factor metrics
    """
    
    def __init__(self, min_capital: float = 10000.0):
        """
        Initialize backtesting engine.
        
        Args:
            min_capital: Minimum capital for position sizing
        """
        self.min_capital = min_capital
        self.db = ParquetDB()
        self.results: Dict[str, BacktestResult] = {}
        
    def backtest_strategy(
        self,
        symbol: str,
        prices_df: pd.DataFrame,
        signal_type: str = "rsi",
        entry_threshold: float = 30.0,
        exit_threshold: float = 70.0,
        stop_loss: float = 0.05,
        take_profit: float = 0.10,
    ) -> BacktestResult:
        """
        Backtest a trading strategy.
        
        Args:
            symbol: Stock ticker
            prices_df: OHLCV data with columns: Open, High, Low, Close, Volume
            signal_type: "rsi", "macd", "bollinger"
            entry_threshold: Entry signal threshold
            exit_threshold: Exit signal threshold
            stop_loss: Stop loss percentage
            take_profit: Take profit percentage
            
        Returns:
            BacktestResult with performance metrics
        """
        result = BacktestResult()
        
        # Generate signals
        signals = self._generate_signals(prices_df, signal_type, entry_threshold, exit_threshold)
        result.signals = signals
        
        # Simulate trades
        trades = self._simulate_trades(
            prices_df, 
            signals,
            stop_loss=stop_loss,
            take_profit=take_profit
        )
        result.trades = trades
        
        # Calculate equity curve
        equity_curve = self._calculate_equity_curve(trades, len(prices_df))
        result.equity_curve = equity_curve
        
        # Calculate returns
        returns = equity_curve.pct_change().fillna(0)
        result.returns = returns
        
        # Calculate metrics
        metrics = self._calculate_metrics(returns, trades)
        result.metrics = metrics
        
        # Calculate drawdowns
        drawdowns = self._calculate_drawdowns(equity_curve)
        result.drawdowns = drawdowns
        
        return result
    
    def _generate_signals(
        self,
        prices_df: pd.DataFrame,
        signal_type: str,
        entry_threshold: float,
        exit_threshold: float,
    ) -> pd.Series:
        """Generate trading signals from technical indicators."""
        signals = pd.Series(0, index=prices_df.index)
        
        if signal_type == "rsi":
            # Calculate RSI
            delta = prices_df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            
            signals[rsi < entry_threshold] = 1  # Buy signal
            signals[rsi > exit_threshold] = -1  # Sell signal
            
        elif signal_type == "macd":
            # Calculate MACD
            ema12 = prices_df['Close'].ewm(span=12).mean()
            ema26 = prices_df['Close'].ewm(span=26).mean()
            macd = ema12 - ema26
            signal_line = macd.ewm(span=9).mean()
            histogram = macd - signal_line
            
            signals[histogram > 0] = 1  # Buy signal
            signals[histogram < 0] = -1  # Sell signal
            
        elif signal_type == "bollinger":
            # Calculate Bollinger Bands
            sma = prices_df['Close'].rolling(window=20).mean()
            std = prices_df['Close'].rolling(window=20).std()
            upper = sma + (std * 2)
            lower = sma - (std * 2)
            
            signals[prices_df['Close'] < lower] = 1  # Buy signal
            signals[prices_df['Close'] > upper] = -1  # Sell signal
        
        return signals
    
    def _simulate_trades(
        self,
        prices_df: pd.DataFrame,
        signals: pd.Series,
        stop_loss: float,
        take_profit: float,
    ) -> List[Dict]:
        """Simulate trades based on signals."""
        trades = []
        position = None
        entry_price = None
        entry_date = None
        
        for idx in range(1, len(prices_df)):
            current_price = prices_df['Close'].iloc[idx]
            current_date = prices_df.index[idx]
            signal = signals.iloc[idx]
            
            # Check stop loss and take profit
            if position is not None:
                loss_pct = (current_price - entry_price) / entry_price
                
                if loss_pct <= -stop_loss or loss_pct >= take_profit:
                    # Close position
                    exit_price = current_price
                    exit_date = current_date
                    pnl = (exit_price - entry_price) * position
                    pnl_pct = loss_pct * 100
                    
                    trades.append({
                        'entry_date': entry_date,
                        'entry_price': entry_price,
                        'exit_date': exit_date,
                        'exit_price': exit_price,
                        'pnl': pnl,
                        'pnl_pct': pnl_pct,
                        'quantity': position,
                        'exit_reason': 'stop_loss' if loss_pct <= -stop_loss else 'take_profit'
                    })
                    position = None
            
            # Check for entry signal
            if signal == 1 and position is None:
                entry_price = current_price
                entry_date = current_date
                position = 100  # Fixed quantity
                
            elif signal == -1 and position is not None:
                exit_price = current_price
                exit_date = current_date
                pnl = (exit_price - entry_price) * position
                pnl_pct = ((exit_price - entry_price) / entry_price) * 100
                
                trades.append({
                    'entry_date': entry_date,
                    'entry_price': entry_price,
                    'exit_date': exit_date,
                    'exit_price': exit_price,
                    'pnl': pnl,
                    'pnl_pct': pnl_pct,
                    'quantity': position,
                    'exit_reason': 'signal'
                })
                position = None
        
        return trades
    
    def _calculate_equity_curve(
        self,
        trades: List[Dict],
        num_periods: int,
    ) -> pd.Series:
        """Calculate equity curve from trades."""
        equity = pd.Series(self.min_capital, index=range(num_periods))
        cumulative_pnl = 0
        
        for trade in trades:
            cumulative_pnl += trade['pnl']
            # Find exit date index and update equity curve
        
        equity = equity + cumulative_pnl
        return equity
    
    def _calculate_drawdowns(self, equity_curve: pd.Series) -> Dict:
        """Calculate maximum drawdown and recovery metrics."""
        running_max = equity_curve.expanding().max()
        drawdown = (equity_curve - running_max) / running_max
        
        max_dd = drawdown.min()
        max_dd_date = drawdown.idxmin()
        
        # Calculate recovery time
        recovery_time = None
        if max_dd < 0:
            recovery_point = equity_curve[equity_curve >= running_max.loc[max_dd_date]].iloc[1:] if len(equity_curve[equity_curve >= running_max.loc[max_dd_date]]) > 1 else None
            if recovery_point is not None:
                recovery_time = recovery_point.index[0] - max_dd_date
        
        return {
            'max_drawdown': max_dd,
            'max_drawdown_date': max_dd_date,
            'recovery_time': recovery_time,
            'drawdown_series': drawdown
        }
    
    def _calculate_metrics(self, returns: pd.Series, trades: List[Dict]) -> Dict:
        """Calculate performance metrics."""
        if len(trades) == 0:
            return {
                'total_return': 0,
                'annualized_return': 0,
                'sharpe_ratio': 0,
                'sortino_ratio': 0,
                'calmar_ratio': 0,
                'win_rate': 0,
                'profit_factor': 0,
                'num_trades': 0
            }
        
        # Return metrics
        total_return = returns.sum()
        annual_return = (1 + returns).prod() ** (252 / len(returns)) - 1 if len(returns) > 0 else 0
        
        # Risk metrics
        annual_std = returns.std() * np.sqrt(252)
        sharpe_ratio = annual_return / annual_std if annual_std > 0 else 0
        
        # Downside standard deviation for Sortino
        downside_returns = returns[returns < 0]
        downside_std = downside_returns.std() * np.sqrt(252)
        sortino_ratio = annual_return / downside_std if downside_std > 0 else 0
        
        # Calmar ratio
        max_dd = abs(min(returns.cumsum()))
        calmar_ratio = annual_return / max_dd if max_dd > 0 else 0
        
        # Trade statistics
        winning_trades = [t for t in trades if t['pnl'] > 0]
        losing_trades = [t for t in trades if t['pnl'] < 0]
        
        win_rate = len(winning_trades) / len(trades) if len(trades) > 0 else 0
        
        total_wins = sum(t['pnl'] for t in winning_trades)
        total_losses = abs(sum(t['pnl'] for t in losing_trades))
        
        profit_factor = total_wins / total_losses if total_losses > 0 else 0
        
        return {
            'total_return': total_return,
            'annualized_return': annual_return,
            'sharpe_ratio': sharpe_ratio,
            'sortino_ratio': sortino_ratio,
            'calmar_ratio': calmar_ratio,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'num_trades': len(trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
        }
    
    def optimize_parameters(
        self,
        symbol: str,
        prices_df: pd.DataFrame,
        signal_type: str = "rsi",
        param_ranges: Optional[Dict] = None,
    ) -> Dict:
        """
        Optimize indicator parameters using grid search.
        
        Args:
            symbol: Stock ticker
            prices_df: OHLCV data
            signal_type: Type of signal to optimize
            param_ranges: Dict with parameter ranges to test
            
        Returns:
            Dict with best parameters and performance
        """
        if param_ranges is None:
            if signal_type == "rsi":
                param_ranges = {
                    'entry_threshold': [20, 25, 30, 35],
                    'exit_threshold': [60, 65, 70, 75]
                }
            elif signal_type == "macd":
                param_ranges = {
                    'entry_threshold': [0.01, 0.02, 0.03],
                    'exit_threshold': [-0.01, -0.02, -0.03]
                }
        
        best_result = None
        best_sharpe = float('-inf')
        best_params = None
        
        # Grid search over parameters
        from itertools import product
        
        param_keys = list(param_ranges.keys())
        param_values = [param_ranges[k] for k in param_keys]
        
        for values in product(*param_values):
            params = dict(zip(param_keys, values))
            
            result = self.backtest_strategy(
                symbol,
                prices_df,
                signal_type=signal_type,
                **params
            )
            
            sharpe = result.metrics.get('sharpe_ratio', 0)
            
            if sharpe > best_sharpe:
                best_sharpe = sharpe
                best_result = result
                best_params = params
        
        return {
            'best_params': best_params,
            'best_sharpe': best_sharpe,
            'result': best_result,
            'metrics': best_result.metrics if best_result else {}
        }
    
    def monte_carlo_simulation(
        self,
        returns: pd.Series,
        num_simulations: int = 1000,
        periods: int = 252,
    ) -> Dict:
        """
        Run Monte Carlo simulation on returns.
        
        Args:
            returns: Historical returns series
            num_simulations: Number of simulations to run
            periods: Number of periods to simulate
            
        Returns:
            Dict with simulation results and statistics
        """
        mean_return = returns.mean()
        std_return = returns.std()
        
        simulations = np.zeros((num_simulations, periods))
        
        # Vectorized Monte Carlo simulation with Dask
        @dask.delayed
        def run_simulation():
            sim = np.zeros((num_simulations, periods))
            for i in range(num_simulations):
                random_returns = np.random.normal(mean_return, std_return, periods)
                sim[i] = (1 + random_returns).cumprod() * 100
            return sim
        
        # Execute simulation
        simulations = run_simulation().compute()
        
        # Calculate statistics
        percentile_5 = np.percentile(simulations[:, -1], 5)
        percentile_50 = np.percentile(simulations[:, -1], 50)
        percentile_95 = np.percentile(simulations[:, -1], 95)
        
        confidence_interval_95 = (
            np.percentile(simulations[:, -1], 2.5),
            np.percentile(simulations[:, -1], 97.5)
        )
        
        return {
            'simulations': simulations,
            'percentile_5': percentile_5,
            'percentile_50': percentile_50,
            'percentile_95': percentile_95,
            'confidence_interval_95': confidence_interval_95,
            'final_values': simulations[:, -1]
        }
    
    def save_backtest_results(
        self,
        symbol: str,
        result: BacktestResult,
        output_dir: str = "db"
    ) -> str:
        """Save backtest results to Parquet."""
        try:
            # Save trades
            if result.trades:
                trades_df = pd.DataFrame(result.trades)
                trades_df['symbol'] = symbol
                trades_df['timestamp'] = pd.Timestamp.now()
                
                output_file = Path(output_dir) / "backtesting" / f"trades_{symbol}.parquet"
                output_file.parent.mkdir(parents=True, exist_ok=True)
                
                trades_df.to_parquet(output_file)
                logger.info(f"Saved {len(trades_df)} trades to {output_file}")
                
            # Save metrics
            metrics_df = pd.DataFrame([result.metrics])
            metrics_df['symbol'] = symbol
            metrics_df['timestamp'] = pd.Timestamp.now()
            
            output_file = Path(output_dir) / "backtesting" / f"metrics_{symbol}.parquet"
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            metrics_df.to_parquet(output_file)
            logger.info(f"Saved metrics to {output_file}")
            
            return str(output_file)
            
        except Exception as e:
            logger.error(f"Error saving backtest results: {e}")
            return ""
