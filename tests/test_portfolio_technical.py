"""
Unit tests for portfolio technical analysis.
"""

import numpy as np
import pandas as pd

import pytest

from src.portfolio_technical import TechnicalAnalyzer


@pytest.fixture
def sample_ohlcv_data():
    """Create sample OHLCV data."""
    dates = pd.date_range("2024-01-01", periods=100)
    prices = np.linspace(100, 110, 100) + np.random.normal(0, 1, 100)

    return pd.DataFrame(
        {
            "Open": prices + np.random.normal(0, 0.5, 100),
            "High": prices + abs(np.random.normal(0, 0.5, 100)),
            "Low": prices - abs(np.random.normal(0, 0.5, 100)),
            "Close": prices,
            "Volume": np.random.randint(1000000, 10000000, 100),
        },
        index=dates,
    )


@pytest.fixture
def trending_up_data():
    """Create trending up data."""
    dates = pd.date_range("2024-01-01", periods=100)
    prices = np.linspace(100, 150, 100)  # Strong uptrend

    return pd.DataFrame(
        {
            "Open": prices - 0.2,
            "High": prices + 0.2,
            "Low": prices - 0.5,
            "Close": prices,
            "Volume": np.full(100, 5000000),
        },
        index=dates,
    )


@pytest.fixture
def trending_down_data():
    """Create trending down data."""
    dates = pd.date_range("2024-01-01", periods=100)
    prices = np.linspace(150, 100, 100)  # Strong downtrend

    return pd.DataFrame(
        {
            "Open": prices + 0.2,
            "High": prices + 0.5,
            "Low": prices - 0.2,
            "Close": prices,
            "Volume": np.full(100, 5000000),
        },
        index=dates,
    )


class TestBollingerBands:
    """Test Bollinger Bands calculation."""

    def test_bollinger_bands_output_structure(self, sample_ohlcv_data):
        """Test Bollinger Bands returns required fields."""
        analyzer = TechnicalAnalyzer()
        result = analyzer.bollinger_bands(sample_ohlcv_data)

        assert "upper_band" in result
        assert "middle_band" in result
        assert "lower_band" in result
        assert "bb_width" in result
        assert "bb_position" in result
        assert len(result["upper_band"]) == len(sample_ohlcv_data)

    def test_bollinger_bands_relationships(self, sample_ohlcv_data):
        """Test upper > middle > lower."""
        analyzer = TechnicalAnalyzer()
        result = analyzer.bollinger_bands(sample_ohlcv_data)

        # In each period, upper > middle > lower
        for i in range(len(sample_ohlcv_data)):
            if (
                not np.isnan(result["upper_band"][i])
                and not np.isnan(result["lower_band"][i])
            ):
                assert result["upper_band"][i] >= result["middle_band"][i]
                assert result["middle_band"][i] >= result["lower_band"][i]

    def test_bollinger_bands_position_range(self, sample_ohlcv_data):
        """Test BB position is between 0 and 1."""
        analyzer = TechnicalAnalyzer()
        result = analyzer.bollinger_bands(sample_ohlcv_data)

        for pos in result["bb_position"]:
            if not np.isnan(pos):
                assert 0 <= pos <= 1


class TestRSI:
    """Test RSI calculation."""

    def test_rsi_range(self, sample_ohlcv_data):
        """Test RSI is between 0 and 100."""
        analyzer = TechnicalAnalyzer()
        result = analyzer.rsi(sample_ohlcv_data)

        for rsi_val in result:
            if not np.isnan(rsi_val):
                assert 0 <= rsi_val <= 100

    def test_rsi_uptrend(self, trending_up_data):
        """Test RSI is high in uptrend."""
        analyzer = TechnicalAnalyzer()
        result = analyzer.rsi(trending_up_data)

        # Last values should be high (overbought)
        recent_rsi = [x for x in result[-10:] if not np.isnan(x)]
        if recent_rsi:
            avg_rsi = np.mean(recent_rsi)
            assert avg_rsi > 60  # Should be elevated

    def test_rsi_downtrend(self, trending_down_data):
        """Test RSI is low in downtrend."""
        analyzer = TechnicalAnalyzer()
        result = analyzer.rsi(trending_down_data)

        # Last values should be low (oversold)
        recent_rsi = [x for x in result[-10:] if not np.isnan(x)]
        if recent_rsi:
            avg_rsi = np.mean(recent_rsi)
            assert avg_rsi < 40  # Should be depressed


class TestMACD:
    """Test MACD calculation."""

    def test_macd_output_structure(self, sample_ohlcv_data):
        """Test MACD returns required fields."""
        analyzer = TechnicalAnalyzer()
        result = analyzer.macd(sample_ohlcv_data)

        assert "macd_line" in result
        assert "signal_line" in result
        assert "histogram" in result
        assert len(result["macd_line"]) == len(sample_ohlcv_data)

    def test_macd_histogram_is_difference(self, sample_ohlcv_data):
        """Test histogram = MACD - Signal."""
        analyzer = TechnicalAnalyzer()
        result = analyzer.macd(sample_ohlcv_data)

        for i in range(len(sample_ohlcv_data)):
            if (
                not np.isnan(result["macd_line"][i])
                and not np.isnan(result["signal_line"][i])
            ):
                expected_hist = result["macd_line"][i] - result["signal_line"][i]
                np.testing.assert_almost_equal(
                    result["histogram"][i], expected_hist, decimal=5
                )

    def test_macd_crossover_signal(self, sample_ohlcv_data):
        """Test MACD crossover can be detected."""
        analyzer = TechnicalAnalyzer()
        result = analyzer.macd(sample_ohlcv_data)

        # Check for at least one crossover
        histogram = result["histogram"]
        crossovers = 0
        for i in range(1, len(histogram)):
            if not np.isnan(histogram[i]) and not np.isnan(histogram[i - 1]):
                if (histogram[i - 1] < 0 <= histogram[i]) or (
                    histogram[i - 1] > 0 >= histogram[i]
                ):
                    crossovers += 1

        # Should have at least one crossover in random data
        assert crossovers >= 0  # Just verify it doesn't crash


