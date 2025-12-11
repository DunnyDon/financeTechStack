#!/usr/bin/env python
"""Wrapper to run backtesting examples with proper path setup."""

import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Now import and run examples
from examples.examples_backtesting import (
    example_single_backtest,
    example_multiple_strategies,
    example_parameter_optimization_prefect,
    example_grid_search_dask,
    example_walk_forward_validation,
    example_ensemble_strategy,
    example_risk_analysis,
)

examples = [
    ("1", example_single_backtest),
    ("2", example_multiple_strategies),
    ("3", example_parameter_optimization_prefect),
    ("4", example_grid_search_dask),
    ("5", example_walk_forward_validation),
    ("6", example_ensemble_strategy),
    ("7", example_risk_analysis),
]

if __name__ == "__main__":
    if len(sys.argv) > 1:
        example_num = sys.argv[1]
        for num, func in examples:
            if num == example_num:
                func()
                break
        else:
            print(f"Example {example_num} not found")
    else:
        print("Backtesting Framework Examples")
        print("\nUsage: python run_examples.py <example_number>")
        print("\nAvailable examples:")
        for num, func in examples:
            doc = func.__doc__ or "No description"
            print(f"  {num}: {doc.strip()}")
