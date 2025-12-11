"""
Test suite for Tax Optimization Engine

Tests for:
- Unrealized loss identification
- Tax lot analysis
- Wash sale detection
- Tax savings calculation
- Replacement security suggestions
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.tax_optimization import (
    TaxOptimizationEngine,
    TaxLot,
    TaxHarvestingOpportunity
)


@pytest.fixture
def sample_holdings():
    """Generate sample portfolio holdings."""
    today = pd.Timestamp.now()
    
    return pd.DataFrame({
        'symbol': ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'BRK.B', 'JPM'],
        'quantity': [100, 50, 25, 10, 20, 30],
        'purchase_price': [150, 300, 2500, 250, 350, 145],
        'current_price': [120, 310, 2600, 180, 340, 150],  # Some losses
        'purchase_date': [
            (today - timedelta(days=400)).strftime('%Y-%m-%d'),
            (today - timedelta(days=200)).strftime('%Y-%m-%d'),
            (today - timedelta(days=50)).strftime('%Y-%m-%d'),
            (today - timedelta(days=100)).strftime('%Y-%m-%d'),
            (today - timedelta(days=30)).strftime('%Y-%m-%d'),
            (today - timedelta(days=150)).strftime('%Y-%m-%d'),
        ]
    })


@pytest.fixture
def engine():
    """Create tax optimization engine."""
    return TaxOptimizationEngine()


class TestUnrealizedLossIdentification:
    """Test unrealized loss detection."""
    
    def test_identify_losses(self, engine, sample_holdings):
        """Test identification of unrealized losses."""
        losses = engine.identify_unrealized_losses(sample_holdings)
        
        assert isinstance(losses, list)
        assert all(isinstance(l, TaxLot) for l in losses)
        
        # Should identify losses
        assert len(losses) > 0
        
        # All should be negative
        for loss in losses:
            assert loss.unrealized_gain_loss < 0
    
    def test_loss_sorting(self, engine, sample_holdings):
        """Test losses are sorted by amount."""
        losses = engine.identify_unrealized_losses(sample_holdings)
        
        if len(losses) > 1:
            # Should be sorted by loss amount
            loss_amounts = [l.unrealized_gain_loss for l in losses]
            assert loss_amounts == sorted(loss_amounts)
    
    def test_holding_period_classification(self, engine, sample_holdings):
        """Test correct classification of holding periods."""
        losses = engine.identify_unrealized_losses(sample_holdings)
        
        for loss in losses:
            assert loss.holding_period in ['short', 'long']
            
            # Check if classification matches holding days
            if loss.holding_period == 'long':
                assert (pd.Timestamp.now() - pd.Timestamp(loss.purchase_date)).days >= 365
    
    def test_no_gains_in_losses(self, engine, sample_holdings):
        """Test that gains are not included in losses."""
        losses = engine.identify_unrealized_losses(sample_holdings)
        
        # All should be losses (negative)
        for loss in losses:
            assert loss.unrealized_gain_loss < 0


class TestTaxSavingsCalculation:
    """Test tax savings calculations."""
    
    def test_capital_gains_rate(self, engine):
        """Test tax savings with capital gains rate."""
        loss = 1000.0
        savings = engine.calculate_tax_savings(
            loss,
            holding_period='long'
        )
        
        # Savings should equal loss * rate
        expected = loss * engine.capital_gains_rate
        assert abs(savings - expected) < 0.01
    
    def test_ordinary_rate(self, engine):
        """Test tax savings with ordinary rate."""
        loss = 1000.0
        savings = engine.calculate_tax_savings(
            loss,
            holding_period='short'
        )
        
        # Should use ordinary rate
        expected = loss * engine.ordinary_rate
        assert abs(savings - expected) < 0.01
    
    def test_custom_rate(self, engine):
        """Test tax savings with custom tax rate."""
        loss = 1000.0
        custom_rate = 0.25
        savings = engine.calculate_tax_savings(
            loss,
            holding_period='short',
            marginal_tax_rate=custom_rate
        )
        
        expected = loss * custom_rate
        assert abs(savings - expected) < 0.01


class TestWashSaleDetection:
    """Test wash sale risk assessment."""
    
    def test_identical_security_wash_sale(self, engine):
        """Test wash sale detection for identical security."""
        risk = engine.assess_wash_sale_risk(
            'AAPL',
            100,
            replacement_symbol='AAPL'
        )
        
        # Should be high risk
        assert risk > 0.8
    
    def test_different_security_no_risk(self, engine):
        """Test no wash sale for different security."""
        risk = engine.assess_wash_sale_risk(
            'AAPL',
            100,
            replacement_symbol='GOOGL'
        )
        
        # Should be low risk
        assert risk < 0.5
    
    def test_similar_sector_risk(self, engine):
        """Test wash sale risk for similar securities."""
        risk = engine.assess_wash_sale_risk(
            'AAPL',
            100,
            replacement_symbol='MSFT'
        )
        
        # Similar tech stocks - moderate risk
        assert 0.1 < risk < 0.5


class TestReplacementSuggestions:
    """Test replacement security suggestions."""
    
    def test_get_replacements(self, engine):
        """Test replacement security suggestions."""
        replacements = engine.suggest_replacement_securities('AAPL', 120.0)
        
        assert isinstance(replacements, list)
        assert len(replacements) > 0
        assert 'AAPL' not in replacements  # Original not suggested
    
    def test_replacements_same_sector(self, engine):
        """Test replacements are in same sector."""
        replacements = engine.suggest_replacement_securities('AAPL', 120.0, sector_focus=True)
        
        # Should get tech alternatives
        assert len(replacements) > 0
    
    def test_replacements_limit(self, engine):
        """Test replacement suggestions are limited."""
        replacements = engine.suggest_replacement_securities('AAPL', 120.0)
        
        # Should not exceed 5
        assert len(replacements) <= 5


class TestBreakEvenTimeline:
    """Test breakeven calculation for tax harvesting."""
    
    def test_breakeven_calculation(self, engine):
        """Test breakeven timeline calculation."""
        tax_savings = 500.0
        breakeven = engine.calculate_breakeven_timeline(tax_savings, 0.05)
        
        # Should be at least 30 days (wash sale period)
        assert breakeven >= 30
        
        # Should be a number of days
        assert isinstance(breakeven, int)
    
    def test_high_return_shorter_breakeven(self, engine):
        """Test higher returns shorten breakeven."""
        tax_savings = 500.0
        
        breakeven_low = engine.calculate_breakeven_timeline(tax_savings, 0.02)
        breakeven_high = engine.calculate_breakeven_timeline(tax_savings, 0.10)
        
        # Higher return should have similar or shorter breakeven
        assert breakeven_high <= breakeven_low + 30


class TestTaxHarvestingReport:
    """Test tax harvesting report generation."""
    
    def test_report_generation(self, engine, sample_holdings):
        """Test tax harvesting report generation."""
        report = engine.generate_tax_harvesting_report(
            sample_holdings,
            max_opportunities=5,
            min_loss_amount=100
        )
        
        assert isinstance(report, dict)
        assert 'report_date' in report
        assert 'total_unrealized_losses' in report
        assert 'opportunities' in report
    
    def test_report_structure(self, engine, sample_holdings):
        """Test report has correct structure."""
        report = engine.generate_tax_harvesting_report(sample_holdings)
        
        required_keys = [
            'report_date',
            'total_unrealized_losses',
            'num_losing_positions',
            'total_potential_tax_savings',
            'avg_wash_sale_risk',
            'opportunities'
        ]
        
        for key in required_keys:
            assert key in report
    
    def test_opportunity_structure(self, engine, sample_holdings):
        """Test individual opportunities have correct structure."""
        report = engine.generate_tax_harvesting_report(sample_holdings)
        
        if report['opportunities']:
            opp = report['opportunities'][0]
            
            required_fields = [
                'symbol',
                'unrealized_loss',
                'tax_savings',
                'replacements',
                'wash_sale_risk'
            ]
            
            for field in required_fields:
                assert field in opp
    
    def test_report_savings_consistency(self, engine, sample_holdings):
        """Test tax savings are consistent in report."""
        report = engine.generate_tax_harvesting_report(sample_holdings)
        
        # Sum of opportunity savings should equal total
        opportunity_total = sum(
            o['tax_savings'] for o in report['opportunities']
        )
        
        # Should be reasonably close
        assert abs(opportunity_total - report['total_potential_tax_savings']) < 1


class TestTaxReportFileGeneration:
    """Test tax report file generation."""
    
    def test_csv_report_generation(self, engine, sample_holdings, tmp_path):
        """Test CSV report generation."""
        report = engine.generate_tax_harvesting_report(sample_holdings)
        
        # Generate CSV (mock the output directory)
        output_file = engine.generate_tax_report_csv(report, str(tmp_path))
        
        assert isinstance(output_file, str)
    
    def test_parquet_report_generation(self, engine, sample_holdings, tmp_path):
        """Test Parquet report generation."""
        report = engine.generate_tax_harvesting_report(sample_holdings)
        
        # Generate Parquet
        output_file = engine.save_tax_analysis_parquet(report, str(tmp_path))
        
        assert isinstance(output_file, str)


class TestTradeExecution:
    """Test tax harvest trade execution."""
    
    def test_trade_execution(self, engine):
        """Test trade execution simulation."""
        trade = engine.execute_tax_harvest_trade(
            symbol='AAPL',
            quantity=100,
            current_price=120.0,
            replacement_symbol='MSFT'
        )
        
        assert isinstance(trade, dict)
        assert trade['symbol'] == 'AAPL'
        assert 'action' in trade
        assert trade['action'] == 'SELL'
    
    def test_trade_fields(self, engine):
        """Test trade has all required fields."""
        trade = engine.execute_tax_harvest_trade(
            symbol='AAPL',
            quantity=100,
            current_price=120.0
        )
        
        required_fields = [
            'action',
            'symbol',
            'quantity',
            'price',
            'proceeds',
            'tax_savings',
            'wash_sale_risk_score'
        ]
        
        for field in required_fields:
            assert field in trade


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_empty_holdings(self, engine):
        """Test with empty holdings."""
        empty_df = pd.DataFrame(columns=[
            'symbol', 'quantity', 'purchase_price', 'current_price', 'purchase_date'
        ])
        
        losses = engine.identify_unrealized_losses(empty_df)
        assert losses == []
    
    def test_all_gains_no_losses(self, engine):
        """Test when all positions are gains."""
        holdings = pd.DataFrame({
            'symbol': ['AAPL', 'MSFT'],
            'quantity': [100, 50],
            'purchase_price': [100, 200],
            'current_price': [150, 250],
            'purchase_date': [
                (pd.Timestamp.now() - timedelta(days=100)).strftime('%Y-%m-%d'),
                (pd.Timestamp.now() - timedelta(days=100)).strftime('%Y-%m-%d')
            ]
        })
        
        losses = engine.identify_unrealized_losses(holdings)
        assert len(losses) == 0
    
    def test_very_large_loss(self, engine):
        """Test handling of very large losses."""
        loss = 1000000.0
        savings = engine.calculate_tax_savings(loss, 'long')
        
        # Should calculate correctly
        expected = loss * engine.capital_gains_rate
        assert abs(savings - expected) < 1
