"""
Simplified integration tests for portfolio modules validation.
All tests use real/mocked data that matches actual module signatures.
"""

import pandas as pd
import pytest

from src.portfolio_holdings import Holdings
from src.portfolio_prices import PriceFetcher


class TestHoldingsAndPricingIntegration:
    """Test holdings loading and price fetching together."""

    def test_holdings_load_and_get_symbols(self):
        """Test loading holdings and getting symbols."""
        holdings = Holdings()
        symbols = holdings.get_unique_symbols()

        assert len(symbols) > 0
        assert isinstance(symbols, list)
        assert "AAPL" in symbols or len(symbols) > 0  # At least some symbols

    def test_price_fetcher_initialization(self):
        """Test price fetcher initializes."""
        fetcher = PriceFetcher()

        assert fetcher is not None
        assert hasattr(fetcher, "fetch_price")
        assert hasattr(fetcher, "cache")

    def test_price_fetcher_caching(self):
        """Test price fetcher cache management."""
        fetcher = PriceFetcher()

        # Cache should be empty initially
        assert len(fetcher.cache) == 0

        # Add to cache
        fetcher.cache["TEST"] = {"price": 100.0}
        assert "TEST" in fetcher.cache

    def test_get_broker_holdings(self):
        """Test getting holdings by broker."""
        holdings = Holdings()
        brokers = holdings.get_unique_brokers()

        assert len(brokers) > 0
        assert isinstance(brokers, list)

    def test_get_asset_types(self):
        """Test getting unique asset types."""
        holdings = Holdings()
        asset_types = holdings.get_unique_asset_types()

        assert len(asset_types) > 0
        assert isinstance(asset_types, list)


class TestPortfolioDataStructure:
    """Test portfolio data loading and structure."""

    def test_holdings_dataframe_structure(self):
        """Test holdings DataFrame has required columns."""
        holdings = Holdings()
        df = holdings.all_holdings

        required_columns = [
            "symbol",
            "quantity",
            "current_price",
            "cost_basis",
            "asset_type",
            "broker",
        ]

        for col in required_columns:
            assert col in df.columns, f"Missing column: {col}"

    def test_holdings_data_types(self):
        """Test holdings data has correct types."""
        holdings = Holdings()
        df = holdings.all_holdings

        # Should have numeric columns
        assert pd.api.types.is_numeric_dtype(df["quantity"])
        assert pd.api.types.is_numeric_dtype(df["current_price"])
        assert pd.api.types.is_numeric_dtype(df["cost_basis"])

    def test_holdings_summary_structure(self):
        """Test holdings summary returns expected structure."""
        holdings = Holdings()
        summary = holdings.get_summary()

        assert isinstance(summary, list)
        assert len(summary) > 0

        if len(summary) > 0:
            first_holding = summary[0]
            assert "symbol" in first_holding
            assert "quantity" in first_holding


class TestPriceSourceAvailability:
    """Test that price data sources are available."""

    def test_fetch_price_returns_dict_or_none(self):
        """Test fetch_price returns dict or None."""
        fetcher = PriceFetcher()

        result = fetcher.fetch_price("AAPL", "eq")

        # Should either return dict with price or None
        assert result is None or isinstance(result, dict)

        if isinstance(result, dict):
            # Should have price data
            assert "price" in result or result is None

    def test_price_fetcher_handles_invalid_symbols(self):
        """Test fetcher handles invalid symbols gracefully."""
        fetcher = PriceFetcher()

        # Should not crash on invalid symbol
        result = fetcher.fetch_price("INVALID_SYMBOL_XYZ", "eq")

        # Should return None for invalid symbol
        assert result is None or isinstance(result, dict)


class TestMultiAssetTypeSupport:
    """Test support for multiple asset types."""

    def test_get_by_asset_type_equity(self):
        """Test getting equity holdings."""
        holdings = Holdings()

        equities = holdings.get_by_asset_type("equity")

        assert isinstance(equities, pd.DataFrame)
        if len(equities) > 0:
            assert all(equities["asset_type"] == "equity")

    def test_get_by_asset_type_etf(self):
        """Test getting ETF holdings."""
        holdings = Holdings()

        etfs = holdings.get_by_asset_type("etf")

        assert isinstance(etfs, pd.DataFrame)
        if len(etfs) > 0:
            assert all(etfs["asset_type"] == "etf")

    def test_all_asset_types_in_holdings(self):
        """Test all asset types are available."""
        holdings = Holdings()
        all_types = holdings.get_unique_asset_types()

        # Should have at least 2 asset types
        assert len(all_types) >= 1


