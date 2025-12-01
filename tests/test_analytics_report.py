"""
Test suite for enhanced analytics reporting.

Tests:
- Report generation with P&L data
- Technical analysis integration
- Fundamental analysis integration
- HTML report creation
- Email configuration
"""

import pandas as pd
import pytest
from datetime import datetime

from src.analytics_report import AnalyticsReporter
from src.analytics_flows import (
    enhanced_analytics_flow,
    generate_technical_insights,
    generate_fundamental_insights,
)


class TestAnalyticsReporter:
    """Test analytics report generation."""

    def test_reporter_initialization(self):
        """Test reporter initialization with email."""
        reporter = AnalyticsReporter(email="test@example.com")
        assert reporter.email == "test@example.com"
        assert reporter.smtp_host == "smtp.gmail.com"
        assert reporter.smtp_port == 587

    def test_pnl_report_empty_data(self):
        """Test P&L report with empty data."""
        reporter = AnalyticsReporter()
        result = reporter.generate_pnl_report(pd.DataFrame())
        assert result.get("error") == "No P&L data available"

    def test_pnl_report_generation(self):
        """Test P&L report generation with sample data."""
        reporter = AnalyticsReporter()
        
        # Create sample P&L data
        pnl_data = pd.DataFrame({
            "symbol": ["AAPL", "MSFT", "GOOGL"],
            "current_value_eur": [10000, 15000, 8000],
            "cost_basis_eur": [9000, 14000, 9000],
            "unrealized_pnl_eur": [1000, 1000, -1000],
            "pnl_percent": [11.11, 7.14, -11.11],
            "asset_type": ["Equity", "Equity", "Equity"],
        })
        
        report = reporter.generate_pnl_report(pnl_data)
        
        assert report["total_positions"] == 3
        assert report["total_value_eur"] == 33000
        assert report["total_cost_basis_eur"] == 32000
        assert report["total_unrealized_pnl"] == 1000
        assert "top_gainers" in report
        assert "top_losers" in report

    def test_technical_report_bollinger_bands(self):
        """Test technical report with Bollinger Band analysis."""
        reporter = AnalyticsReporter()
        
        # Create sample technical data
        technical_data = pd.DataFrame({
            "symbol": ["AAPL", "MSFT", "GOOGL"],
            "close_price": [150, 300, 100],
            "bb_lower": [145, 290, 105],
            "bb_upper": [155, 310, 95],
            "bb_middle": [150, 300, 100],
            "rsi_14": [45, 75, 25],
            "macd": [0.5, 0.3, -0.2],
            "macd_signal": [0.4, 0.4, -0.1],
            "macd_histogram": [0.1, -0.1, -0.1],
            "sma_200": [148, 295, 102],
            "sma_50": [149, 298, 101],
            "sma_20": [151, 302, 99],
        })
        
        report = reporter.generate_technical_report(technical_data)
        
        assert "bollinger_oversold" in report or "bollinger_overbought" in report
        assert "rsi_oversold" in report or "rsi_overbought" in report

    def test_fundamental_report_generation(self):
        """Test fundamental report generation."""
        reporter = AnalyticsReporter()
        
        # Create sample fundamental data
        fundamental_data = pd.DataFrame({
            "symbol": ["AAPL", "MSFT", "GOOGL"],
            "pe_ratio": [25.5, 28.3, 22.1],
            "pb_ratio": [35.2, 15.3, 5.8],
            "ps_ratio": [8.5, 9.2, 6.3],
            "roe": [85.4, 42.1, 15.8],
            "roa": [15.2, 12.5, 8.3],
            "debt_to_equity": [1.2, 0.5, 0.3],
            "profit_margin": [25.3, 30.1, 21.5],
            "operating_margin": [28.5, 32.1, 24.3],
            "dividend_yield": [0.5, 0.8, 0.0],
            "revenue_growth_yoy": [5.2, 8.3, 9.5],
            "earnings_growth_yoy": [3.2, 5.1, 12.3],
        })
        
        report = reporter.generate_fundamental_report(fundamental_data)
        
        assert "avg_pe_ratio" in report
        assert "dividend_payers" in report
        assert report["dividend_payers"] == 2

    def test_html_report_generation(self):
        """Test HTML report generation."""
        reporter = AnalyticsReporter(email="test@example.com")
        
        # Create sample data
        pnl_data = pd.DataFrame({
            "symbol": ["AAPL"],
            "current_value_eur": [10000],
            "cost_basis_eur": [9000],
            "unrealized_pnl_eur": [1000],
            "pnl_percent": [11.11],
            "asset_type": ["Equity"],
        })
        
        pnl_report = reporter.generate_pnl_report(pnl_data)
        technical_report = {}
        fundamental_report = {}
        
        html = reporter.generate_html_report(pnl_report, technical_report, fundamental_report)
        
        assert "<html>" in html
        assert "Portfolio Analytics Report" in html
        assert "€10,000.00" in html or "10000" in html
        assert "</html>" in html

    def test_technical_insights_generation(self):
        """Test technical insights string generation."""
        technical_signals = {
            "bollinger_oversold": 2,
            "bollinger_overbought": 1,
            "macd_bullish": 3,
        }
        
        insights = generate_technical_insights(technical_signals)
        assert "oversold" in insights.lower()
        assert "overbought" in insights.lower()

    def test_fundamental_insights_generation(self):
        """Test fundamental insights string generation."""
        fundamental_metrics = {
            "avg_pe_ratio": 25.5,
            "dividend_payers": 2,
            "avg_roe": 42.1,
        }
        
        insights = generate_fundamental_insights(fundamental_metrics)
        assert "P/E" in insights or "pe" in insights.lower()
        assert "dividend" in insights.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
