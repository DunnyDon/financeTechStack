"""
Unit tests for portfolio fundamental analysis.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.portfolio_fundamentals import FundamentalAnalyzer


@pytest.fixture
def fundamental_data():
    """Create sample fundamental data."""
    return {
        "revenue": 365.8e9,
        "net_income": 96.9e9,
        "total_assets": 352.7e9,
        "total_liabilities": 123.5e9,
        "current_assets": 162.1e9,
        "current_liabilities": 123.5e9,
        "stockholders_equity": 229.2e9,
    }


@pytest.fixture
def sample_holdings():
    """Create sample holdings."""
    return [
        {"symbol": "AAPL", "quantity": 10, "current_price": 150.0},
        {"symbol": "MSFT", "quantity": 5, "current_price": 380.0},
        {"symbol": "META", "quantity": 2, "current_price": 310.0},
    ]


class TestFundamentalAnalyzer:
    """Test FundamentalAnalyzer class."""

    def test_initialization(self):
        """Test analyzer initialization."""
        analyzer = FundamentalAnalyzer()

        assert analyzer is not None

    def test_calculate_net_margin(self, fundamental_data):
        """Test net margin calculation."""
        analyzer = FundamentalAnalyzer()

        net_margin = analyzer.calculate_net_margin(
            fundamental_data["net_income"], fundamental_data["revenue"]
        )

        # Net margin = net_income / revenue = 96.9B / 365.8B
        expected = (96.9e9 / 365.8e9) * 100
        assert abs(net_margin - expected) < 0.01

    def test_calculate_debt_to_equity(self, fundamental_data):
        """Test debt-to-equity ratio."""
        analyzer = FundamentalAnalyzer()

        de_ratio = analyzer.calculate_debt_to_equity(
            fundamental_data["total_liabilities"],
            fundamental_data["stockholders_equity"],
        )

        # D/E = total_liabilities / equity = 123.5B / 229.2B
        expected = 123.5e9 / 229.2e9
        assert abs(de_ratio - expected) < 0.01

    def test_calculate_current_ratio(self, fundamental_data):
        """Test current ratio."""
        analyzer = FundamentalAnalyzer()

        current_ratio = analyzer.calculate_current_ratio(
            fundamental_data["current_assets"], fundamental_data["current_liabilities"]
        )

        # Current ratio = current_assets / current_liabilities
        expected = fundamental_data["current_assets"] / fundamental_data["current_liabilities"]
        assert abs(current_ratio - expected) < 0.01

    def test_calculate_roe(self, fundamental_data):
        """Test Return on Equity."""
        analyzer = FundamentalAnalyzer()

        roe = analyzer.calculate_roe(
            fundamental_data["net_income"], fundamental_data["stockholders_equity"]
        )

        # ROE = net_income / equity = 96.9B / 229.2B
        expected = (fundamental_data["net_income"] / fundamental_data["stockholders_equity"]) * 100
        assert abs(roe - expected) < 0.01

    def test_calculate_roa(self, fundamental_data):
        """Test Return on Assets."""
        analyzer = FundamentalAnalyzer()

        roa = analyzer.calculate_roa(
            fundamental_data["net_income"], fundamental_data["total_assets"]
        )

        # ROA = net_income / total_assets = 96.9B / 352.7B
        expected = (fundamental_data["net_income"] / fundamental_data["total_assets"]) * 100
        assert abs(roa - expected) < 0.01

    def test_calculate_all_ratios(self, fundamental_data):
        """Test calculating all ratios at once."""
        analyzer = FundamentalAnalyzer()

        ratios = analyzer.calculate_all_ratios(fundamental_data)

        assert "net_margin" in ratios
        assert "debt_to_equity" in ratios
        assert "current_ratio" in ratios
        assert "roe" in ratios
        assert "roa" in ratios

        # All should be numeric
        assert all(isinstance(v, (int, float)) for v in ratios.values())


class TestFundamentalAnalyzerEdgeCases:
    """Test edge cases in fundamental analysis."""

    def test_zero_revenue(self):
        """Test handling of zero revenue."""
        analyzer = FundamentalAnalyzer()

        # Division by zero should be handled
        result = analyzer.calculate_net_margin(96.9e9, 0)
        assert result is None or result == 0

    def test_zero_equity(self):
        """Test handling of zero equity."""
        analyzer = FundamentalAnalyzer()

        # Division by zero should be handled
        result = analyzer.calculate_roe(96.9e9, 0)
        assert result is None or result == 0

    def test_negative_values(self):
        """Test handling of negative values (losses)."""
        analyzer = FundamentalAnalyzer()

        # Negative net income (loss)
        net_margin = analyzer.calculate_net_margin(-10e9, 100e9)
        assert net_margin < 0  # Should be negative

    def test_high_leverage(self):
        """Test high debt-to-equity ratio."""
        analyzer = FundamentalAnalyzer()

        # High leverage
        de_ratio = analyzer.calculate_debt_to_equity(500e9, 100e9)
        assert de_ratio == 5.0  # 500B / 100B

    def test_poor_current_ratio(self):
        """Test poor current ratio (less than 1)."""
        analyzer = FundamentalAnalyzer()

        # Current liabilities > current assets
        current_ratio = analyzer.calculate_current_ratio(50e9, 100e9)
        assert current_ratio == 0.5  # Poor liquidity

    def test_excellent_current_ratio(self):
        """Test excellent current ratio (greater than 2)."""
        analyzer = FundamentalAnalyzer()

        # Lots of liquid assets
        current_ratio = analyzer.calculate_current_ratio(300e9, 100e9)
        assert current_ratio == 3.0  # Strong liquidity


class TestRatioInterpretation:
    """Test interpretation of financial ratios."""

    def test_healthy_company_metrics(self):
        """Test ratios for a healthy company."""
        analyzer = FundamentalAnalyzer()

        # Apple-like metrics (healthy)
        data = {
            "revenue": 400e9,
            "net_income": 100e9,  # 25% net margin
            "total_assets": 350e9,
            "total_liabilities": 100e9,  # 0.44 D/E
            "current_assets": 160e9,
            "current_liabilities": 120e9,  # 1.33 current ratio
            "stockholders_equity": 250e9,
        }

        ratios = analyzer.calculate_all_ratios(data)

        # Should have healthy metrics
        assert ratios["net_margin"] > 20  # Good profitability
        assert ratios["debt_to_equity"] < 1  # Moderate leverage
        assert ratios["current_ratio"] > 1  # Can pay short-term obligations
        assert ratios["roe"] > 30  # Good return on equity
        assert ratios["roa"] > 25  # Good return on assets

    def test_struggling_company_metrics(self):
        """Test ratios for a struggling company."""
        analyzer = FundamentalAnalyzer()

        # Struggling company metrics
        data = {
            "revenue": 100e9,
            "net_income": 2e9,  # 2% net margin
            "total_assets": 500e9,
            "total_liabilities": 400e9,  # 4.0 D/E (high leverage)
            "current_assets": 50e9,
            "current_liabilities": 100e9,  # 0.5 current ratio (poor)
            "stockholders_equity": 100e9,
        }

        ratios = analyzer.calculate_all_ratios(data)

        # Should have poor metrics
        assert ratios["net_margin"] < 5  # Low profitability
        assert ratios["debt_to_equity"] > 2  # High leverage
        assert ratios["current_ratio"] < 1  # Liquidity concerns
        assert ratios["roe"] < 5  # Poor return on equity
        assert ratios["roa"] < 5  # Poor return on assets


class TestIntegrationWithPortfolio:
    """Test integration with portfolio data."""

    @patch("src.portfolio_fundamentals.xbrl.parse_xbrl_fundamentals")
    def test_portfolio_fundamentals_analysis(self, mock_parse):
        """Test analyzing fundamentals for portfolio holdings."""
        mock_parse.return_value = {
            "revenue": 365.8e9,
            "net_income": 96.9e9,
            "total_assets": 352.7e9,
            "total_liabilities": 123.5e9,
            "current_assets": 162.1e9,
            "current_liabilities": 123.5e9,
            "stockholders_equity": 229.2e9,
        }

        analyzer = FundamentalAnalyzer()

        # This would be called for a specific ticker
        result = analyzer.analyze_portfolio_fundamentals(
            [{"symbol": "AAPL", "quantity": 10, "current_price": 150.0}]
        )

        assert result is not None

    @patch("src.portfolio_fundamentals.xbrl.fetch_company_cik")
    def test_get_ticker_fundamentals(self, mock_fetch_cik):
        """Test getting fundamentals for a ticker."""
        mock_fetch_cik.return_value = ("0000320193", "Apple Inc.")

        analyzer = FundamentalAnalyzer()

        # Should handle ticker lookups
        result = analyzer.get_ticker_fundamentals("AAPL")

        # Either returns data or None, but shouldn't crash
        assert result is None or isinstance(result, dict)


class TestDataQualityHandling:
    """Test handling of data quality issues."""

    def test_missing_fundamental_data(self):
        """Test handling of incomplete fundamental data."""
        analyzer = FundamentalAnalyzer()

        # Partial data
        partial_data = {
            "revenue": 365.8e9,
            "net_income": 96.9e9,
            # Missing other fields
        }

        # Should handle gracefully
        result = analyzer.calculate_all_ratios(partial_data)

        # Should either calculate what it can or return None
        assert result is None or isinstance(result, dict)

    def test_extreme_values(self):
        """Test handling of extreme financial values."""
        analyzer = FundamentalAnalyzer()

        # Extreme values (like Berkshire Hathaway or Tesla)
        data = {
            "revenue": 1e12,  # $1 trillion revenue
            "net_income": 1e11,  # $100 billion net income
            "total_assets": 1e12,
            "total_liabilities": 1e11,
            "current_assets": 5e11,
            "current_liabilities": 2e11,
            "stockholders_equity": 9e11,
        }

        ratios = analyzer.calculate_all_ratios(data)

        # Should handle large numbers
        assert ratios is not None
        assert all(isinstance(v, (int, float)) for v in ratios.values())

    def test_ratios_within_reasonable_ranges(self):
        """Test that calculated ratios are within reasonable ranges."""
        analyzer = FundamentalAnalyzer()

        data = {
            "revenue": 100e9,
            "net_income": 20e9,  # 20% margin
            "total_assets": 200e9,
            "total_liabilities": 50e9,
            "current_assets": 100e9,
            "current_liabilities": 40e9,
            "stockholders_equity": 150e9,
        }

        ratios = analyzer.calculate_all_ratios(data)

        # All ratios should be positive and reasonable
        for ratio_name, ratio_value in ratios.items():
            if ratio_value is not None:
                # Most ratios should be between 0 and 1000 (covering outliers)
                assert 0 <= ratio_value <= 1000, f"{ratio_name} = {ratio_value}"
