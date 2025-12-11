#!/usr/bin/env python
"""Quick test to verify backtesting framework setup."""

import sys
import pandas as pd
from datetime import datetime

print("=" * 60)
print("BACKTESTING FRAMEWORK SETUP TEST")
print("=" * 60)

# Test 1: Import all modules
print("\n1. Testing imports...")
try:
    from src.backtesting.engine import BacktestEngine, Trade, PortfolioSnapshot
    from src.backtesting.strategies import (
        BaseStrategy, MomentumStrategy, MeanReversionStrategy,
        SectorRotationStrategy, PortfolioBetaStrategy, Signal
    )
    from src.backtesting.data_loader import BacktestDataLoader
    from src.backtesting.analyzer import BacktestAnalyzer
    from src.backtesting.metrics import (
        calculate_sharpe_ratio, calculate_sortino_ratio,
        calculate_max_drawdown, calculate_information_ratio
    )
    print("   ✓ All modules imported successfully")
except Exception as e:
    print(f"   ✗ Import failed: {e}")
    sys.exit(1)

# Test 2: Load data
print("\n2. Testing data loading...")
try:
    loader = BacktestDataLoader()
    prices_df, technical_df, fundamental_df = loader.load_backtest_data(
        symbols=["AAPL"],
        start_date="2024-01-01",
        end_date="2024-12-31"
    )
    
    if prices_df is None or prices_df.empty:
        print("   ⚠ No data returned (expected if prices not in DB)")
    else:
        print(f"   ✓ Loaded {len(prices_df)} price records")
except Exception as e:
    print(f"   ✗ Data loading failed: {e}")
    sys.exit(1)

# Test 3: Create strategy
print("\n3. Testing strategy creation...")
try:
    strategy = MomentumStrategy(lookback=20, threshold=0.10)
    print(f"   ✓ Created {strategy.name} strategy")
except Exception as e:
    print(f"   ✗ Strategy creation failed: {e}")
    sys.exit(1)

# Test 4: Create engine
print("\n4. Testing engine creation...")
try:
    engine = BacktestEngine(
        initial_capital=100000.0,
        commission_pct=0.001,
        slippage_bps=5.0
    )
    print("   ✓ Created BacktestEngine")
except Exception as e:
    print(f"   ✗ Engine creation failed: {e}")
    sys.exit(1)

# Test 5: Create sample trade
print("\n5. Testing trade creation...")
try:
    trade = Trade(
        trade_id="test_1",
        symbol="AAPL",
        entry_date=pd.Timestamp("2024-01-01"),
        entry_price=150.0,
        quantity=10.0,
        entry_value=1500.0,
        commission=1.5,
        slippage=2.0
    )
    print("   ✓ Created Trade object")
except Exception as e:
    print(f"   ✗ Trade creation failed: {e}")
    sys.exit(1)

# Test 6: Create analyzer
print("\n6. Testing analyzer...")
try:
    from src.backtesting.engine import BacktestEngine
    
    # Create minimal backtest result
    results = {
        "trades": [trade],
        "portfolio_history": [
            PortfolioSnapshot(
                date=pd.Timestamp("2024-01-01"),
                cash=98500.0,
                total_value=99500.0
            )
        ],
        "daily_returns": [0.0],
        "equity_curve": [100000.0, 99500.0],
        "metrics": {
            "sharpe_ratio": 0.0,
            "sortino_ratio": 0.0,
            "max_drawdown": 0.0,
            "total_return": -0.005,
        }
    }
    
    analyzer = BacktestAnalyzer(results)
    summary = analyzer.summary()
    print("   ✓ Created BacktestAnalyzer")
    print("\n   Sample summary output (first 200 chars):")
    print(f"   {summary[:200]}...")
except Exception as e:
    print(f"   ✗ Analyzer creation failed: {e}")
    sys.exit(1)

print("\n" + "=" * 60)
print("✓ ALL TESTS PASSED!")
print("=" * 60)
print("\nBacktesting framework is ready to use.")
print("\nRun examples with:")
print("  python examples/examples_backtesting.py 1  # Single strategy")
print("  python examples/examples_backtesting.py 2  # Multiple strategies")
print("  python examples/examples_backtesting.py 6  # Ensemble strategies")
print("\nSee docs/BACKTESTING_FRAMEWORK_GUIDE.md for full documentation.")
