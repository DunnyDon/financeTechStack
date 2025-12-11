"""
Options Strategy Automation Module

Automated generation and analysis of multi-leg options strategies:
- Iron Condor (sell OTM put spread + sell OTM call spread)
- Strangle/Straddle (directional or neutral plays)
- Covered Call (income optimization)
- Greeks-based hedge recommendations
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class OptionLeg:
    """Single leg of a multi-leg options strategy."""
    
    strike: float
    option_type: str  # 'call' or 'put'
    expiration: datetime
    action: str  # 'buy' or 'sell'
    quantity: int
    current_price: float
    delta: float = 0.0
    gamma: float = 0.0
    theta: float = 0.0
    vega: float = 0.0
    implied_vol: float = 0.0
    
    @property
    def premium_obligation(self) -> float:
        """Total premium for this leg (negative = credit received)."""
        sign = -1 if self.action == 'sell' else 1
        return sign * self.current_price * self.quantity * 100
    
    @property
    def net_delta(self) -> float:
        """Net delta exposure for this leg."""
        sign = 1 if self.action == 'buy' else -1
        call_multiplier = 1 if self.option_type == 'call' else 0
        put_multiplier = -1 if self.option_type == 'put' else 0
        return sign * self.delta * (call_multiplier or put_multiplier) * self.quantity


@dataclass
class OptionsStrategy:
    """Multi-leg options strategy with Greeks aggregation."""
    
    name: str  # 'Iron Condor', 'Strangle', 'Straddle', 'Covered Call', etc.
    underlying: str
    current_price: float
    legs: List[OptionLeg]
    entry_date: datetime = None
    
    def __post_init__(self):
        if self.entry_date is None:
            self.entry_date = datetime.now()
    
    @property
    def net_debit_credit(self) -> float:
        """Total premium paid/received. Positive = net debit, negative = net credit."""
        return sum(leg.premium_obligation for leg in self.legs)
    
    @property
    def max_profit(self) -> float:
        """Maximum profit at expiration."""
        # Varies by strategy type - calculated in subclass or post-analysis
        pass
    
    @property
    def max_loss(self) -> float:
        """Maximum loss at expiration."""
        # Varies by strategy type - calculated in subclass or post-analysis
        pass
    
    @property
    def breakeven_points(self) -> List[float]:
        """Strike prices at which profit/loss = 0."""
        # Complex calculation requiring payoff diagram analysis
        pass
    
    @property
    def aggregate_greeks(self) -> Dict[str, float]:
        """Sum of Greeks across all legs."""
        return {
            'delta': sum(leg.net_delta for leg in self.legs),
            'gamma': sum(leg.gamma * leg.quantity for leg in self.legs),
            'theta': sum(leg.theta * leg.quantity for leg in self.legs),
            'vega': sum(leg.vega * leg.quantity for leg in self.legs),
        }
    
    @property
    def days_to_expiration(self) -> int:
        """Days until strategy expiration."""
        if self.legs:
            exp = self.legs[0].expiration
            return max(0, (exp - datetime.now()).days)
        return 0


class OptionsStrategyAutomation:
    """Automatic generation and analysis of options strategies."""
    
    def __init__(self, risk_tolerance: str = 'moderate', max_loss_percent: float = 2.0):
        """
        Initialize options strategy automation.
        
        Args:
            risk_tolerance: 'conservative', 'moderate', 'aggressive'
            max_loss_percent: Maximum loss as % of account (for position sizing)
        """
        self.risk_tolerance = risk_tolerance
        self.max_loss_percent = max_loss_percent
        self.strategies: List[OptionsStrategy] = []
        
    def generate_iron_condor(
        self,
        underlying: str,
        current_price: float,
        volatility_percentile: float,
        days_to_expiration: int = 45,
        put_strike_pct: float = 0.02,
        call_strike_pct: float = 0.02,
        spread_width: float = 5.0
    ) -> OptionsStrategy:
        """
        Generate Iron Condor strategy (sell OTM put spread + sell OTM call spread).
        
        Best when: High IV percentile (>70), expecting mean reversion
        
        Args:
            underlying: Stock ticker
            current_price: Current stock price
            volatility_percentile: IV percentile (0-100)
            days_to_expiration: Days until option expiration
            put_strike_pct: OTM % for put short strike
            call_strike_pct: OTM % for call short strike
            spread_width: Width between short and long strikes ($)
        
        Returns:
            OptionsStrategy with Iron Condor configuration
        """
        exp = datetime.now() + timedelta(days=days_to_expiration)
        
        # Short put strike (below current price)
        short_put_strike = round(current_price * (1 - put_strike_pct), 2)
        # Long put strike (further below)
        long_put_strike = round(short_put_strike - spread_width, 2)
        
        # Short call strike (above current price)
        short_call_strike = round(current_price * (1 + call_strike_pct), 2)
        # Long call strike (further above)
        long_call_strike = round(short_call_strike + spread_width, 2)
        
        legs = [
            # Sell put spread (bullish)
            OptionLeg(
                strike=short_put_strike,
                option_type='put',
                expiration=exp,
                action='sell',
                quantity=1,
                current_price=self._estimate_option_price(
                    current_price, short_put_strike, days_to_expiration, 
                    volatility_percentile, 'put'
                ),
                delta=-0.3,  # Sample delta
                gamma=-0.02,
                theta=0.08,
                vega=-0.15,
                implied_vol=volatility_percentile / 100
            ),
            OptionLeg(
                strike=long_put_strike,
                option_type='put',
                expiration=exp,
                action='buy',
                quantity=1,
                current_price=self._estimate_option_price(
                    current_price, long_put_strike, days_to_expiration,
                    volatility_percentile, 'put'
                ),
                delta=0.15,
                gamma=0.02,
                theta=-0.04,
                vega=0.08,
                implied_vol=volatility_percentile / 100
            ),
            # Sell call spread (bearish)
            OptionLeg(
                strike=short_call_strike,
                option_type='call',
                expiration=exp,
                action='sell',
                quantity=1,
                current_price=self._estimate_option_price(
                    current_price, short_call_strike, days_to_expiration,
                    volatility_percentile, 'call'
                ),
                delta=-0.3,
                gamma=-0.02,
                theta=0.08,
                vega=-0.15,
                implied_vol=volatility_percentile / 100
            ),
            OptionLeg(
                strike=long_call_strike,
                option_type='call',
                expiration=exp,
                action='buy',
                quantity=1,
                current_price=self._estimate_option_price(
                    current_price, long_call_strike, days_to_expiration,
                    volatility_percentile, 'call'
                ),
                delta=0.15,
                gamma=0.02,
                theta=-0.04,
                vega=0.08,
                implied_vol=volatility_percentile / 100
            ),
        ]
        
        strategy = OptionsStrategy(
            name='Iron Condor',
            underlying=underlying,
            current_price=current_price,
            legs=legs,
        )
        
        self.strategies.append(strategy)
        return strategy
    
    def generate_strangle(
        self,
        underlying: str,
        current_price: float,
        volatility_percentile: float,
        days_to_expiration: int = 30,
        put_otm_pct: float = 0.05,
        call_otm_pct: float = 0.05,
        direction: str = 'long'  # 'long' for volatility play, 'short' for mean reversion
    ) -> OptionsStrategy:
        """
        Generate Strangle strategy (buy/sell OTM call + OTM put).
        
        Long strangle: Bet on large move, low cost, limited loss
        Short strangle: Income, undefined risk (use for high IV)
        
        Args:
            underlying: Stock ticker
            current_price: Current stock price
            volatility_percentile: IV percentile
            days_to_expiration: Days until expiration
            put_otm_pct: OTM % for put strike
            call_otm_pct: OTM % for call strike
            direction: 'long' or 'short'
        
        Returns:
            OptionsStrategy with Strangle configuration
        """
        exp = datetime.now() + timedelta(days=days_to_expiration)
        
        put_strike = round(current_price * (1 - put_otm_pct), 2)
        call_strike = round(current_price * (1 + call_otm_pct), 2)
        
        action = 'buy' if direction == 'long' else 'sell'
        sign = 1 if direction == 'long' else -1
        
        legs = [
            OptionLeg(
                strike=put_strike,
                option_type='put',
                expiration=exp,
                action=action,
                quantity=1,
                current_price=self._estimate_option_price(
                    current_price, put_strike, days_to_expiration,
                    volatility_percentile, 'put'
                ),
                delta=sign * -0.25,
                gamma=sign * 0.02,
                theta=sign * -0.06 if direction == 'long' else sign * 0.06,
                vega=sign * 0.20,
                implied_vol=volatility_percentile / 100
            ),
            OptionLeg(
                strike=call_strike,
                option_type='call',
                expiration=exp,
                action=action,
                quantity=1,
                current_price=self._estimate_option_price(
                    current_price, call_strike, days_to_expiration,
                    volatility_percentile, 'call'
                ),
                delta=sign * 0.25,
                gamma=sign * 0.02,
                theta=sign * -0.06 if direction == 'long' else sign * 0.06,
                vega=sign * 0.20,
                implied_vol=volatility_percentile / 100
            ),
        ]
        
        strategy = OptionsStrategy(
            name=f'{direction.capitalize()} Strangle',
            underlying=underlying,
            current_price=current_price,
            legs=legs,
        )
        
        self.strategies.append(strategy)
        return strategy
    
    def generate_covered_call(
        self,
        underlying: str,
        current_price: float,
        shares_owned: int,
        call_strike_pct: float = 0.05,
        days_to_expiration: int = 30,
        volatility_percentile: float = 50.0
    ) -> OptionsStrategy:
        """
        Generate Covered Call strategy (own stock + sell call).
        
        Best for: Income generation on holdings, slightly bullish view
        
        Args:
            underlying: Stock ticker
            current_price: Current stock price
            shares_owned: Number of shares held
            call_strike_pct: OTM % for call strike
            days_to_expiration: Days until expiration
            volatility_percentile: IV percentile
        
        Returns:
            OptionsStrategy with Covered Call configuration
        """
        exp = datetime.now() + timedelta(days=days_to_expiration)
        call_strike = round(current_price * (1 + call_strike_pct), 2)
        
        # Number of call contracts (each represents 100 shares)
        contracts = shares_owned // 100
        
        legs = [
            # Long stock (synthetic - track as underlying)
            OptionLeg(
                strike=current_price,
                option_type='stock',
                expiration=exp,
                action='hold',
                quantity=shares_owned,
                current_price=current_price,
                delta=shares_owned,
                gamma=0.0,
                theta=0.0,
                vega=0.0,
                implied_vol=0.0
            ),
            # Short call
            OptionLeg(
                strike=call_strike,
                option_type='call',
                expiration=exp,
                action='sell',
                quantity=contracts,
                current_price=self._estimate_option_price(
                    current_price, call_strike, days_to_expiration,
                    volatility_percentile, 'call'
                ),
                delta=-0.40 * contracts,
                gamma=-0.02 * contracts,
                theta=0.10 * contracts,
                vega=-0.15 * contracts,
                implied_vol=volatility_percentile / 100
            ),
        ]
        
        strategy = OptionsStrategy(
            name='Covered Call',
            underlying=underlying,
            current_price=current_price,
            legs=legs,
        )
        
        self.strategies.append(strategy)
        return strategy
    
    def generate_straddle(
        self,
        underlying: str,
        current_price: float,
        volatility_percentile: float,
        days_to_expiration: int = 30,
        direction: str = 'long'  # 'long' for vol expansion, 'short' for vol contraction
    ) -> OptionsStrategy:
        """
        Generate Straddle strategy (buy/sell ATM call + ATM put).
        
        Long straddle: Large move expected (vol expansion play)
        Short straddle: Mean reversion expected (vol contraction play)
        
        Args:
            underlying: Stock ticker
            current_price: Current stock price
            volatility_percentile: IV percentile
            days_to_expiration: Days until expiration
            direction: 'long' or 'short'
        
        Returns:
            OptionsStrategy with Straddle configuration
        """
        exp = datetime.now() + timedelta(days=days_to_expiration)
        strike = round(current_price, 2)
        
        action = 'buy' if direction == 'long' else 'sell'
        sign = 1 if direction == 'long' else -1
        
        legs = [
            OptionLeg(
                strike=strike,
                option_type='put',
                expiration=exp,
                action=action,
                quantity=1,
                current_price=self._estimate_option_price(
                    current_price, strike, days_to_expiration,
                    volatility_percentile, 'put'
                ),
                delta=sign * -0.50,
                gamma=sign * 0.04,
                theta=sign * -0.08 if direction == 'long' else sign * 0.08,
                vega=sign * 0.25,
                implied_vol=volatility_percentile / 100
            ),
            OptionLeg(
                strike=strike,
                option_type='call',
                expiration=exp,
                action=action,
                quantity=1,
                current_price=self._estimate_option_price(
                    current_price, strike, days_to_expiration,
                    volatility_percentile, 'call'
                ),
                delta=sign * 0.50,
                gamma=sign * 0.04,
                theta=sign * -0.08 if direction == 'long' else sign * 0.08,
                vega=sign * 0.25,
                implied_vol=volatility_percentile / 100
            ),
        ]
        
        strategy = OptionsStrategy(
            name=f'{direction.capitalize()} Straddle',
            underlying=underlying,
            current_price=current_price,
            legs=legs,
        )
        
        self.strategies.append(strategy)
        return strategy
    
    def generate_hedge_recommendations(
        self,
        portfolio_delta: float,
        portfolio_vega: float,
        portfolio_value: float,
        max_hedge_cost_pct: float = 2.0
    ) -> Dict[str, any]:
        """
        Generate Greeks-based hedge recommendations.
        
        Args:
            portfolio_delta: Net delta exposure
            portfolio_vega: Net vega exposure
            portfolio_value: Total portfolio value
            max_hedge_cost_pct: Max cost of hedge as % of portfolio
        
        Returns:
            Dictionary with hedge recommendations
        """
        max_hedge_cost = portfolio_value * (max_hedge_cost_pct / 100)
        
        recommendations = {
            'timestamp': datetime.now(),
            'portfolio_delta': portfolio_delta,
            'portfolio_vega': portfolio_vega,
            'delta_hedges': [],
            'vega_hedges': [],
            'combined_hedges': [],
            'estimated_costs': {}
        }
        
        # Delta hedges
        if abs(portfolio_delta) > 100:  # Significant delta exposure
            if portfolio_delta > 0:
                recommendations['delta_hedges'].append({
                    'type': 'Put Spread',
                    'description': 'Buy protective puts (long calls optional to reduce cost)',
                    'hedge_delta': -abs(portfolio_delta),
                    'estimated_cost': max_hedge_cost * 0.3,
                    'rationale': 'Downside protection for long portfolio'
                })
            else:
                recommendations['delta_hedges'].append({
                    'type': 'Call Spread',
                    'description': 'Buy protective calls (sell higher calls to reduce cost)',
                    'hedge_delta': abs(portfolio_delta),
                    'estimated_cost': max_hedge_cost * 0.3,
                    'rationale': 'Upside protection for short portfolio'
                })
        
        # Vega hedges
        if abs(portfolio_vega) > 50:  # Significant vega exposure
            if portfolio_vega > 0:
                recommendations['vega_hedges'].append({
                    'type': 'Short Straddle/Strangle',
                    'description': 'Sell options to reduce long vega (profit from vol contraction)',
                    'hedge_vega': -abs(portfolio_vega),
                    'estimated_credit': max_hedge_cost * 0.4,
                    'rationale': 'Hedge long volatility exposure'
                })
            else:
                recommendations['vega_hedges'].append({
                    'type': 'Long Strangle',
                    'description': 'Buy OTM options to hedge short vega (profit from vol expansion)',
                    'hedge_vega': abs(portfolio_vega),
                    'estimated_cost': max_hedge_cost * 0.25,
                    'rationale': 'Hedge short volatility exposure'
                })
        
        return recommendations
    
    def _estimate_option_price(
        self,
        stock_price: float,
        strike: float,
        days: int,
        iv_percentile: float,
        option_type: str
    ) -> float:
        """
        Estimate option price using simplified Black-Scholes.
        
        Args:
            stock_price: Current stock price
            strike: Option strike price
            days: Days to expiration
            iv_percentile: IV percentile (0-100)
            option_type: 'call' or 'put'
        
        Returns:
            Estimated option premium
        """
        iv = iv_percentile / 100 * 0.5  # Scale IV to 0-50% range
        t = days / 365
        
        # Simplified approximation
        moneyness = stock_price / strike
        intrinsic = max(0, stock_price - strike) if option_type == 'call' else max(0, strike - stock_price)
        time_value = iv * stock_price * np.sqrt(t) * 0.4
        
        return intrinsic + time_value
    
    def strategy_to_dataframe(self) -> pd.DataFrame:
        """Convert strategies to DataFrame for analysis."""
        rows = []
        for strat in self.strategies:
            greeks = strat.aggregate_greeks
            rows.append({
                'Strategy': strat.name,
                'Underlying': strat.underlying,
                'Current_Price': strat.current_price,
                'Num_Legs': len(strat.legs),
                'Net_Debit': strat.net_debit_credit,
                'Days_To_Exp': strat.days_to_expiration,
                'Delta': greeks['delta'],
                'Gamma': greeks['gamma'],
                'Theta': greeks['theta'],
                'Vega': greeks['vega'],
                'Entry_Date': strat.entry_date,
            })
        return pd.DataFrame(rows)
    
    def save_to_parquet(self, output_path: str = 'db/options_strategies') -> str:
        """
        Save strategies to Parquet format.
        
        Args:
            output_path: Directory to save Parquet files
        
        Returns:
            Path to saved file
        """
        output_dir = Path(output_path)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        df = self.strategy_to_dataframe()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filepath = output_dir / f'strategies_{timestamp}.parquet'
        
        df.to_parquet(filepath, compression='snappy')
        logger.info(f'Saved {len(self.strategies)} strategies to {filepath}')
        
        return str(filepath)
    
    def analyze_strategy_performance(self, strategy: OptionsStrategy, price_range: np.ndarray) -> pd.DataFrame:
        """
        Analyze P&L across a range of underlying prices at expiration.
        
        Args:
            strategy: OptionsStrategy to analyze
            price_range: Array of prices to evaluate
        
        Returns:
            DataFrame with P&L analysis
        """
        results = []
        
        for price in price_range:
            pnl = 0
            
            for leg in strategy.legs:
                if leg.option_type == 'stock':
                    pnl += (price - leg.strike) * leg.quantity
                elif leg.option_type == 'call':
                    intrinsic = max(0, price - leg.strike)
                    sign = -1 if leg.action == 'sell' else 1
                    pnl += sign * (intrinsic - leg.current_price) * leg.quantity * 100
                elif leg.option_type == 'put':
                    intrinsic = max(0, leg.strike - price)
                    sign = -1 if leg.action == 'sell' else 1
                    pnl += sign * (intrinsic - leg.current_price) * leg.quantity * 100
            
            results.append({
                'Price': price,
                'P&L': pnl,
                'Profit': pnl > 0,
            })
        
        return pd.DataFrame(results)


# Utility functions for strategy recommendations
def recommend_strategy_for_market_condition(
    volatility_percentile: float,
    market_direction: str = 'neutral',
    time_horizon_days: int = 30
) -> str:
    """
    Recommend options strategy based on market conditions.
    
    Args:
        volatility_percentile: IV percentile (0-100)
        market_direction: 'bullish', 'bearish', or 'neutral'
        time_horizon_days: Days until event/expiration
    
    Returns:
        Recommended strategy name
    """
    if volatility_percentile > 70:
        # High IV: Prefer selling strategies
        if market_direction == 'bullish':
            return 'Covered Call'
        elif market_direction == 'bearish':
            return 'Short Call Spread'
        else:
            return 'Iron Condor'
    elif volatility_percentile < 30:
        # Low IV: Prefer buying strategies
        if market_direction == 'bullish':
            return 'Long Call Spread'
        elif market_direction == 'bearish':
            return 'Long Put Spread'
        else:
            return 'Long Straddle'
    else:
        # Normal IV
        if market_direction == 'bullish':
            return 'Call Spread'
        elif market_direction == 'bearish':
            return 'Put Spread'
        else:
            return 'Long Strangle'
