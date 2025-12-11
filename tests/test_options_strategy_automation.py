"""
Tests for Options Strategy Automation Module

Coverage:
- Iron Condor strategy generation and Greeks aggregation
- Strangle/Straddle configuration
- Covered Call for income strategies
- Greeks-based hedge recommendations
- Strategy P&L analysis and performance
- Parquet export and persistence
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from src.options_strategy_automation import (
    OptionLeg, OptionsStrategy, OptionsStrategyAutomation,
    recommend_strategy_for_market_condition
)


class TestOptionLeg:
    """Test OptionLeg class."""
    
    def test_leg_creation(self):
        """Test creating an option leg."""
        leg = OptionLeg(
            strike=100.0,
            option_type='call',
            expiration=datetime.now() + timedelta(days=30),
            action='buy',
            quantity=1,
            current_price=5.0,
            delta=0.5,
            gamma=0.02,
            theta=-0.05,
            vega=0.15
        )
        assert leg.strike == 100.0
        assert leg.option_type == 'call'
        assert leg.action == 'buy'
        assert leg.quantity == 1
    
    def test_premium_obligation_buy(self):
        """Test premium calculation for long positions."""
        leg = OptionLeg(
            strike=100.0,
            option_type='call',
            expiration=datetime.now() + timedelta(days=30),
            action='buy',
            quantity=2,
            current_price=5.0
        )
        assert leg.premium_obligation == 1000.0  # 5.0 * 2 * 100
    
    def test_premium_obligation_sell(self):
        """Test premium calculation for short positions."""
        leg = OptionLeg(
            strike=100.0,
            option_type='call',
            expiration=datetime.now() + timedelta(days=30),
            action='sell',
            quantity=2,
            current_price=5.0
        )
        assert leg.premium_obligation == -1000.0  # -(5.0 * 2 * 100)
    
    def test_net_delta_call(self):
        """Test net delta for call leg."""
        leg = OptionLeg(
            strike=100.0,
            option_type='call',
            expiration=datetime.now() + timedelta(days=30),
            action='buy',
            quantity=1,
            current_price=5.0,
            delta=0.6
        )
        assert leg.net_delta == 0.6


class TestOptionsStrategy:
    """Test OptionsStrategy class."""
    
    def test_strategy_creation(self):
        """Test creating an options strategy."""
        legs = [
            OptionLeg(
                strike=100.0, option_type='call', expiration=datetime.now() + timedelta(days=30),
                action='buy', quantity=1, current_price=5.0, delta=0.5
            )
        ]
        strategy = OptionsStrategy(
            name='Test',
            underlying='AAPL',
            current_price=100.0,
            legs=legs
        )
        assert strategy.name == 'Test'
        assert strategy.underlying == 'AAPL'
        assert len(strategy.legs) == 1
    
    def test_net_debit_credit_single_leg(self):
        """Test net debit/credit calculation."""
        legs = [
            OptionLeg(
                strike=100.0, option_type='call', expiration=datetime.now() + timedelta(days=30),
                action='buy', quantity=1, current_price=5.0
            )
        ]
        strategy = OptionsStrategy(
            name='Test',
            underlying='AAPL',
            current_price=100.0,
            legs=legs
        )
        assert strategy.net_debit_credit == 500.0  # 5.0 * 100
    
    def test_aggregate_greeks(self):
        """Test aggregation of Greeks across legs."""
        legs = [
            OptionLeg(
                strike=100.0, option_type='call', expiration=datetime.now() + timedelta(days=30),
                action='buy', quantity=1, current_price=5.0,
                delta=0.5, gamma=0.02, theta=-0.05, vega=0.15
            ),
            OptionLeg(
                strike=105.0, option_type='call', expiration=datetime.now() + timedelta(days=30),
                action='sell', quantity=1, current_price=2.0,
                delta=0.3, gamma=0.01, theta=0.03, vega=-0.1
            )
        ]
        strategy = OptionsStrategy(
            name='Spread',
            underlying='AAPL',
            current_price=100.0,
            legs=legs
        )
        greeks = strategy.aggregate_greeks
        assert greeks['delta'] < 1.0  # Combined delta
        assert greeks['gamma'] > 0
        assert greeks['theta'] < 0  # Net negative theta for long spread
    
    def test_days_to_expiration(self):
        """Test days to expiration calculation."""
        exp = datetime.now() + timedelta(days=45)
        legs = [
            OptionLeg(
                strike=100.0, option_type='call', expiration=exp,
                action='buy', quantity=1, current_price=5.0
            )
        ]
        strategy = OptionsStrategy(
            name='Test',
            underlying='AAPL',
            current_price=100.0,
            legs=legs
        )
        assert 44 <= strategy.days_to_expiration <= 45


class TestOptionsStrategyAutomation:
    """Test OptionsStrategyAutomation class."""
    
    @pytest.fixture
    def automator(self):
        """Create automator instance."""
        return OptionsStrategyAutomation(risk_tolerance='moderate')
    
    def test_iron_condor_generation(self, automator):
        """Test Iron Condor strategy generation."""
        strategy = automator.generate_iron_condor(
            underlying='SPY',
            current_price=450.0,
            volatility_percentile=75,
            days_to_expiration=45,
            put_strike_pct=0.02,
            call_strike_pct=0.02,
            spread_width=5.0
        )
        
        assert strategy.name == 'Iron Condor'
        assert strategy.underlying == 'SPY'
        assert len(strategy.legs) == 4  # 2 put spread + 2 call spread
        assert strategy.net_debit_credit < 0  # Should be credit (income)
    
    def test_iron_condor_structure(self, automator):
        """Test Iron Condor has correct structure."""
        strategy = automator.generate_iron_condor(
            underlying='SPY',
            current_price=450.0,
            volatility_percentile=75,
            days_to_expiration=45
        )
        
        # Should have 2 puts and 2 calls
        calls = [leg for leg in strategy.legs if leg.option_type == 'call']
        puts = [leg for leg in strategy.legs if leg.option_type == 'put']
        assert len(calls) == 2
        assert len(puts) == 2
        
        # Should have 2 sells and 2 buys
        sells = [leg for leg in strategy.legs if leg.action == 'sell']
        buys = [leg for leg in strategy.legs if leg.action == 'buy']
        assert len(sells) == 2
        assert len(buys) == 2
    
    def test_long_strangle_generation(self, automator):
        """Test long strangle generation."""
        strategy = automator.generate_strangle(
            underlying='QQQ',
            current_price=350.0,
            volatility_percentile=40,
            days_to_expiration=30,
            direction='long'
        )
        
        assert 'Strangle' in strategy.name
        assert len(strategy.legs) == 2
        assert strategy.net_debit_credit > 0  # Long strangles cost money
    
    def test_short_strangle_generation(self, automator):
        """Test short strangle generation."""
        strategy = automator.generate_strangle(
            underlying='QQQ',
            current_price=350.0,
            volatility_percentile=80,
            days_to_expiration=30,
            direction='short'
        )
        
        assert 'Strangle' in strategy.name
        assert strategy.net_debit_credit < 0  # Short strangles credit
    
    def test_covered_call_generation(self, automator):
        """Test covered call generation."""
        strategy = automator.generate_covered_call(
            underlying='MSFT',
            current_price=400.0,
            shares_owned=200,
            call_strike_pct=0.05,
            days_to_expiration=30
        )
        
        assert strategy.name == 'Covered Call'
        assert len(strategy.legs) == 2  # Stock + call
        
        # First leg should be stock
        assert strategy.legs[0].option_type == 'stock'
        assert strategy.legs[0].quantity == 200
    
    def test_long_straddle_generation(self, automator):
        """Test long straddle generation."""
        strategy = automator.generate_straddle(
            underlying='NVDA',
            current_price=850.0,
            volatility_percentile=40,
            days_to_expiration=30,
            direction='long'
        )
        
        assert 'Straddle' in strategy.name
        assert len(strategy.legs) == 2
        assert strategy.legs[0].strike == strategy.legs[1].strike
    
    def test_short_straddle_generation(self, automator):
        """Test short straddle generation."""
        strategy = automator.generate_straddle(
            underlying='NVDA',
            current_price=850.0,
            volatility_percentile=80,
            days_to_expiration=30,
            direction='short'
        )
        
        assert 'Straddle' in strategy.name
        assert strategy.net_debit_credit < 0  # Credit for short straddle
    
    def test_hedge_recommendations_positive_delta(self, automator):
        """Test hedge recommendations for long portfolio."""
        recommendations = automator.generate_hedge_recommendations(
            portfolio_delta=500.0,  # Long delta exposure
            portfolio_vega=100.0,
            portfolio_value=100000,
            max_hedge_cost_pct=2.0
        )
        
        assert 'delta_hedges' in recommendations
        assert len(recommendations['delta_hedges']) > 0
    
    def test_hedge_recommendations_negative_vega(self, automator):
        """Test hedge recommendations for short vega portfolio."""
        recommendations = automator.generate_hedge_recommendations(
            portfolio_delta=0.0,
            portfolio_vega=-150.0,  # Short vega exposure
            portfolio_value=100000,
            max_hedge_cost_pct=2.0
        )
        
        assert 'vega_hedges' in recommendations
        assert len(recommendations['vega_hedges']) > 0
    
    def test_strategy_to_dataframe(self, automator):
        """Test converting strategies to DataFrame."""
        automator.generate_iron_condor(
            underlying='SPY',
            current_price=450.0,
            volatility_percentile=75
        )
        automator.generate_covered_call(
            underlying='MSFT',
            current_price=400.0,
            shares_owned=100
        )
        
        df = automator.strategy_to_dataframe()
        assert len(df) == 2
        assert 'Strategy' in df.columns
        assert 'Delta' in df.columns
        assert 'Vega' in df.columns
    
    def test_save_to_parquet(self, automator, tmp_path):
        """Test saving strategies to Parquet."""
        automator.generate_iron_condor(
            underlying='SPY',
            current_price=450.0,
            volatility_percentile=75
        )
        
        output_path = str(tmp_path / 'strategies')
        filepath = automator.save_to_parquet(output_path)
        
        assert filepath is not None
        assert 'parquet' in filepath
        
        # Verify saved data
        df = pd.read_parquet(filepath)
        assert len(df) >= 1
    
    def test_strategy_performance_analysis(self, automator):
        """Test strategy P&L analysis across price range."""
        strategy = automator.generate_iron_condor(
            underlying='SPY',
            current_price=450.0,
            volatility_percentile=75
        )
        
        price_range = np.linspace(430, 470, 50)
        analysis = automator.analyze_strategy_performance(strategy, price_range)
        
        assert len(analysis) == 50
        assert 'Price' in analysis.columns
        assert 'P&L' in analysis.columns
        assert 'Profit' in analysis.columns
    
    def test_option_price_estimation(self, automator):
        """Test option price estimation."""
        price = automator._estimate_option_price(
            stock_price=100.0,
            strike=105.0,
            days=30,
            iv_percentile=50,
            option_type='call'
        )
        
        assert price > 0  # Option price should be positive
    
    def test_multiple_strategies_tracking(self, automator):
        """Test tracking multiple strategies."""
        automator.generate_iron_condor('SPY', 450.0, 75)
        automator.generate_covered_call('MSFT', 400.0, 100)
        automator.generate_long_strangle('QQQ', 350.0, 40)
        
        assert len(automator.strategies) == 3


class TestStrategyRecommendations:
    """Test strategy recommendation logic."""
    
    def test_recommend_strategy_high_iv_neutral(self):
        """Test recommendation for high IV, neutral market."""
        strategy = recommend_strategy_for_market_condition(
            volatility_percentile=85,
            market_direction='neutral',
            time_horizon_days=30
        )
        assert strategy == 'Iron Condor'
    
    def test_recommend_strategy_high_iv_bullish(self):
        """Test recommendation for high IV, bullish market."""
        strategy = recommend_strategy_for_market_condition(
            volatility_percentile=85,
            market_direction='bullish',
            time_horizon_days=30
        )
        assert strategy == 'Covered Call'
    
    def test_recommend_strategy_low_iv_bullish(self):
        """Test recommendation for low IV, bullish market."""
        strategy = recommend_strategy_for_market_condition(
            volatility_percentile=20,
            market_direction='bullish',
            time_horizon_days=30
        )
        assert 'Call Spread' in strategy or 'Spread' in strategy
    
    def test_recommend_strategy_low_iv_neutral(self):
        """Test recommendation for low IV, neutral market."""
        strategy = recommend_strategy_for_market_condition(
            volatility_percentile=15,
            market_direction='neutral',
            time_horizon_days=30
        )
        assert 'Straddle' in strategy or 'Strangle' in strategy


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_zero_quantity_leg(self):
        """Test leg with zero quantity."""
        leg = OptionLeg(
            strike=100.0,
            option_type='call',
            expiration=datetime.now() + timedelta(days=30),
            action='buy',
            quantity=0,
            current_price=5.0
        )
        assert leg.premium_obligation == 0
    
    def test_very_otm_option(self):
        """Test very OTM option pricing."""
        automator = OptionsStrategyAutomation()
        price = automator._estimate_option_price(
            stock_price=100.0,
            strike=150.0,
            days=7,
            iv_percentile=10,
            option_type='call'
        )
        assert price >= 0
    
    def test_expiring_option(self):
        """Test option expiring today."""
        leg = OptionLeg(
            strike=100.0,
            option_type='call',
            expiration=datetime.now(),
            action='buy',
            quantity=1,
            current_price=0.01
        )
        strategy = OptionsStrategy(
            name='Test',
            underlying='TEST',
            current_price=100.0,
            legs=[leg]
        )
        assert strategy.days_to_expiration == 0
    
    def test_empty_strategy_dataframe(self):
        """Test DataFrame conversion with no strategies."""
        automator = OptionsStrategyAutomation()
        df = automator.strategy_to_dataframe()
        assert len(df) == 0


class TestGreeksCalculations:
    """Test Greeks calculations and aggregations."""
    
    def test_gamma_aggregation_call_spread(self):
        """Test gamma aggregation for call spread."""
        legs = [
            OptionLeg(
                strike=100.0, option_type='call', expiration=datetime.now() + timedelta(days=30),
                action='buy', quantity=1, current_price=5.0, gamma=0.03
            ),
            OptionLeg(
                strike=105.0, option_type='call', expiration=datetime.now() + timedelta(days=30),
                action='sell', quantity=1, current_price=2.0, gamma=-0.02
            )
        ]
        strategy = OptionsStrategy('Spread', 'TEST', 100.0, legs)
        greeks = strategy.aggregate_greeks
        assert greeks['gamma'] == 0.01  # 0.03 - 0.02
    
    def test_theta_decay_long_call(self):
        """Test theta for long call."""
        leg = OptionLeg(
            strike=100.0, option_type='call', expiration=datetime.now() + timedelta(days=30),
            action='buy', quantity=1, current_price=5.0, theta=-0.05
        )
        assert leg.theta < 0  # Long options have negative theta
    
    def test_vega_volatility_play(self):
        """Test vega for volatility plays."""
        legs = [
            OptionLeg(
                strike=100.0, option_type='call', expiration=datetime.now() + timedelta(days=30),
                action='buy', quantity=1, current_price=5.0, vega=0.20
            ),
            OptionLeg(
                strike=100.0, option_type='put', expiration=datetime.now() + timedelta(days=30),
                action='buy', quantity=1, current_price=5.0, vega=0.20
            )
        ]
        strategy = OptionsStrategy('Long Straddle', 'TEST', 100.0, legs)
        greeks = strategy.aggregate_greeks
        assert greeks['vega'] > 0  # Long volatility


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
