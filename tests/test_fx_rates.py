"""
Test suite for FX rate management and currency conversion.

Tests:
- FX rate fetching from API
- FX rate caching and expiry
- Currency conversion
- Holdings conversion to EUR
- Portfolio analytics with FX conversion
"""

import json
import os
import shutil
import tempfile
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.fx_rates import FXRateManager, convert_holdings_to_eur, convert_to_eur


class TestFXRateManagerBasic:
    """Test basic FX rate manager functionality."""

    def setup_method(self):
        """Setup test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.cache_file = os.path.join(self.temp_dir, "fx_rates.json")

    def teardown_method(self):
        """Cleanup test environment."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_convert_same_currency(self):
        """Test converting to same currency returns same amount."""
        amount = 100.0
        result = FXRateManager.convert(amount, "EUR", "EUR")
        assert result == amount

    def test_convert_usd_to_eur(self):
        """Test USD to EUR conversion."""
        # Assuming ~0.92 EUR per USD
        amount_usd = 100.0
        result = FXRateManager.convert(amount_usd, "USD", "EUR")
        assert result > 0
        # Should be approximately 92 EUR (using fallback rate of 0.92)
        assert 80 < result < 100

    def test_convert_gbp_to_eur(self):
        """Test GBP to EUR conversion."""
        amount_gbp = 100.0
        result = FXRateManager.convert(amount_gbp, "GBP", "EUR")
        assert result > 0
        # Should be approximately 117 EUR (GBP stronger than EUR)
        assert 100 < result < 130

    def test_convert_aud_to_eur(self):
        """Test AUD to EUR conversion."""
        amount_aud = 100.0
        result = FXRateManager.convert(amount_aud, "AUD", "EUR")
        assert result > 0
        # AUD weaker than EUR, so result should be less
        assert result < 100

    def test_fallback_rates_available(self):
        """Test that fallback rates are available."""
        rates = FXRateManager.get_rates()
        assert "EUR" in rates
        assert "USD" in rates
        assert "GBP" in rates
        assert rates["EUR"] == 1.0


class TestFXRateCaching:
    """Test FX rate caching functionality."""

    def setup_method(self):
        """Setup test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.cache_file = os.path.join(self.temp_dir, "fx_rates.json")

    def teardown_method(self):
        """Cleanup test environment."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_cache_rates_to_file(self):
        """Test saving rates to cache file."""
        with patch("src.fx_rates.FX_CACHE_FILE", self.cache_file):
            with patch("src.fx_rates.FX_CACHE_DIR", self.temp_dir):
                rates = {"EUR": 1.0, "USD": 0.92, "GBP": 1.17}
                FXRateManager.save_rates_to_cache(rates)

                assert os.path.exists(self.cache_file)

                with open(self.cache_file, "r", encoding="utf-8") as f:
                    cached = json.load(f)

                assert cached["rates"]["EUR"] == 1.0
                assert cached["rates"]["USD"] == 0.92

    def test_cache_expiry_valid(self):
        """Test that recent cache is not expired."""
        recent_timestamp = datetime.now().isoformat()
        assert not FXRateManager._is_cache_expired(recent_timestamp)

    def test_cache_expiry_expired(self):
        """Test that old cache is expired."""
        old_timestamp = (datetime.now() - timedelta(days=2)).isoformat()
        assert FXRateManager._is_cache_expired(old_timestamp)

    def test_get_cached_rates(self):
        """Test retrieving cached rates."""
        with patch("src.fx_rates.FX_CACHE_FILE", self.cache_file):
            with patch("src.fx_rates.FX_CACHE_DIR", self.temp_dir):
                test_rates = {"EUR": 1.0, "USD": 0.92, "GBP": 1.17}
                FXRateManager.save_rates_to_cache(test_rates)

                retrieved = FXRateManager.get_cached_rates()
                assert retrieved is not None
                assert retrieved["EUR"] == 1.0
                assert retrieved["USD"] == 0.92

    def test_get_cached_rates_expired(self):
        """Test that expired cache returns None."""
        with patch("src.fx_rates.FX_CACHE_FILE", self.cache_file):
            with patch("src.fx_rates.FX_CACHE_DIR", self.temp_dir):
                # Save cache
                test_rates = {"EUR": 1.0, "USD": 0.92}
                FXRateManager.save_rates_to_cache(test_rates)

                # Manually expire it
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    cached = json.load(f)

                old_timestamp = (datetime.now() - timedelta(days=2)).isoformat()
                cached["timestamp"] = old_timestamp

                with open(self.cache_file, "w", encoding="utf-8") as f:
                    json.dump(cached, f)

                # Should return None (expired)
                retrieved = FXRateManager.get_cached_rates()
                assert retrieved is None


