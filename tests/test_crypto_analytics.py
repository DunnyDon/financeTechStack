"""
Test suite for Crypto Advanced Analytics

Tests for:
- On-chain metrics
- Market structure analysis
- Correlation analysis
- Volatility analysis
- Portfolio risk metrics
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.crypto_analytics import CryptoAdvancedAnalytics


@pytest.fixture
def analytics():
    """Create crypto analytics instance."""
    return CryptoAdvancedAnalytics()


@pytest.fixture
def sample_price_data():
    """Generate sample price data for multiple assets."""
    dates = pd.date_range(start='2023-01-01', periods=252, freq='D')
    
    return {
        'BTC': pd.Series(
            40000 + np.cumsum(np.random.randn(252) * 500),
            index=dates
        ),
        'ETH': pd.Series(
            2000 + np.cumsum(np.random.randn(252) * 50),
            index=dates
        ),
        'SOL': pd.Series(
            100 + np.cumsum(np.random.randn(252) * 5),
            index=dates
        )
    }


class TestOnChainMetrics:
    """Test on-chain metrics fetching."""
    
    def test_fetch_active_addresses(self, analytics):
        """Test fetching active addresses metric."""
        metrics = analytics.fetch_on_chain_metrics('BTC', 'active_addresses')
        
        assert 'symbol' in metrics
        assert metrics['symbol'] == 'BTC'
        assert 'metrics' in metrics
        assert 'active_addresses_24h' in metrics['metrics']
    
    def test_fetch_transaction_volume(self, analytics):
        """Test fetching transaction volume metric."""
        metrics = analytics.fetch_on_chain_metrics('ETH', 'transaction_volume')
        
        assert 'metrics' in metrics
        assert 'transaction_volume_24h' in metrics['metrics']
        assert 'transaction_count_24h' in metrics['metrics']
    
    def test_fetch_whale_watch(self, analytics):
        """Test fetching whale watch metrics."""
        metrics = analytics.fetch_on_chain_metrics('BTC', 'whale_watch')
        
        whale_metrics = metrics['metrics']
        assert 'large_transactions_24h' in whale_metrics
        assert 'whale_addresses_holding_1pct_supply' in whale_metrics
        assert 'top_10_address_concentration' in whale_metrics
    
    def test_metrics_have_timestamp(self, analytics):
        """Test metrics include timestamp."""
        metrics = analytics.fetch_on_chain_metrics('BTC')
        
        assert 'timestamp' in metrics
        assert metrics['timestamp'] is not None


class TestMarketStructure:
    """Test market structure analysis."""
    
    def test_market_structure_analysis(self, analytics):
        """Test market structure analysis."""
        structure = analytics.analyze_market_structure(
            'BTC',
            price=50000,
            volume_24h=30e9
        )
        
        assert 'price' in structure
        assert 'market_cap' in structure
        assert 'volume_24h' in structure
    
    def test_volatility_metrics(self, analytics):
        """Test volatility metrics in structure."""
        structure = analytics.analyze_market_structure(
            'ETH',
            price=2500,
            volume_24h=15e9
        )
        
        assert 'volatility_7d' in structure
        assert 'volatility_30d' in structure
        assert structure['volatility_7d'] >= 0
        assert structure['volatility_30d'] >= 0
    
    def test_liquidity_score(self, analytics):
        """Test liquidity score calculation."""
        structure = analytics.analyze_market_structure(
            'BTC',
            price=50000,
            volume_24h=30e9
        )
        
        score = structure['liquidity_score']
        assert 0 <= score <= 100
    
    def test_orderbook_depth(self, analytics):
        """Test orderbook depth analysis."""
        structure = analytics.analyze_market_structure(
            'BTC',
            price=50000,
            volume_24h=30e9
        )
        
        orderbook = structure['orderbook_depth']
        assert 'total_value' in orderbook
        assert 'by_level' in orderbook
        assert len(orderbook['by_level']) > 0
    
    def test_volume_profile(self, analytics):
        """Test volume profile analysis."""
        structure = analytics.analyze_market_structure(
            'BTC',
            price=50000,
            volume_24h=30e9
        )
        
        profile = structure['volume_profile']
        assert 'total_volume_24h' in profile
        assert 'volume_concentration' in profile


class TestCorrelationAnalysis:
    """Test correlation analysis."""
    
    def test_correlation_matrix(self, analytics, sample_price_data):
        """Test correlation matrix calculation."""
        correlation = analytics.analyze_correlation_matrix(
            ['BTC', 'ETH', 'SOL'],
            sample_price_data
        )
        
        assert isinstance(correlation, pd.DataFrame)
        assert correlation.shape[0] > 0
    
    def test_correlation_values(self, analytics, sample_price_data):
        """Test correlation values are between -1 and 1."""
        correlation = analytics.analyze_correlation_matrix(
            ['BTC', 'ETH', 'SOL'],
            sample_price_data
        )
        
        for row in correlation.values:
            for val in row:
                assert -1 <= val <= 1
    
    def test_diagonal_correlation_one(self, analytics, sample_price_data):
        """Test diagonal correlation is 1 (self-correlation)."""
        correlation = analytics.analyze_correlation_matrix(
            ['BTC', 'ETH'],
            sample_price_data
        )
        
        # Diagonal should be 1
        for i in range(len(correlation)):
            assert abs(correlation.iloc[i, i] - 1.0) < 0.01


class TestVolatilityTermStructure:
    """Test volatility term structure analysis."""
    
    def test_volatility_analysis(self, analytics):
        """Test volatility term structure analysis."""
        vol_data = {
            'vol_7d': 0.05,
            'vol_30d': 0.07,
            'vol_90d': 0.06
        }
        
        analysis = analytics.analyze_volatility_term_structure('BTC', vol_data)
        
        assert 'volatility_7d' in analysis
        assert 'vol_trend' in analysis
        assert analysis['vol_trend'] in ['increasing', 'decreasing']
    
    def test_volatility_regime(self, analytics):
        """Test volatility regime classification."""
        vol_data = {
            'vol_7d': 0.10,
            'vol_30d': 0.09,
            'vol_90d': 0.08
        }
        
        analysis = analytics.analyze_volatility_term_structure('BTC', vol_data)
        
        regime = analysis['vol_regime']
        assert regime in ['high', 'low', 'normal']
    
    def test_mean_reversion_signal(self, analytics):
        """Test mean reversion signal calculation."""
        # High volatility
        vol_data = {'vol_7d': 0.12, 'vol_30d': 0.06, 'vol_90d': 0.06}
        analysis = analytics.analyze_volatility_term_structure('BTC', vol_data)
        assert analysis['vol_mean_reversion_signal'] == 'elevated_vol'
        
        # Low volatility
        vol_data = {'vol_7d': 0.02, 'vol_30d': 0.06, 'vol_90d': 0.06}
        analysis = analytics.analyze_volatility_term_structure('BTC', vol_data)
        assert analysis['vol_mean_reversion_signal'] == 'depressed_vol'


class TestPortfolioRisk:
    """Test crypto portfolio risk calculation."""
    
    def test_portfolio_risk_calculation(self, analytics):
        """Test portfolio risk metrics calculation."""
        holdings = {'BTC': 1, 'ETH': 10}
        prices = {'BTC': 50000, 'ETH': 2500}
        correlation = pd.DataFrame(
            [[1.0, 0.7], [0.7, 1.0]],
            index=['BTC', 'ETH'],
            columns=['BTC', 'ETH']
        )
        
        risk = analytics.calculate_crypto_portfolio_risk(
            holdings,
            prices,
            correlation
        )
        
        assert 'portfolio_value' in risk
        assert 'portfolio_volatility' in risk
        assert 'var_95' in risk
        assert 'sharpe_ratio' in risk
    
    def test_value_at_risk(self, analytics):
        """Test Value at Risk calculation."""
        holdings = {'BTC': 1}
        prices = {'BTC': 50000}
        correlation = pd.DataFrame([[1.0]], index=['BTC'], columns=['BTC'])
        
        risk = analytics.calculate_crypto_portfolio_risk(
            holdings,
            prices,
            correlation
        )
        
        var_95 = risk['var_95']
        var_99 = risk['var_99']
        
        # VaR 99 should be higher than VaR 95
        assert var_99 >= var_95
        assert var_95 >= 0
    
    def test_portfolio_weights(self, analytics):
        """Test portfolio weight calculation."""
        holdings = {'BTC': 2, 'ETH': 10}
        prices = {'BTC': 50000, 'ETH': 2000}
        correlation = pd.DataFrame(
            [[1.0, 0.7], [0.7, 1.0]],
            index=['BTC', 'ETH'],
            columns=['BTC', 'ETH']
        )
        
        risk = analytics.calculate_crypto_portfolio_risk(
            holdings,
            prices,
            correlation
        )
        
        weights = risk['weights']
        
        # Weights should sum to approximately 1
        total_weight = sum(weights.values())
        assert abs(total_weight - 1.0) < 0.01
        
        # All weights should be positive
        for w in weights.values():
            assert w >= 0
    
    def test_concentration_risk(self, analytics):
        """Test concentration risk metric."""
        # Concentrated portfolio
        holdings = {'BTC': 10, 'ETH': 1}
        prices = {'BTC': 50000, 'ETH': 2000}
        correlation = pd.DataFrame(
            [[1.0, 0.7], [0.7, 1.0]],
            index=['BTC', 'ETH'],
            columns=['BTC', 'ETH']
        )
        
        risk = analytics.calculate_crypto_portfolio_risk(
            holdings,
            prices,
            correlation
        )
        
        concentration = risk['concentration_risk']
        assert concentration > 0.5  # Concentrated
    
    def test_diversification_ratio(self, analytics):
        """Test diversification ratio."""
        holdings = {'BTC': 1, 'ETH': 1}
        prices = {'BTC': 50000, 'ETH': 2000}
        correlation = pd.DataFrame(
            [[1.0, 0.0], [0.0, 1.0]],
            index=['BTC', 'ETH'],
            columns=['BTC', 'ETH']
        )
        
        risk = analytics.calculate_crypto_portfolio_risk(
            holdings,
            prices,
            correlation
        )
        
        ratio = risk['diversification_ratio']
        assert ratio >= 1  # Should benefit from diversification


class TestDataStorage:
    """Test crypto analysis data storage."""
    
    def test_save_analysis(self, analytics, tmp_path):
        """Test saving crypto analysis to Parquet."""
        analysis_data = {
            'on_chain_metrics': {
                'symbol': 'BTC',
                'metrics': {'active_addresses_24h': 500000}
            },
            'market_structure': {
                'symbol': 'BTC',
                'liquidity_score': 85.5,
                'market_strength': 'strong'
            }
        }
        
        output = analytics.save_crypto_analysis(
            analysis_data,
            output_dir=str(tmp_path)
        )
        
        assert isinstance(output, str)


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_empty_holdings(self, analytics):
        """Test with empty holdings."""
        holdings = {}
        prices = {}
        correlation = pd.DataFrame()
        
        # Should handle gracefully or return error
        try:
            risk = analytics.calculate_crypto_portfolio_risk(
                holdings,
                prices,
                correlation
            )
            # If no error, portfolio value should be 0
            assert risk['portfolio_value'] == 0
        except (KeyError, ValueError, IndexError):
            # Expected behavior for empty portfolio
            pass
    
    def test_single_asset_portfolio(self, analytics):
        """Test portfolio with single asset."""
        holdings = {'BTC': 1}
        prices = {'BTC': 50000}
        correlation = pd.DataFrame([[1.0]], index=['BTC'], columns=['BTC'])
        
        risk = analytics.calculate_crypto_portfolio_risk(
            holdings,
            prices,
            correlation
        )
        
        # Should still calculate metrics
        assert risk['portfolio_value'] == 50000
        assert 'var_95' in risk
    
    def test_extreme_volatility(self, analytics):
        """Test with extreme volatility values."""
        vol_data = {
            'vol_7d': 0.50,
            'vol_30d': 0.30,
            'vol_90d': 0.20
        }
        
        analysis = analytics.analyze_volatility_term_structure('BTC', vol_data)
        
        assert analysis['vol_regime'] == 'high'
        assert 'vol_trend' in analysis
    
    def test_negative_prices_handled(self, analytics):
        """Test handling of invalid price data."""
        structure = analytics.analyze_market_structure(
            'BTC',
            price=-50000,  # Invalid
            volume_24h=30e9
        )
        
        # Should have some result (may be invalid but shouldn't crash)
        assert 'market_cap' in structure
