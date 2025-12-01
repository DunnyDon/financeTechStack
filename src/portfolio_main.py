"""
Main portfolio analysis orchestration flow.

Comprehensive portfolio analysis workflow using Prefect that:
- Loads holdings
- Fetches current prices
- Calculates P&L
- Performs technical analysis
- Integrates fundamental analysis
- Generates comprehensive reports
"""

import json
import os
from datetime import datetime
from typing import Dict, Optional

import pandas as pd
from prefect import flow, get_run_logger, task

from .constants import DEFAULT_OUTPUT_DIR
from .portfolio_analytics import PortfolioAnalytics, calculate_pnl, calculate_portfolio_metrics
from .portfolio_fundamentals import analyze_portfolio_fundamentals
from .portfolio_holdings import Holdings, load_holdings, parse_holdings
from .portfolio_prices import fetch_multiple_prices
from .portfolio_technical import calculate_technical_indicators
from .utils import get_logger, make_request_with_backoff

__all__ = [
    "analyze_portfolio",
    "generate_portfolio_report",
]

logger = get_logger(__name__)


@task
def prepare_price_fetch_list(holdings: Holdings) -> tuple[list, dict]:
    """
    Prepare list of symbols to fetch prices for.

    Args:
        holdings: Holdings object

    Returns:
        Tuple of (symbols list, symbol to asset type mapping)
    """
    logger_instance = get_run_logger()

    df = holdings.all_holdings

    if df.empty:
        logger_instance.warning("No holdings to fetch prices for")
        return [], {}

    symbols = df["sym"].unique().tolist()
    asset_types = dict(zip(df["sym"], df["asset"]))

    logger_instance.info(f"Prepared to fetch prices for {len(symbols)} symbols")

    return symbols, asset_types


@task
def aggregate_price_data(price_results: Dict[str, Dict], holdings: Holdings) -> pd.DataFrame:
    """
    Aggregate price data with holdings.

    Args:
        price_results: Dict of symbol to price data
        holdings: Holdings object

    Returns:
        DataFrame with holdings and price data
    """
    logger_instance = get_run_logger()

    holdings_df = holdings.all_holdings.copy()

    if holdings_df.empty:
        return pd.DataFrame()

    # Extract prices
    prices_dict = {}
    for symbol, price_data in price_results.items():
        if isinstance(price_data, dict):
            if "price" in price_data:
                prices_dict[symbol] = price_data["price"]
            elif "price_usd" in price_data:
                prices_dict[symbol] = price_data["price_usd"]
            elif "price_eur" in price_data:
                prices_dict[symbol] = price_data["price_eur"]

    holdings_df["current_price"] = holdings_df["sym"].map(prices_dict)
    holdings_df["has_price"] = holdings_df["current_price"].notna()

    success_count = holdings_df["has_price"].sum()
    logger_instance.info(f"Successfully aggregated prices for {success_count}/{len(holdings_df)} holdings")

    return holdings_df


