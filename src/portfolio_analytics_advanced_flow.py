"""
Portfolio Analytics Flow - Uses actual holdings from holdings.csv

Automatically runs all advanced analytics using your actual portfolio:
- Risk metrics
- Portfolio optimization
- Quick wins analytics
- Options analysis (if applicable)
- Fixed income analysis (if applicable)

Usage:
    uv run python -c "from src.portfolio_analytics_advanced_flow import portfolio_analytics_advanced; portfolio_analytics_advanced()"
    
Or with Prefect:
    uv run python src/portfolio_analytics_advanced_flow.py --serve
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Tuple
from pathlib import Path
import sys

from prefect import flow, task, get_run_logger

from src.portfolio_holdings import Holdings
from src.portfolio_prices import PriceFetcher
from src.portfolio_risk import RiskAnalytics
from src.portfolio_optimization import PortfolioOptimizer
from src.parquet_db import ParquetDB
from src.quick_wins_analytics import QuickWinsAnalytics
from src.advanced_analytics_flows import (
    fetch_historical_prices,
    calculate_risk_metrics,
    calculate_optimization_metrics,
    calculate_quick_wins,
    generate_advanced_report,
)


@task
def load_portfolio_data() -> Tuple[pd.DataFrame, Dict[str, float], List[str]]:
    """Load holdings and calculate portfolio weights."""
    logger = get_run_logger()
    logger.info("Loading portfolio from holdings.csv...")

    try:
        holdings = Holdings()
        holdings_df = holdings.all_holdings

        if holdings_df.empty:
            logger.warning("No holdings found")
            return pd.DataFrame(), {}, []

        logger.info(f"Loaded {len(holdings_df)} holdings")

        # Get current prices
        fetcher = PriceFetcher()
        tickers = holdings_df["sym"].unique().tolist()

        prices = {}
        for ticker in tickers:
            try:
                price_data = fetcher.fetch_price(ticker, asset_type="eq")
                if price_data is not None and len(price_data) > 0:
                    current_price = price_data["close"].iloc[-1]
                    prices[ticker] = current_price
                    logger.info(f"  {ticker}: ${current_price:.2f}")
            except Exception as e:
                logger.warning(f"  {ticker}: Could not fetch price - {e}")

        # Calculate portfolio value and weights
        holdings_df["current_price"] = holdings_df["sym"].map(prices)
        holdings_df["position_value"] = holdings_df["qty"] * holdings_df["current_price"]

        total_value = holdings_df["position_value"].sum()
        holdings_df["weight"] = holdings_df["position_value"] / total_value

        # Create weights dict
        weights = dict(zip(holdings_df["sym"], holdings_df["weight"]))

        # Create holdings dict with metadata
        holdings_dict = {}
        for _, row in holdings_df.iterrows():
            holdings_dict[row["sym"]] = {
                "quantity": row["qty"],
                "price": row["current_price"],
                "entry_price": row["bep"],
                "asset_class": "equity" if row["asset"] == "eq" else row["asset"],
                "sector": "Technology" if row["sym"] in ["AAPL", "MSFT", "TSLA"] else "Other",
            }

        logger.info(f"Portfolio value: ${total_value:,.2f}")
        logger.info(f"Holdings: {len(weights)}")

        return holdings_df, weights, list(weights.keys())

    except Exception as e:
        logger.error(f"Error loading portfolio: {e}")
        raise


@task
def calculate_portfolio_performance(holdings_df: pd.DataFrame) -> Dict:
    """Calculate portfolio performance metrics."""
    logger = get_run_logger()
    logger.info("Calculating portfolio performance...")

    performance = {}

    for _, row in holdings_df.iterrows():
        ticker = row["sym"]
        entry_price = row["bep"]
        current_price = row["current_price"]
        qty = row["qty"]

        pnl = (current_price - entry_price) * qty
        pnl_pct = ((current_price - entry_price) / entry_price * 100) if entry_price > 0 else 0

        performance[ticker] = {
            "entry_price": entry_price,
            "current_price": current_price,
            "pnl_pct": pnl_pct,
            "pnl_dollars": pnl,
            "quantity": qty,
            "position_value": current_price * qty,
        }

    return performance


@task
def generate_portfolio_report(
    holdings_df: pd.DataFrame,
    risk_metrics: Dict,
    optimization_metrics: Dict,
    quick_wins: Dict,
    performance: Dict,
    weights: Dict[str, float],
) -> str:
    """Generate comprehensive portfolio analytics report."""
    logger = get_run_logger()

    report = []
    report.append("=" * 90)
    report.append("YOUR PORTFOLIO - ADVANCED ANALYTICS REPORT")
    report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("=" * 90)

    # Portfolio Summary
    total_value = holdings_df["position_value"].sum()
    report.append(f"\n📊 PORTFOLIO SUMMARY")
    report.append("-" * 90)
    report.append(f"Total Value: ${total_value:,.2f}")
    report.append(f"Holdings: {len(holdings_df)}")
    report.append(f"Brokers: {holdings_df['brokerName'].nunique()}")

    # Performance
    total_pnl = sum(p["pnl_dollars"] for p in performance.values())
    total_pnl_pct = (total_pnl / (total_value - total_pnl)) * 100 if total_value > total_pnl else 0

    report.append(f"\n💰 PERFORMANCE")
    report.append("-" * 90)
    report.append(f"Total P&L: ${total_pnl:,.2f} ({total_pnl_pct:+.2f}%)")

    # Top performers
    sorted_perf = sorted(performance.items(), key=lambda x: x[1]["pnl_pct"], reverse=True)
    report.append(f"\nTop 3 Winners:")
    for ticker, perf in sorted_perf[:3]:
        report.append(f"  {ticker}: {perf['pnl_pct']:+.2f}% (${perf['pnl_dollars']:+,.2f})")

    report.append(f"\nTop 3 Losers:")
    for ticker, perf in sorted_perf[-3:]:
        report.append(f"  {ticker}: {perf['pnl_pct']:+.2f}% (${perf['pnl_dollars']:+,.2f})")

    # Risk Metrics
    report.append(f"\n📈 RISK ANALYSIS")
    report.append("-" * 90)
    if risk_metrics:
        report.append(f"Portfolio Volatility: {risk_metrics.get('portfolio_volatility', 0):.2f}%")
        report.append(f"Daily VaR (95%): {risk_metrics.get('var_95_daily', 0):.4f}")
        report.append(f"Daily VaR (99%): {risk_metrics.get('var_99_daily', 0):.4f}")
        report.append(f"Portfolio Beta: {risk_metrics.get('portfolio_beta', 0):.4f}")
        report.append(f"Concentration (HHI): {risk_metrics.get('concentration_hhi', 0):.4f}")
        report.append(f"Diversification Score: {risk_metrics.get('diversification_score', 0):.2f}")

        if risk_metrics.get("is_concentrated"):
            report.append("⚠️  Portfolio is CONCENTRATED - Consider diversifying")
        else:
            report.append("✓ Portfolio is well-diversified")

    # Optimization
    report.append(f"\n🎯 OPTIMIZATION RECOMMENDATIONS")
    report.append("-" * 90)
    if optimization_metrics and "max_sharpe_weights" in optimization_metrics:
        report.append("Current vs. Optimal (Max Sharpe Ratio):")
        for ticker in list(weights.keys())[:5]:  # Show top 5
            current = weights.get(ticker, 0) * 100
            optimal = optimization_metrics["max_sharpe_weights"].get(ticker, 0) * 100
            diff = optimal - current
            action = "INCREASE" if diff > 1 else "DECREASE" if diff < -1 else "HOLD"
            report.append(
                f"  {ticker}: {current:.1f}% → {optimal:.1f}% ({action} {abs(diff):+.1f}%)"
            )

    # Quick Wins
    report.append(f"\n⚡ QUICK INSIGHTS")
    report.append("-" * 90)
    if quick_wins:
        if "sector_allocation" in quick_wins:
            report.append("Sector Breakdown:")
            for sector, alloc in sorted(quick_wins["sector_allocation"].items(), key=lambda x: x[1], reverse=True):
                report.append(f"  {sector}: {alloc:.1f}%")

        if "sharpe_ratio" in quick_wins:
            report.append(f"\nSharpe Ratio: {quick_wins['sharpe_ratio']:.4f}")

        if "concentration_risk" in quick_wins:
            conc = quick_wins["concentration_risk"]
            report.append(f"\nTop Holdings:")
            report.append(f"  Largest: {conc.get('top_1_concentration', 0):.1f}%")
            report.append(f"  Top 3: {conc.get('top_3_concentration', 0):.1f}%")

    report.append("\n" + "=" * 90)
    report.append("END OF REPORT")
    report.append("=" * 90)

    report_text = "\n".join(report)
    logger.info(report_text)

    return report_text


@flow(name="portfolio_analytics_advanced", description="Advanced analytics for your actual portfolio")
def portfolio_analytics_advanced() -> Dict:
    """
    Run complete advanced analytics on your actual portfolio.

    Returns:
        Dict with all analytics results and report
    """
    logger = get_run_logger()
    logger.info("Starting portfolio advanced analytics...")

    try:
        # Load portfolio
        holdings_df, weights, tickers = load_portfolio_data()

        if not tickers:
            logger.error("No portfolio data available")
            return {"error": "No portfolio found"}

        # Calculate performance
        performance = calculate_portfolio_performance(holdings_df)

        # Fetch historical prices
        prices_df = fetch_historical_prices(tickers, days=252)

        # Run analytics
        risk_metrics = calculate_risk_metrics(prices_df, weights) if not prices_df.empty else {}
        optimization_metrics = (
            calculate_optimization_metrics(prices_df, tickers) if not prices_df.empty else {}
        )
        quick_wins = calculate_quick_wins(prices_df, {}) if not prices_df.empty else {}

        # Generate report
        report = generate_portfolio_report(
            holdings_df, risk_metrics, optimization_metrics, quick_wins, performance, weights
        )

        return {
            "portfolio": {
                "total_value": holdings_df["position_value"].sum(),
                "num_holdings": len(holdings_df),
                "weights": weights,
                "tickers": tickers,
            },
            "performance": performance,
            "risk_metrics": risk_metrics,
            "optimization_metrics": optimization_metrics,
            "quick_wins": quick_wins,
            "report": report,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error in portfolio analytics: {e}")
        raise


if __name__ == "__main__":
    import asyncio

    # Run without Prefect server - direct execution
    logger_print = print

    try:
        # Load portfolio
        holdings = Holdings()
        holdings_df = holdings.all_holdings

        if holdings_df.empty:
            logger_print("❌ No holdings found")
            sys.exit(1)

        logger_print(f"✓ Loaded {len(holdings_df)} holdings")

        # Get current prices
        fetcher = PriceFetcher()
        tickers = holdings_df["sym"].unique().tolist()

        # Filter out invalid tickers (manual entries, crypto, etc)
        valid_tickers = []
        invalid_tickers = []
        skip_keywords = ["MANUAL", "BITCOIN", "ETHEREUM", "CRYPTO", "SAVINGS"]
        for ticker in tickers:
            if any(keyword in ticker.upper() for keyword in skip_keywords):
                invalid_tickers.append(ticker)
            else:
                valid_tickers.append(ticker)

        if invalid_tickers:
            logger_print(f"⚠️  Skipping {len(invalid_tickers)} non-tradable holdings: {', '.join(invalid_tickers)}")

        prices = {}
        logger_print(f"\n📥 Fetching prices for {len(valid_tickers)} valid tickers...")
        for ticker in valid_tickers:
            try:
                price_data = fetcher.fetch_price(ticker, asset_type="eq")
                if price_data is not None:
                    # Handle both dict and scalar price responses
                    if isinstance(price_data, dict):
                        current_price = price_data.get("price") or price_data.get("close")
                    else:
                        current_price = price_data
                    
                    if current_price and not pd.isna(current_price):
                        prices[ticker] = current_price
                        logger_print(f"  {ticker}: ${current_price:.2f}")
                    else:
                        logger_print(f"  {ticker}: ⚠️  No price data available")
                else:
                    logger_print(f"  {ticker}: ⚠️  Could not fetch price")
            except Exception as e:
                logger_print(f"  {ticker}: ⚠️  {e}")

        # Calculate portfolio value and weights (only for holdings with prices)
        holdings_df["current_price"] = holdings_df["sym"].map(prices)
        holdings_df["position_value"] = holdings_df["qty"] * holdings_df["current_price"]

        # Remove rows with NaN prices (invalid/skipped tickers)
        # Use .loc to preserve all columns
        valid_indices = holdings_df["current_price"].notna()
        holdings_with_prices = holdings_df[valid_indices].reset_index(drop=True)

        if holdings_with_prices.empty:
            logger_print("❌ No valid holdings with prices")
            sys.exit(1)

        total_value = holdings_with_prices["position_value"].sum()
        holdings_with_prices["weight"] = holdings_with_prices["position_value"] / total_value

        weights = dict(zip(holdings_with_prices["sym"], holdings_with_prices["weight"]))

        # Calculate performance
        performance = {}
        for _, row in holdings_with_prices.iterrows():
            ticker = row["sym"]
            entry_price = row["bep"]
            current_price = row["current_price"]
            qty = row["qty"]

            pnl = (current_price - entry_price) * qty
            pnl_pct = ((current_price - entry_price) / entry_price * 100) if entry_price > 0 else 0

            performance[ticker] = {
                "entry_price": entry_price,
                "current_price": current_price,
                "pnl_pct": pnl_pct,
                "pnl_dollars": pnl,
                "quantity": qty,
                "position_value": current_price * qty,
            }

        # Fetch historical prices for analytics (use only valid tickers)
        logger_print(f"\n📊 Running analytics...")

        try:
            prices_df = fetch_historical_prices(valid_tickers, days=252)
        except Exception as e:
            logger_print(f"⚠️  Could not fetch historical prices: {e}")
            prices_df = pd.DataFrame()

        # Run analytics
        risk_metrics = calculate_risk_metrics(prices_df, weights) if not prices_df.empty else {}
        optimization_metrics = (
            calculate_optimization_metrics(prices_df, valid_tickers) if not prices_df.empty else {}
        )
        quick_wins = calculate_quick_wins(prices_df, {}) if not prices_df.empty else {}

        # Generate report
        report_lines = []
        report_lines.append("=" * 90)
        report_lines.append("YOUR PORTFOLIO - ADVANCED ANALYTICS REPORT")
        report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("=" * 90)

        # Historical Data Status
        report_lines.append(f"\n📦 HISTORICAL DATA STATUS")
        report_lines.append("-" * 90)
        try:
            db = ParquetDB()
            data_summary = f"Price data points collected: {len(prices_df) if not prices_df.empty else 0} days"
            if not prices_df.empty:
                data_summary += f" × {len(prices_df.columns)} tickers"
                report_lines.append(data_summary)
                report_lines.append(f"Data stored in: db/prices/")
                report_lines.append("ℹ️  Data accumulates daily. Run this flow regularly for better risk analysis.")
            else:
                report_lines.append("Collecting initial price data (1 year)...")
                report_lines.append("ℹ️  Risk calculations available after 30+ days of data collection")
        except Exception as e:
            pass

        # Portfolio Summary
        report_lines.append(f"\n📊 PORTFOLIO SUMMARY")
        report_lines.append("-" * 90)
        report_lines.append(f"Total Value: ${total_value:,.2f}")
        report_lines.append(f"Holdings: {len(holdings_with_prices)}")
        report_lines.append(f"Brokers: {', '.join(holdings_with_prices['brokername'].unique())}")

        # Performance
        total_pnl = sum(p["pnl_dollars"] for p in performance.values())
        total_pnl_pct = (total_pnl / (total_value - total_pnl)) * 100 if total_value > total_pnl else 0

        report_lines.append(f"\n💰 PERFORMANCE")
        report_lines.append("-" * 90)
        report_lines.append(f"Total P&L: ${total_pnl:,.2f} ({total_pnl_pct:+.2f}%)")

        # Top performers
        sorted_perf = sorted(performance.items(), key=lambda x: x[1]["pnl_pct"], reverse=True)
        report_lines.append(f"\nTop 3 Winners:")
        for ticker, perf in sorted_perf[:3]:
            report_lines.append(f"  {ticker}: {perf['pnl_pct']:+.2f}% (${perf['pnl_dollars']:+,.2f})")

        report_lines.append(f"\nTop 3 Losers:")
        for ticker, perf in sorted_perf[-3:]:
            report_lines.append(f"  {ticker}: {perf['pnl_pct']:+.2f}% (${perf['pnl_dollars']:+,.2f})")

        # Risk Metrics
        report_lines.append(f"\n📈 RISK ANALYSIS")
        report_lines.append("-" * 90)
        if risk_metrics:
            report_lines.append(f"Portfolio Volatility: {risk_metrics.get('portfolio_volatility', 0):.2f}%")
            report_lines.append(
                f"Daily VaR (95%): {risk_metrics.get('var_95_daily', 0):.4f}"
            )
            report_lines.append(
                f"Daily VaR (99%): {risk_metrics.get('var_99_daily', 0):.4f}"
            )
            report_lines.append(f"Portfolio Beta: {risk_metrics.get('portfolio_beta', 0):.4f}")
            report_lines.append(
                f"Concentration (HHI): {risk_metrics.get('concentration_hhi', 0):.4f}"
            )
            report_lines.append(
                f"Diversification Score: {risk_metrics.get('diversification_score', 0):.2f}"
            )

            if risk_metrics.get("is_concentrated"):
                report_lines.append("⚠️  Portfolio is CONCENTRATED - Consider diversifying")
            else:
                report_lines.append("✓ Portfolio is well-diversified")
        else:
            report_lines.append("(Risk metrics unavailable - need historical data)")

        # Optimization
        report_lines.append(f"\n🎯 OPTIMIZATION RECOMMENDATIONS")
        report_lines.append("-" * 90)
        if optimization_metrics and "max_sharpe_weights" in optimization_metrics:
            report_lines.append("Current vs. Optimal (Max Sharpe Ratio):")
            for ticker in list(weights.keys())[:5]:  # Show top 5
                current = weights.get(ticker, 0) * 100
                optimal = optimization_metrics["max_sharpe_weights"].get(ticker, 0) * 100
                diff = optimal - current
                action = "INCREASE" if diff > 1 else "DECREASE" if diff < -1 else "HOLD"
                report_lines.append(
                    f"  {ticker}: {current:.1f}% → {optimal:.1f}% ({action} {abs(diff):+.1f}%)"
                )
        else:
            report_lines.append("(Optimization unavailable - need historical data)")

        # Quick Wins
        report_lines.append(f"\n⚡ QUICK INSIGHTS")
        report_lines.append("-" * 90)
        if quick_wins:
            if "sector_allocation" in quick_wins:
                report_lines.append("Sector Breakdown:")
                for sector, alloc in sorted(
                    quick_wins["sector_allocation"].items(), key=lambda x: x[1], reverse=True
                ):
                    report_lines.append(f"  {sector}: {alloc:.1f}%")

            if "sharpe_ratio" in quick_wins:
                report_lines.append(f"\nSharpe Ratio: {quick_wins['sharpe_ratio']:.4f}")

            if "concentration_risk" in quick_wins:
                conc = quick_wins["concentration_risk"]
                report_lines.append(f"\nTop Holdings:")
                report_lines.append(f"  Largest: {conc.get('top_1_concentration', 0):.1f}%")
                report_lines.append(f"  Top 3: {conc.get('top_3_concentration', 0):.1f}%")
        else:
            report_lines.append("(Quick wins unavailable - need historical data)")

        report_lines.append("\n" + "=" * 90)
        report_lines.append("END OF REPORT")
        report_lines.append("=" * 90)

        report_text = "\n".join(report_lines)
        print("\n" + report_text)

    except Exception as e:
        logger_print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
