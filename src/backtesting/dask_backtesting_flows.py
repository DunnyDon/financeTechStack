"""Dask-integrated backtesting workflows for distributed processing."""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np
import logging
from itertools import product

from prefect import flow, task, get_run_logger
from dask.distributed import Client
import dask.dataframe as dd

from .engine import BacktestEngine
from .strategies import (
    MomentumStrategy,
    MeanReversionStrategy,
    SectorRotationStrategy,
    PortfolioBetaStrategy,
)
from .data_loader import BacktestDataLoader
from ..dask_integration import DaskClientManager

logger = logging.getLogger(__name__)


@task(name="backtest_with_dask_client")
def backtest_with_dask_client(
    strategy_name: str,
    params: Dict,
    prices_df: pd.DataFrame,
    technical_df: pd.DataFrame,
    holdings_df: pd.DataFrame,
    client: Client,
) -> Dict:
    """
    Run single backtest using Dask client.

    Args:
        strategy_name: Name of strategy
        params: Strategy parameters
        prices_df: Historical prices
        technical_df: Technical indicators
        holdings_df: Holdings
        client: Dask client instance

    Returns:
        Backtest results
    """
    task_logger = get_run_logger()

    # Create strategy
    strategy_class_map = {
        "momentum": MomentumStrategy,
        "mean_reversion": MeanReversionStrategy,
        "sector_rotation": SectorRotationStrategy,
        "portfolio_beta": PortfolioBetaStrategy,
    }

    if strategy_name not in strategy_class_map:
        raise ValueError(f"Unknown strategy: {strategy_name}")

    strategy = strategy_class_map[strategy_name](**params)

    # Run backtest
    engine = BacktestEngine(
        initial_capital=100000.0,
        start_date=pd.to_datetime(prices_df.index.min()),
        end_date=pd.to_datetime(prices_df.index.max()),
        commission_pct=0.001,
        slippage_bps=5.0,
        name=f"{strategy_name}_{str(params).replace(' ', '')}",
    )

    task_logger.info(f"Running {strategy_name} with params: {params}")

    results = engine.run(
        strategies=[strategy],
        prices_df=prices_df,
        technical_df=technical_df,
        holdings_df=holdings_df,
    )

    return {
        "strategy": strategy_name,
        "parameters": params,
        "metrics": results["metrics"],
        "total_trades": len(results["trades"]),
    }


@task(name="parameter_grid_search")
def parameter_grid_search_task(
    strategy_name: str,
    param_grid: Dict[str, List],
    prices_df: pd.DataFrame,
    technical_df: pd.DataFrame,
    holdings_df: pd.DataFrame,
    scheduler_address: str = "tcp://localhost:8786",
) -> List[Dict]:
    """
    Perform grid search over strategy parameters using Dask.

    Args:
        strategy_name: Name of strategy
        param_grid: Dict of {param_name: [values]}
        prices_df: Historical prices
        technical_df: Technical indicators
        holdings_df: Holdings
        scheduler_address: Dask scheduler address

    Returns:
        List of results for each parameter combination
    """
    task_logger = get_run_logger()

    try:
        client = DaskClientManager.get_client(scheduler_address)
    except Exception as e:
        task_logger.warning(f"Dask unavailable, running locally: {e}")
        client = None

    # Generate parameter combinations
    param_names = list(param_grid.keys())
    param_values = [param_grid[name] for name in param_names]
    combinations = list(product(*param_values))

    task_logger.info(
        f"Running {len(combinations)} parameter combinations for {strategy_name}"
    )

    results = []

    if client:
        # Submit all jobs to Dask
        futures = []
        for combo in combinations:
            params = dict(zip(param_names, combo))

            future = client.submit(
                backtest_with_dask_client,
                strategy_name,
                params,
                prices_df,
                technical_df,
                holdings_df,
                client,
            )
            futures.append(future)

        # Collect results as they complete
        from dask.distributed import as_completed

        for future in as_completed(futures):
            try:
                result = future.result()
                results.append(result)
                task_logger.info(
                    f"Completed: {result['strategy']} {result['parameters']} "
                    f"-> Return: {result['metrics']['total_return_pct']:.2f}%"
                )
            except Exception as e:
                task_logger.error(f"Backtest failed: {e}")

    else:
        # Run locally
        for combo in combinations:
            params = dict(zip(param_names, combo))

            try:
                engine = BacktestEngine(
                    initial_capital=100000.0,
                    start_date=pd.to_datetime(prices_df.index.min()),
                    end_date=pd.to_datetime(prices_df.index.max()),
                )

                strategy_class_map = {
                    "momentum": MomentumStrategy,
                    "mean_reversion": MeanReversionStrategy,
                    "sector_rotation": SectorRotationStrategy,
                    "portfolio_beta": PortfolioBetaStrategy,
                }

                strategy = strategy_class_map[strategy_name](**params)

                result = engine.run(
                    strategies=[strategy],
                    prices_df=prices_df,
                    technical_df=technical_df,
                    holdings_df=holdings_df,
                )

                results.append(
                    {
                        "strategy": strategy_name,
                        "parameters": params,
                        "metrics": result["metrics"],
                        "total_trades": len(result["trades"]),
                    }
                )
            except Exception as e:
                task_logger.error(f"Backtest failed for params {params}: {e}")

    return results


