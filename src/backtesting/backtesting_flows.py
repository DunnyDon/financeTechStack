"""Prefect workflows for backtesting with Dask parallelization."""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pandas as pd
import logging

from prefect import flow, task, get_run_logger
from prefect.futures import PrefectFuture

from .engine import BacktestEngine
from .strategies import (
    MomentumStrategy,
    MeanReversionStrategy,
    SectorRotationStrategy,
    PortfolioBetaStrategy,
)
from .data_loader import BacktestDataLoader
from .analyzer import BacktestAnalyzer
from ..parquet_db import ParquetDB

logger = logging.getLogger(__name__)


@task(name="load_backtest_data")
def load_backtest_data_task(
    symbols: List[str],
    start_date: str,
    end_date: str,
    resample_freq: str = "D",
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Load historical data for backtesting.

    Args:
        symbols: List of ticker symbols
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        resample_freq: Frequency for resampling

    Returns:
        Tuple of (prices_df, technical_df, fundamental_df)
    """
    task_logger = get_run_logger()
    task_logger.info(f"Loading data for {len(symbols)} symbols...")

    loader = BacktestDataLoader()
    prices_df, technical_df, fundamental_df = loader.load_backtest_data(
        symbols=symbols,
        start_date=start_date,
        end_date=end_date,
        resample_freq=resample_freq,
    )

    task_logger.info(
        f"Loaded {len(prices_df)} price records, "
        f"{len(technical_df)} technical records"
    )

    return prices_df, technical_df, fundamental_df


@task(name="load_holdings")
def load_holdings_task(holdings_file: str = "holdings.csv") -> pd.DataFrame:
    """
    Load portfolio holdings.

    Args:
        holdings_file: Path to holdings CSV file

    Returns:
        Holdings DataFrame
    """
    task_logger = get_run_logger()
    loader = BacktestDataLoader()
    holdings = loader.load_holdings(holdings_file)
    task_logger.info(f"Loaded {len(holdings)} holdings")

    return holdings


@task(name="run_single_backtest")
def run_single_backtest_task(
    strategy_name: str,
    strategy_params: Dict,
    prices_df: pd.DataFrame,
    technical_df: pd.DataFrame,
    holdings_df: pd.DataFrame,
    initial_capital: float = 100000.0,
    commission_pct: float = 0.001,
    slippage_bps: float = 5.0,
) -> Dict:
    """
    Run single strategy backtest.

    Args:
        strategy_name: Name of strategy ("momentum", "mean_reversion", etc.)
        strategy_params: Strategy parameters dictionary
        prices_df: Historical prices
        technical_df: Technical indicators
        holdings_df: Portfolio holdings
        initial_capital: Starting capital
        commission_pct: Commission percentage
        slippage_bps: Slippage in basis points

    Returns:
        Backtest results dictionary
    """
    task_logger = get_run_logger()

    # Create strategy
    if strategy_name == "momentum":
        strategy = MomentumStrategy(**strategy_params)
    elif strategy_name == "mean_reversion":
        strategy = MeanReversionStrategy(**strategy_params)
    elif strategy_name == "sector_rotation":
        strategy = SectorRotationStrategy(**strategy_params)
    elif strategy_name == "portfolio_beta":
        strategy = PortfolioBetaStrategy(**strategy_params)
    else:
        raise ValueError(f"Unknown strategy: {strategy_name}")

    # Run engine
    engine = BacktestEngine(
        initial_capital=initial_capital,
        start_date=pd.to_datetime(prices_df.index.min()),
        end_date=pd.to_datetime(prices_df.index.max()),
        commission_pct=commission_pct,
        slippage_bps=slippage_bps,
    )

    task_logger.info(f"Running {strategy_name} backtest with params: {strategy_params}")

    results = engine.run(
        strategies=[strategy],
        prices_df=prices_df,
        technical_df=technical_df,
        holdings_df=holdings_df,
    )

    task_logger.info(
        f"Backtest complete. Return: {results['metrics']['total_return_pct']:.2f}%, "
        f"Sharpe: {results['metrics']['sharpe_ratio']:.2f}"
    )

    return {
        "strategy": strategy_name,
        "parameters": strategy_params,
        "results": results,
    }


@task(name="save_backtest_results")
def save_backtest_results_task(
    backtest_data: Dict,
    run_id: str,
) -> str:
    """
    Save backtest results to ParquetDB.

    Args:
        backtest_data: Backtest results dictionary
        run_id: Unique run identifier

    Returns:
        Run ID
    """
    task_logger = get_run_logger()

    db = ParquetDB()
    strategy_name = backtest_data["strategy"]
    results = backtest_data["results"]
    metrics = results["metrics"]

    # Create metadata
    run_metadata = pd.DataFrame(
        [
            {
                "run_id": run_id,
                "strategy": strategy_name,
                "timestamp": datetime.now(),
                "initial_capital": results["parameters"]["initial_capital"],
                "total_return_pct": metrics["total_return_pct"],
                "annual_return_pct": metrics["annual_return_pct"],
                "annual_volatility_pct": metrics["annual_volatility_pct"],
                "sharpe_ratio": metrics["sharpe_ratio"],
                "sortino_ratio": metrics["sortino_ratio"],
                "max_drawdown_pct": metrics["max_drawdown_pct"],
                "win_rate_pct": metrics["win_rate_pct"],
                "profit_factor": metrics["profit_factor"],
                "total_trades": metrics["total_trades"],
            }
        ]
    )

    # Save trades if available
    if results["trades"]:
        trades_list = []
        for trade in results["trades"]:
            trades_list.append(
                {
                    "run_id": run_id,
                    "trade_id": trade.trade_id,
                    "symbol": trade.symbol,
                    "entry_date": trade.entry_date,
                    "exit_date": trade.exit_date,
                    "entry_price": trade.entry_price,
                    "exit_price": trade.exit_price,
                    "quantity": trade.quantity,
                    "pnl": trade.pnl,
                    "pnl_pct": trade.pnl_pct,
                    "signal_type": trade.signal_type,
                    "bars_held": trade.bars_held,
                }
            )

        trades_df = pd.DataFrame(trades_list)
        # TODO: Save to ParquetDB backtest_trades table
        task_logger.info(f"Saved {len(trades_df)} trades")

    # Save portfolio snapshots
    if results["portfolio_history"]:
        portfolio_list = []
        for snapshot in results["portfolio_history"]:
            portfolio_list.append(
                {
                    "run_id": run_id,
                    "date": snapshot.date,
                    "total_value": snapshot.total_value,
                    "cash": snapshot.cash,
                    "leverage": snapshot.leverage,
                    "num_positions": snapshot.num_positions,
                    "concentration": snapshot.concentration,
                    "daily_return_pct": snapshot.daily_return,
                    "cumulative_return_pct": snapshot.cumulative_return,
                }
            )

        portfolio_df = pd.DataFrame(portfolio_list)
        # TODO: Save to ParquetDB backtest_metrics table
        task_logger.info(f"Saved {len(portfolio_df)} portfolio snapshots")

    task_logger.info(f"Backtest results saved with run_id: {run_id}")

    return run_id


@flow(name="backtest_single_strategy")
def backtest_single_strategy_flow(
    symbols: List[str],
    strategy_name: str,
    strategy_params: Dict,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    holdings_file: str = "holdings.csv",
    save_results: bool = True,
) -> Dict:
    """
    Backtest a single strategy.

    Args:
        symbols: List of ticker symbols
        strategy_name: Strategy name
        strategy_params: Strategy parameters
        start_date: Start date (default: 1 year ago)
        end_date: End date (default: today)
        holdings_file: Path to holdings file
        save_results: Whether to save results

    Returns:
        Backtest results
    """
    # Default dates
    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")
    if start_date is None:
        start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")

    # Load data and holdings
    prices_df, technical_df, fundamental_df = load_backtest_data_task(
        symbols=symbols,
        start_date=start_date,
        end_date=end_date,
    )

    holdings_df = load_holdings_task(holdings_file)

    # Run backtest
    backtest_result = run_single_backtest_task(
        strategy_name=strategy_name,
        strategy_params=strategy_params,
        prices_df=prices_df,
        technical_df=technical_df,
        holdings_df=holdings_df,
    )

    # Save results
    if save_results:
        run_id = f"backtest_{strategy_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        save_backtest_results_task(backtest_result, run_id)

    return backtest_result["results"]


@flow(name="backtest_multiple_strategies")
def backtest_multiple_strategies_flow(
    symbols: List[str],
    strategies: Dict[str, Dict],
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    holdings_file: str = "holdings.csv",
    save_results: bool = True,
) -> Dict[str, Dict]:
    """
    Backtest multiple strategies in parallel.

    Args:
        symbols: List of ticker symbols
        strategies: Dict of {strategy_name: parameters}
        start_date: Start date
        end_date: End date
        holdings_file: Path to holdings file
        save_results: Whether to save results

    Returns:
        Dictionary of results by strategy name
    """
    # Load data and holdings once
    prices_df, technical_df, fundamental_df = load_backtest_data_task(
        symbols=symbols,
        start_date=start_date or (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d"),
        end_date=end_date or datetime.now().strftime("%Y-%m-%d"),
    )

    holdings_df = load_holdings_task(holdings_file)

    # Run backtests in parallel
    backtest_futures = {}
    for strategy_name, strategy_params in strategies.items():
        future = run_single_backtest_task.submit(
            strategy_name=strategy_name,
            strategy_params=strategy_params,
            prices_df=prices_df,
            technical_df=technical_df,
            holdings_df=holdings_df,
        )
        backtest_futures[strategy_name] = future

    # Collect results
    results = {}
    for strategy_name, future in backtest_futures.items():
        backtest_data = future.result()
        results[strategy_name] = backtest_data["results"]

        # Save results
        if save_results:
            run_id = f"backtest_{strategy_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            save_backtest_results_task(backtest_data, run_id)

    return results
