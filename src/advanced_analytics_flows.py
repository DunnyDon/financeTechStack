"""
Advanced Analytics Flows

Prefect flows for risk, optimization, options, fixed income, and quick wins analytics.
Integrates all advanced portfolio analytics into the workflow orchestration.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from prefect import flow, task, get_run_logger

from src.portfolio_risk import RiskAnalytics
from src.portfolio_optimization import PortfolioOptimizer
from src.options_analysis import OptionsAnalysis
from src.fixed_income_analysis import FixedIncomeAnalysis
from src.quick_wins_analytics import QuickWinsAnalytics
from src.portfolio_prices import PriceFetcher
from src.parquet_db import ParquetDB

# Import data pipeline robustness components
try:
    from src.pipeline_robustness_integration import (
        PRICE_VALIDATOR,
        TECHNICAL_VALIDATOR,
        FUNDAMENTAL_VALIDATOR,
        PRICE_RETRY_POLICY,
    )
    ROBUSTNESS_AVAILABLE = True
except ImportError:
    ROBUSTNESS_AVAILABLE = False


@task(retries=2, retry_delay_seconds=5)
def fetch_historical_prices(tickers: List[str], days: int = 252) -> pd.DataFrame:
    """Fetch historical price data for risk calculations, with persistence to ParquetDB."""
    logger = get_run_logger()
    logger.info(f"Fetching {days} days of price data for {len(tickers)} tickers")

    try:
        fetcher = PriceFetcher()
        db = ParquetDB()
        prices_dict = {}
        
        # Try to read from ParquetDB first
        logger.info(f"Checking ParquetDB for existing historical data...")
        for ticker in tickers:
            try:
                # Read from parquet DB using read_table method
                hist_data = db.read_table(
                    'prices',
                    filters=[('symbol', '==', ticker)],
                    columns=['timestamp', 'close_price']
                )
                if hist_data is not None and len(hist_data) > 0:
                    logger.info(f"  {ticker}: Found {len(hist_data)} days in ParquetDB")
                    # Convert close_price to numeric (in case stored as string)
                    prices_dict[ticker] = pd.to_numeric(hist_data['close_price'], errors='coerce').values
            except Exception as e:
                logger.debug(f"  {ticker}: Not in ParquetDB yet ({e})")

        # Fetch missing data from yfinance
        missing_tickers = [t for t in tickers if t not in prices_dict]
        if missing_tickers:
            logger.info(f"Fetching historical data from yfinance for {len(missing_tickers)} tickers...")
            
            for ticker in missing_tickers:
                try:
                    price_data = fetcher.fetch_historical(ticker, period="1y")
                    if price_data is not None and len(price_data) > 0:
                        # Save to ParquetDB
                        try:
                            save_data = price_data[['close']].reset_index()
                            save_data.columns = ['timestamp', 'close_price']
                            save_data['symbol'] = ticker
                            save_data['currency'] = 'USD'
                            save_data['frequency'] = 'daily'
                            db.upsert_prices(save_data)
                            logger.info(f"  {ticker}: Saved {len(save_data)} days to ParquetDB")
                        except Exception as e:
                            logger.warning(f"  {ticker}: Could not save to ParquetDB: {e}")
                        
                        # Use for current analysis
                        prices_dict[ticker] = price_data['Close'].values
                    else:
                        logger.warning(f"  {ticker}: No historical data available")
                except Exception as e:
                    logger.warning(f"  {ticker}: Error fetching: {e}")

        # Create DataFrame with equal-length data
        if prices_dict:
            min_length = min(len(v) if hasattr(v, '__len__') else 1 for v in prices_dict.values())
            if min_length > 0:
                prices_df = pd.DataFrame({k: v[-min_length:] if hasattr(v, '__len__') else [v] for k, v in prices_dict.items()})
                logger.info(f"✓ Fetched price data: {prices_df.shape} ({min_length} days of history)")
                return prices_df

        logger.warning("No price data available")
        return pd.DataFrame()
    except Exception as e:
        logger.error(f"Error fetching prices: {e}")
        raise


@task(retries=2)
def calculate_risk_metrics(prices_df: pd.DataFrame, weights: Dict[str, float]) -> Dict:
    """Calculate comprehensive risk metrics with error handling."""
    logger = get_run_logger()
    logger.info("Calculating risk metrics...")

    if prices_df.empty:
        logger.warning("Empty price data")
        return {}

    try:
        ra = RiskAnalytics(prices_df, risk_free_rate=0.04)

        # VaR
        var_95 = ra.calculate_var(confidence=0.95, days=1)
        var_99 = ra.calculate_var(confidence=0.99, days=1)

        # Correlation
        corr_matrix = ra.calculate_correlation_matrix()

        # Portfolio beta
        portfolio_beta = ra.calculate_portfolio_beta(weights, market_ticker="SPY")

        # Volatility
        portfolio_vol = ra.calculate_portfolio_volatility(weights)

        # Concentration
        concentration = ra.calculate_concentration_risk(weights)

        result = {
            "var_95_daily": var_95.get("portfolio", 0),
            "var_99_daily": var_99.get("portfolio", 0),
            "portfolio_beta": portfolio_beta,
            "portfolio_volatility": portfolio_vol,
            "concentration_hhi": concentration.get("hhi", 0),
            "diversification_score": concentration.get("diversification_ratio", 0),
            "top_3_concentration": concentration.get("top_3_concentration", 0),
            "is_concentrated": concentration.get("num_holdings", 0) < 5,
        }
        
        logger.info(f"Risk metrics calculated successfully: VaR(95%)={result['var_95_daily']:.4f}")
        return result
        
    except Exception as e:
        logger.error(f"Error calculating risk metrics: {e}")
        return {}


@task(retries=2)
def calculate_optimization_metrics(prices_df: pd.DataFrame, tickers: List[str]) -> Dict:
    """Calculate portfolio optimization recommendations with error handling."""
    logger = get_run_logger()
    logger.info("Calculating portfolio optimization...")

    if prices_df.empty or len(tickers) < 2:
        logger.warning("Insufficient data for optimization")
        return {}

    try:
        returns_df = prices_df.pct_change().dropna()
        optimizer = PortfolioOptimizer(returns_df, risk_free_rate=0.04)

        # Minimum variance portfolio
        min_var = optimizer.minimum_variance_portfolio(tickers)

        # Maximum Sharpe portfolio
        max_sharpe = optimizer.maximum_sharpe_ratio_portfolio(tickers)

        # Efficient frontier
        frontier = optimizer.efficient_frontier(tickers, num_points=15)

        result = {
            "min_variance_weights": min_var.weights,
            "min_variance_volatility": min_var.expected_volatility,
            "max_sharpe_weights": max_sharpe.weights,
            "max_sharpe_ratio": max_sharpe.sharpe_ratio,
            "max_sharpe_return": max_sharpe.expected_return,
            "efficient_frontier": frontier,
        }
        
        logger.info(f"Optimization complete: Max Sharpe ratio={result['max_sharpe_ratio']:.4f}")
        return result
        
    except Exception as e:
        logger.error(f"Error calculating optimization metrics: {e}")
        return {}


@task(retries=2)
def calculate_quick_wins(prices_df: pd.DataFrame, holdings: Dict[str, Dict]) -> Dict:
    """Calculate quick wins analytics with error handling."""
    logger = get_run_logger()
    logger.info("Calculating quick wins analytics...")

    if prices_df.empty:
        return {}

    try:
        results = {}

        # Sector allocation
        if any("sector" in h for h in holdings.values()):
            results["sector_allocation"] = QuickWinsAnalytics.sector_allocation(holdings)

        # Asset class breakdown
        if any("asset_class" in h for h in holdings.values()):
            results["asset_class_breakdown"] = QuickWinsAnalytics.asset_class_breakdown(holdings)

        # Portfolio volatility
        returns = prices_df.pct_change().dropna()
        portfolio_returns = []
        if len(returns) > 0:
            portfolio_returns = returns.mean(axis=1).values.tolist()
            results["portfolio_volatility"] = QuickWinsAnalytics.portfolio_volatility(portfolio_returns)

        # Dividend projection
        if any("dividend_yield" in h for h in holdings.values()):
            div_proj = QuickWinsAnalytics.dividend_income_projection(holdings)
            results["dividend_projection"] = div_proj

        # Winners/losers
        if any("entry_price" in h and "current_price" in h for h in holdings.values()):
            wl = QuickWinsAnalytics.winners_losers_report(holdings, top_n=3)
            results["winners_losers"] = wl

        # Concentration risk
        weights = {}
        total_value = sum(h.get("quantity", 0) * h.get("price", 0) for h in holdings.values())
        if total_value > 0:
            for ticker, h in holdings.items():
                value = h.get("quantity", 0) * h.get("price", 0)
                weights[ticker] = value / total_value

            results["concentration_risk"] = QuickWinsAnalytics.concentration_risk_metrics(weights)

        # Sharpe ratio
        if len(portfolio_returns) > 0:
            results["sharpe_ratio"] = QuickWinsAnalytics.sharpe_ratio_calculation(portfolio_returns)

        logger.info(f"Quick wins analysis complete with {len(results)} metrics")
        return results
        
    except Exception as e:
        logger.error(f"Error calculating quick wins: {e}")
        return {}


@task(retries=2)
def analyze_options_positions(option_positions: List[Dict], spot_price: float) -> Dict:
    """Analyze options strategy Greeks with error handling."""
    logger = get_run_logger()
    logger.info(f"Analyzing {len(option_positions)} options positions...")

    if not option_positions:
        return {}

    try:
        analysis = OptionsAnalysis.analyze_position(option_positions, spot_price)

        result = {
            "portfolio_delta": analysis["portfolio_delta"],
            "portfolio_theta": analysis["portfolio_theta"],  # Daily decay
            "portfolio_vega": analysis["portfolio_vega"],  # Vol sensitivity
            "positions_detail": analysis["positions"],
        }
        
        logger.info(f"Options analysis complete: Portfolio Delta={result['portfolio_delta']:.4f}")
        return result
        
    except Exception as e:
        logger.error(f"Error analyzing options positions: {e}")
        return {}


@task(retries=2)
def analyze_fixed_income_positions(bond_positions: List[Dict]) -> Dict:
    """Analyze fixed income portfolio with error handling."""
    logger = get_run_logger()
    logger.info(f"Analyzing {len(bond_positions)} bond positions...")

    if not bond_positions:
        return {}

    try:
        results = {}

        for i, pos in enumerate(bond_positions):
            bond_analysis = analyze_bond_position(
                current_price=pos.get("price", 1000),
                face_value=pos.get("face_value", 1000),
                coupon_rate=pos.get("coupon_rate", 0.05),
                years_to_maturity=pos.get("years_to_maturity", 5),
            )

            ticker = pos.get("ticker", f"BOND_{i}")
            results[ticker] = bond_analysis

        logger.info(f"Fixed income analysis complete for {len(results)} positions")
        return results
        
    except Exception as e:
        logger.error(f"Error analyzing fixed income positions: {e}")
        return {}


@task(retries=1)
def generate_advanced_report(
    risk_metrics: Dict,
    optimization_metrics: Dict,
    quick_wins: Dict,
    options_analysis: Dict = None,
    fixed_income: Dict = None,
) -> str:
    """Generate comprehensive advanced analytics report with error handling."""
    logger = get_run_logger()

    try:
        report = []
        report.append("=" * 80)
        report.append("ADVANCED PORTFOLIO ANALYTICS REPORT")
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("=" * 80)

        # Risk Metrics
        report.append("\n📊 RISK ANALYTICS")
        report.append("-" * 80)
        if risk_metrics:
            report.append(f"  VaR (95% conf): {risk_metrics.get('var_95_daily', 0):.4f}")
            report.append(f"  VaR (99% conf): {risk_metrics.get('var_99_daily', 0):.4f}")
            report.append(f"  Portfolio Beta: {risk_metrics.get('portfolio_beta', 0):.4f}")
            report.append(f"  Portfolio Volatility: {risk_metrics.get('portfolio_volatility', 0):.2f}%")
            report.append(f"  Concentration (HHI): {risk_metrics.get('concentration_hhi', 0):.4f}")
            report.append(f"  Diversification Score: {risk_metrics.get('diversification_score', 0):.2f}")

        # Optimization
        report.append("\n🎯 PORTFOLIO OPTIMIZATION")
        report.append("-" * 80)
        if optimization_metrics:
            report.append("  Min Variance Portfolio:")
            for ticker, weight in optimization_metrics.get("min_variance_weights", {}).items():
                report.append(f"    {ticker}: {weight * 100:.2f}%")

            report.append(f"\n  Max Sharpe Portfolio (Sharpe: {optimization_metrics.get('max_sharpe_ratio', 0):.4f}):")
            for ticker, weight in optimization_metrics.get("max_sharpe_weights", {}).items():
                report.append(f"    {ticker}: {weight * 100:.2f}%")

        # Quick Wins
        report.append("\n⚡ QUICK WINS ANALYTICS")
        report.append("-" * 80)
        if quick_wins:
            if "sector_allocation" in quick_wins:
                report.append("  Sector Allocation:")
                for sector, alloc in quick_wins["sector_allocation"].items():
                    report.append(f"    {sector}: {alloc:.2f}%")

            if "winners_losers" in quick_wins:
                report.append("  Top 3 Winners:")
                for w in quick_wins["winners_losers"].get("winners", [])[:3]:
                    report.append(f"    {w['ticker']}: {w['pnl_pct']:.2f}%")

            report.append(f"\n  Portfolio Volatility: {quick_wins.get('portfolio_volatility', 0):.2f}%")
            report.append(f"  Sharpe Ratio: {quick_wins.get('sharpe_ratio', 0):.4f}")

        # Options
        if options_analysis:
            report.append("\n📈 OPTIONS ANALYSIS")
            report.append("-" * 80)
            report.append(f"  Portfolio Delta: {options_analysis.get('portfolio_delta', 0):.4f}")
            report.append(f"  Daily Theta (time decay): ${options_analysis.get('portfolio_theta', 0):.2f}")
            report.append(f"  Vega (per 1% vol): ${options_analysis.get('portfolio_vega', 0):.2f}")

        # Fixed Income
        if fixed_income:
            report.append("\n🏦 FIXED INCOME ANALYSIS")
            report.append("-" * 80)
            for ticker, metrics in fixed_income.items():
                report.append(f"  {ticker}:")
                report.append(f"    YTM: {metrics.get('ytm', 0) * 100:.2f}%")
                report.append(f"    Duration: {metrics.get('duration', 0):.2f} years")

        report.append("\n" + "=" * 80)

        report_text = "\n".join(report)
        logger.info(report_text)

        return report_text
        
    except Exception as e:
        logger.error(f"Error generating advanced report: {e}")
        return f"Report generation failed: {e}"


@flow(name="advanced_analytics_flow", description="Comprehensive advanced portfolio analytics")
def advanced_analytics_flow(
    tickers: List[str],
    weights: Dict[str, float],
    holdings: Dict[str, Dict] = None,
    option_positions: List[Dict] = None,
    bond_positions: List[Dict] = None,
) -> Dict:
    """
    Run comprehensive advanced analytics flow.

    Args:
        tickers: List of ticker symbols
        weights: Portfolio weights
        holdings: Holdings with sector/dividend info
        option_positions: Options positions for Greeks analysis
        bond_positions: Bond positions for fixed income analysis

    Returns:
        Dict with all analytics results
    """
    logger = get_run_logger()
    logger.info(f"Starting advanced analytics for {len(tickers)} tickers")

    # Fetch historical data
    prices_df = fetch_historical_prices(tickers, days=252)

    # Calculate metrics
    risk_metrics = calculate_risk_metrics(prices_df, weights)
    optimization_metrics = calculate_optimization_metrics(prices_df, tickers)
    quick_wins = calculate_quick_wins(prices_df, holdings or {})

    # Optional analyses
    options_analysis = None
    if option_positions:
        spot_price = prices_df.iloc[-1].mean() if not prices_df.empty else 100
        options_analysis = analyze_options_positions(option_positions, spot_price)

    fixed_income_analysis = None
    if bond_positions:
        fixed_income_analysis = analyze_fixed_income_positions(bond_positions)

    # Generate report
    report = generate_advanced_report(
        risk_metrics, optimization_metrics, quick_wins, options_analysis, fixed_income_analysis
    )

    return {
        "risk_metrics": risk_metrics,
        "optimization_metrics": optimization_metrics,
        "quick_wins": quick_wins,
        "options_analysis": options_analysis,
        "fixed_income_analysis": fixed_income_analysis,
        "report": report,
        "timestamp": datetime.now().isoformat(),
    }


if __name__ == "__main__":
    # Example usage
    example_tickers = ["AAPL", "MSFT", "GOOGL"]
    example_weights = {"AAPL": 0.4, "MSFT": 0.35, "GOOGL": 0.25}

    result = advanced_analytics_flow(example_tickers, example_weights)
    print(result["report"])
