"""
Unit tests for portfolio analytics and P&L tracking.
"""

import numpy as np
import pandas as pd

import pytest

from src.portfolio_analytics import PortfolioAnalytics


@pytest.fixture
def sample_holdings_df():
    """Create sample holdings data."""
    return pd.DataFrame(
        {
            "symbol": ["AAPL", "MSFT", "GOOGL", "TSLA", "META"],
            "current_price": [150.0, 380.0, 140.0, 250.0, 310.0],
            "cost_basis": [140.0, 370.0, 145.0, 260.0, 300.0],
            "quantity": [10, 5, 8, 4, 2],
            "asset_type": ["equity", "equity", "equity", "equity", "equity"],
            "broker": ["DEGIRO", "DEGIRO", "REVOLUT", "REVOLUT", "KRAKEN"],
            "currency": ["USD", "USD", "USD", "USD", "USD"],
        }
    )


@pytest.fixture
def mixed_holdings_df():
    """Create mixed asset type holdings."""
    return pd.DataFrame(
        {
            "symbol": ["AAPL", "VTSAX", "BTC", "GLD", "SPY"],
            "current_price": [150.0, 95.0, 45000.0, 195.0, 450.0],
            "cost_basis": [140.0, 90.0, 40000.0, 200.0, 440.0],
            "quantity": [10, 50, 0.5, 20, 10],
            "asset_type": ["equity", "fund", "crypto", "etf", "etf"],
            "broker": ["DEGIRO", "DEGIRO", "KRAKEN", "DEGIRO", "REVOLUT"],
            "currency": ["USD", "USD", "USD", "USD", "USD"],
        }
    )


