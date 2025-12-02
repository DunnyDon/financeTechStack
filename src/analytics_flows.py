"""
Enhanced analytics and reporting flow for Prefect orchestration.

Generates comprehensive analytics reports with:
- Enhanced technical analysis (Bollinger bands, RSI, MACD)
- Fundamental analysis integration
- Portfolio P&L tracking
- Email delivery with HTML formatting and embedded graphs

This flow reads from ParquetDB and generates insights for portfolio management.
"""

from datetime import datetime
from typing import Dict, Optional

import pandas as pd
from prefect import flow, get_run_logger, task

from .analytics_report import AnalyticsReporter, generate_analytics_report, send_analytics_email
from .parquet_db import ParquetDB
from .portfolio_analytics import PortfolioAnalytics
from .portfolio_holdings import Holdings
from .portfolio_prices import PriceFetcher
from .portfolio_technical import TechnicalAnalyzer
from .utils import get_logger

__all__ = [
    "enhanced_analytics_flow",
    "send_report_email_flow",
    "generate_technical_insights",
    "generate_fundamental_insights",
]

logger = get_logger(__name__)


@task(name="load_portfolio_data")
def load_portfolio_data() -> tuple:
    """
    Load portfolio data from holdings and database.

    Returns:
        Tuple of (holdings_df, prices_dict, technical_data, fundamental_data)
    """
    task_logger = get_run_logger()
    task_logger.info("Loading portfolio data...")

    try:
        # Load holdings
        holdings = Holdings("holdings.csv")
        holdings_df = holdings.all_holdings
        task_logger.info(f"Loaded {len(holdings_df)} holdings")

        # Get prices - build asset type mapping
        symbols = holdings_df["sym"].tolist()
        asset_types = dict(zip(holdings_df["sym"], holdings_df.get("asset", "eq")))
        price_fetcher = PriceFetcher()
        prices_dict = {}
        for symbol in symbols:
            price_data = price_fetcher.fetch_price(symbol, asset_types.get(symbol, "eq"))
            if price_data:
                prices_dict[symbol] = price_data
        task_logger.info(f"Fetched prices for {len(prices_dict)} securities")

        # Load from ParquetDB
        db = ParquetDB()

        # Get technical data
        technical_data = db.read_table("technical_analysis")
        if technical_data is None:
            technical_data = pd.DataFrame()
        task_logger.info(f"Loaded {len(technical_data)} technical records")

        # Get fundamental data
        fundamental_data = db.read_table("fundamental_analysis")
        if fundamental_data is None:
            fundamental_data = pd.DataFrame()
        task_logger.info(f"Loaded {len(fundamental_data)} fundamental records")

        return holdings_df, prices_dict, technical_data, fundamental_data

    except Exception as e:
        task_logger.error(f"Error loading portfolio data: {e}")
        raise


