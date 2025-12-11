"""
Backtesting Framework Examples

This file demonstrates various usage patterns for the backtesting framework.
Run these examples to validate your backtesting setup.
"""

import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List

# Example 1: Simple Single Strategy Backtest
def example_single_backtest():
    """Run a single momentum strategy backtest."""
    print("\n" + "="*60)
    print("EXAMPLE 1: Single Strategy Backtest (Momentum)")
    print("="*60)
    
    from src.backtesting.engine import BacktestEngine
    from src.backtesting.strategies import MomentumStrategy
    from src.backtesting.data_loader import BacktestDataLoader
    from src.backtesting.analyzer import BacktestAnalyzer

    # Load data
    loader = BacktestDataLoader()
    symbols = ["AAPL", "MSFT", "GOOGL"]
    prices_df, technical_df, _ = loader.load_backtest_data(
        symbols=symbols,
        start_date="2024-01-01",
        end_date="2024-12-31"
    )
    
    # Load holdings
    holdings_df = pd.DataFrame({
        "sym": symbols,
        "sector": ["Tech", "Tech", "Tech"]
    })
    
    # Create strategy and engine
    strategy = MomentumStrategy(lookback=20, threshold=0.10)
    engine = BacktestEngine(
        initial_capital=100000.0,
        start_date=pd.to_datetime(prices_df.index.min()),
        end_date=pd.to_datetime(prices_df.index.max()),
        commission_pct=0.001,
        slippage_bps=5.0
    )
    
    # Run backtest
    results = engine.run(
        strategies=[strategy],
        prices_df=prices_df,
        technical_df=technical_df,
        holdings_df=holdings_df
    )
    
    # Analyze results
    analyzer = BacktestAnalyzer(results)
    print(analyzer.summary())
    print("\nBest Trades:")
    print(analyzer.best_trades(n=3))


# Example 2: Multiple Strategies in Parallel
def example_multiple_strategies():
    """Run multiple strategies and compare results."""
    print("\n" + "="*60)
    print("EXAMPLE 2: Multiple Strategies in Parallel")
    print("="*60)
    
    from src.backtesting.engine import BacktestEngine
    from src.backtesting.strategies import (
        MomentumStrategy,
        MeanReversionStrategy,
        SectorRotationStrategy
    )
    from src.backtesting.data_loader import BacktestDataLoader
    
    # Load data once
    loader = BacktestDataLoader()
    symbols = ["AAPL", "MSFT", "GOOGL", "TSLA", "META"]
    prices_df, technical_df, _ = loader.load_backtest_data(
        symbols=symbols,
        start_date="2024-01-01",
        end_date="2024-12-31"
    )
    
    holdings_df = pd.DataFrame({
        "sym": symbols,
        "sector": ["Tech", "Tech", "Tech", "Auto", "Tech"]
    })
    
    # Define strategies
    strategies = [
        MomentumStrategy(lookback=20, threshold=0.10),
        MeanReversionStrategy(lookback=20, z_threshold=2.0),
        SectorRotationStrategy(lookback=60)
    ]
    
    # Run each strategy
    results_summary = {}
    engine = BacktestEngine(
        initial_capital=100000.0,
        start_date=pd.to_datetime(prices_df.index.min()),
        end_date=pd.to_datetime(prices_df.index.max()),
    )
    
    for strategy in strategies:
        results = engine.run(
            strategies=[strategy],
            prices_df=prices_df,
            technical_df=technical_df,
            holdings_df=holdings_df
        )
        
        metrics = results["metrics"]
        results_summary[strategy.name] = {
            "Total Return": f"{metrics['total_return_pct']:.2f}%",
            "Sharpe Ratio": f"{metrics['sharpe_ratio']:.2f}",
            "Max Drawdown": f"{metrics['max_drawdown_pct']:.2f}%",
            "Win Rate": f"{metrics['win_rate_pct']:.2f}%",
            "Total Trades": metrics["total_trades"],
        }
    
    # Print comparison
    print("\nStrategy Comparison:")
    comparison_df = pd.DataFrame(results_summary).T
    print(comparison_df)