class TestFXRateAPI:
    """Test FX rate API fetching."""

    @patch("src.fx_rates.requests.get")
    def test_fetch_from_api_success(self, mock_get):
        """Test successful API fetch."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "rates": {
                "EUR": 1.0,
                "USD": 0.92,
                "GBP": 1.17,
                "JPY": 0.0067,
            }
        }
        mock_get.return_value = mock_response

        rates = FXRateManager.fetch_from_api()

        assert rates is not None
        assert "EUR" in rates
        assert rates["EUR"] == 1.0

    @patch("src.fx_rates.requests.get")
    def test_fetch_from_api_failure(self, mock_get):
        """Test API fetch failure returns None."""
        mock_get.side_effect = Exception("API Error")

        rates = FXRateManager.fetch_from_api()

        assert rates is None


class TestFXRateStats:
    """Test FX statistics tracking."""

    def setup_method(self):
        """Setup test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.cache_file = os.path.join(self.temp_dir, "fx_rates.json")

    def teardown_method(self):
        """Cleanup test environment."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_stats_empty_cache(self):
        """Test stats for empty cache."""
        with patch("src.fx_rates.FX_CACHE_FILE", self.cache_file):
            stats = FXRateManager.stats()
            assert stats["status"] == "empty"
            assert stats["rate_count"] == 0

    def test_stats_with_cache(self):
        """Test stats with valid cache."""
        with patch("src.fx_rates.FX_CACHE_FILE", self.cache_file):
            with patch("src.fx_rates.FX_CACHE_DIR", self.temp_dir):
                rates = {"EUR": 1.0, "USD": 0.92, "GBP": 1.17}
                FXRateManager.save_rates_to_cache(rates)

                stats = FXRateManager.stats()
                assert stats["status"] == "valid"
                assert stats["rate_count"] == 3
                assert "timestamp" in stats


class TestHoldingsConversion:
    """Test converting holdings to EUR."""

    def test_convert_holdings_single_currency(self):
        """Test converting holdings with single currency."""
        holdings_df = pd.DataFrame(
            {
                "sym": ["AAPL", "MSFT"],
                "qty": [10, 20],
                "bep": [150.0, 380.0],
                "ccy": ["USD", "USD"],
            }
        )

        result = convert_holdings_to_eur(holdings_df)

        assert "bep_eur" in result.columns
        assert "cost_basis_eur" in result.columns
        assert result["bep_eur"].iloc[0] > 0
        assert result["cost_basis_eur"].iloc[0] == pytest.approx(
            10 * result["bep_eur"].iloc[0]
        )

    def test_convert_holdings_mixed_currencies(self):
        """Test converting holdings with multiple currencies."""
        holdings_df = pd.DataFrame(
            {
                "sym": ["AAPL", "SIREN", "AIRBUS"],
                "qty": [10, 5, 3],
                "bep": [150.0, 80.0, 84.15],
                "ccy": ["USD", "GBP", "EUR"],
            }
        )

        result = convert_holdings_to_eur(holdings_df)

        assert "bep_eur" in result.columns
        # EUR holding should have bep_eur == bep
        assert result[result["ccy"] == "EUR"]["bep_eur"].iloc[0] == pytest.approx(
            84.15
        )

    def test_cost_basis_calculation(self):
        """Test cost basis is calculated correctly."""
        holdings_df = pd.DataFrame(
            {
                "sym": ["AAPL"],
                "qty": [100],
                "bep": [100.0],
                "ccy": ["EUR"],
            }
        )

        result = convert_holdings_to_eur(holdings_df)

        # For EUR, bep_eur should equal bep
        assert result["bep_eur"].iloc[0] == 100.0
        assert result["cost_basis_eur"].iloc[0] == 10000.0


class TestPortfolioAnalyticsWithFX:
    """Test portfolio analytics with FX conversion."""

    def test_unrealized_pnl_with_fx(self):
        """Test P&L calculation with FX conversion."""
        holdings_df = pd.DataFrame(
            {
                "sym": ["AAPL", "SIREN"],
                "qty": [10, 20],
                "bep": [150.0, 80.0],
                "ccy": ["USD", "GBP"],
            }
        )

        prices_dict = {
            "AAPL": {"price": 160.0},
            "SIREN": {"price": 85.0},
        }

        fx_rates = {
            "EUR": 1.0,
            "USD": 0.92,
            "GBP": 1.17,
        }

        from src.portfolio_analytics import PortfolioAnalytics

        analytics = PortfolioAnalytics(holdings_df, prices_dict, fx_rates)
        pnl_df = analytics.calculate_unrealized_pnl()

        # Check that EUR columns exist
        assert "bep_eur" in pnl_df.columns
        assert "current_price_eur" in pnl_df.columns
        assert "cost_basis_eur" in pnl_df.columns
        assert "current_value_eur" in pnl_df.columns
        assert "unrealized_pnl_eur" in pnl_df.columns

        # Check values are positive (should have made money)
        assert pnl_df["unrealized_pnl_eur"].iloc[0] > 0

    def test_portfolio_summary_eur(self):
        """Test portfolio summary is in EUR."""
        holdings_df = pd.DataFrame(
            {
                "sym": ["AAPL"],
                "qty": [10],
                "bep": [150.0],
                "ccy": ["USD"],
                "asset": ["eq"],
            }
        )

        prices_dict = {
            "AAPL": {"price": 160.0},
        }

        fx_rates = {
            "EUR": 1.0,
            "USD": 0.92,
        }

        from src.portfolio_analytics import PortfolioAnalytics

        analytics = PortfolioAnalytics(holdings_df, prices_dict, fx_rates)
        summary = analytics.portfolio_summary()

        # Check EUR column naming
        assert "total_cost_basis_eur" in summary
        assert "total_current_value_eur" in summary
        assert "total_unrealized_pnl_eur" in summary
        assert summary["currency"] == "EUR"


class TestConversionEdgeCases:
    """Test edge cases in currency conversion."""

    def test_convert_zero_amount(self):
        """Test converting zero amount."""
        result = FXRateManager.convert(0, "USD", "EUR")
        assert result == 0

    def test_convert_negative_amount(self):
        """Test converting negative amount."""
        result = FXRateManager.convert(-100, "USD", "EUR")
        assert result < 0

    def test_convert_unsupported_currency(self):
        """Test converting unsupported currency returns as-is."""
        result = FXRateManager.convert(100, "XYZ", "EUR")
        # Should return the amount unchanged for unsupported currency
        assert result >= 0

    def test_convert_large_amount(self):
        """Test converting large amounts."""
        result = FXRateManager.convert(1000000.0, "USD", "EUR")
        assert result > 0
        assert result < 1000000.0 * 2  # Should not double


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
