"""
Tax Loss Harvesting Optimization

Provides tax optimization strategies with:
- Unrealized loss identification
- Tax lot matching algorithms
- Replacement security suggestions
- Tax loss report generation
- Estimated tax savings calculation
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Set
from datetime import datetime, timedelta
from dataclasses import dataclass
import logging
from pathlib import Path

from src.parquet_db import ParquetDB
from src.utils import get_logger

logger = get_logger(__name__)


@dataclass
class TaxLot:
    """Represents a tax lot (position with specific purchase date and cost)."""
    symbol: str
    quantity: float
    purchase_price: float
    purchase_date: str
    current_price: float
    current_value: float
    unrealized_gain_loss: float
    gain_loss_pct: float
    holding_period: str  # 'short' (< 1 year) or 'long' (>= 1 year)


@dataclass
class TaxHarvestingOpportunity:
    """Represents a tax loss harvesting opportunity."""
    original_symbol: str
    unrealized_loss: float
    quantity: float
    tax_lot: TaxLot
    suggested_replacements: List[str]
    estimated_tax_savings: float
    wash_sale_risk: float  # 0-1, probability of wash sale


class TaxOptimizationEngine:
    """
    Tax optimization engine for identifying and executing tax loss harvesting.
    
    Features:
    - Identifies unrealized losses across portfolio
    - Suggests replacement securities (same sector/type)
    - Calculates tax savings
    - Tracks wash sale risk
    - Generates tax reports
    """
    
    def __init__(self, capital_gains_rate: float = 0.20, ordinary_rate: float = 0.35):
        """
        Initialize tax optimization engine.
        
        Args:
            capital_gains_rate: Long-term capital gains tax rate
            ordinary_rate: Ordinary income tax rate (for short-term gains)
        """
        self.capital_gains_rate = capital_gains_rate
        self.ordinary_rate = ordinary_rate
        self.db = ParquetDB()
        
        # Sector mappings for replacement suggestions
        self.sector_replacements = {
            'AAPL': ['MSFT', 'GOOGL', 'NVDA'],  # Tech
            'MSFT': ['AAPL', 'GOOGL', 'NVDA'],
            'GOOGL': ['AAPL', 'MSFT', 'META'],
            'META': ['GOOGL', 'NFLX', 'SNAP'],
            'TSLA': ['NIO', 'LUCID', 'RIVN'],  # EV makers
            'JPM': ['BAC', 'WFC', 'GS'],  # Banks
            'BAC': ['JPM', 'WFC', 'C'],
            'XOM': ['CVX', 'MPC', 'PSX'],  # Energy
            'PG': ['KO', 'CL', 'MO'],  # Consumer staples
            'JNJ': ['UNH', 'LLY', 'ABBV'],  # Healthcare
        }
    
    def identify_unrealized_losses(
        self,
        holdings: pd.DataFrame,
        include_short_term: bool = True
    ) -> List[TaxLot]:
        """
        Identify all unrealized losses in portfolio.
        
        Args:
            holdings: DataFrame with columns:
                - symbol, quantity, purchase_price, purchase_date, current_price
            include_short_term: Whether to include short-term losses
            
        Returns:
            List of TaxLot objects with losses
        """
        losing_positions = []
        today = pd.Timestamp.now()
        
        for _, row in holdings.iterrows():
            symbol = row['symbol']
            quantity = row['quantity']
            purchase_price = row['purchase_price']
            current_price = row['current_price']
            purchase_date = pd.Timestamp(row['purchase_date'])
            
            # Calculate gains/losses
            current_value = quantity * current_price
            book_value = quantity * purchase_price
            unrealized_gl = current_value - book_value
            gl_pct = (unrealized_gl / book_value) * 100 if book_value != 0 else 0
            
            # Determine holding period
            holding_days = (today - purchase_date).days
            is_long_term = holding_days >= 365
            holding_period = 'long' if is_long_term else 'short'
            
            # Only include losses
            if unrealized_gl < 0:
                if include_short_term or is_long_term:
                    tax_lot = TaxLot(
                        symbol=symbol,
                        quantity=quantity,
                        purchase_price=purchase_price,
                        purchase_date=purchase_date.strftime('%Y-%m-%d'),
                        current_price=current_price,
                        current_value=current_value,
                        unrealized_gain_loss=unrealized_gl,
                        gain_loss_pct=gl_pct,
                        holding_period=holding_period
                    )
                    losing_positions.append(tax_lot)
        
        # Sort by loss amount (descending)
        losing_positions.sort(key=lambda x: x.unrealized_gain_loss)
        
        return losing_positions
    
    def suggest_replacement_securities(
        self,
        symbol: str,
        current_price: float,
        sector_focus: bool = True
    ) -> List[str]:
        """
        Suggest replacement securities to avoid wash sale.
        
        Args:
            symbol: Symbol to replace
            current_price: Current price of symbol
            sector_focus: Whether to prioritize same sector
            
        Returns:
            List of suggested replacement symbols
        """
        suggestions = []
        
        # Check if we have sector replacements
        if sector_focus and symbol in self.sector_replacements:
            suggestions = self.sector_replacements[symbol].copy()
        
        # Add alternatives based on characteristics
        if not suggestions:
            # If no direct mapping, suggest similar price point alternatives
            if current_price < 50:
                suggestions = ['ARKK', 'IJH', 'IWM']  # Small/mid cap alternatives
            elif current_price < 200:
                suggestions = ['VOO', 'QQQ', 'SPLG']  # Large cap alternatives
            else:
                suggestions = ['BRK.B', 'AFRM', 'MSTR']  # High-price alternatives
        
        return suggestions[:5]  # Limit to 5 suggestions
    
    def calculate_tax_savings(
        self,
        loss_amount: float,
        holding_period: str,
        marginal_tax_rate: Optional[float] = None
    ) -> float:
        """
        Calculate estimated tax savings from realizing a loss.
        
        Args:
            loss_amount: Absolute value of loss
            holding_period: 'short' or 'long'
            marginal_tax_rate: Override marginal tax rate
            
        Returns:
            Estimated tax savings
        """
        if marginal_tax_rate is None:
            # Use holding period to determine tax rate
            if holding_period == 'short':
                marginal_tax_rate = self.ordinary_rate
            else:
                marginal_tax_rate = self.capital_gains_rate
        
        # Tax savings = loss amount * marginal rate
        tax_savings = loss_amount * marginal_tax_rate
        
        return tax_savings
    
    def assess_wash_sale_risk(
        self,
        symbol: str,
        quantity_to_sell: float,
        replacement_symbol: Optional[str] = None
    ) -> float:
        """
        Assess wash sale risk for selling and potentially buying replacement.
        
        Wash sale: If you buy substantially identical security within 30 days
        before/after selling at a loss, loss is disallowed.
        
        Args:
            symbol: Symbol being sold
            quantity_to_sell: Quantity to sell
            replacement_symbol: Potential replacement symbol
            
        Returns:
            Risk score 0-1 (0 = no risk, 1 = certain wash sale)
        """
        risk = 0.0
        
        # Risk 1: If replacement is the same security
        if replacement_symbol and replacement_symbol.split('.')[0] == symbol.split('.')[0]:
            risk = 0.95  # High risk
        
        # Risk 2: If replacement is very similar
        if replacement_symbol:
            # Check if same sector/type (would need real data for accuracy)
            similar_pairs = [
                (['AAPL', 'MSFT'], 0.3),
                (['JPM', 'BAC'], 0.3),
                (['XOM', 'CVX'], 0.25),
            ]
            
            for pair, pair_risk in similar_pairs:
                if {symbol, replacement_symbol} == set(pair):
                    risk = pair_risk
        
        return risk
    
    def calculate_breakeven_timeline(
        self,
        tax_savings: float,
        alternative_investment_return_pct: float = 0.05
    ) -> int:
        """
        Calculate how long until tax savings can be re-invested.
        
        Args:
            tax_savings: Amount of tax savings
            alternative_investment_return_pct: Annual return on alternative investment
            
        Returns:
            Days until breakeven
        """
        if alternative_investment_return_pct <= 0:
            return 365  # Default to 1 year
        
        daily_rate = alternative_investment_return_pct / 252
        
        # Timeline = 30 days minimum (wash sale period) + optimization window
        breakeven_days = 30 + int(365 * (0.02 / alternative_investment_return_pct))
        
        return breakeven_days
    
    def generate_tax_harvesting_report(
        self,
        holdings: pd.DataFrame,
        max_opportunities: int = 10,
        min_loss_amount: float = 100.0
    ) -> Dict:
        """
        Generate comprehensive tax harvesting report.
        
        Args:
            holdings: Portfolio holdings DataFrame
            max_opportunities: Maximum opportunities to report
            min_loss_amount: Minimum loss to consider
            
        Returns:
            Dict with harvesting opportunities and summary
        """
        # Identify losses
        losses = self.identify_unrealized_losses(holdings)
        
        # Filter by minimum loss amount
        significant_losses = [
            loss for loss in losses
            if abs(loss.unrealized_gain_loss) >= min_loss_amount
        ]
        
        opportunities = []
        total_potential_savings = 0.0
        
        for loss in significant_losses[:max_opportunities]:
            tax_savings = self.calculate_tax_savings(
                abs(loss.unrealized_gain_loss),
                loss.holding_period
            )
            
            replacements = self.suggest_replacement_securities(
                loss.symbol,
                loss.current_price
            )
            
            wash_sale_risk = min(
                [self.assess_wash_sale_risk(loss.symbol, loss.quantity, r) for r in replacements],
                default=0.1
            )
            
            opportunity = TaxHarvestingOpportunity(
                original_symbol=loss.symbol,
                unrealized_loss=abs(loss.unrealized_gain_loss),
                quantity=loss.quantity,
                tax_lot=loss,
                suggested_replacements=replacements,
                estimated_tax_savings=tax_savings,
                wash_sale_risk=wash_sale_risk
            )
            
            opportunities.append(opportunity)
            total_potential_savings += tax_savings
        
        # Calculate aggregate metrics
        short_term_losses = sum(
            abs(l.unrealized_gain_loss) for l in significant_losses
            if l.holding_period == 'short'
        )
        
        long_term_losses = sum(
            abs(l.unrealized_gain_loss) for l in significant_losses
            if l.holding_period == 'long'
        )
        
        report = {
            'report_date': pd.Timestamp.now().strftime('%Y-%m-%d'),
            'total_unrealized_losses': sum(abs(l.unrealized_gain_loss) for l in significant_losses),
            'short_term_losses': short_term_losses,
            'long_term_losses': long_term_losses,
            'num_losing_positions': len(significant_losses),
            'num_opportunities': len(opportunities),
            'total_potential_tax_savings': total_potential_savings,
            'avg_tax_savings_per_position': total_potential_savings / len(opportunities) if opportunities else 0,
            'avg_wash_sale_risk': np.mean([o.wash_sale_risk for o in opportunities]) if opportunities else 0,
            'opportunities': [
                {
                    'symbol': opp.original_symbol,
                    'unrealized_loss': opp.unrealized_loss,
                    'quantity': opp.quantity,
                    'tax_savings': opp.estimated_tax_savings,
                    'replacements': opp.suggested_replacements,
                    'wash_sale_risk': opp.wash_sale_risk,
                    'holding_period': opp.tax_lot.holding_period,
                    'days_held': (pd.Timestamp.now() - pd.Timestamp(opp.tax_lot.purchase_date)).days
                }
                for opp in opportunities
            ]
        }
        
        return report
    
    def generate_tax_report_csv(
        self,
        report: Dict,
        output_dir: str = "db"
    ) -> str:
        """Generate and save tax report as CSV."""
        try:
            # Create DataFrame from opportunities
            opportunities_df = pd.DataFrame(report['opportunities'])
            
            # Add summary row
            summary_df = pd.DataFrame([{
                'symbol': 'SUMMARY',
                'unrealized_loss': report['total_unrealized_losses'],
                'tax_savings': report['total_potential_tax_savings'],
                'quantity': '',
                'replacements': '',
                'wash_sale_risk': report['avg_wash_sale_risk'],
                'holding_period': '',
                'days_held': ''
            }])
            
            result_df = pd.concat([opportunities_df, summary_df], ignore_index=True)
            
            output_file = Path(output_dir) / "tax_optimization" / f"tax_report_{pd.Timestamp.now().strftime('%Y%m%d')}.csv"
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            result_df.to_csv(output_file, index=False)
            logger.info(f"Saved tax report to {output_file}")
            
            return str(output_file)
            
        except Exception as e:
            logger.error(f"Error saving tax report: {e}")
            return ""
    
    def save_tax_analysis_parquet(
        self,
        report: Dict,
        output_dir: str = "db"
    ) -> str:
        """Save tax analysis to Parquet format."""
        try:
            # Extract summary metrics
            summary_df = pd.DataFrame([{
                'report_date': report['report_date'],
                'total_unrealized_losses': report['total_unrealized_losses'],
                'short_term_losses': report['short_term_losses'],
                'long_term_losses': report['long_term_losses'],
                'num_losing_positions': report['num_losing_positions'],
                'total_potential_tax_savings': report['total_potential_tax_savings'],
                'avg_wash_sale_risk': report['avg_wash_sale_risk'],
                'timestamp': pd.Timestamp.now()
            }])
            
            output_file = Path(output_dir) / "tax_optimization" / f"summary_{pd.Timestamp.now().strftime('%Y%m%d')}.parquet"
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            summary_df.to_parquet(output_file)
            logger.info(f"Saved tax analysis summary to {output_file}")
            
            # Also save opportunities
            if report['opportunities']:
                opportunities_df = pd.DataFrame(report['opportunities'])
                opportunities_file = Path(output_dir) / "tax_optimization" / f"opportunities_{pd.Timestamp.now().strftime('%Y%m%d')}.parquet"
                opportunities_df.to_parquet(opportunities_file)
                logger.info(f"Saved tax opportunities to {opportunities_file}")
            
            return str(output_file)
            
        except Exception as e:
            logger.error(f"Error saving tax analysis: {e}")
            return ""
    
    def execute_tax_harvest_trade(
        self,
        symbol: str,
        quantity: float,
        current_price: float,
        replacement_symbol: Optional[str] = None
    ) -> Dict:
        """
        Simulate executing a tax harvest trade.
        
        Args:
            symbol: Symbol to sell at loss
            quantity: Quantity to sell
            current_price: Current market price
            replacement_symbol: Optional replacement security
            
        Returns:
            Trade execution summary
        """
        sale_proceeds = quantity * current_price
        loss_amount = quantity * (self.sector_replacements.get(symbol, [symbol])[0] or current_price * 0.1)  # Simulated purchase price
        
        tax_savings = self.calculate_tax_savings(loss_amount, 'short')
        wash_sale_risk = self.assess_wash_sale_risk(symbol, quantity, replacement_symbol)
        
        return {
            'action': 'SELL',
            'symbol': symbol,
            'quantity': quantity,
            'price': current_price,
            'proceeds': sale_proceeds,
            'loss_realized': loss_amount,
            'tax_savings': tax_savings,
            'replacement_symbol': replacement_symbol,
            'replacement_price': None,  # Would fetch real price in production
            'wash_sale_risk_score': wash_sale_risk,
            'execution_timestamp': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S'),
            'status': 'simulated'
        }
