# Tax Optimization & Loss Harvesting

## Overview

The Tax Optimization Engine identifies tax loss harvesting opportunities to reduce taxable gains:
- **Unrealized Loss Detection**: Scans portfolio for losing positions
- **Tax Savings Estimation**: Calculates potential tax savings by tax bracket
- **Replacement Suggestions**: Suggests sector-aligned alternatives to avoid wash sales
- **Wash Sale Analysis**: Quantifies risk of disallowed losses
- **Tax Reports**: Generates CSV/Parquet reports for tax preparation

## Quick Start

```python
from src.tax_optimization import TaxOptimizationEngine
import pandas as pd

# Initialize engine (customize tax rates as needed)
engine = TaxOptimizationEngine(
    capital_gains_rate=0.20,  # 20% long-term cap gains
    ordinary_rate=0.37        # 37% ordinary income
)

# Load portfolio holdings
holdings = pd.DataFrame({
    'symbol': ['AAPL', 'MSFT', 'TSLA'],
    'quantity': [100, 50, 10],
    'purchase_price': [150, 300, 250],
    'current_price': [120, 310, 180],
    'purchase_date': ['2023-01-15', '2023-06-20', '2024-06-10']
})

# Generate tax harvesting report
report = engine.generate_tax_harvesting_report(
    holdings,
    max_opportunities=10,
    min_loss_amount=100
)

print(f"Total Unrealized Losses: ${report['total_unrealized_losses']:,.2f}")
print(f"Potential Tax Savings: ${report['total_potential_tax_savings']:,.2f}")
print(f"Opportunities: {report['num_opportunities']}")
```

## Core Features

### 1. Loss Identification

```python
losses = engine.identify_unrealized_losses(holdings)

for loss in losses:
    print(f"{loss.symbol}: Loss = ${-loss.unrealized_gain_loss:.2f}")
    print(f"  Holding Period: {loss.holding_period}")
    print(f"  Days Held: {(pd.Timestamp.now() - pd.Timestamp(loss.purchase_date)).days}")
```

**Holding Period Classification**:
- **Long-term** (≥1 year): Preferential tax rate (~20%)
- **Short-term** (<1 year): Ordinary income rate (~37%)

### 2. Tax Savings Calculation

```python
# Calculate tax savings for a specific loss
loss_amount = 1000.0
holding_period = 'long'

tax_savings = engine.calculate_tax_savings(
    loss_amount,
    holding_period
)
# Result: $1000 × 0.20 = $200
```

**Tax Rates**:
- Short-term losses offset ordinary income (highest rate)
- Long-term losses offset capital gains (preferential rate)
- Unused losses carry forward indefinitely

### 3. Wash Sale Detection

```python
# Check wash sale risk when replacing a position
risk = engine.assess_wash_sale_risk(
    symbol='AAPL',
    quantity_to_sell=100,
    replacement_symbol='MSFT'
)

print(f"Wash Sale Risk: {risk:.1%}")
# Output: 0.1% (low risk - different companies)
```

**Wash Sale Rules**:
- Cannot buy substantially identical security within ±30 days
- Purchase before sale is risky (opens the window)
- Better to wait 31 days after sale or buy different security
- Risk Score: 0 (no risk) to 1 (certain wash sale)

### 4. Replacement Security Suggestions

```python
replacements = engine.suggest_replacement_securities(
    symbol='AAPL',
    current_price=120.0,
    sector_focus=True
)

print(f"Suggested Replacements: {replacements}")
# Output: ['MSFT', 'GOOGL', 'NVDA']
```

**Replacement Strategy**:
- **Same Sector**: Maintains market exposure
- **Different Type**: Switches asset class entirely
- **Risk-Adjusted**: Matches similar volatility profile

### 5. Comprehensive Tax Report

```python
report = engine.generate_tax_harvesting_report(holdings)

# Summary metrics
print(f"Total Unrealized Losses: ${report['total_unrealized_losses']:,.0f}")
print(f"  Short-term: ${report['short_term_losses']:,.0f}")
print(f"  Long-term: ${report['long_term_losses']:,.0f}")
print(f"Total Potential Tax Savings: ${report['total_potential_tax_savings']:,.0f}")
print(f"Average Wash Sale Risk: {report['avg_wash_sale_risk']:.1%}")

# Per-position opportunities
for opp in report['opportunities']:
    print(f"\n{opp['symbol']}")
    print(f"  Loss: ${opp['unrealized_loss']:,.0f}")
    print(f"  Tax Savings: ${opp['tax_savings']:,.0f}")
    print(f"  Replacements: {opp['replacements']}")
    print(f"  Wash Sale Risk: {opp['wash_sale_risk']:.1%}")
```