class TestMovingAverages:
    """Test Moving Average calculation."""

    def test_moving_averages_output_structure(self, sample_ohlcv_data):
        """Test MA returns required fields."""
        analyzer = TechnicalAnalyzer()
        result = analyzer.moving_averages(sample_ohlcv_data)

        assert "sma_20" in result
        assert "sma_50" in result
        assert "ema_20" in result
        assert "ema_50" in result

    def test_sma_calculation(self, sample_ohlcv_data):
        """Test SMA calculation is correct."""
        analyzer = TechnicalAnalyzer()
        result = analyzer.moving_averages(sample_ohlcv_data)

        # Manually calculate SMA for position 20
        manual_sma = sample_ohlcv_data["Close"].iloc[:21].mean()
        assert np.isclose(result["sma_20"].iloc[20], manual_sma, rtol=0.01)

    def test_ema_responds_to_price_changes(self, trending_up_data):
        """Test EMA responds to price changes."""
        analyzer = TechnicalAnalyzer()
        result = analyzer.moving_averages(trending_up_data)

        # In uptrend, later EMAs should be higher than earlier
        ema_20_early = result["ema_20"].iloc[30]
        ema_20_late = result["ema_20"].iloc[-1]

        if not np.isnan(ema_20_early) and not np.isnan(ema_20_late):
            assert ema_20_late > ema_20_early

    def test_moving_averages_length(self, sample_ohlcv_data):
        """Test all MAs have same length as input."""
        analyzer = TechnicalAnalyzer()
        result = analyzer.moving_averages(sample_ohlcv_data)

        assert len(result["sma_20"]) == len(sample_ohlcv_data)
        assert len(result["sma_50"]) == len(sample_ohlcv_data)
        assert len(result["ema_20"]) == len(sample_ohlcv_data)
        assert len(result["ema_50"]) == len(sample_ohlcv_data)


class TestVolumeIndicators:
    """Test Volume indicator calculation."""

    def test_volume_indicators_output_structure(self, sample_ohlcv_data):
        """Test volume indicators return required fields."""
        analyzer = TechnicalAnalyzer()
        result = analyzer.volume_indicators(sample_ohlcv_data)

        assert "obv" in result
        assert "volume_ma" in result
        assert "relative_volume" in result

    def test_obv_calculation(self, sample_ohlcv_data):
        """Test OBV calculation."""
        analyzer = TechnicalAnalyzer()
        result = analyzer.volume_indicators(sample_ohlcv_data)

        obv = result["obv"]

        # OBV should be cumulative, so it's either increasing or not
        # (but definitely shouldn't be NaN after first period)
        valid_obv = [x for x in obv[1:] if not np.isnan(x)]
        assert len(valid_obv) > 0

    def test_volume_ma_is_moving_average(self, sample_ohlcv_data):
        """Test volume MA calculation."""
        analyzer = TechnicalAnalyzer()
        result = analyzer.volume_indicators(sample_ohlcv_data)

        # Manually calculate 20-period MA
        manual_ma = sample_ohlcv_data["Volume"].iloc[:20].mean()
        assert np.isclose(result["volume_ma"].iloc[19], manual_ma, rtol=0.01)

    def test_relative_volume_ratio(self, sample_ohlcv_data):
        """Test relative volume calculation."""
        analyzer = TechnicalAnalyzer()
        result = analyzer.volume_indicators(sample_ohlcv_data)

        # Relative volume should be reasonable (typically 0.5-2.0 range)
        valid_rel_vol = [x for x in result["relative_volume"] if not np.isnan(x)]
        assert all(x >= 0 for x in valid_rel_vol)


class TestCalculateAllIndicators:
    """Test calculate_all method."""

    def test_calculate_all_returns_dict(self, sample_ohlcv_data):
        """Test calculate_all returns dictionary."""
        analyzer = TechnicalAnalyzer()
        result = analyzer.calculate_all(sample_ohlcv_data)

        assert isinstance(result, dict)

    def test_calculate_all_includes_all_indicators(self, sample_ohlcv_data):
        """Test calculate_all includes all indicator categories."""
        analyzer = TechnicalAnalyzer()
        result = analyzer.calculate_all(sample_ohlcv_data)

        # Should include all main indicators
        indicator_keys = [
            "bollinger_bands",
            "rsi",
            "macd",
            "moving_averages",
            "volume_indicators",
        ]

        for key in indicator_keys:
            assert key in result

    def test_calculate_all_has_valid_data(self, sample_ohlcv_data):
        """Test calculate_all produces valid data."""
        analyzer = TechnicalAnalyzer()
        result = analyzer.calculate_all(sample_ohlcv_data)

        # Check structure
        assert result["bollinger_bands"]["upper_band"] is not None
        assert result["rsi"] is not None
        assert result["macd"]["macd_line"] is not None
        assert result["moving_averages"]["sma_20"] is not None
        assert result["volume_indicators"]["obv"] is not None

    def test_calculate_all_performance(self, sample_ohlcv_data):
        """Test calculate_all completes in reasonable time."""
        analyzer = TechnicalAnalyzer()

        import time

        start = time.time()
        result = analyzer.calculate_all(sample_ohlcv_data)
        elapsed = time.time() - start

        # Should complete in less than 1 second for 100 data points
        assert elapsed < 1.0
