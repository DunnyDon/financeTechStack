"""Backtesting Framework

Production-ready backtesting engine with Prefect and Dask integration.

Modules:
    strategies: Strategy base class and concrete implementations
    engine: Core backtesting engine with P&L tracking
    data_loader: Data loading from ParquetDB
    analyzer: Performance analysis and reporting
    metrics: Risk and performance metrics
"""

from .strategies import (
    BaseStrategy,
    Signal,
    MomentumStrategy,
    MeanReversionStrategy,
    SectorRotationStrategy,
    PortfolioBetaStrategy,
)
from .engine import BacktestEngine, Trade, PortfolioSnapshot, OrderType
from .data_loader import BacktestDataLoader
from .analyzer import BacktestAnalyzer
from .metrics import (
    calculate_sharpe_ratio,
    calculate_sortino_ratio,
    calculate_max_drawdown,
    calculate_calmar_ratio,
    calculate_information_ratio,
)

__all__ = [
    "BaseStrategy",
    "Signal",
    "MomentumStrategy",
    "MeanReversionStrategy",
    "SectorRotationStrategy",
    "PortfolioBetaStrategy",
    "BacktestEngine",
    "Trade",
    "PortfolioSnapshot",
    "OrderType",
    "BacktestDataLoader",
    "BacktestAnalyzer",
    "calculate_sharpe_ratio",
    "calculate_sortino_ratio",
    "calculate_max_drawdown",
    "calculate_calmar_ratio",
    "calculate_information_ratio",
]