# Example 3: Parameter Optimization with Prefect
def example_parameter_optimization_prefect():
    """Run parameter optimization using Prefect."""
    print("\n" + "="*60)
    print("EXAMPLE 3: Parameter Optimization (Prefect)")
    print("="*60)
    
    from src.backtesting.backtesting_flows import backtest_multiple_strategies_flow
    
    symbols = ["AAPL", "MSFT", "GOOGL"]
    
    # Define strategies with different parameters
    strategies = {
        "momentum_10": {"lookback": 10, "threshold": 0.05},
        "momentum_20": {"lookback": 20, "threshold": 0.10},
        "momentum_30": {"lookback": 30, "threshold": 0.15},
    }
    
    # Run with Prefect
    results = backtest_multiple_strategies_flow(
        symbols=symbols,
        strategies=strategies,
        start_date="2024-01-01",
        end_date="2024-12-31"
    )
    
    print(f"\nCompleted {len(results)} backtests")
    for strategy_name, result in results.items():
        metrics = result["metrics"]
        print(f"\n{strategy_name}:")
        print(f"  Return: {metrics['total_return_pct']:.2f}%")
        print(f"  Sharpe: {metrics['sharpe_ratio']:.2f}")


# Example 4: Grid Search Parameter Optimization with Dask
def example_grid_search_dask():
    """Run parameter grid search using Dask."""
    print("\n" + "="*60)
    print("EXAMPLE 4: Grid Search with Dask Parallelization")
    print("="*60)
    
    from src.backtesting.dask_backtesting_flows import parameter_optimization_flow
    
    symbols = ["AAPL", "MSFT", "GOOGL"]
    
    # Define parameter grid
    param_grid = {
        "lookback": [10, 15, 20, 25, 30],
        "threshold": [0.05, 0.10, 0.15, 0.20],
    }
    
    # Run optimization
    optimal_params, results_df = parameter_optimization_flow(
        symbols=symbols,
        strategy_name="momentum",
        param_grid=param_grid,
        start_date="2024-01-01",
        end_date="2024-12-31",
        optimization_metric="sharpe_ratio"
    )
    
    print(f"\nTested {len(results_df)} parameter combinations")
    print(f"\nOptimal Parameters:")
    for param, value in optimal_params.items():
        print(f"  {param}: {value}")
    
    print(f"\nTop 5 Results:")
    print(results_df[["lookback", "threshold", "total_return_pct", "sharpe_ratio"]].head())


# Example 5: Walk-Forward Validation with Dask
def example_walk_forward_validation():
    """Run walk-forward validation."""
    print("\n" + "="*60)
    print("EXAMPLE 5: Walk-Forward Validation")
    print("="*60)
    
    from src.backtesting.dask_backtesting_flows import walk_forward_validation_flow
    
    symbols = ["AAPL", "MSFT", "GOOGL"]
    
    # Run walk-forward validation
    results_df = walk_forward_validation_flow(
        symbols=symbols,
        strategy_name="momentum",
        strategy_params={"lookback": 20, "threshold": 0.10},
        total_days=365,
        train_days=252,
        test_days=30,
        start_date="2024-01-01"
    )
    
    print(f"\nCompleted {len(results_df)} walk-forward periods")
    print(f"\nAverage Metrics:")
    print(f"  Return: {results_df['total_return_pct'].mean():.2f}%")
    print(f"  Sharpe: {results_df['sharpe_ratio'].mean():.2f}")
    print(f"  Max DD: {results_df['max_drawdown_pct'].mean():.2f}%")
    
    print(f"\nPeriod-by-Period Results:")
    print(results_df[["window", "total_return_pct", "sharpe_ratio", "max_drawdown_pct"]])


