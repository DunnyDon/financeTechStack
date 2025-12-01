"""
Unit tests for portfolio holdings module.
"""

import os
import tempfile
from datetime import datetime

import pandas as pd
import pytest

from src.portfolio_holdings import Holdings, load_holdings, parse_holdings


class TestHoldingsClass:
    """Test Holdings class functionality."""

    @pytest.fixture
    def sample_holdings_file(self):
        """Create sample holdings CSV for testing."""
        data = {
            "brokerName": ["DEGIRO", "REVOLUT", "DEGIRO"],
            "brokerID": ["DEG", "REVOLUT", "DEG"],
            "account": ["SKTRADE", "REVO001", "SKTRADE"],
            "sym": ["AAPL", "MSFT", "GOOGL"],
            "secName": ["Apple Inc", "Microsoft Corp", "Alphabet Inc"],
            "qty": [10.0, 5.0, 2.0],
            "bep": [150.0, 200.0, 140.0],
            "ccy": ["usd", "usd", "usd"],
            "asset": ["eq", "eq", "eq"],
            "exchange": ["nyse", "nasdaq", "nasdaq"],
        }

        df = pd.DataFrame(data)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            df.to_csv(f.name, index=False)
            yield f.name
            os.unlink(f.name)

    def test_holdings_load(self, sample_holdings_file):
        """Test loading holdings from file."""
        holdings = Holdings(sample_holdings_file)
        assert not holdings.df.empty
        assert len(holdings.df) == 3

    def test_holdings_get_by_symbol(self, sample_holdings_file):
        """Test getting holding by symbol."""
        holdings = Holdings(sample_holdings_file)
        holding = holdings.get_by_symbol("AAPL")
        assert holding is not None
        assert holding["qty"] == 10.0

    def test_holdings_get_by_broker(self, sample_holdings_file):
        """Test filtering holdings by broker."""
        holdings = Holdings(sample_holdings_file)
        degiro_holdings = holdings.get_by_broker("DEG")
        assert len(degiro_holdings) == 2

    def test_holdings_get_unique_symbols(self, sample_holdings_file):
        """Test getting unique symbols."""
        holdings = Holdings(sample_holdings_file)
        symbols = holdings.get_unique_symbols()
        assert len(symbols) == 3
        assert "AAPL" in symbols

    def test_holdings_get_summary(self, sample_holdings_file):
        """Test portfolio summary."""
        holdings = Holdings(sample_holdings_file)
        summary = holdings.get_summary()
        assert summary["total_holdings"] == 3
        assert summary["total_quantity"] == pytest.approx(17.0)
        assert summary["total_cost_basis"] == pytest.approx(
            10 * 150 + 5 * 200 + 2 * 140
        )

    def test_holdings_by_asset_type(self, sample_holdings_file):
        """Test filtering by asset type."""
        holdings = Holdings(sample_holdings_file)
        equities = holdings.get_equities()
        assert len(equities) == 3
        assert equities["asset"].unique().tolist() == ["eq"]


class TestHoldingsParsing:
    """Test holdings parsing."""

    def test_parse_holdings(self):
        """Test parsing holdings into analysis format."""
        data = {
            "brokerName": ["DEGIRO"],
            "brokerID": ["DEG"],
            "account": ["SKTRADE"],
            "sym": ["AAPL"],
            "secName": ["Apple Inc"],
            "qty": ["10.5"],  # String to test conversion
            "bep": ["150.50"],  # String to test conversion
            "ccy": ["usd"],
            "asset": ["eq"],
            "exchange": ["nyse"],
        }

        df = pd.DataFrame(data)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            df.to_csv(f.name, index=False)
            holdings = Holdings(f.name)
            parsed_df = parse_holdings(holdings)

            assert not parsed_df.empty
            assert parsed_df["qty"].dtype in [float, int]
            assert "cost_basis" in parsed_df.columns
            assert parsed_df["cost_basis"].iloc[0] == pytest.approx(10.5 * 150.50)

            os.unlink(f.name)


class TestHoldingsEdgeCases:
    """Test edge cases."""

    def test_holdings_empty_file(self):
        """Test handling of empty holdings file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("")
            f.flush()
            holdings = Holdings(f.name)
            assert holdings.df.empty
            os.unlink(f.name)

    def test_holdings_nonexistent_file(self):
        """Test handling of nonexistent file."""
        holdings = Holdings("/nonexistent/path/holdings.csv")
        assert holdings.df.empty

    def test_holdings_get_symbol_case_insensitive(self):
        """Test symbol lookup is case-insensitive."""
        data = {
            "sym": ["AAPL"],
            "qty": [10.0],
            "bep": [150.0],
            "ccy": ["usd"],
            "asset": ["eq"],
        }
        df = pd.DataFrame(data)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            df.to_csv(f.name, index=False)
            holdings = Holdings(f.name)

            # Should find regardless of case
            assert holdings.get_by_symbol("aapl") is not None
            assert holdings.get_by_symbol("AAPL") is not None
            assert holdings.get_by_symbol("AaPl") is not None

            os.unlink(f.name)