@task(name="calculate_technical_indicators")
def calculate_technical_indicators(prices_dict: Dict, holdings_df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate technical indicators for all holdings and store in ParquetDB.

    Args:
        prices_dict: Dictionary of current prices by symbol
        holdings_df: Portfolio holdings with symbols

    Returns:
        DataFrame with technical indicators
    """
    task_logger = get_run_logger()
    task_logger.info("Calculating technical indicators...")

    try:
        db = ParquetDB()
        analyzer = TechnicalAnalyzer()
        technical_records = []

        # Get historical prices for each symbol using PriceFetcher
        for symbol in holdings_df["sym"].tolist():
            try:
                # Fetch 200 days of historical data
                hist_data = PriceFetcher().fetch_historical(symbol, period="200d")

                if hist_data is not None and not hist_data.empty:
                    prices = hist_data["Close"].values if "Close" in hist_data.columns else hist_data.iloc[:, 0].values

                    if len(prices) < 20:  # Need minimum data for indicators
                        task_logger.warning(f"Insufficient data for {symbol}: {len(prices)} days")
                        continue

                    # Calculate indicators
                    indicators = {}
                    prices_series = pd.Series(prices)
                    
                    # Bollinger Bands
                    try:
                        bb = analyzer.bollinger_bands(prices_series)
                        if bb and "bb_upper" in bb:
                            indicators["bb_upper"] = float(bb["bb_upper"].iloc[-1]) if len(bb["bb_upper"]) > 0 else None
                            indicators["bb_lower"] = float(bb["bb_lower"].iloc[-1]) if len(bb["bb_lower"]) > 0 else None
                            indicators["bb_middle"] = float(bb["bb_middle"].iloc[-1]) if len(bb["bb_middle"]) > 0 else None
                    except Exception as e:
                        task_logger.debug(f"Bollinger Bands error for {symbol}: {e}")

                    # RSI (14-period)
                    try:
                        rsi = analyzer.rsi(prices_series, period=14)
                        if rsi is not None and len(rsi) > 0:
                            indicators["rsi_14"] = float(rsi.iloc[-1])
                    except Exception as e:
                        task_logger.debug(f"RSI error for {symbol}: {e}")

                    # MACD
                    try:
                        macd = analyzer.macd(prices_series)
                        if macd:
                            if "macd" in macd and len(macd["macd"]) > 0:
                                indicators["macd"] = float(macd["macd"].iloc[-1])
                            if "signal" in macd and len(macd["signal"]) > 0:
                                indicators["macd_signal"] = float(macd["signal"].iloc[-1])
                            if "histogram" in macd and len(macd["histogram"]) > 0:
                                indicators["macd_histogram"] = float(macd["histogram"].iloc[-1])
                    except Exception as e:
                        task_logger.debug(f"MACD error for {symbol}: {e}")

                    # Moving Averages
                    try:
                        ma = analyzer.moving_averages(prices_series)
                        if ma:
                            if "sma_short" in ma and len(ma["sma_short"]) > 0:
                                indicators["sma_20"] = float(ma["sma_short"].iloc[-1])
                            if "sma_long" in ma and len(ma["sma_long"]) > 0:
                                indicators["sma_50"] = float(ma["sma_long"].iloc[-1])
                            if "ema_short" in ma and len(ma["ema_short"]) > 0:
                                indicators["ema_20"] = float(ma["ema_short"].iloc[-1])
                            if "ema_long" in ma and len(ma["ema_long"]) > 0:
                                indicators["ema_50"] = float(ma["ema_long"].iloc[-1])
                    except Exception as e:
                        task_logger.debug(f"Moving averages error for {symbol}: {e}")

                    # Get current price
                    current_price = float(prices[-1])
                    
                    # Create record
                    record = {
                        "symbol": symbol,
                        "timestamp": pd.Timestamp.now(),
                        "close_price": current_price,
                        "frequency": "daily",
                        **indicators,
                    }
                    technical_records.append(record)
                    task_logger.info(f"Calculated {len(indicators)} indicators for {symbol}")

            except Exception as e:
                task_logger.warning(f"Could not calculate indicators for {symbol}: {e}")
                continue

        if technical_records:
            # Convert to DataFrame and store
            technical_df = pd.DataFrame(technical_records)
            inserted, updated = db.upsert_technical_analysis(technical_df)
            task_logger.info(f"Stored technical indicators: {inserted} inserted, {updated} updated")
            return technical_df
        else:
            task_logger.warning("No technical indicators calculated")
            return pd.DataFrame()

    except Exception as e:
        task_logger.error(f"Error calculating technical indicators: {e}")
        return pd.DataFrame()


@task(name="load_portfolio_data")
def load_portfolio_data() -> tuple:
    """
    Load portfolio data from holdings and database.

    Returns:
        Tuple of (holdings_df, prices_dict, technical_data, fundamental_data)
    """
    task_logger = get_run_logger()
    task_logger.info("Loading portfolio data...")

    try:
        # Load holdings
        holdings = Holdings("holdings.csv")
        holdings_df = holdings.all_holdings
        task_logger.info(f"Loaded {len(holdings_df)} holdings")

        # Get prices - build asset type mapping
        symbols = holdings_df["sym"].tolist()
        asset_types = dict(zip(holdings_df["sym"], holdings_df.get("asset", "eq")))
        price_fetcher = PriceFetcher()
        prices_dict = {}
        for symbol in symbols:
            price_data = price_fetcher.fetch_price(symbol, asset_types.get(symbol, "eq"))
            if price_data:
                prices_dict[symbol] = price_data
        task_logger.info(f"Fetched prices for {len(prices_dict)} securities")

        # Load from ParquetDB
        db = ParquetDB()

        # Get technical data
        technical_data = db.read_table("technical_analysis")
        if technical_data is None:
            technical_data = pd.DataFrame()
        task_logger.info(f"Loaded {len(technical_data)} technical records")

        # Get fundamental data
        fundamental_data = db.read_table("fundamental_analysis")
        if fundamental_data is None:
            fundamental_data = pd.DataFrame()
        task_logger.info(f"Loaded {len(fundamental_data)} fundamental records")

        return holdings_df, prices_dict, technical_data, fundamental_data

    except Exception as e:
        task_logger.error(f"Error loading portfolio data: {e}")
        raise


@task(name="calculate_pnl_enhanced")
def calculate_pnl_enhanced(
    holdings_df: pd.DataFrame, prices_dict: Dict
) -> pd.DataFrame:
    """
    Calculate enhanced P&L with all metrics, including cash and fixed-income.

    Args:
        holdings_df: Portfolio holdings
        prices_dict: Current prices

    Returns:
        DataFrame with detailed P&L metrics
    """
    task_logger = get_run_logger()
    task_logger.info("Calculating enhanced P&L...")

    try:
        from .fx_rates import FXRateManager
        
        analytics = PortfolioAnalytics(holdings_df, prices_dict)
        pnl_df = analytics.calculate_unrealized_pnl()

        # Add cash and fixed-income positions that don't have prices
        cash_fixed_income = holdings_df[
            holdings_df["asset"].isin(["cash", "fixed-income"])
        ].copy()
        
        if not cash_fixed_income.empty:
            # For cash/fixed-income: qty is the actual amount, convert to EUR
            cash_fixed_income["current_price"] = 1.0  # Placeholder
            cash_fixed_income["current_price_eur"] = 1.0  # Normalized for conversion
            
            # Convert qty (which is the actual amount) to EUR
            cash_fixed_income["current_value_eur"] = cash_fixed_income.apply(
                lambda row: FXRateManager.convert(
                    row["qty"], row.get("ccy", "EUR"), "EUR"
                ),
                axis=1,
            )
            
            # Cost basis is the same as current value for cash/fixed-income
            cash_fixed_income["cost_basis_eur"] = cash_fixed_income["current_value_eur"]
            cash_fixed_income["bep_eur"] = 1.0  # Placeholder
            cash_fixed_income["unrealized_pnl_eur"] = 0  # No P&L for cash/fixed-income
            cash_fixed_income["pnl_percent"] = 0
            cash_fixed_income["return_pct"] = 0
            
            pnl_df = pd.concat([pnl_df, cash_fixed_income], ignore_index=True)

        task_logger.info(
            f"P&L Calculation: {len(pnl_df)} positions, "
            f"Total Value: €{pnl_df['current_value_eur'].sum():,.2f}"
        )

        return pnl_df

    except Exception as e:
        task_logger.error(f"Error calculating P&L: {e}")
        raise


@task(name="calculate_portfolio_weights")
def calculate_portfolio_weights(pnl_data: pd.DataFrame) -> Dict:
    """
    Calculate portfolio weight breakdown by asset class.

    Args:
        pnl_data: DataFrame with P&L data including asset class info

    Returns:
        Dictionary with asset class weights
    """
    task_logger = get_run_logger()
    task_logger.info("Calculating portfolio weights...")

    try:
        if pnl_data.empty:
            return {"error": "No P&L data available"}

        total_value = pnl_data["current_value_eur"].sum()
        
        if total_value == 0:
            return {"error": "Total portfolio value is zero"}

        weights = {
            "timestamp": datetime.now().isoformat(),
            "total_value_eur": total_value,
            "by_asset_class": {},
        }

        # Weight by asset class (including cash and fixed-income)
        if "asset" in pnl_data.columns:
            asset_breakdown = (
                pnl_data.groupby("asset")["current_value_eur"]
                .sum()
                .to_dict()
            )
            weights["by_asset_class"] = {
                asset: {
                    "value_eur": value,
                    "weight_percent": (value / total_value * 100) if total_value > 0 else 0,
                    "count": len(pnl_data[pnl_data["asset"] == asset])
                }
                for asset, value in asset_breakdown.items()
            }

        task_logger.info(f"Portfolio weights calculated: {weights['by_asset_class']}")
        return weights

    except Exception as e:
        task_logger.error(f"Error calculating portfolio weights: {e}")
        raise


@task(name="analyze_technical_signals")
def analyze_technical_signals(technical_data: pd.DataFrame) -> Dict:
    """
    Analyze technical signals and opportunities.
    
    Technical indicators include price-based signals like:
    - Bollinger Bands (oversold/overbought detection)
    - RSI (Relative Strength Index for momentum)
    - MACD (Moving Average Convergence Divergence)
    - Moving Averages (SMA 20/50/200)

    Args:
        technical_data: Technical indicators data (calculated from historical prices)

    Returns:
        Dictionary with technical analysis
    """
    task_logger = get_run_logger()
    task_logger.info("Analyzing technical signals...")

    try:
        if technical_data.empty:
            task_logger.info(
                "No technical data available - this requires historical price analysis. "
                "Technical indicators (Bollinger Bands, MACD, RSI, Moving Averages) "
                "are calculated from price history and need to be generated separately."
            )

        signals = {
            "timestamp": datetime.now().isoformat(),
            "total_analyzed": len(technical_data),
        }

        # Bollinger Band analysis
        if "bb_upper" in technical_data.columns and "bb_lower" in technical_data.columns:
            oversold = technical_data[
                technical_data["close_price"] < technical_data["bb_lower"]
            ]
            overbought = technical_data[
                technical_data["close_price"] > technical_data["bb_upper"]
            ]
            signals["bollinger_oversold"] = len(oversold)
            signals["bollinger_overbought"] = len(overbought)

        # RSI analysis
        if "rsi_14" in technical_data.columns:
            oversold_rsi = technical_data[technical_data["rsi_14"] < 30]
            overbought_rsi = technical_data[technical_data["rsi_14"] > 70]
            signals["rsi_oversold"] = len(oversold_rsi)
            signals["rsi_overbought"] = len(overbought_rsi)

        # MACD analysis
        if "macd" in technical_data.columns and "macd_signal" in technical_data.columns:
            bullish = technical_data[technical_data["macd"] > technical_data["macd_signal"]]
            bearish = technical_data[technical_data["macd"] < technical_data["macd_signal"]]
            signals["macd_bullish"] = len(bullish)
            signals["macd_bearish"] = len(bearish)

        # Moving average analysis
        if "sma_200" in technical_data.columns:
            above_200 = technical_data[
                technical_data["close_price"] > technical_data["sma_200"]
            ]
            signals["above_sma_200"] = len(above_200)

        if "sma_50" in technical_data.columns:
            above_50 = technical_data[
                technical_data["close_price"] > technical_data["sma_50"]
            ]
            signals["above_sma_50"] = len(above_50)

        task_logger.info(f"Technical signals analyzed: {signals}")
        return signals

    except Exception as e:
        task_logger.error(f"Error analyzing technical signals: {e}")
        raise


@task(name="analyze_fundamental_metrics")
def analyze_fundamental_metrics(fundamental_data: pd.DataFrame) -> Dict:
    """
    Analyze fundamental metrics and opportunities.

    Args:
        fundamental_data: Fundamental analysis data

    Returns:
        Dictionary with fundamental analysis
    """
    task_logger = get_run_logger()
    task_logger.info("Analyzing fundamental metrics...")

    try:
        if fundamental_data.empty:
            return {"total_analyzed": 0}

        # Convert numeric columns to float
        numeric_cols = ["pe_ratio", "pb_ratio", "ps_ratio", "roe", "roa", "debt_to_equity", 
                       "profit_margin", "operating_margin", "dividend_yield", 
                       "revenue_growth_yoy", "earnings_growth_yoy"]
        for col in numeric_cols:
            if col in fundamental_data.columns:
                fundamental_data[col] = pd.to_numeric(fundamental_data[col], errors="coerce")

        metrics = {
            "timestamp": datetime.now().isoformat(),
            "total_analyzed": len(fundamental_data),
        }

        # Value metrics
        if "pe_ratio" in fundamental_data.columns:
            valid_pe = fundamental_data[fundamental_data["pe_ratio"] > 0]
            if not valid_pe.empty:
                metrics["avg_pe_ratio"] = float(valid_pe["pe_ratio"].mean())
                metrics["min_pe_ratio"] = float(valid_pe["pe_ratio"].min())
                metrics["max_pe_ratio"] = float(valid_pe["pe_ratio"].max())

        if "pb_ratio" in fundamental_data.columns:
            valid_pb = fundamental_data[fundamental_data["pb_ratio"] > 0]
            if not valid_pb.empty:
                metrics["avg_pb_ratio"] = float(valid_pb["pb_ratio"].mean())

        if "ps_ratio" in fundamental_data.columns:
            valid_ps = fundamental_data[fundamental_data["ps_ratio"] > 0]
            if not valid_ps.empty:
                metrics["avg_ps_ratio"] = float(valid_ps["ps_ratio"].mean())

        # Quality metrics
        if "roe" in fundamental_data.columns:
            valid_roe = fundamental_data[fundamental_data["roe"] > 0]
            if not valid_roe.empty:
                metrics["avg_roe"] = float(valid_roe["roe"].mean())
                metrics["high_roe_count"] = len(
                    valid_roe[valid_roe["roe"] > valid_roe["roe"].quantile(0.75)]
                )

        if "roa" in fundamental_data.columns:
            valid_roa = fundamental_data[fundamental_data["roa"] > 0]
            if not valid_roa.empty:
                metrics["avg_roa"] = float(valid_roa["roa"].mean())

        if "debt_to_equity" in fundamental_data.columns:
            valid_dte = fundamental_data[fundamental_data["debt_to_equity"] > 0]
            if not valid_dte.empty:
                metrics["avg_debt_to_equity"] = float(valid_dte["debt_to_equity"].mean())
                metrics["low_debt_count"] = len(
                    valid_dte[valid_dte["debt_to_equity"] < valid_dte["debt_to_equity"].quantile(0.25)]
                )

        # Dividend yield
        if "dividend_yield" in fundamental_data.columns:
            dividend_payers = fundamental_data[
                fundamental_data["dividend_yield"] > 0
            ]
            metrics["dividend_payers"] = len(dividend_payers)
            if not dividend_payers.empty:
                metrics["avg_dividend_yield"] = float(dividend_payers["dividend_yield"].mean())

        # Growth metrics
        if "earnings_growth_yoy" in fundamental_data.columns:
            valid_growth = fundamental_data[
                fundamental_data["earnings_growth_yoy"].notna()
            ]
            if not valid_growth.empty:
                metrics["avg_earnings_growth"] = float(valid_growth["earnings_growth_yoy"].mean())

        task_logger.info(f"Fundamental metrics analyzed: {metrics}")
        return metrics

    except Exception as e:
        task_logger.error(f"Error analyzing fundamental metrics: {e}")
        raise


@task(name="generate_insights")
def generate_insights(
    pnl_data: pd.DataFrame,
    technical_signals: Dict,
    fundamental_metrics: Dict,
) -> Dict:
    """
    Generate actionable insights from analysis.

    Args:
        pnl_data: P&L data
        technical_signals: Technical analysis results
        fundamental_metrics: Fundamental analysis results

    Returns:
        Dictionary with insights and recommendations
    """
    task_logger = get_run_logger()
    task_logger.info("Generating insights...")

    insights = {
        "generated_at": datetime.now().isoformat(),
        "recommendations": [],
    }

    # P&L-based insights
    if not pnl_data.empty:
        total_pnl = pnl_data["unrealized_pnl_eur"].sum()
        total_value = pnl_data["current_value_eur"].sum()
        pnl_percent = (
            (total_pnl / pnl_data["cost_basis_eur"].sum() * 100)
            if pnl_data["cost_basis_eur"].sum() > 0
            else 0
        )

        if pnl_percent > 10:
            insights["recommendations"].append(
                f"Strong portfolio performance: +{pnl_percent:.2f}% return"
            )
        elif pnl_percent < -10:
            insights["recommendations"].append(
                f"Consider reviewing losing positions: {pnl_percent:.2f}% return"
            )

        # Position concentration
        max_weight = (pnl_data["current_value_eur"] / total_value).max() * 100
        if max_weight > 25:
            insights["recommendations"].append(
                f"High position concentration detected: {max_weight:.1f}% in largest position"
            )

    # Technical-based insights
    if technical_signals.get("bollinger_oversold", 0) > 0:
        insights["recommendations"].append(
            f"Oversold opportunities: {technical_signals['bollinger_oversold']} positions below Bollinger Bands"
        )

    if technical_signals.get("bollinger_overbought", 0) > 0:
        insights["recommendations"].append(
            f"Overbought signals: {technical_signals['bollinger_overbought']} positions above Bollinger Bands"
        )

    if technical_signals.get("macd_bullish", 0) > 0:
        insights["recommendations"].append(
            f"Bullish momentum: {technical_signals['macd_bullish']} positions with bullish MACD"
        )

    # Fundamental-based insights
    if fundamental_metrics.get("avg_pe_ratio"):
        avg_pe = fundamental_metrics["avg_pe_ratio"]
        if avg_pe < 15:
            insights["recommendations"].append(
                f"Attractive valuations: Average P/E of {avg_pe:.2f}"
            )
        elif avg_pe > 25:
            insights["recommendations"].append(
                f"Premium valuations: Average P/E of {avg_pe:.2f}, consider quality"
            )

    if fundamental_metrics.get("dividend_payers", 0) > 0:
        insights["recommendations"].append(
            f"Income potential: {fundamental_metrics['dividend_payers']} dividend payers in portfolio"
        )

    task_logger.info(f"Generated {len(insights['recommendations'])} insights")
    return insights


@flow(name="enhanced_analytics_flow")
def enhanced_analytics_flow(
    email: Optional[str] = None,
    send_email_report: bool = True,
) -> Dict:
    """
    Complete enhanced analytics flow.

    Args:
        email: Email address for report delivery
        send_email_report: Whether to send email report

    Returns:
        Dictionary with analysis results
    """
    flow_logger = get_run_logger()
    flow_logger.info("Starting enhanced analytics flow...")

    try:
        # Load data
        (
            holdings_df,
            prices_dict,
            technical_data,
            fundamental_data,
        ) = load_portfolio_data()

        # Calculate technical indicators and store them
        flow_logger.info("Calculating technical indicators...")
        calculated_tech = calculate_technical_indicators(prices_dict, holdings_df)
        if not calculated_tech.empty:
            technical_data = calculated_tech
            flow_logger.info(f"Technical indicators calculated and stored: {len(technical_data)} records")

        # Analyze
        pnl_data = calculate_pnl_enhanced(holdings_df, prices_dict)
        portfolio_weights = calculate_portfolio_weights(pnl_data)
        technical_signals = analyze_technical_signals(technical_data)
        fundamental_metrics = analyze_fundamental_metrics(fundamental_data)
        insights = generate_insights(pnl_data, technical_signals, fundamental_metrics)

        # Save portfolio weights to Parquet
        if "error" not in portfolio_weights:
            try:
                db = ParquetDB()
                weights_df = pd.DataFrame([portfolio_weights])
                db.save(weights_df, "portfolio_weights")
                flow_logger.info("Portfolio weights saved to Parquet")
            except Exception as e:
                flow_logger.warning(f"Could not save portfolio weights: {e}")

        # Generate report
        report_result = generate_analytics_report(
            pnl_data=pnl_data,
            technical_data=technical_data,
            fundamental_data=fundamental_data,
            email=email,
        )

        result = {
            "status": "success",
            "pnl_data": pnl_data.to_dict("records") if not pnl_data.empty else [],
            "portfolio_weights": portfolio_weights,
            "technical_signals": technical_signals,
            "fundamental_metrics": fundamental_metrics,
            "insights": insights,
            "report": report_result,
        }

        # Send email if requested
        if send_email_report:
            email_success = send_analytics_email(
                pnl_data=pnl_data,
                technical_data=technical_data,
                fundamental_data=fundamental_data,
                portfolio_weights=portfolio_weights,
                email=email,
            )
            result["email_sent"] = email_success

        flow_logger.info("Enhanced analytics flow completed successfully")
        return result

    except Exception as e:
        flow_logger.error(f"Error in enhanced analytics flow: {e}")
        return {"status": "error", "message": str(e)}


@flow(name="send_report_email_flow")
def send_report_email_flow(email: str) -> bool:
    """
    Send analytics report via email.

    Args:
        email: Email address for delivery

    Returns:
        True if successful
    """
    flow_logger = get_run_logger()
    flow_logger.info(f"Sending analytics report to {email}...")

    try:
        # Load data
        (
            holdings_df,
            prices_dict,
            technical_data,
            fundamental_data,
        ) = load_portfolio_data()

        # Calculate P&L
        pnl_data = calculate_pnl_enhanced(holdings_df, prices_dict)

        # Send email
        success = send_analytics_email(
            pnl_data=pnl_data,
            technical_data=technical_data,
            fundamental_data=fundamental_data,
            email=email,
        )

        if success:
            flow_logger.info(f"Report sent successfully to {email}")
        else:
            flow_logger.warning(f"Failed to send report to {email}")

        return success

    except Exception as e:
        flow_logger.error(f"Error sending report email: {e}")
        return False


def generate_technical_insights(technical_signals: Dict) -> str:
    """Generate technical analysis insights summary."""
    insights = []

    if technical_signals.get("bollinger_oversold", 0) > 0:
        insights.append(
            f"📈 {technical_signals['bollinger_oversold']} oversold opportunities (Bollinger Bands)"
        )

    if technical_signals.get("bollinger_overbought", 0) > 0:
        insights.append(
            f"📉 {technical_signals['bollinger_overbought']} overbought signals (Bollinger Bands)"
        )

    if technical_signals.get("macd_bullish", 0) > 0:
        insights.append(
            f"🔼 {technical_signals['macd_bullish']} bullish momentum signals (MACD)"
        )

    return "\n".join(insights) if insights else "No significant technical signals"


def generate_fundamental_insights(fundamental_metrics: Dict) -> str:
    """Generate fundamental analysis insights summary."""
    insights = []

    if fundamental_metrics.get("avg_pe_ratio"):
        avg_pe = fundamental_metrics["avg_pe_ratio"]
        insights.append(f"Average P/E Ratio: {avg_pe:.2f}x")

    if fundamental_metrics.get("dividend_payers", 0) > 0:
        insights.append(
            f"💰 {fundamental_metrics['dividend_payers']} dividend-paying positions"
        )

    if fundamental_metrics.get("avg_roe"):
        avg_roe = fundamental_metrics["avg_roe"]
        insights.append(f"Average ROE: {avg_roe:.2f}%")

    return "\n".join(insights) if insights else "No fundamental data available"


if __name__ == "__main__":
    """
    Run enhanced analytics flow directly or serve for Prefect server.
    
    Usage:
        # Run once
        uv run python src/analytics_flows.py
        
        # Serve on Prefect server
        uv run python src/analytics_flows.py --serve
    """
    import sys
    
    if "--serve" in sys.argv:
        # Serve the flows for Prefect scheduler/UI
        print("📡 Serving enhanced_analytics_flow on Prefect server...")
        enhanced_analytics_flow.serve(
            name="Enhanced Analytics",
            description="Comprehensive portfolio analytics with technical, fundamental, and P&L analysis"
        )
    else:
        # Run once
        print("🚀 Running enhanced_analytics_flow...")
        result = enhanced_analytics_flow(send_email_report=False)
        
        if result["status"] == "success":
            print("\n✅ Analytics flow completed successfully!")
            print(f"\n📊 Results:")
            print(f"  - Positions analyzed: {len(result.get('pnl_data', []))}")
            print(f"  - Technical signals: {result.get('technical_signals', {})}")
            print(f"  - Insights: {len(result.get('insights', {}).get('recommendations', []))}")
        else:
            print(f"\n❌ Error: {result.get('message')}")