## Implementation Strategy

### Immediate Losses (This Month)
1. Identify losses ≥$500
2. Calculate tax savings
3. Execute sales before month-end
4. Use specified lot method
5. Wait 31 days before buying back

### Accumulated Losses (Year Planning)
1. Monitor throughout year
2. Bank losses for tax planning
3. Harvest before Dec 31 deadline
4. Consider future income (bunching strategy)
5. Coordinate with gains realization

### Edge Cases

**No Wash Sales Risk**:
```python
# Different sector
risk = engine.assess_wash_sale_risk('AAPL', 100, 'JPM')  # 0.1%

# Unrelated asset class
risk = engine.assess_wash_sale_risk('AAPL', 100, 'GLD')  # ~0%
```

**Significant Losses**:
```python
# Large loss that exceeds cap gains limit ($3,000/year)
loss_amount = 15000.0
# - Can offset $3,000 ordinary income
# - Remaining $12,000 carries forward to next year
# - Total tax savings: $3,000 × rate + future years
```

## Export Formats

### CSV Report
```python
output_file = engine.generate_tax_report_csv(report)
# Output: db/tax_optimization/tax_report_YYYYMMDD.csv
```

Columns: symbol, unrealized_loss, tax_savings, replacements, wash_sale_risk, holding_period

### Parquet Report
```python
output_file = engine.save_tax_analysis_parquet(report)
# Output: db/tax_optimization/summary_YYYYMMDD.parquet
#         db/tax_optimization/opportunities_YYYYMMDD.parquet
```

## Tax Planning Scenarios

### Scenario 1: Year-End Tax Planning
```python
# Current situation: $50k gains, $30k losses identified
# Tax impact: (50k - 30k) × 0.20 = $4,000 taxes saved

# Solution: Harvest all identified losses before Dec 31
report = engine.generate_tax_harvesting_report(holdings, min_loss_amount=0)
print(f"Tax Savings from Harvesting: ${report['total_potential_tax_savings']:,.0f}")
```

### Scenario 2: Income Smoothing
```python
# High income year - maximize loss harvesting
# Low income year - realize capital gains (lower rate)

losses = engine.identify_unrealized_losses(holdings)
total_loss = sum(-l.unrealized_gain_loss for l in losses if l.holding_period == 'short')
# Harvest short-term losses (offset ordinary income)
```

### Scenario 3: Maintain Exposure
```python
# Sell losing position, buy replacement in same sector
trade = engine.execute_tax_harvest_trade(
    symbol='AAPL',
    quantity=100,
    current_price=120.0,
    replacement_symbol='MSFT'
)

print(f"Action: {trade['action']} {trade['quantity']} {trade['symbol']} @ ${trade['price']}")
print(f"Tax Savings: ${trade['tax_savings']:,.0f}")
```

## Configuration

### Tax Rates (US Federal, 2024)
```python
# Long-term capital gains
engine = TaxOptimizationEngine(capital_gains_rate=0.20)

# Ordinary income tax (based on bracket)
engine = TaxOptimizationEngine(ordinary_rate=0.37)
```

### State Taxes (Add supplementary rate)
```python
# California has additional state tax
federal_rate = 0.20
state_rate = 0.135  # CA top rate
total_rate = federal_rate + state_rate  # 33.5%
```

## Data Requirements

**Holdings DataFrame columns**:
- `symbol`: Stock ticker
- `quantity`: Number of shares
- `purchase_price`: Cost basis per share
- `current_price`: Current market price
- `purchase_date`: Date of purchase (YYYY-MM-DD)

## Performance & Limitations

- Processes portfolios with 100+ positions instantly
- Wash sale detection based on ticker similarity (not perfect)
- Tax rates are configurable (defaults are 2024 US federal)
- Does not account for Alternative Minimum Tax (AMT)
- State tax considerations not included (add manually)

## Common Pitfalls

❌ **Selling winner then buying immediately**: Creates wash sale  
✅ Solution: Wait 31 days or buy different security

❌ **Harvesting 12/31, buying 1/1**: IRS considers wash sale  
✅ Solution: Wait until 1/31 to repurchase

❌ **Spouse buys identical security within 30 days**: Disallows loss  
✅ Solution: Coordinate with spouse; use replacements

## See Also

- [README](../../README.md) - Project overview
- [ARCHITECTURE_OVERVIEW](../architecture/ARCHITECTURE_OVERVIEW.md) - System design
- [TAX_OPTIMIZATION](../reference/TAX_OPTIMIZATION.md) - API reference