# Example 6: Combining Multiple Strategies
def example_ensemble_strategy():
    """Run multiple strategies together."""
    print("\n" + "="*60)
    print("EXAMPLE 6: Ensemble Strategy (Multiple Strategies Together)")
    print("="*60)
    
    from src.backtesting.engine import BacktestEngine
    from src.backtesting.strategies import (
        MomentumStrategy,
        MeanReversionStrategy,
        SectorRotationStrategy
    )
    from src.backtesting.data_loader import BacktestDataLoader
    from src.backtesting.analyzer import BacktestAnalyzer
    
    # Load data
    loader = BacktestDataLoader()
    symbols = ["AAPL", "MSFT", "GOOGL", "TSLA", "META"]
    prices_df, technical_df, _ = loader.load_backtest_data(
        symbols=symbols,
        start_date="2024-01-01",
        end_date="2024-12-31"
    )
    
    holdings_df = pd.DataFrame({
        "sym": symbols,
        "sector": ["Tech", "Tech", "Tech", "Auto", "Tech"]
    })
    
    # Create multiple strategies to run together
    strategies = [
        MomentumStrategy(lookback=20, threshold=0.10),
        MeanReversionStrategy(lookback=20, z_threshold=2.0),
        SectorRotationStrategy(lookback=60)
    ]
    
    # Run all strategies together
    engine = BacktestEngine(
        initial_capital=100000.0,
        start_date=pd.to_datetime(prices_df.index.min()),
        end_date=pd.to_datetime(prices_df.index.max()),
        name="ensemble"
    )
    
    results = engine.run(
        strategies=strategies,
        prices_df=prices_df,
        technical_df=technical_df,
        holdings_df=holdings_df
    )
    
    # Analyze combined results
    analyzer = BacktestAnalyzer(results)
    print(analyzer.summary())
    
    print("\nTrades by Signal Type:")
    print(analyzer.by_signal_type())


# Example 7: Risk Analysis
def example_risk_analysis():
    """Detailed risk analysis of backtest results."""
    print("\n" + "="*60)
    print("EXAMPLE 7: Risk Analysis")
    print("="*60)
    
    from src.backtesting.engine import BacktestEngine
    from src.backtesting.strategies import MomentumStrategy
    from src.backtesting.data_loader import BacktestDataLoader
    from src.backtesting.analyzer import BacktestAnalyzer
    
    # Load data and run backtest
    loader = BacktestDataLoader()
    symbols = ["AAPL", "MSFT", "GOOGL"]
    prices_df, technical_df, _ = loader.load_backtest_data(
        symbols=symbols,
        start_date="2024-01-01",
        end_date="2024-12-31"
    )
    
    holdings_df = pd.DataFrame({
        "sym": symbols,
        "sector": ["Tech", "Tech", "Tech"]
    })
    
    strategy = MomentumStrategy(lookback=20, threshold=0.10)
    engine = BacktestEngine(
        initial_capital=100000.0,
        start_date=pd.to_datetime(prices_df.index.min()),
        end_date=pd.to_datetime(prices_df.index.max()),
    )
    
    results = engine.run(
        strategies=[strategy],
        prices_df=prices_df,
        technical_df=technical_df,
        holdings_df=holdings_df
    )
    
    # Risk analysis
    analyzer = BacktestAnalyzer(results)
    
    print("\nRisk Metrics:")
    risk = analyzer.risk_analysis()
    for metric, value in risk.items():
        if isinstance(value, float):
            print(f"  {metric}: {value:.4f}")
        else:
            print(f"  {metric}: {value}")
    
    print("\nConsecutive Streaks:")
    streaks = analyzer.consecutive_wins_losses()
    print(f"  Max Consecutive Wins: {streaks['max_consecutive_wins']}")
    print(f"  Max Consecutive Losses: {streaks['max_consecutive_losses']}")
    
    print("\nMonthly Returns:")
    monthly = analyzer.monthly_returns()
    if not monthly.empty:
        print(monthly.describe())


if __name__ == "__main__":
    """Run all examples."""
    import sys
    
    examples = [
        ("1", example_single_backtest),
        ("2", example_multiple_strategies),
        ("3", example_parameter_optimization_prefect),
        ("4", example_grid_search_dask),
        ("5", example_walk_forward_validation),
        ("6", example_ensemble_strategy),
        ("7", example_risk_analysis),
    ]
    
    if len(sys.argv) > 1:
        example_num = sys.argv[1]
        for num, func in examples:
            if num == example_num:
                func()
                break
    else:
        print("Backtesting Framework Examples")
        print("\nUsage: python examples_backtesting.py <example_number>")
        print("\nAvailable examples:")
        for num, func in examples:
            print(f"  {num}: {func.__doc__.strip().split(chr(10))[0]}")