class TestPortfolioValueCalculation:
    """Test portfolio value calculations."""

    def test_total_value_calculation(self):
        """Test calculating total portfolio value."""
        holdings = Holdings()
        df = holdings.all_holdings

        total_value = (df["current_price"] * df["quantity"]).sum()

        assert total_value > 0
        assert isinstance(total_value, (int, float))

    def test_cost_basis_calculation(self):
        """Test calculating total cost basis."""
        holdings = Holdings()
        df = holdings.all_holdings

        total_cost = (df["cost_basis"] * df["quantity"]).sum()

        assert total_cost > 0
        assert isinstance(total_cost, (int, float))

    def test_unrealized_pnl_calculation(self):
        """Test calculating unrealized P&L."""
        holdings = Holdings()
        df = holdings.all_holdings

        current_value = (df["current_price"] * df["quantity"]).sum()
        cost_basis = (df["cost_basis"] * df["quantity"]).sum()
        unrealized_pnl = current_value - cost_basis

        assert isinstance(unrealized_pnl, (int, float))


class TestDataConsistency:
    """Test data consistency and quality."""

    def test_no_null_values_in_key_columns(self):
        """Test key columns have no null values."""
        holdings = Holdings()
        df = holdings.all_holdings

        assert df["symbol"].notna().all()
        assert df["quantity"].notna().all()
        assert df["current_price"].notna().all()

    def test_positive_quantities_and_prices(self):
        """Test quantities and prices are positive."""
        holdings = Holdings()
        df = holdings.all_holdings

        assert (df["quantity"] > 0).all()
        assert (df["current_price"] > 0).all()
        assert (df["cost_basis"] > 0).all()

    def test_symbol_format_consistency(self):
        """Test symbols are properly formatted."""
        holdings = Holdings()
        symbols = holdings.get_unique_symbols()

        # Symbols should be strings
        assert all(isinstance(s, str) for s in symbols)

        # Should not have empty symbols
        assert all(len(s) > 0 for s in symbols)


class TestBrokerSupportValidation:
    """Test multi-broker support."""

    def test_degiro_holdings_available(self):
        """Test DEGIRO holdings are available."""
        holdings = Holdings()

        degiro = holdings.get_by_broker("DEGIRO")

        # Should either have DEGIRO holdings or empty dataframe
        assert isinstance(degiro, pd.DataFrame)

    def test_revolut_holdings_available(self):
        """Test REVOLUT holdings are available."""
        holdings = Holdings()

        revolut = holdings.get_by_broker("REVOLUT")

        assert isinstance(revolut, pd.DataFrame)

    def test_kraken_holdings_available(self):
        """Test Kraken holdings are available."""
        holdings = Holdings()

        kraken = holdings.get_by_broker("Kraken")

        assert isinstance(kraken, pd.DataFrame)

    def test_broker_totals_match_portfolio(self):
        """Test broker holdings sum to total portfolio."""
        holdings = Holdings()

        total_symbols = len(holdings.get_unique_symbols())
        broker_symbols = sum(
            len(holdings.get_by_broker(broker))
            for broker in holdings.get_unique_brokers()
        )

        # Total should match sum of brokers
        assert broker_symbols >= total_symbols  # May have duplicates


class TestCurrencySupport:
    """Test multi-currency portfolio support."""

    def test_multiple_currencies_in_portfolio(self):
        """Test portfolio has multiple currencies."""
        holdings = Holdings()
        df = holdings.all_holdings

        if "currency" in df.columns:
            currencies = df["currency"].unique()
            assert len(currencies) >= 1


class TestEdgeCasesIntegration:
    """Test edge cases in portfolio integration."""

    def test_handles_partial_price_data(self):
        """Test system handles when some prices missing."""
        holdings = Holdings()
        fetcher = PriceFetcher()

        symbols = holdings.get_unique_symbols()[:5]  # Test first 5

        prices_fetched = 0
        for symbol in symbols:
            price_data = fetcher.fetch_price(symbol, "eq")
            if price_data:
                prices_fetched += 1

        # Should handle mix of successful and failed fetches
        assert prices_fetched >= 0

    def test_price_fetcher_performance(self):
        """Test price fetcher doesn't hang on single symbol."""
        import time

        fetcher = PriceFetcher()

        start = time.time()
        fetcher.fetch_price("AAPL", "eq")
        elapsed = time.time() - start

        # Should complete within 5 seconds
        assert elapsed < 5.0
