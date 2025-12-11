"""
Tests for advanced analytics modules.

Comprehensive tests for risk, optimization, options, fixed income, and quick wins.
"""

import pytest
import pandas as pd
import numpy as np
from src.portfolio_risk import RiskAnalytics
from src.portfolio_optimization import PortfolioOptimizer, equal_weight_portfolio
from src.options_analysis import OptionsAnalysis
from src.fixed_income_analysis import FixedIncomeAnalysis, analyze_bond_position
from src.quick_wins_analytics import QuickWinsAnalytics


class TestRiskAnalytics:
    """Test risk analytics module."""

    @pytest.fixture
    def sample_prices_df(self):
        """Create sample price data."""
        dates = pd.date_range("2023-01-01", periods=252)
        data = {
            "AAPL": np.random.randn(252).cumsum() + 150,
            "MSFT": np.random.randn(252).cumsum() + 300,
            "GOOGL": np.random.randn(252).cumsum() + 100,
        }
        return pd.DataFrame(data, index=dates)

    def test_var_calculation(self, sample_prices_df):
        """Test VaR calculation."""
        ra = RiskAnalytics(sample_prices_df)
        var = ra.calculate_var(confidence=0.95)

        assert "AAPL" in var
        assert "MSFT" in var
        assert "portfolio" in var
        assert -1 < var["AAPL"] < 0  # Should be negative return

    def test_correlation_matrix(self, sample_prices_df):
        """Test correlation matrix calculation."""
        ra = RiskAnalytics(sample_prices_df)
        corr = ra.calculate_correlation_matrix()

        assert corr.shape[0] == 3
        assert corr.shape[1] == 3
        assert all(corr.iloc[i, i] == pytest.approx(1.0, abs=0.01) for i in range(3))

    def test_portfolio_volatility(self, sample_prices_df):
        """Test portfolio volatility calculation."""
        ra = RiskAnalytics(sample_prices_df)
        weights = {"AAPL": 0.33, "MSFT": 0.33, "GOOGL": 0.34}
        vol = ra.calculate_portfolio_volatility(weights)

        assert vol > 0
        assert vol < 100  # Reasonable bounds

    def test_max_drawdown(self):
        """Test max drawdown calculation."""
        ra = RiskAnalytics(pd.DataFrame({"X": [100]}))
        portfolio_values = [100, 110, 105, 95, 98, 102, 90, 92]
        dd = ra.calculate_max_drawdown(portfolio_values)

        assert dd < 0  # Should be negative
        assert dd > -20  # ~19% drawdown from peak

    def test_sharpe_ratio(self):
        """Test Sharpe ratio calculation."""
        ra = RiskAnalytics(pd.DataFrame({"X": [100]}))
        returns = [0.01] * 100  # Consistent positive returns
        sharpe = ra.calculate_sharpe_ratio(returns)

        assert sharpe > 0

    def test_concentration_risk(self):
        """Test concentration risk metrics."""
        ra = RiskAnalytics(pd.DataFrame({"X": [100]}))
        weights = {"AAPL": 0.7, "MSFT": 0.2, "GOOGL": 0.1}
        conc = ra.calculate_concentration_risk(weights)

        assert "hhi" in conc
        assert "top_3_concentration" in conc
        assert conc["hhi"] > 0.25  # Should be concentrated