@task(name="analyze_parameter_results")
def analyze_parameter_results_task(results: List[Dict]) -> pd.DataFrame:
    """
    Analyze parameter grid search results.

    Args:
        results: List of backtest results

    Returns:
        DataFrame of results sorted by Sharpe ratio
    """
    task_logger = get_run_logger()

    if not results:
        task_logger.warning("No results to analyze")
        return pd.DataFrame()

    # Convert to DataFrame
    data = []
    for result in results:
        row = {
            "strategy": result["strategy"],
            **result["parameters"],
            **result["metrics"],
        }
        data.append(row)

    df = pd.DataFrame(data)

    # Sort by Sharpe ratio
    if "sharpe_ratio" in df.columns:
        df = df.sort_values("sharpe_ratio", ascending=False)

    task_logger.info(f"Analyzed {len(df)} parameter combinations")

    return df


@task(name="find_optimal_parameters")
def find_optimal_parameters_task(
    results_df: pd.DataFrame, metric: str = "sharpe_ratio"
) -> Dict:
    """
    Find optimal parameters based on a metric.

    Args:
        results_df: Results DataFrame from grid search
        metric: Metric to optimize (default: sharpe_ratio)

    Returns:
        Dictionary of optimal parameters
    """
    task_logger = get_run_logger()

    if results_df.empty or metric not in results_df.columns:
        task_logger.warning(f"Cannot optimize on metric: {metric}")
        return {}

    # Find row with best metric value
    best_idx = results_df[metric].idxmax()
    best_result = results_df.loc[best_idx]

    task_logger.info(
        f"Optimal parameters (metric={metric}): "
        f"{best_result[metric]:.2f}"
    )

    # Extract parameters (everything except metrics)
    metric_cols = [
        "strategy",
        "total_return_pct",
        "annual_return_pct",
        "annual_volatility_pct",
        "sharpe_ratio",
        "sortino_ratio",
        "calmar_ratio",
        "max_drawdown_pct",
        "win_rate_pct",
        "profit_factor",
        "total_trades",
        "winning_trades",
        "losing_trades",
        "avg_bars_held",
        "avg_win_pnl",
        "avg_loss_pnl",
    ]

    optimal_params = {
        k: v
        for k, v in best_result.items()
        if k not in metric_cols and not pd.isna(v)
    }

    return optimal_params