@task
def generate_html_report(
    portfolio_data: Dict, output_dir: str = DEFAULT_OUTPUT_DIR
) -> str:
    """
    Generate HTML report from portfolio data.

    Args:
        portfolio_data: Dict with portfolio analysis data
        output_dir: Output directory for report

    Returns:
        Path to generated HTML report
    """
    logger_instance = get_run_logger()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = os.path.join(output_dir, f"portfolio_report_{timestamp}.html")

    os.makedirs(output_dir, exist_ok=True)

    summary = portfolio_data.get("summary", {})
    top_performers = portfolio_data.get("top_performers", [])
    worst_performers = portfolio_data.get("worst_performers", [])
    by_asset = portfolio_data.get("by_asset_type", {})
    by_broker = portfolio_data.get("by_broker", {})

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Portfolio Analysis Report - {datetime.now().strftime('%Y-%m-%d')}</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
            .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
            h1 {{ color: #333; border-bottom: 3px solid #0066cc; padding-bottom: 10px; }}
            h2 {{ color: #0066cc; margin-top: 30px; }}
            table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
            th {{ background: #0066cc; color: white; padding: 12px; text-align: left; }}
            td {{ padding: 10px; border-bottom: 1px solid #ddd; }}
            tr:hover {{ background: #f9f9f9; }}
            .metric {{ display: inline-block; margin: 10px 20px; }}
            .metric-value {{ font-size: 24px; font-weight: bold; color: #0066cc; }}
            .metric-label {{ font-size: 12px; color: #666; text-transform: uppercase; }}
            .positive {{ color: #28a745; }}
            .negative {{ color: #dc3545; }}
            .section {{ margin: 30px 0; }}
            .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; }}
            .card {{ background: #f9f9f9; padding: 20px; border-radius: 4px; border-left: 4px solid #0066cc; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Portfolio Analysis Report</h1>
            <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>

            <div class="section">
                <h2>Portfolio Summary</h2>
                <div>
                    <div class="metric">
                        <div class="metric-label">Total Value</div>
                        <div class="metric-value">€{summary.get('total_current_value', 0):.2f}</div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">Cost Basis</div>
                        <div class="metric-value">€{summary.get('total_cost_basis', 0):.2f}</div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">Unrealized P&L</div>
                        <div class="metric-value {'positive' if summary.get('total_unrealized_pnl', 0) >= 0 else 'negative'}">
                            €{summary.get('total_unrealized_pnl', 0):.2f}
                        </div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">Return %</div>
                        <div class="metric-value {'positive' if summary.get('total_pnl_percent', 0) >= 0 else 'negative'}">
                            {summary.get('total_pnl_percent', 0):.2f}%
                        </div>
                    </div>
                </div>
            </div>

            <div class="section">
                <h2>Top Performers</h2>
                <table>
                    <tr>
                        <th>Symbol</th>
                        <th>Quantity</th>
                        <th>Current Price</th>
                        <th>Unrealized P&L</th>
                        <th>Return %</th>
                    </tr>
                    {''.join(f'''
                    <tr>
                        <td>{p.get("sym", "")}</td>
                        <td>{p.get("qty", 0):.4f}</td>
                        <td>€{p.get("current_price", 0):.2f}</td>
                        <td class="{'positive' if p.get("unrealized_pnl", 0) >= 0 else 'negative'}">
                            €{p.get("unrealized_pnl", 0):.2f}
                        </td>
                        <td class="{'positive' if p.get("pnl_percent", 0) >= 0 else 'negative'}">
                            {p.get("pnl_percent", 0):.2f}%
                        </td>
                    </tr>
                    ''' for p in top_performers[:10])}
                </table>
            </div>

            <div class="section">
                <h2>Worst Performers</h2>
                <table>
                    <tr>
                        <th>Symbol</th>
                        <th>Quantity</th>
                        <th>Current Price</th>
                        <th>Unrealized P&L</th>
                        <th>Return %</th>
                    </tr>
                    {''.join(f'''
                    <tr>
                        <td>{p.get("sym", "")}</td>
                        <td>{p.get("qty", 0):.4f}</td>
                        <td>€{p.get("current_price", 0):.2f}</td>
                        <td class="{'positive' if p.get("unrealized_pnl", 0) >= 0 else 'negative'}">
                            €{p.get("unrealized_pnl", 0):.2f}
                        </td>
                        <td class="{'positive' if p.get("pnl_percent", 0) >= 0 else 'negative'}">
                            {p.get("pnl_percent", 0):.2f}%
                        </td>
                    </tr>
                    ''' for p in worst_performers[:10])}
                </table>
            </div>

            <div class="section">
                <h2>Allocation by Asset Type</h2>
                <div class="grid">
                    {''.join(f'''
                    <div class="card">
                        <div style="font-weight: bold; color: #0066cc;">{asset_type.upper()}</div>
                        <div>Value: €{data.get("current_value", 0):.2f}</div>
                        <div>Positions: {data.get("num_positions", 0)}</div>
                        <div class="{'positive' if data.get("pnl_percent", 0) >= 0 else 'negative'}">
                            Return: {data.get("pnl_percent", 0):.2f}%
                        </div>
                    </div>
                    ''' for asset_type, data in by_asset.items())}
                </div>
            </div>

            <div class="section">
                <h2>Allocation by Broker</h2>
                <div class="grid">
                    {''.join(f'''
                    <div class="card">
                        <div style="font-weight: bold; color: #0066cc;">{broker}</div>
                        <div>Value: €{data.get("current_value", 0):.2f}</div>
                        <div>Positions: {data.get("num_positions", 0)}</div>
                        <div class="{'positive' if data.get("pnl_percent", 0) >= 0 else 'negative'}">
                            Return: {data.get("pnl_percent", 0):.2f}%
                        </div>
                    </div>
                    ''' for broker, data in by_broker.items())}
                </div>
            </div>
        </div>
    </body>
    </html>
    """

    with open(report_file, "w") as f:
        f.write(html_content)

    logger_instance.info(f"Generated HTML report: {report_file}")

    return report_file


@task
def save_portfolio_data(portfolio_data: Dict, output_dir: str = DEFAULT_OUTPUT_DIR) -> str:
    """
    Save portfolio data to JSON.

    Args:
        portfolio_data: Dict with portfolio analysis data
        output_dir: Output directory

    Returns:
        Path to saved JSON file
    """
    logger_instance = get_run_logger()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(output_dir, f"portfolio_data_{timestamp}.json")

    os.makedirs(output_dir, exist_ok=True)

    with open(output_file, "w") as f:
        json.dump(portfolio_data, f, indent=2, default=str)

    logger_instance.info(f"Saved portfolio data: {output_file}")

    return output_file


@flow(name="analyze_portfolio")
def analyze_portfolio(holdings_file: str = "holdings.csv") -> Dict:
    """
    Comprehensive portfolio analysis flow.

    Args:
        holdings_file: Path to holdings CSV file

    Returns:
        Dict with complete portfolio analysis
    """
    logger_instance = get_run_logger()
    logger_instance.info("Starting portfolio analysis flow")

    # Load holdings
    holdings = load_holdings(holdings_file)
    holdings_df = parse_holdings(holdings)

    if holdings_df.empty:
        logger_instance.error("No holdings loaded")
        return {}

    # Prepare symbols for price fetching
    symbols, asset_types = prepare_price_fetch_list(holdings)

    # Fetch prices
    price_results = fetch_multiple_prices(symbols, asset_types)

    # Aggregate data
    aggregated_df = aggregate_price_data(price_results, holdings)

    # Calculate P&L
    pnl_data = calculate_pnl(aggregated_df, price_results)

    # Calculate metrics
    metrics = calculate_portfolio_metrics(aggregated_df, price_results)

    logger_instance.info("Portfolio analysis complete")

    return {
        "holdings": holdings_df.to_dict("records"),
        "pnl": pnl_data,
        "metrics": metrics,
        "timestamp": datetime.now().isoformat(),
    }


@flow(name="generate_portfolio_report")
def generate_portfolio_report(holdings_file: str = "holdings.csv") -> Dict:
    """
    Generate comprehensive portfolio report.

    Args:
        holdings_file: Path to holdings CSV file

    Returns:
        Dict with report paths and summary
    """
    logger_instance = get_run_logger()
    logger_instance.info("Generating portfolio report")

    # Run analysis
    analysis_result = analyze_portfolio(holdings_file)

    if not analysis_result:
        logger_instance.error("Analysis failed")
        return {}

    pnl_data = analysis_result.get("pnl", {})

    # Generate reports
    html_report = generate_html_report(pnl_data)
    json_file = save_portfolio_data(analysis_result)

    logger_instance.info("Portfolio report generation complete")

    return {
        "html_report": html_report,
        "json_file": json_file,
        "summary": pnl_data.get("summary", {}),
    }
