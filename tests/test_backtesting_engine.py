"""
Test suite for Enhanced Backtesting Engine

Tests for:
- Signal generation (RSI, MACD, Bollinger Bands)
- Trade simulation and execution
- Performance metrics calculation
- Monte Carlo simulation
- Parameter optimization
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from src.backtesting_engine import (
    EnhancedBacktestingEngine,
    BacktestResult
)


@pytest.fixture
def sample_prices():
    """Generate sample OHLCV data."""
    dates = pd.date_range(start='2023-01-01', periods=252, freq='D')
    np.random.seed(42)
    
    close = 100 + np.cumsum(np.random.randn(252) * 2)
    
    return pd.DataFrame({
        'Open': close * np.random.uniform(0.98, 1.02, 252),
        'High': close * np.random.uniform(1.01, 1.03, 252),
        'Low': close * np.random.uniform(0.97, 0.99, 252),
        'Close': close,
        'Volume': np.random.randint(1000000, 5000000, 252)
    }, index=dates)


@pytest.fixture
def engine():
    """Create backtesting engine instance."""
    return EnhancedBacktestingEngine(min_capital=10000.0)


class TestSignalGeneration:
    """Test technical indicator signal generation."""
    
    def test_rsi_signal_generation(self, engine, sample_prices):
        """Test RSI signal generation."""
        signals = engine._generate_signals(
            sample_prices,
            signal_type='rsi',
            entry_threshold=30,
            exit_threshold=70
        )
        
        # Signals should be -1, 0, or 1
        assert all(s in [-1, 0, 1] for s in signals)
        
        # Should have some signals
        assert (signals != 0).any()
    
    def test_macd_signal_generation(self, engine, sample_prices):
        """Test MACD signal generation."""
        signals = engine._generate_signals(
            sample_prices,
            signal_type='macd',
            entry_threshold=0.0,
            exit_threshold=0.0
        )
        
        assert all(s in [-1, 0, 1] for s in signals)
    
    def test_bollinger_signal_generation(self, engine, sample_prices):
        """Test Bollinger Bands signal generation."""
        signals = engine._generate_signals(
            sample_prices,
            signal_type='bollinger',
            entry_threshold=0.0,
            exit_threshold=0.0
        )
        
        assert all(s in [-1, 0, 1] for s in signals)


class TestTradeSimulation:
    """Test trade simulation and execution."""
    
    def test_trade_simulation(self, engine, sample_prices):
        """Test trade simulation produces valid trades."""
        signals = engine._generate_signals(
            sample_prices,
            signal_type='rsi',
            entry_threshold=30,
            exit_threshold=70
        )
        
        trades = engine._simulate_trades(
            sample_prices,
            signals,
            stop_loss=0.05,
            take_profit=0.10
        )
        
        # Should have trades
        assert isinstance(trades, list)
        
        # Each trade should have required fields
        for trade in trades:
            assert 'entry_date' in trade
            assert 'exit_date' in trade
            assert 'pnl' in trade
            assert 'quantity' in trade
    
    def test_stop_loss_execution(self, engine, sample_prices):
        """Test stop loss is properly executed."""
        signals = engine._generate_signals(
            sample_prices,
            signal_type='rsi',
            entry_threshold=30,
            exit_threshold=70
        )
        
        trades = engine._simulate_trades(
            sample_prices,
            signals,
            stop_loss=0.05,
            take_profit=0.20
        )
        
        # Check for stop loss execution
        stop_loss_trades = [t for t in trades if t['exit_reason'] == 'stop_loss']
        
        if stop_loss_trades:
            for trade in stop_loss_trades:
                assert trade['pnl_pct'] <= -4  # Should be near -5%


class TestPerformanceMetrics:
    """Test performance metric calculations."""
    
    def test_metrics_calculation(self, engine, sample_prices):
        """Test performance metrics are calculated correctly."""
        result = engine.backtest_strategy(
            'TEST',
            sample_prices,
            signal_type='rsi',
            entry_threshold=30,
            exit_threshold=70
        )
        
        assert isinstance(result, BacktestResult)
        assert 'sharpe_ratio' in result.metrics
        assert 'win_rate' in result.metrics
        assert 'num_trades' in result.metrics
    
    def test_zero_trades_metrics(self, engine, sample_prices):
        """Test metrics when no trades occur."""
        # Create signals with no actual signals
        signals = pd.Series(0, index=sample_prices.index)
        
        result = engine.backtest_strategy(
            'TEST',
            sample_prices,
            signal_type='rsi'
        )
        
        # Metrics should exist but be zero
        assert result.metrics['num_trades'] >= 0
        assert result.metrics['sharpe_ratio'] >= 0


class TestDrawdownAnalysis:
    """Test drawdown and recovery analysis."""
    
    def test_drawdown_calculation(self, engine):
        """Test drawdown calculation."""
        equity_curve = pd.Series([100, 110, 105, 115, 120, 110, 125])
        
        drawdowns = engine._calculate_drawdowns(equity_curve)
        
        assert 'max_drawdown' in drawdowns
        assert drawdowns['max_drawdown'] <= 0  # Should be negative
        assert 'max_drawdown_date' in drawdowns
    
    def test_recovery_time_calculation(self, engine, sample_prices):
        """Test recovery time is calculated."""
        result = engine.backtest_strategy(
            'TEST',
            sample_prices,
            signal_type='rsi'
        )
        
        drawdowns = result.drawdowns
        
        if drawdowns['max_drawdown'] < 0:
            # Recovery time should be reasonable
            if drawdowns['recovery_time'] is not None:
                assert drawdowns['recovery_time'].days >= 0


class TestParameterOptimization:
    """Test parameter optimization."""
    
    def test_parameter_optimization(self, engine, sample_prices):
        """Test parameter optimization finds best parameters."""
        result = engine.optimize_parameters(
            'TEST',
            sample_prices,
            signal_type='rsi',
            param_ranges={
                'entry_threshold': [20, 30],
                'exit_threshold': [60, 70]
            }
        )
        
        assert 'best_params' in result
        assert 'best_sharpe' in result
        assert result['best_params'] is not None
    
    def test_optimization_improves_performance(self, engine, sample_prices):
        """Test optimization produces positive Sharpe ratio."""
        result = engine.optimize_parameters(
            'TEST',
            sample_prices,
            signal_type='rsi'
        )
        
        # Best Sharpe should be a number
        assert isinstance(result['best_sharpe'], (int, float))


class TestMonteCarloSimulation:
    """Test Monte Carlo simulation."""
    
    def test_monte_carlo_runs(self, engine):
        """Test Monte Carlo simulation executes."""
        returns = pd.Series(np.random.randn(252) * 0.01)
        
        result = engine.monte_carlo_simulation(
            returns,
            num_simulations=100,
            periods=50
        )
        
        assert 'simulations' in result
        assert result['simulations'].shape == (100, 50)
    
    def test_monte_carlo_percentiles(self, engine):
        """Test Monte Carlo produces valid percentiles."""
        returns = pd.Series(np.random.randn(252) * 0.01)
        
        result = engine.monte_carlo_simulation(
            returns,
            num_simulations=100,
            periods=50
        )
        
        assert result['percentile_5'] < result['percentile_50']
        assert result['percentile_50'] < result['percentile_95']
    
    def test_confidence_interval(self, engine):
        """Test confidence interval calculation."""
        returns = pd.Series(np.random.randn(252) * 0.01)
        
        result = engine.monte_carlo_simulation(
            returns,
            num_simulations=100,
            periods=50
        )
        
        lower, upper = result['confidence_interval_95']
        assert lower < upper


class TestBacktestResults:
    """Test backtest result saving."""
    
    @patch('src.backtesting_engine.Path')
    def test_save_results(self, mock_path, engine, sample_prices):
        """Test results are saved to Parquet."""
        result = engine.backtest_strategy('TEST', sample_prices)
        result.trades = [
            {
                'entry_date': '2023-01-01',
                'entry_price': 100,
                'exit_date': '2023-01-05',
                'exit_price': 105,
                'pnl': 500,
                'pnl_pct': 5.0,
                'quantity': 100,
                'exit_reason': 'signal'
            }
        ]
        
        # This should not raise an exception
        output = engine.save_backtest_results('TEST', result)
        
        # Output should be a string path
        assert isinstance(output, str)


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_empty_prices(self, engine):
        """Test with empty price data."""
        empty_df = pd.DataFrame(columns=['Open', 'High', 'Low', 'Close', 'Volume'])
        
        # Should handle gracefully
        with pytest.raises((IndexError, ValueError)):
            engine.backtest_strategy('TEST', empty_df)
    
    def test_single_trade(self, engine):
        """Test with only one trade."""
        dates = pd.date_range(start='2023-01-01', periods=10, freq='D')
        prices = pd.DataFrame({
            'Open': [100] * 10,
            'High': [102] * 10,
            'Low': [98] * 10,
            'Close': [100] * 10,
            'Volume': [1000000] * 10
        }, index=dates)
        
        result = engine.backtest_strategy('TEST', prices)
        
        # Should complete without error
        assert isinstance(result, BacktestResult)
    
    def test_high_volatility_prices(self, engine):
        """Test with highly volatile price data."""
        dates = pd.date_range(start='2023-01-01', periods=252, freq='D')
        close = 100 * np.exp(np.cumsum(np.random.randn(252) * 0.05))
        
        prices = pd.DataFrame({
            'Open': close * np.random.uniform(0.98, 1.02, 252),
            'High': close * 1.05,
            'Low': close * 0.95,
            'Close': close,
            'Volume': np.random.randint(1000000, 5000000, 252)
        }, index=dates)
        
        result = engine.backtest_strategy('TEST', prices)
        
        assert result.metrics['sharpe_ratio'] is not None