class TestPortfolioAnalytics:
    """Test PortfolioAnalytics class."""

    def test_initialization(self, sample_holdings_df):
        """Test analytics initialization."""
        analytics = PortfolioAnalytics(sample_holdings_df)

        assert analytics.holdings is not None
        assert len(analytics.holdings) == 5

    def test_unrealized_pnl_calculation(self, sample_holdings_df):
        """Test unrealized P&L calculation."""
        analytics = PortfolioAnalytics(sample_holdings_df)
        pnl = analytics.calculate_unrealized_pnl()

        # AAPL: (150-140)*10 = 100
        # MSFT: (380-370)*5 = 50
        # GOOGL: (140-145)*8 = -40
        # TSLA: (250-260)*4 = -40
        # META: (310-300)*2 = 20

        assert "symbol" in pnl
        assert "quantity" in pnl
        assert "unrealized_pnl" in pnl
        assert "unrealized_pnl_pct" in pnl

        # Check specific values
        aapl_row = pnl[pnl["symbol"] == "AAPL"].iloc[0]
        assert aapl_row["unrealized_pnl"] == 100.0

    def test_total_portfolio_pnl(self, sample_holdings_df):
        """Test total portfolio P&L."""
        analytics = PortfolioAnalytics(sample_holdings_df)
        summary = analytics.portfolio_summary()

        # Total should be: 100 + 50 - 40 - 40 + 20 = 90
        assert summary["total_unrealized_pnl"] == 90.0

    def test_portfolio_value_calculation(self, sample_holdings_df):
        """Test portfolio value calculation."""
        analytics = PortfolioAnalytics(sample_holdings_df)
        summary = analytics.portfolio_summary()

        # Total current value
        expected_current = 150 * 10 + 380 * 5 + 140 * 8 + 250 * 4 + 310 * 2
        # 1500 + 1900 + 1120 + 1000 + 620 = 6140

        assert summary["total_current_value"] == expected_current

    def test_portfolio_cost_basis(self, sample_holdings_df):
        """Test portfolio cost basis calculation."""
        analytics = PortfolioAnalytics(sample_holdings_df)
        summary = analytics.portfolio_summary()

        # Total cost basis
        expected_cost = 140 * 10 + 370 * 5 + 145 * 8 + 260 * 4 + 300 * 2
        # 1400 + 1850 + 1160 + 1040 + 600 = 6050

        assert summary["total_cost_basis"] == expected_cost

    def test_portfolio_return_percentage(self, sample_holdings_df):
        """Test portfolio return percentage."""
        analytics = PortfolioAnalytics(sample_holdings_df)
        summary = analytics.portfolio_summary()

        # 90 / 6050 = 0.01488...
        expected_return_pct = (90 / 6050) * 100
        assert np.isclose(summary["total_return_pct"], expected_return_pct, rtol=0.01)

    def test_pnl_by_asset_type(self, mixed_holdings_df):
        """Test P&L breakdown by asset type."""
        analytics = PortfolioAnalytics(mixed_holdings_df)
        pnl_by_type = analytics.pnl_by_asset_type()

        assert "asset_type" in pnl_by_type
        assert "total_pnl" in pnl_by_type
        assert "avg_return_pct" in pnl_by_type

    def test_pnl_by_broker(self, mixed_holdings_df):
        """Test P&L breakdown by broker."""
        analytics = PortfolioAnalytics(mixed_holdings_df)
        pnl_by_broker = analytics.pnl_by_broker()

        assert "broker" in pnl_by_broker
        assert "total_pnl" in pnl_by_broker
        assert "position_count" in pnl_by_broker

    def test_win_rate_calculation(self, sample_holdings_df):
        """Test win rate calculation."""
        analytics = PortfolioAnalytics(sample_holdings_df)
        summary = analytics.portfolio_summary()

        # Profitable: AAPL, MSFT, META = 3/5 = 60%
        assert summary["win_rate_pct"] == 60.0

    def test_top_performers(self, sample_holdings_df):
        """Test identifying top performers."""
        analytics = PortfolioAnalytics(sample_holdings_df)
        top = analytics.top_performers(n=2)

        assert len(top) == 2
        assert top.iloc[0]["symbol"] == "AAPL"  # +100 USD
        assert top.iloc[1]["symbol"] == "MSFT"  # +50 USD

    def test_worst_performers(self, sample_holdings_df):
        """Test identifying worst performers."""
        analytics = PortfolioAnalytics(sample_holdings_df)
        worst = analytics.worst_performers(n=2)

        assert len(worst) == 2
        # Should be TSLA and GOOGL (both -40)
        worst_symbols = set(worst["symbol"].values)
        assert "TSLA" in worst_symbols
        assert "GOOGL" in worst_symbols

    def test_position_weights(self, sample_holdings_df):
        """Test portfolio position weights."""
        analytics = PortfolioAnalytics(sample_holdings_df)
        summary = analytics.portfolio_summary()

        assert "position_weights" in summary
        weights = summary["position_weights"]

        # Weights should sum to 100%
        total_weight = sum(weights.values())
        assert np.isclose(total_weight, 100.0, rtol=0.01)

    def test_position_weight_calculation(self, sample_holdings_df):
        """Test individual position weight calculation."""
        analytics = PortfolioAnalytics(sample_holdings_df)
        summary = analytics.portfolio_summary()

        weights = summary["position_weights"]

        # AAPL: 1500 / 6140 = 24.43%
        expected_aapl_weight = (1500 / 6140) * 100
        assert np.isclose(weights["AAPL"], expected_aapl_weight, rtol=0.01)