class TestPortfolioOptimizer:
    """Test portfolio optimization module."""

    @pytest.fixture
    def sample_returns_df(self):
        """Create sample returns data."""
        dates = pd.date_range("2023-01-01", periods=252)
        data = {
            "AAPL": np.random.randn(252) * 0.02,
            "MSFT": np.random.randn(252) * 0.018,
            "GOOGL": np.random.randn(252) * 0.025,
        }
        return pd.DataFrame(data, index=dates)

    def test_minimum_variance_portfolio(self, sample_returns_df):
        """Test minimum variance portfolio calculation."""
        opt = PortfolioOptimizer(sample_returns_df)
        result = opt.minimum_variance_portfolio(["AAPL", "MSFT", "GOOGL"])

        assert len(result.weights) == 3
        assert abs(sum(result.weights.values()) - 1.0) < 0.01
        assert result.expected_volatility > 0

    def test_maximum_sharpe_portfolio(self, sample_returns_df):
        """Test maximum Sharpe ratio portfolio."""
        opt = PortfolioOptimizer(sample_returns_df)
        result = opt.maximum_sharpe_ratio_portfolio(["AAPL", "MSFT", "GOOGL"])

        assert len(result.weights) == 3
        assert abs(sum(result.weights.values()) - 1.0) < 0.01
        assert result.sharpe_ratio >= 0

    def test_efficient_frontier(self, sample_returns_df):
        """Test efficient frontier calculation."""
        opt = PortfolioOptimizer(sample_returns_df)
        frontier = opt.efficient_frontier(["AAPL", "MSFT", "GOOGL"], num_points=10)

        assert "volatilities" in frontier
        assert "returns" in frontier
        assert len(frontier["volatilities"]) > 0

    def test_rebalancing_recommendations(self):
        """Test rebalancing recommendations."""
        opt = PortfolioOptimizer(pd.DataFrame({"X": [0.01]}))
        current = {"AAPL": 0.4, "MSFT": 0.3, "GOOGL": 0.3}
        target = {"AAPL": 0.33, "MSFT": 0.33, "GOOGL": 0.34}

        recs = opt.rebalancing_recommendations(current, target, threshold=0.05)

        # Should recommend buying MSFT/GOOGL and selling AAPL
        assert len(recs) > 0

    def test_equal_weight_portfolio(self):
        """Test equal weight portfolio."""
        weights = equal_weight_portfolio(["AAPL", "MSFT", "GOOGL"])

        assert len(weights) == 3
        assert abs(sum(weights.values()) - 1.0) < 0.01
        assert all(w == pytest.approx(1 / 3, abs=0.01) for w in weights.values())


class TestOptionsAnalysis:
    """Test options analysis module."""

    def test_greeks_calculation(self):
        """Test Greeks calculation."""
        greeks = OptionsAnalysis.calculate_greeks(
            spot_price=100, strike_price=100, time_to_expiry=0.25, volatility=0.20
        )

        assert -1 <= greeks.delta <= 1
        assert greeks.gamma >= 0
        assert -1 <= greeks.vega <= 1
        assert greeks.theta is not None

    def test_greeks_call_vs_put(self):
        """Test difference between call and put Greeks."""
        call_greeks = OptionsAnalysis.calculate_greeks(
            spot_price=100, strike_price=100, time_to_expiry=0.25, volatility=0.20, option_type="call"
        )

        put_greeks = OptionsAnalysis.calculate_greeks(
            spot_price=100, strike_price=100, time_to_expiry=0.25, volatility=0.20, option_type="put"
        )

        # Call delta should be positive, put delta negative
        assert call_greeks.delta > 0
        assert put_greeks.delta < 0

    def test_implied_volatility_estimation(self):
        """Test implied volatility calculation."""
        # Use known option price
        iv = OptionsAnalysis.estimate_implied_volatility(
            option_price=10, spot_price=100, strike_price=100, time_to_expiry=0.25, option_type="call"
        )

        assert 0.01 <= iv <= 2.0  # Reasonable IV range

    def test_position_analysis(self):
        """Test option position analysis."""
        positions = [
            {"type": "call", "strike": 100, "quantity": 1, "expiry_days": 30},
            {"type": "put", "strike": 95, "quantity": 1, "expiry_days": 30},
        ]

        analysis = OptionsAnalysis.analyze_position(positions, spot_price=100)

        assert "aggregate_greeks" in analysis
        assert "portfolio_delta" in analysis
        assert analysis["portfolio_delta"] is not None


class TestFixedIncomeAnalysis:
    """Test fixed income analysis module."""

    def test_bond_price_calculation(self):
        """Test bond price calculation."""
        price = FixedIncomeAnalysis.calculate_bond_price(
            face_value=1000, coupon_rate=0.05, years_to_maturity=5, yield_to_maturity=0.04
        )

        # Price should be above par since coupon > yield
        assert price > 1000

    def test_ytm_calculation(self):
        """Test YTM calculation."""
        ytm = FixedIncomeAnalysis.calculate_ytm_simple(
            current_price=950, face_value=1000, coupon_rate=0.05, years_to_maturity=5
        )

        assert 0 < ytm < 0.15
        # YTM should be above coupon since price is below par
        assert ytm > 0.05

    def test_duration_calculation(self):
        """Test duration calculation."""
        mac_dur, mod_dur, eff_dur = FixedIncomeAnalysis.calculate_duration(
            face_value=1000, coupon_rate=0.05, years_to_maturity=5, yield_to_maturity=0.04
        )

        assert mac_dur > 0
        assert mod_dur > 0
        assert mod_dur < mac_dur  # Modified < Macaulay

    def test_convexity_calculation(self):
        """Test convexity calculation."""
        convexity = FixedIncomeAnalysis.calculate_convexity(
            face_value=1000, coupon_rate=0.05, years_to_maturity=5, yield_to_maturity=0.04
        )

        assert convexity > 0

    def test_yield_curve_building(self):
        """Test yield curve analysis."""
        maturities = [1, 2, 3, 5, 10]
        yields = [0.02, 0.025, 0.03, 0.035, 0.04]

        curve = FixedIncomeAnalysis.build_yield_curve(maturities, yields)

        assert "slope" in curve
        assert curve["inverted"] == False  # Upward sloping