@flow(name="parameter_optimization_flow")
def parameter_optimization_flow(
    symbols: List[str],
    strategy_name: str,
    param_grid: Dict[str, List],
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    holdings_file: str = "holdings.csv",
    optimization_metric: str = "sharpe_ratio",
) -> Tuple[Dict, pd.DataFrame]:
    """
    Run parameter optimization for a strategy using Dask parallelization.

    Args:
        symbols: List of ticker symbols
        strategy_name: Strategy name
        param_grid: Dict of {param_name: [values]} for grid search
        start_date: Start date
        end_date: End date
        holdings_file: Holdings file path
        optimization_metric: Metric to optimize on

    Returns:
        Tuple of (optimal_parameters, results_dataframe)
    """
    task_logger = get_run_logger()

    # Load data
    loader = BacktestDataLoader()
    prices_df, technical_df, _ = loader.load_backtest_data(
        symbols=symbols,
        start_date=start_date
        or (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d"),
        end_date=end_date or datetime.now().strftime("%Y-%m-%d"),
    )

    holdings_df = loader.load_holdings(holdings_file)

    task_logger.info(
        f"Starting parameter optimization for {strategy_name}. "
        f"Testing {len(list(product(*param_grid.values())))} combinations."
    )

    # Run grid search
    results = parameter_grid_search_task(
        strategy_name=strategy_name,
        param_grid=param_grid,
        prices_df=prices_df,
        technical_df=technical_df,
        holdings_df=holdings_df,
    )

    # Analyze results
    results_df = analyze_parameter_results_task(results)

    # Find optimal parameters
    optimal_params = find_optimal_parameters_task(
        results_df, metric=optimization_metric
    )

    return optimal_params, results_df


@flow(name="walk_forward_validation_flow")
def walk_forward_validation_flow(
    symbols: List[str],
    strategy_name: str,
    strategy_params: Dict,
    total_days: int = 365,
    train_days: int = 252,
    test_days: int = 30,
    start_date: Optional[str] = None,
    holdings_file: str = "holdings.csv",
) -> pd.DataFrame:
    """
    Run walk-forward validation for strategy.

    Args:
        symbols: List of ticker symbols
        strategy_name: Strategy name
        strategy_params: Strategy parameters
        total_days: Total period for validation
        train_days: Training window size
        test_days: Testing window size
        start_date: Start date
        holdings_file: Holdings file

    Returns:
        DataFrame with walk-forward results
    """
    task_logger = get_run_logger()

    loader = BacktestDataLoader()

    if start_date is None:
        start_date = (datetime.now() - timedelta(days=total_days)).strftime(
            "%Y-%m-%d"
        )

    end_date = datetime.now().strftime("%Y-%m-%d")

    # Load full data
    prices_df, technical_df, _ = loader.load_backtest_data(
        symbols=symbols,
        start_date=start_date,
        end_date=end_date,
    )

    holdings_df = loader.load_holdings(holdings_file)

    task_logger.info(f"Running walk-forward validation with windows: "
                     f"train={train_days}, test={test_days}")

    # Generate walk-forward windows
    unique_dates = sorted(prices_df.index.unique())
    windows = []

    for i in range(0, len(unique_dates) - train_days - test_days, test_days):
        train_end = unique_dates[i + train_days]
        test_start = unique_dates[i + train_days + 1]
        test_end = unique_dates[min(i + train_days + test_days, len(unique_dates) - 1)]

        windows.append(
            {
                "train_start": unique_dates[i],
                "train_end": train_end,
                "test_start": test_start,
                "test_end": test_end,
            }
        )

    task_logger.info(f"Generated {len(windows)} walk-forward windows")

    # Run backtests for each window
    wf_results = []

    for i, window in enumerate(windows):
        # Get data for this window
        window_prices = prices_df[
            (prices_df.index >= window["test_start"])
            & (prices_df.index <= window["test_end"])
        ]

        if window_prices.empty:
            continue

        engine = BacktestEngine(
            initial_capital=100000.0,
            start_date=window["test_start"],
            end_date=window["test_end"],
        )

        strategy_class_map = {
            "momentum": MomentumStrategy,
            "mean_reversion": MeanReversionStrategy,
            "sector_rotation": SectorRotationStrategy,
            "portfolio_beta": PortfolioBetaStrategy,
        }

        strategy = strategy_class_map[strategy_name](**strategy_params)

        result = engine.run(
            strategies=[strategy],
            prices_df=window_prices,
            technical_df=technical_df[
                (technical_df.index >= window["test_start"])
                & (technical_df.index <= window["test_end"])
            ],
            holdings_df=holdings_df,
        )

        wf_results.append(
            {
                "window": i,
                "test_start": window["test_start"],
                "test_end": window["test_end"],
                **result["metrics"],
            }
        )

    results_df = pd.DataFrame(wf_results)

    task_logger.info(
        f"Walk-forward complete. "
        f"Average return: {results_df['total_return_pct'].mean():.2f}%, "
        f"Avg Sharpe: {results_df['sharpe_ratio'].mean():.2f}"
    )

    return results_df