class TestPortfolioAnalyticsEdgeCases:
    """Test edge cases in portfolio analytics."""

    def test_all_positions_profitable(self):
        """Test portfolio where all positions are profitable."""
        df = pd.DataFrame(
            {
                "symbol": ["A", "B", "C"],
                "current_price": [110.0, 120.0, 105.0],
                "cost_basis": [100.0, 100.0, 100.0],
                "quantity": [1, 1, 1],
                "asset_type": ["equity", "equity", "equity"],
                "broker": ["DEGIRO", "DEGIRO", "DEGIRO"],
                "currency": ["USD", "USD", "USD"],
            }
        )

        analytics = PortfolioAnalytics(df)
        summary = analytics.portfolio_summary()

        assert summary["win_rate_pct"] == 100.0

    def test_all_positions_losing(self):
        """Test portfolio where all positions are losing."""
        df = pd.DataFrame(
            {
                "symbol": ["A", "B", "C"],
                "current_price": [90.0, 80.0, 95.0],
                "cost_basis": [100.0, 100.0, 100.0],
                "quantity": [1, 1, 1],
                "asset_type": ["equity", "equity", "equity"],
                "broker": ["DEGIRO", "DEGIRO", "DEGIRO"],
                "currency": ["USD", "USD", "USD"],
            }
        )

        analytics = PortfolioAnalytics(df)
        summary = analytics.portfolio_summary()

        assert summary["win_rate_pct"] == 0.0

    def test_breakeven_position(self):
        """Test position at breakeven."""
        df = pd.DataFrame(
            {
                "symbol": ["A", "B"],
                "current_price": [100.0, 90.0],
                "cost_basis": [100.0, 100.0],
                "quantity": [1, 1],
                "asset_type": ["equity", "equity"],
                "broker": ["DEGIRO", "DEGIRO"],
                "currency": ["USD", "USD"],
            }
        )

        analytics = PortfolioAnalytics(df)
        summary = analytics.portfolio_summary()

        # One at breakeven (0%), one losing (-10%)
        # Win rate should count only positive
        assert summary["win_rate_pct"] == 0.0

    def test_single_position_portfolio(self):
        """Test portfolio with single position."""
        df = pd.DataFrame(
            {
                "symbol": ["AAPL"],
                "current_price": [150.0],
                "cost_basis": [140.0],
                "quantity": [10],
                "asset_type": ["equity"],
                "broker": ["DEGIRO"],
                "currency": ["USD"],
            }
        )

        analytics = PortfolioAnalytics(df)
        summary = analytics.portfolio_summary()

        assert summary["position_count"] == 1
        assert summary["total_unrealized_pnl"] == 100.0

    def test_zero_quantity_positions(self):
        """Test handling of zero quantity positions."""
        df = pd.DataFrame(
            {
                "symbol": ["AAPL", "MSFT"],
                "current_price": [150.0, 380.0],
                "cost_basis": [140.0, 370.0],
                "quantity": [0, 5],
                "asset_type": ["equity", "equity"],
                "broker": ["DEGIRO", "DEGIRO"],
                "currency": ["USD", "USD"],
            }
        )

        analytics = PortfolioAnalytics(df)
        summary = analytics.portfolio_summary()

        # Should only count MSFT
        assert summary["position_count"] == 1


class TestPortfolioAnalyticsNumerics:
    """Test numeric accuracy in calculations."""

    def test_floating_point_precision(self):
        """Test floating point precision in calculations."""
        df = pd.DataFrame(
            {
                "symbol": ["A", "B", "C"],
                "current_price": [100.123, 200.456, 300.789],
                "cost_basis": [99.876, 199.234, 299.111],
                "quantity": [1.5, 2.3, 3.7],
                "asset_type": ["equity", "equity", "equity"],
                "broker": ["DEGIRO", "DEGIRO", "DEGIRO"],
                "currency": ["USD", "USD", "USD"],
            }
        )

        analytics = PortfolioAnalytics(df)
        pnl = analytics.calculate_unrealized_pnl()

        # All should have some PnL
        assert all(pnl["unrealized_pnl"] > 0)

    def test_large_position_values(self):
        """Test calculations with large position values."""
        df = pd.DataFrame(
            {
                "symbol": ["AAPL"],
                "current_price": [150.0],
                "cost_basis": [140.0],
                "quantity": [1000000],  # 1 million shares
                "asset_type": ["equity"],
                "broker": ["DEGIRO"],
                "currency": ["USD"],
            }
        )

        analytics = PortfolioAnalytics(df)
        summary = analytics.portfolio_summary()

        # Should handle large numbers
        assert summary["total_current_value"] == 150000000.0
        assert summary["total_unrealized_pnl"] == 10000000.0

    def test_small_position_values(self):
        """Test calculations with small position values."""
        df = pd.DataFrame(
            {
                "symbol": ["BTC"],
                "current_price": [45000.0],
                "cost_basis": [44000.0],
                "quantity": [0.0001],  # 0.0001 BTC
                "asset_type": ["crypto"],
                "broker": ["KRAKEN"],
                "currency": ["USD"],
            }
        )

        analytics = PortfolioAnalytics(df)
        summary = analytics.portfolio_summary()

        # Should handle small fractions
        assert summary["total_unrealized_pnl"] > 0