class TestQuickWinsAnalytics:
    """Test quick wins analytics module."""

    def test_sector_allocation(self):
        """Test sector allocation calculation."""
        holdings = {
            "AAPL": {"quantity": 10, "price": 150, "sector": "Technology"},
            "JPM": {"quantity": 5, "price": 150, "sector": "Finance"},
            "MSFT": {"quantity": 8, "price": 300, "sector": "Technology"},
        }

        allocation = QuickWinsAnalytics.sector_allocation(holdings)

        assert "Technology" in allocation
        assert "Finance" in allocation
        # Tech should be ~70%
        assert allocation["Technology"] > 65

    def test_asset_class_breakdown(self):
        """Test asset class breakdown."""
        holdings = {
            "AAPL": {"quantity": 10, "price": 150, "asset_class": "equity"},
            "BTC": {"quantity": 0.5, "price": 40000, "asset_class": "crypto"},
        }

        breakdown = QuickWinsAnalytics.asset_class_breakdown(holdings)

        assert "equity" in breakdown
        assert "crypto" in breakdown

    def test_portfolio_volatility(self):
        """Test portfolio volatility."""
        returns = [0.01, -0.02, 0.015, -0.01, 0.012]
        vol = QuickWinsAnalytics.portfolio_volatility(returns)

        assert vol > 0
        assert vol < 100  # Reasonable bounds

    def test_dividend_projection(self):
        """Test dividend income projection."""
        holdings = {
            "JPM": {"quantity": 100, "price": 150, "dividend_yield": 0.03},
            "KO": {"quantity": 50, "price": 60, "dividend_yield": 0.025},
        }

        projection = QuickWinsAnalytics.dividend_income_projection(holdings, annual_projection=True)

        assert "projected_income" in projection
        assert projection["projected_income"] > 0

    def test_winners_losers(self):
        """Test winners/losers report."""
        positions = {
            "AAPL": {"entry_price": 100, "current_price": 150},
            "MSFT": {"entry_price": 200, "current_price": 180},
            "GOOGL": {"entry_price": 1000, "current_price": 1200},
        }

        report = QuickWinsAnalytics.winners_losers_report(positions, top_n=2)

        assert len(report["winners"]) == 2
        assert len(report["losers"]) == 2
        assert report["winners"][0]["pnl_pct"] > report["losers"][0]["pnl_pct"]

    def test_correlation_matrix(self):
        """Test correlation matrix summary."""
        dates = pd.date_range("2023-01-01", periods=100)
        prices = pd.DataFrame(
            {
                "AAPL": np.random.randn(100).cumsum() + 100,
                "MSFT": np.random.randn(100).cumsum() + 100,
                "GOOGL": np.random.randn(100).cumsum() + 100,
            },
            index=dates,
        )

        summary = QuickWinsAnalytics.correlation_matrix_summary(prices)

        assert "correlation_matrix" in summary
        assert "top_positive_correlations" in summary

    def test_concentration_risk(self):
        """Test concentration risk metrics."""
        weights = {"AAPL": 0.6, "MSFT": 0.25, "GOOGL": 0.15}
        metrics = QuickWinsAnalytics.concentration_risk_metrics(weights)

        assert "hhi_index" in metrics
        assert "top_1_concentration" in metrics
        assert metrics["is_concentrated"] == True

    def test_sharpe_ratio(self):
        """Test Sharpe ratio calculation."""
        returns = [0.01] * 100  # Consistent positive returns
        sharpe = QuickWinsAnalytics.sharpe_ratio_calculation(returns)

        assert sharpe > 0

    def test_portfolio_summary(self):
        """Test portfolio summary statistics."""
        holdings = {"AAPL": 10, "MSFT": 5}
        prices = {"AAPL": 150, "MSFT": 300}

        summary = QuickWinsAnalytics.portfolio_summary_statistics(holdings, prices)

        assert "total_portfolio_value" in summary
        assert summary["total_portfolio_value"] == 3000  # 10*150 + 5*300
        assert summary["num_holdings"] == 2
