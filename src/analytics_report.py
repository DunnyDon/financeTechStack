"""
Enhanced portfolio analytics report with email delivery.

Generates comprehensive reports including:
- Portfolio P&L analysis
- Technical analysis with Bollinger Band opportunities
- Fundamental analysis metrics
- Position recommendations
- Visual charts and graphs
- Email delivery with HTML formatting
"""

import io
import smtplib
from datetime import datetime, timedelta
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.figure import Figure
from prefect import get_run_logger, task

from .config import config
from .utils import get_logger

__all__ = [
    "AnalyticsReporter",
    "generate_analytics_report",
    "send_analytics_email",
]

logger = get_logger(__name__)


class AnalyticsReporter:
    """Generate comprehensive analytics reports with visualizations."""

    def __init__(self, email: Optional[str] = None):
        """
        Initialize analytics reporter.

        Args:
            email: Email address for report delivery (from config if not provided)
        """
        self.email = email or config.get("report_email")
        self.smtp_host = config.get("smtp_host", "smtp.gmail.com")
        self.smtp_port = int(config.get("smtp_port", "587"))
        self.sender_email = config.get("sender_email")
        self.sender_password = config.get("sender_password")
        self.generated_at = datetime.now()
        self.report_html = ""
        self.charts = {}

    def generate_pnl_report(self, pnl_data: pd.DataFrame) -> Dict:
        """
        Generate P&L analysis report.

        Args:
            pnl_data: DataFrame with P&L data

        Returns:
            Dictionary with P&L metrics
        """
        if pnl_data.empty:
            return {"error": "No P&L data available"}

        report = {}

        # Overall metrics
        report["total_positions"] = len(pnl_data)
        report["total_value_eur"] = pnl_data["current_value_eur"].sum()
        report["total_cost_basis_eur"] = pnl_data["cost_basis_eur"].sum()
        report["total_unrealized_pnl"] = pnl_data["unrealized_pnl_eur"].sum()
        report["total_pnl_percent"] = (
            report["total_unrealized_pnl"] / report["total_cost_basis_eur"] * 100
            if report["total_cost_basis_eur"] > 0
            else 0
        )

        # By asset type (use "asset" column if it exists, otherwise skip)
        if "asset" in pnl_data.columns:
            report["by_asset_type"] = (
                pnl_data.groupby("asset")
                .agg(
                    {
                        "current_value_eur": "sum",
                        "unrealized_pnl_eur": "sum",
                        "sym": "count",
                    }
                )
                .rename(columns={"sym": "count"})
                .to_dict("index")
            )

        # Top gainers and losers
        report["top_gainers"] = (
            pnl_data.nlargest(5, "pnl_percent")[["sym", "pnl_percent", "unrealized_pnl_eur"]].to_dict("records")
        )
        report["top_losers"] = (
            pnl_data.nsmallest(5, "pnl_percent")[["sym", "pnl_percent", "unrealized_pnl_eur"]].to_dict("records")
        )

        return report

    def generate_technical_report(self, technical_data: pd.DataFrame) -> Dict:
        """
        Generate technical analysis report.

        Args:
            technical_data: DataFrame with technical indicators

        Returns:
            Dictionary with technical metrics
        """
        if technical_data.empty:
            return {"error": "No technical data available"}

        report = {}

        # Bollinger Band opportunities
        # Only try if we have the necessary columns
        if all(col in technical_data.columns for col in ["bb_upper", "bb_lower", "bb_middle", "close_price"]):
            bb_data = technical_data.dropna(subset=["bb_upper", "bb_lower", "bb_middle"])
            if not bb_data.empty:
                # Oversold (price below lower band)
                oversold = bb_data[bb_data["close_price"] < bb_data["bb_lower"]][
                    ["symbol", "close_price", "bb_lower", "bb_upper"]
                ]
                # Overbought (price above upper band)
                overbought = bb_data[bb_data["close_price"] > bb_data["bb_upper"]][
                    ["symbol", "close_price", "bb_lower", "bb_upper"]
                ]

                report["bollinger_oversold"] = oversold.to_dict("records")
                report["bollinger_overbought"] = overbought.to_dict("records")

        # RSI signals
        rsi_data = technical_data.dropna(subset=["rsi_14"])
        if not rsi_data.empty:
            # Oversold RSI < 30
            oversold_rsi = rsi_data[rsi_data["rsi_14"] < 30][["symbol", "rsi_14"]]
            # Overbought RSI > 70
            overbought_rsi = rsi_data[rsi_data["rsi_14"] > 70][["symbol", "rsi_14"]]

            report["rsi_oversold"] = oversold_rsi.to_dict("records")
            report["rsi_overbought"] = overbought_rsi.to_dict("records")

        # MACD signals
        macd_data = technical_data.dropna(subset=["macd", "macd_signal"])
        if not macd_data.empty:
            macd_bullish = macd_data[macd_data["macd"] > macd_data["macd_signal"]][
                ["symbol", "macd", "macd_signal", "macd_histogram"]
            ]
            macd_bearish = macd_data[macd_data["macd"] < macd_data["macd_signal"]][
                ["symbol", "macd", "macd_signal", "macd_histogram"]
            ]

            report["macd_bullish"] = macd_bullish.to_dict("records")
            report["macd_bearish"] = macd_bearish.to_dict("records")

        # Moving averages - only if columns exist
        if "sma_200" in technical_data.columns:
            report["above_200_sma"] = len(technical_data[technical_data["close_price"] > technical_data["sma_200"].fillna(0)])
        if "sma_50" in technical_data.columns:
            report["above_50_sma"] = len(technical_data[technical_data["close_price"] > technical_data["sma_50"].fillna(0)])
        if "sma_20" in technical_data.columns:
            report["above_20_sma"] = len(technical_data[technical_data["close_price"] > technical_data["sma_20"].fillna(0)])

        return report

    def generate_fundamental_report(self, fundamental_data: pd.DataFrame) -> Dict:
        """
        Generate fundamental analysis report.

        Args:
            fundamental_data: DataFrame with fundamental metrics

        Returns:
            Dictionary with fundamental metrics
        """
        if fundamental_data.empty:
            return {"error": "No fundamental data available"}

        report = {}

        # Value metrics - check if columns exist
        if "pe_ratio" in fundamental_data.columns:
            report["avg_pe_ratio"] = fundamental_data["pe_ratio"].mean()
        if "pb_ratio" in fundamental_data.columns:
            report["avg_pb_ratio"] = fundamental_data["pb_ratio"].mean()
        if "ps_ratio" in fundamental_data.columns:
            report["avg_ps_ratio"] = fundamental_data["ps_ratio"].mean()

        # Quality metrics
        if "roe" in fundamental_data.columns:
            report["avg_roe"] = fundamental_data["roe"].mean()
        if "roa" in fundamental_data.columns:
            report["avg_roa"] = fundamental_data["roa"].mean()
        if "debt_to_equity" in fundamental_data.columns:
            report["avg_debt_to_equity"] = fundamental_data["debt_to_equity"].mean()

        # Profitability
        if "profit_margin" in fundamental_data.columns:
            report["avg_profit_margin"] = fundamental_data["profit_margin"].mean()
        if "operating_margin" in fundamental_data.columns:
            report["avg_operating_margin"] = fundamental_data["operating_margin"].mean()

        # Dividend yield
        if "dividend_yield" in fundamental_data.columns:
            report["avg_dividend_yield"] = fundamental_data["dividend_yield"].mean()
            report["dividend_payers"] = len(fundamental_data[fundamental_data["dividend_yield"] > 0])

        # Growth metrics
        if "revenue_growth_yoy" in fundamental_data.columns:
            report["avg_revenue_growth_yoy"] = fundamental_data["revenue_growth_yoy"].mean()
        if "earnings_growth_yoy" in fundamental_data.columns:
            report["avg_earnings_growth_yoy"] = fundamental_data["earnings_growth_yoy"].mean()

        # Value opportunities (low PE, high growth)
        if "pe_ratio" in fundamental_data.columns and "earnings_growth_yoy" in fundamental_data.columns:
            try:
                value_stocks = fundamental_data[
                    (fundamental_data["pe_ratio"] < fundamental_data["pe_ratio"].quantile(0.33))
                    & (fundamental_data["earnings_growth_yoy"] > fundamental_data["earnings_growth_yoy"].quantile(0.67))
                ]
                report["value_opportunities"] = value_stocks[["symbol", "pe_ratio", "earnings_growth_yoy"]].to_dict(
                    "records"
                )
            except Exception:
                report["value_opportunities"] = []

        # Quality stocks (high ROE, low debt)
        if "roe" in fundamental_data.columns and "debt_to_equity" in fundamental_data.columns:
            try:
                quality_stocks = fundamental_data[
                    (fundamental_data["roe"] > fundamental_data["roe"].quantile(0.67))
                    & (fundamental_data["debt_to_equity"] < fundamental_data["debt_to_equity"].quantile(0.33))
                ]
                report["quality_stocks"] = quality_stocks[["symbol", "roe", "debt_to_equity"]].to_dict("records")
            except Exception:
                report["quality_stocks"] = []

        return report

    def create_chart(self, chart_type: str, data: pd.DataFrame, title: str) -> Optional[Tuple[str, bytes]]:
        """
        Create a visualization chart.

        Args:
            chart_type: Type of chart (pie, bar, line, scatter)
            data: Data to visualize
            title: Chart title

        Returns:
            Tuple of (filename, image_bytes) or None
        """
        try:
            fig, ax = plt.subplots(figsize=(10, 6))

            if chart_type == "pie":
                ax.pie(data.values, labels=data.index, autopct="%1.1f%%")
            elif chart_type == "bar":
                data.plot(kind="bar", ax=ax)
            elif chart_type == "line":
                data.plot(kind="line", ax=ax)
            elif chart_type == "scatter":
                ax.scatter(data.index, data.values)

            ax.set_title(title, fontsize=14, fontweight="bold")
            ax.grid(True, alpha=0.3)
            plt.tight_layout()

            # Convert to bytes
            img_buffer = io.BytesIO()
            fig.savefig(img_buffer, format="png", dpi=100)
            img_buffer.seek(0)
            plt.close(fig)

            filename = f"{title.lower().replace(' ', '_')}.png"
            return filename, img_buffer.getvalue()

        except Exception as e:
            logger.error(f"Error creating chart {title}: {e}")
            return None

    def generate_html_report(
        self, pnl_report: Dict, technical_report: Dict, fundamental_report: Dict
    ) -> str:
        """
        Generate HTML report combining all analyses.

        Args:
            pnl_report: P&L analysis results
            technical_report: Technical analysis results
            fundamental_report: Fundamental analysis results

        Returns:
            HTML string for email body
        """
        html = f"""
        <html>
        <head>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    margin: 20px;
                    background-color: #f5f5f5;
                }}
                .header {{
                    background-color: #2c3e50;
                    color: white;
                    padding: 20px;
                    border-radius: 5px;
                    margin-bottom: 20px;
                }}
                .section {{
                    background-color: white;
                    padding: 15px;
                    margin: 10px 0;
                    border-left: 4px solid #3498db;
                    border-radius: 3px;
                }}
                .section h2 {{
                    color: #2c3e50;
                    margin-top: 0;
                }}
                .metric {{
                    display: inline-block;
                    margin: 10px 20px 10px 0;
                    padding: 10px;
                    background-color: #ecf0f1;
                    border-radius: 3px;
                }}
                .positive {{
                    color: #27ae60;
                    font-weight: bold;
                }}
                .negative {{
                    color: #e74c3c;
                    font-weight: bold;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin: 10px 0;
                }}
                th {{
                    background-color: #34495e;
                    color: white;
                    padding: 10px;
                    text-align: left;
                }}
                td {{
                    padding: 8px;
                    border-bottom: 1px solid #bdc3c7;
                }}
                tr:hover {{
                    background-color: #ecf0f1;
                }}
                .chart {{
                    margin: 20px 0;
                    text-align: center;
                }}
                img {{
                    max-width: 100%;
                    height: auto;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>📊 Portfolio Analytics Report</h1>
                <p>Generated on {self.generated_at.strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
        """

        # P&L Section
        if isinstance(pnl_report, dict) and "error" not in pnl_report:
            html += """
            <div class="section">
                <h2>💰 Portfolio Performance</h2>
            """
            html += f"""
                <div class="metric">
                    <strong>Total Value:</strong> €{pnl_report.get('total_value_eur', 0):,.2f}
                </div>
                <div class="metric">
                    <strong>Total Cost Basis:</strong> €{pnl_report.get('total_cost_basis_eur', 0):,.2f}
                </div>
            """
            pnl_class = "positive" if pnl_report.get("total_unrealized_pnl", 0) >= 0 else "negative"
            html += f"""
                <div class="metric {pnl_class}">
                    <strong>Total Unrealized P&L:</strong> €{pnl_report.get('total_unrealized_pnl', 0):,.2f}
                </div>
                <div class="metric {pnl_class}">
                    <strong>Total Return:</strong> {pnl_report.get('total_pnl_percent', 0):.2f}%
                </div>
            </div>
            """

            # Top Gainers
            if pnl_report.get("top_gainers"):
                html += """
                <div class="section">
                    <h2>📈 Top Gainers</h2>
                    <table>
                        <tr>
                            <th>Symbol</th>
                            <th>Return %</th>
                            <th>P&L (EUR)</th>
                        </tr>
                """
                for gainer in pnl_report["top_gainers"]:
                    html += f"""
                        <tr>
                            <td>{gainer.get('sym', gainer.get('symbol', 'N/A'))}</td>
                            <td class="positive">{gainer.get('pnl_percent', 0):.2f}%</td>
                            <td class="positive">€{gainer.get('unrealized_pnl_eur', 0):,.2f}</td>
                        </tr>
                    """
                html += "</table></div>"

            # Top Losers
            if pnl_report.get("top_losers"):
                html += """
                <div class="section">
                    <h2>📉 Top Losers</h2>
                    <table>
                        <tr>
                            <th>Symbol</th>
                            <th>Return %</th>
                            <th>P&L (EUR)</th>
                        </tr>
                """
                for loser in pnl_report["top_losers"]:
                    html += f"""
                        <tr>
                            <td>{loser.get('sym', loser.get('symbol', 'N/A'))}</td>
                            <td class="negative">{loser.get('pnl_percent', 0):.2f}%</td>
                            <td class="negative">€{loser.get('unrealized_pnl_eur', 0):,.2f}</td>
                        </tr>
                    """
                html += "</table></div>"

        # Technical Analysis Section
        if isinstance(technical_report, dict) and "error" not in technical_report:
            html += """
            <div class="section">
                <h2>📊 Technical Analysis</h2>
            """

            # Bollinger Bands
            if technical_report.get("bollinger_oversold"):
                html += """
                <h3>Bollinger Band Opportunities - Oversold</h3>
                <table>
                    <tr>
                        <th>Symbol</th>
                        <th>Price</th>
                        <th>Lower Band</th>
                        <th>Upper Band</th>
                    </tr>
                """
                for item in technical_report["bollinger_oversold"][:5]:
                    html += f"""
                    <tr>
                        <td>{item.get('symbol', 'N/A')}</td>
                        <td>€{item.get('close_price', 0):.2f}</td>
                        <td>€{item.get('bb_lower', 0):.2f}</td>
                        <td>€{item.get('bb_upper', 0):.2f}</td>
                    </tr>
                    """
                html += "</table>"

            if technical_report.get("bollinger_overbought"):
                html += """
                <h3>Bollinger Band Opportunities - Overbought</h3>
                <table>
                    <tr>
                        <th>Symbol</th>
                        <th>Price</th>
                        <th>Lower Band</th>
                        <th>Upper Band</th>
                    </tr>
                """
                for item in technical_report["bollinger_overbought"][:5]:
                    html += f"""
                    <tr>
                        <td>{item.get('symbol', 'N/A')}</td>
                        <td>€{item.get('close_price', 0):.2f}</td>
                        <td>€{item.get('bb_lower', 0):.2f}</td>
                        <td>€{item.get('bb_upper', 0):.2f}</td>
                    </tr>
                    """
                html += "</table>"

            # RSI
            if technical_report.get("rsi_oversold"):
                html += f"""
                <h3>RSI Signals</h3>
                <p>Oversold (RSI < 30): {len(technical_report['rsi_oversold'])} symbols</p>
                """
            if technical_report.get("rsi_overbought"):
                html += f"""
                <p>Overbought (RSI > 70): {len(technical_report['rsi_overbought'])} symbols</p>
                """

            # Moving Averages
            html += f"""
            <h3>Moving Averages</h3>
            <p>Above 200-day SMA: {technical_report.get('above_200_sma', 0)} symbols</p>
            <p>Above 50-day SMA: {technical_report.get('above_50_sma', 0)} symbols</p>
            <p>Above 20-day SMA: {technical_report.get('above_20_sma', 0)} symbols</p>
            </div>
            """

        # Technical Indicators Summary Section
        if isinstance(technical_report, dict) and "error" not in technical_report:
            html += """
            <div class="section">
                <h2>📊 Technical Indicators Summary</h2>
                <p style="line-height: 1.6; color: #555;">
            """
            
            summary_items = []
            
            # MACD signals
            macd_bullish = len(technical_report.get("macd_bullish", []))
            macd_bearish = len(technical_report.get("macd_bearish", []))
            if macd_bullish > 0 or macd_bearish > 0:
                summary_items.append(
                    f"<strong>MACD Signals:</strong> {macd_bullish} bullish crossovers and {macd_bearish} bearish crossovers - "
                    f"indicates {'upward momentum' if macd_bullish > macd_bearish else 'downward momentum' if macd_bearish > macd_bullish else 'mixed momentum'}"
                )
            
            # RSI signals
            rsi_oversold = len(technical_report.get("rsi_oversold", []))
            rsi_overbought = len(technical_report.get("rsi_overbought", []))
            if rsi_oversold > 0 or rsi_overbought > 0:
                summary_items.append(
                    f"<strong>RSI Conditions:</strong> {rsi_oversold} oversold opportunities (RSI < 30) and {rsi_overbought} overbought signals (RSI > 70)"
                )
            
            # Bollinger Bands
            bb_oversold = len(technical_report.get("bollinger_oversold", []))
            bb_overbought = len(technical_report.get("bollinger_overbought", []))
            if bb_oversold > 0 or bb_overbought > 0:
                summary_items.append(
                    f"<strong>Bollinger Bands:</strong> {bb_oversold} oversold signals (price below lower band) and {bb_overbought} overbought signals (price above upper band) - "
                    f"potential mean reversion opportunities"
                )
            
            # Moving averages
            sma_20 = technical_report.get("above_20_sma", 0)
            sma_50 = technical_report.get("above_50_sma", 0)
            sma_200 = technical_report.get("above_200_sma", 0)
            total_analyzed = technical_report.get("total_analyzed", 1)
            
            if total_analyzed > 0:
                pct_50 = (sma_50 / total_analyzed * 100) if total_analyzed > 0 else 0
                pct_200 = (sma_200 / total_analyzed * 100) if total_analyzed > 0 else 0
                summary_items.append(
                    f"<strong>Moving Averages:</strong> {sma_50} positions ({pct_50:.0f}%) above 50-day SMA and {sma_200} ({pct_200:.0f}%) above 200-day SMA - "
                    f"indicates {'uptrend' if pct_50 > 60 else 'mixed trend' if pct_50 > 40 else 'downtrend'}"
                )
            
            html += "<br>".join(summary_items) if summary_items else "<em>No technical signals detected</em>"
            
            html += """
                </p>
                <p style="font-size: 12px; color: #888; margin-top: 15px; font-style: italic;">
                    <strong>Technical Indicators Explanation:</strong><br>
                    • <strong>MACD:</strong> Moving Average Convergence Divergence - bullish when moving average crosses above signal line<br>
                    • <strong>RSI:</strong> Relative Strength Index (0-100) - below 30 suggests oversold (potential buy), above 70 suggests overbought (potential sell)<br>
                    • <strong>Bollinger Bands:</strong> Price deviation from moving average - price outside bands suggests mean reversion opportunity<br>
                    • <strong>Moving Averages:</strong> Trend indicator - prices above moving average suggest uptrend, below suggest downtrend
                </p>
            </div>
            """

        # Fundamental Analysis Section
        if isinstance(fundamental_report, dict) and "error" not in fundamental_report:
            html += """
            <div class="section">
                <h2>📈 Fundamental Analysis</h2>
            """
            html += f"""
                <div class="metric">
                    <strong>Average P/E Ratio:</strong> {fundamental_report.get('avg_pe_ratio', 0):.2f}
                </div>
                <div class="metric">
                    <strong>Average P/B Ratio:</strong> {fundamental_report.get('avg_pb_ratio', 0):.2f}
                </div>
                <div class="metric">
                    <strong>Average P/S Ratio:</strong> {fundamental_report.get('avg_ps_ratio', 0):.2f}
                </div>
                <div class="metric">
                    <strong>Average ROE:</strong> {fundamental_report.get('avg_roe', 0):.2f}%
                </div>
                <div class="metric">
                    <strong>Average ROA:</strong> {fundamental_report.get('avg_roa', 0):.2f}%
                </div>
                <div class="metric">
                    <strong>Average Debt/Equity:</strong> {fundamental_report.get('avg_debt_to_equity', 0):.2f}
                </div>
                <div class="metric">
                    <strong>Dividend Payers:</strong> {fundamental_report.get('dividend_payers', 0)}
                </div>
            """

            # Value Opportunities
            if fundamental_report.get("value_opportunities"):
                html += """
                <h3>Value Opportunities (Low P/E, High Growth)</h3>
                <table>
                    <tr>
                        <th>Symbol</th>
                        <th>P/E Ratio</th>
                        <th>Earnings Growth YoY</th>
                    </tr>
                """
                for item in fundamental_report["value_opportunities"][:5]:
                    html += f"""
                    <tr>
                        <td>{item.get('symbol', 'N/A')}</td>
                        <td>{item.get('pe_ratio', 0):.2f}</td>
                        <td>{item.get('earnings_growth_yoy', 0):.2f}%</td>
                    </tr>
                    """
                html += "</table>"

            # Quality Stocks
            if fundamental_report.get("quality_stocks"):
                html += """
                <h3>Quality Stocks (High ROE, Low Debt)</h3>
                <table>
                    <tr>
                        <th>Symbol</th>
                        <th>ROE</th>
                        <th>Debt/Equity</th>
                    </tr>
                """
                for item in fundamental_report["quality_stocks"][:5]:
                    html += f"""
                    <tr>
                        <td>{item.get('symbol', 'N/A')}</td>
                        <td>{item.get('roe', 0):.2f}%</td>
                        <td>{item.get('debt_to_equity', 0):.2f}</td>
                    </tr>
                    """
                html += "</table>"

            html += "</div>"

        # Fundamental Metrics Summary Section
        if isinstance(fundamental_report, dict) and "error" not in fundamental_report:
            html += """
            <div class="section">
                <h2>📊 Fundamental Analysis Summary</h2>
                <p style="line-height: 1.6; color: #555;">
            """
            
            summary_items = []
            
            # Add average P/E ratio
            if "avg_pe_ratio" in fundamental_report:
                avg_pe = fundamental_report.get("avg_pe_ratio", 0)
                summary_items.append(
                    f"<strong>Average P/E Ratio:</strong> {avg_pe:.2f}x - "
                    f"{'Undervalued' if avg_pe < 20 else 'Moderately valued' if avg_pe < 30 else 'Premium valuation'} "
                    f"compared to historical averages"
                )
            
            # Add dividend information
            if "dividend_payers" in fundamental_report:
                div_payers = fundamental_report.get("dividend_payers", 0)
                avg_div_yield = fundamental_report.get("avg_dividend_yield", 0)
                summary_items.append(
                    f"<strong>Dividend Payers:</strong> {div_payers} positions paying dividends "
                    f"with average yield of {avg_div_yield:.2%}"
                )
            
            # Add ROE information
            if "avg_roe" in fundamental_report:
                avg_roe = fundamental_report.get("avg_roe", 0)
                summary_items.append(
                    f"<strong>Average ROE:</strong> {avg_roe:.2%} - "
                    f"{'Strong profitability' if avg_roe > 0.15 else 'Moderate profitability' if avg_roe > 0.10 else 'Below average'} "
                    f"in generating returns on shareholder equity"
                )
            
            # Add ROA information
            if "avg_roa" in fundamental_report:
                avg_roa = fundamental_report.get("avg_roa", 0)
                summary_items.append(
                    f"<strong>Average ROA:</strong> {avg_roa:.2%} - "
                    f"Portfolio efficiency in using assets to generate earnings"
                )
            
            # Add P/B ratio if available
            if "avg_pb_ratio" in fundamental_report:
                avg_pb = fundamental_report.get("avg_pb_ratio", 0)
                summary_items.append(
                    f"<strong>Average P/B Ratio:</strong> {avg_pb:.2f}x - "
                    f"Price relative to book value"
                )
            
            # Add debt information
            if "avg_debt_to_equity" in fundamental_report:
                avg_dte = fundamental_report.get("avg_debt_to_equity", 0)
                summary_items.append(
                    f"<strong>Average Debt/Equity:</strong> {avg_dte:.2f}x - "
                    f"{'Conservative leverage' if avg_dte < 0.5 else 'Moderate leverage' if avg_dte < 1.0 else 'High leverage'}"
                )
            
            html += "<br>".join(summary_items)
            html += """
                </p>
                <p style="font-size: 12px; color: #888; margin-top: 15px; font-style: italic;">
                    <strong>Metrics Explanation:</strong><br>
                    • <strong>P/E Ratio:</strong> Price-to-Earnings - lower values may indicate undervaluation<br>
                    • <strong>ROE:</strong> Return on Equity - higher is better, indicates profitability<br>
                    • <strong>ROA:</strong> Return on Assets - measures asset efficiency<br>
                    • <strong>P/B Ratio:</strong> Price-to-Book - compares market value to book value<br>
                    • <strong>Debt/Equity:</strong> Financial leverage ratio - lower is less risky
                </p>
            </div>
            """

        html += """
        </body>
        </html>
        """

        return html

    def send_email(
        self, subject: str, html_body: str, attachments: Optional[Dict[str, bytes]] = None
    ) -> bool:
        """
        Send analytics report via email.

        Args:
            subject: Email subject
            html_body: HTML email body
            attachments: Dictionary of {filename: image_bytes}

        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.email:
                logger.error("No email address configured for report delivery")
                return False

            if not self.sender_email or not self.sender_password:
                logger.error("Email configuration incomplete (sender_email or sender_password missing)")
                return False

            # Create message
            msg = MIMEMultipart("related")
            msg["Subject"] = subject
            msg["From"] = self.sender_email
            msg["To"] = self.email

            # Add HTML body
            msg_alternative = MIMEMultipart("alternative")
            msg.attach(msg_alternative)
            msg_alternative.attach(MIMEText(html_body, "html"))

            # Add attachments
            if attachments and isinstance(attachments, dict):
                for filename, image_bytes in attachments.items():
                    part = MIMEImage(image_bytes, name=filename)
                    part["Content-Disposition"] = f'attachment; filename="{filename}"'
                    msg.attach(part)

            # Send email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)

            logger.info(f"Analytics report sent successfully to {self.email}")
            return True

        except Exception as e:
            logger.error(f"Error sending analytics email: {e}")
            return False


@task(name="generate_analytics_report")
def generate_analytics_report(
    pnl_data: Optional[pd.DataFrame] = None,
    technical_data: Optional[pd.DataFrame] = None,
    fundamental_data: Optional[pd.DataFrame] = None,
    email: Optional[str] = None,
) -> Dict:
    """
    Generate comprehensive analytics report.

    Args:
        pnl_data: Portfolio P&L data
        technical_data: Technical indicators
        fundamental_data: Fundamental metrics
        email: Email address for delivery

    Returns:
        Dictionary with report status and results
    """
    logger_instance = get_run_logger()
    logger_instance.info("Generating analytics report...")

    try:
        reporter = AnalyticsReporter(email)

        # Generate individual reports - handle DataFrames properly
        pnl_df = pnl_data if isinstance(pnl_data, pd.DataFrame) else pd.DataFrame()
        technical_df = technical_data if isinstance(technical_data, pd.DataFrame) else pd.DataFrame()
        fundamental_df = fundamental_data if isinstance(fundamental_data, pd.DataFrame) else pd.DataFrame()

        pnl_report = reporter.generate_pnl_report(pnl_df)
        technical_report = reporter.generate_technical_report(technical_df)
        fundamental_report = reporter.generate_fundamental_report(fundamental_df)

        # Generate HTML
        html_body = reporter.generate_html_report(pnl_report, technical_report, fundamental_report)

        result = {
            "status": "success",
            "pnl_report": pnl_report,
            "technical_report": technical_report,
            "fundamental_report": fundamental_report,
            "html": html_body,
        }

        logger_instance.info("Analytics report generated successfully")
        return result

    except Exception as e:
        logger_instance.error(f"Error generating analytics report: {e}")
        return {"status": "error", "message": str(e)}


@task(name="send_analytics_email")
def send_analytics_email(
    pnl_data: Optional[pd.DataFrame] = None,
    technical_data: Optional[pd.DataFrame] = None,
    fundamental_data: Optional[pd.DataFrame] = None,
    email: Optional[str] = None,
) -> bool:
    """
    Generate and send analytics report via email.

    Args:
        pnl_data: Portfolio P&L data
        technical_data: Technical indicators
        fundamental_data: Fundamental metrics
        email: Email address for delivery

    Returns:
        True if successful
    """
    logger_instance = get_run_logger()

    try:
        reporter = AnalyticsReporter(email)

        # Generate reports - handle DataFrames properly
        pnl_df = pnl_data if isinstance(pnl_data, pd.DataFrame) else pd.DataFrame()
        technical_df = technical_data if isinstance(technical_data, pd.DataFrame) else pd.DataFrame()
        fundamental_df = fundamental_data if isinstance(fundamental_data, pd.DataFrame) else pd.DataFrame()

        pnl_report = reporter.generate_pnl_report(pnl_df)
        technical_report = reporter.generate_technical_report(technical_df)
        fundamental_report = reporter.generate_fundamental_report(fundamental_df)

        # Generate HTML
        html_body = reporter.generate_html_report(pnl_report, technical_report, fundamental_report)

        # Send email
        subject = f"Portfolio Analytics Report - {datetime.now().strftime('%Y-%m-%d')}"
        success = reporter.send_email(subject, html_body)

        if success:
            logger_instance.info(f"Analytics report sent to {reporter.email}")
        else:
            logger_instance.warning("Failed to send analytics report")

        return success

    except Exception as e:
        logger_instance.error(f"Error in send_analytics_email: {e}")
        return False
