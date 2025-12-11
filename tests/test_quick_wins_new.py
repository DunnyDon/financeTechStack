"""
Test suite for new quick wins analytics functions.

Tests the newly implemented quick wins:
- Portfolio beta visualization
- Sector rotation strategy
- Momentum screening
- Mean reversion signals
"""

import numpy as np
import pandas as pd
import pytest

from src.quick_wins_analytics import QuickWinsAnalytics


@pytest.fixture
def sample_returns_df():
    """Create sample returns data."""
    np.random.seed(42)
    dates = pd.date_range(start="2025-01-01", periods=100, freq="D")
    data = {
        "AAPL": np.random.normal(0.001, 0.02, 100),
        "MSFT": np.random.normal(0.0015, 0.018, 100),
        "GOOGL": np.random.normal(0.0008, 0.022, 100),
        "TSLA": np.random.normal(0.002, 0.03, 100),
    }
    return pd.DataFrame(data, index=dates)


@pytest.fixture
def sample_prices_df():
    """Create sample price data."""
    np.random.seed(42)
    dates = pd.date_range(start="2025-01-01", periods=100, freq="D")
    prices = {
        "AAPL": 150 + np.cumsum(np.random.normal(0.5, 2, 100)),
        "MSFT": 380 + np.cumsum(np.random.normal(0.6, 1.8, 100)),
        "GOOGL": 140 + np.cumsum(np.random.normal(0.3, 2.2, 100)),
        "TSLA": 250 + np.cumsum(np.random.normal(0.8, 3, 100)),
    }
    return pd.DataFrame(prices, index=dates)


@pytest.fixture
def market_returns():
    """Create sample market returns."""
    np.random.seed(42)
    return pd.Series(
        np.random.normal(0.001, 0.015, 100),
        index=pd.date_range(start="2025-01-01", periods=100, freq="D")
    )


@pytest.fixture
def sector_returns():
    """Create sample sector returns."""
    return {
        "Technology": 15.5,
        "Healthcare": 8.2,
        "Finance": 12.1,
        "Energy": -2.3,
        "Utilities": 3.1,
        "Consumer": 5.8,
    }


@pytest.fixture
def holding_sectors():
    """Create sample holding sectors."""
    return {
        "AAPL": "Technology",
        "MSFT": "Technology",
        "JNJ": "Healthcare",
        "JPM": "Finance",
        "XOM": "Energy",
        "PG": "Consumer",
    }


class TestPortfolioBetaVisualization:
    """Test portfolio beta visualization."""

    def test_portfolio_beta_calculation(self, sample_returns_df, market_returns):
        """Test beta calculation."""
        result = QuickWinsAnalytics.portfolio_beta_visualization(
            sample_returns_df,
            market_returns
        )
        
        assert "portfolio_beta" in result
        assert "individual_betas" in result
        assert len(result["individual_betas"]) == 4
        assert "beta_interpretation" in result
        assert result["beta_interpretation"] in ["Aggressive", "Moderate", "Conservative", "Inverse/Hedge"]

    def test_beta_has_high_and_low(self, sample_returns_df, market_returns):
        """Test that beta results include high and low beta holdings."""
        result = QuickWinsAnalytics.portfolio_beta_visualization(
            sample_returns_df,
            market_returns
        )
        
        assert "high_beta_holdings" in result
        assert "low_beta_holdings" in result


class TestSectorRotationStrategy:
    """Test sector rotation strategy."""

    def test_sector_rotation_recommendations(self, sector_returns, holding_sectors):
        """Test sector rotation recommendations."""
        result = QuickWinsAnalytics.sector_rotation_strategy(
            sector_returns,
            holding_sectors
        )
        
        assert "best_performing_sectors" in result
        assert "worst_performing_sectors" in result
        assert len(result["best_performing_sectors"]) <= 3
        assert len(result["worst_performing_sectors"]) <= 3

    def test_rotation_candidates_identified(self, sector_returns, holding_sectors):
        """Test that holdings in underperforming sectors are identified."""
        result = QuickWinsAnalytics.sector_rotation_strategy(
            sector_returns,
            holding_sectors
        )
        
        assert "candidates_for_rotation" in result
        # Energy is worst sector, should have XOM
        if "Energy" in result["candidates_for_rotation"]:
            assert "XOM" in result["candidates_for_rotation"]["Energy"]


class TestMomentumScreening:
    """Test momentum screening."""

    def test_momentum_scores_calculated(self, sample_returns_df):
        """Test momentum scores are calculated."""
        result = QuickWinsAnalytics.momentum_screening(sample_returns_df, period=20)
        
        assert "all_scores" in result
        assert len(result["all_scores"]) == 4
        for ticker, scores in result["all_scores"].items():
            assert "momentum_pct" in scores
            assert "positive_day_ratio" in scores
            assert "score" in scores
            assert "signal" in scores

    def test_momentum_signals_generated(self, sample_returns_df):
        """Test momentum signals are generated."""
        result = QuickWinsAnalytics.momentum_screening(sample_returns_df, period=20)
        
        assert "top_momentum" in result
        assert "bottom_momentum" in result
        assert all(s["signal"] in ["Strong Uptrend", "Uptrend", "Downtrend"] 
                   for s in result["all_scores"].values())


class TestMeanReversionSignals:
    """Test mean reversion signals."""

    def test_mean_reversion_signals_generated(self, sample_prices_df):
        """Test mean reversion signals are generated."""
        result = QuickWinsAnalytics.mean_reversion_signals(
            sample_prices_df,
            period=20,
            std_dev_threshold=2.0
        )
        
        assert "all_signals" in result
        assert "buy_candidates" in result
        assert "sell_candidates" in result

    def test_signal_attributes_complete(self, sample_prices_df):
        """Test signal attributes are complete."""
        result = QuickWinsAnalytics.mean_reversion_signals(
            sample_prices_df,
            period=20
        )
        
        for ticker, signal in result["all_signals"].items():
            assert "current_price" in signal
            assert "moving_average" in signal
            assert "z_score" in signal
            assert "signal" in signal
            assert "strength" in signal
            assert "deviation_pct" in signal

    def test_buy_sell_signals_identified(self, sample_prices_df):
        """Test that buy and sell signals are identified."""
        result = QuickWinsAnalytics.mean_reversion_signals(
            sample_prices_df,
            period=20,
            std_dev_threshold=2.0
        )
        
        # Should have some signals
        total_signals = len(result["all_signals"])
        assert total_signals > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
