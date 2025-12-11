# Advanced Analytics Documentation

Complete guide to all new advanced portfolio analytics features.

---

## 📚 Modules Overview

### 1. Risk Analytics (`src/portfolio_risk.py`)
Comprehensive risk measurement and stress testing.

**Key Classes:**
- `RiskAnalytics` - Main risk calculation engine

**Key Methods:**
- `calculate_var()` - Value at Risk (historical simulation)
- `calculate_correlation_matrix()` - Asset correlation analysis
- `calculate_portfolio_beta()` - Beta against market benchmark
- `calculate_portfolio_volatility()` - Annualized volatility
- `calculate_max_drawdown()` - Peak-to-trough decline
- `calculate_sharpe_ratio()` - Risk-adjusted return metric
- `stress_test()` - Scenario analysis with price shocks
- `calculate_concentration_risk()` - Portfolio concentration metrics

**Usage Example:**
```python
from src.portfolio_risk import RiskAnalytics
import pandas as pd

prices_df = pd.DataFrame(...)  # DataFrame with date index, ticker columns
ra = RiskAnalytics(prices_df, risk_free_rate=0.04)

# VaR
var_95 = ra.calculate_var(confidence=0.95, days=1)

# Beta
weights = {"AAPL": 0.5, "MSFT": 0.5}
portfolio_beta = ra.calculate_portfolio_beta(weights, market_ticker="SPY")

# Concentration
conc = ra.calculate_concentration_risk(weights)
```

---

### 2. Portfolio Optimization (`src/portfolio_optimization.py`)
Mean-variance optimization and rebalancing recommendations.

**Key Classes:**
- `PortfolioOptimizer` - Optimization engine
- `OptimizationResult` - Result dataclass

**Key Methods:**
- `minimum_variance_portfolio()` - Lowest-risk allocation
- `maximum_sharpe_ratio_portfolio()` - Highest risk-adjusted return
- `efficient_frontier()` - Frontier points for visualization
- `rebalancing_recommendations()` - When and how to rebalance
- `tax_loss_harvesting_opportunities()` - Losses to harvest

**Usage Example:**
```python
from src.portfolio_optimization import PortfolioOptimizer

returns_df = prices_df.pct_change().dropna()
optimizer = PortfolioOptimizer(returns_df, risk_free_rate=0.04)

# Get optimal weights
min_var = optimizer.minimum_variance_portfolio(["AAPL", "MSFT", "GOOGL"])
print(f"Optimal weights: {min_var.weights}")
print(f"Expected return: {min_var.expected_return:.2%}")
print(f"Sharpe ratio: {min_var.sharpe_ratio:.4f}")

# Rebalancing
current = {"AAPL": 0.4, "MSFT": 0.3, "GOOGL": 0.3}
target = {"AAPL": 0.33, "MSFT": 0.33, "GOOGL": 0.34}
recommendations = optimizer.rebalancing_recommendations(current, target, threshold=0.05)
```

---

### 3. Options Analysis (`src/options_analysis.py`)
Greeks calculations and options strategy analysis.

**Key Classes:**
- `OptionsAnalysis` - Options pricing and Greeks
- `GreeksResult` - Greeks dataclass

**Key Methods:**
- `calculate_greeks()` - Delta, Gamma, Theta, Vega, Rho
- `estimate_implied_volatility()` - IV from option price
- `analyze_position()` - Multi-position strategy Greeks

**Greeks Explained:**
- **Delta**: Rate of change with underlying price (-1 to +1)
- **Gamma**: Rate of change of delta (curvature)
- **Theta**: Time decay (daily P&L from time passage)
- **Vega**: Sensitivity to 1% change in volatility
- **Rho**: Sensitivity to interest rates

**Usage Example:**
```python
from src.options_analysis import OptionsAnalysis

# Single option Greeks
greeks = OptionsAnalysis.calculate_greeks(
    spot_price=100,
    strike_price=105,
    time_to_expiry=0.25,  # 3 months
    volatility=0.20,
    option_type="call"
)
print(f"Delta: {greeks.delta:.4f}")
print(f"Theta (daily decay): ${greeks.theta:.2f}")

# Multi-position strategy
positions = [
    {"type": "call", "strike": 100, "quantity": 1, "expiry_days": 30},
    {"type": "put", "strike": 95, "quantity": 1, "expiry_days": 30},
]
analysis = OptionsAnalysis.analyze_position(positions, spot_price=100)
print(f"Portfolio delta: {analysis['portfolio_delta']:.4f}")
```

---

### 4. Fixed Income Analysis (`src/fixed_income_analysis.py`)
Bond analytics and fixed income metrics.

**Key Classes:**
- `FixedIncomeAnalysis` - Bond calculations
- `BondMetrics` - Bond metrics dataclass

**Key Methods:**
- `calculate_bond_price()` - PV of cash flows
- `calculate_ytm_simple()` - Yield to maturity (Newton-Raphson)
- `calculate_duration()` - Macaulay, modified, effective duration
- `calculate_convexity()` - Convexity adjustment
- `estimate_price_change()` - Price sensitivity to rate changes
- `build_yield_curve()` - Yield curve analysis
- `calculate_credit_spread()` - OAS approximation

**Duration Interpretation:**
- Macaulay duration: Weighted average time to cash flows
- Modified duration: Bond price sensitivity to 1% rate change
- Example: 5-year duration bond = 5% price decline if rates rise 1%

**Usage Example:**
```python
from src.fixed_income_analysis import FixedIncomeAnalysis

# Bond pricing and YTM
ytm = FixedIncomeAnalysis.calculate_ytm_simple(
    current_price=950,
    face_value=1000,
    coupon_rate=0.05,
    years_to_maturity=5
)

# Duration
mac_dur, mod_dur, _ = FixedIncomeAnalysis.calculate_duration(
    face_value=1000,
    coupon_rate=0.05,
    years_to_maturity=5,
    yield_to_maturity=ytm
)
print(f"Modified duration: {mod_dur:.2f} years")

# Price if rates change
new_price = FixedIncomeAnalysis.estimate_price_change(
    current_price=950,
    yield_change=0.01,  # +1%
    duration=mod_dur,
    convexity=...
)
```

---

### 5. Quick Wins Analytics (`src/quick_wins_analytics.py`)
High-value, easy-to-implement analytics.

**Key Classes:**
- `QuickWinsAnalytics` - Quick calculations

**Key Methods:**
- `sector_allocation()` - Portfolio by sector
- `asset_class_breakdown()` - Equity/crypto/bond mix
- `portfolio_volatility()` - Annualized volatility
- `dividend_income_projection()` - Expected dividends
- `winners_losers_report()` - Best and worst performers
- `correlation_matrix_summary()` - Correlation analysis
- `sharpe_ratio_calculation()` - Risk-adjusted performance
- `concentration_risk_metrics()` - Diversification score

**Usage Example:**
```python
from src.quick_wins_analytics import QuickWinsAnalytics

# Sector allocation
holdings = {
    "AAPL": {"quantity": 10, "price": 150, "sector": "Technology"},
    "JPM": {"quantity": 5, "price": 150, "sector": "Finance"},
}
allocation = QuickWinsAnalytics.sector_allocation(holdings)
# Output: {"Technology": 66.67, "Finance": 33.33}

# Winners/losers
positions = {
    "AAPL": {"entry_price": 100, "current_price": 150},
    "MSFT": {"entry_price": 200, "current_price": 180},
}
report = QuickWinsAnalytics.winners_losers_report(positions)

# Concentration risk
weights = {"AAPL": 0.6, "MSFT": 0.25, "GOOGL": 0.15}
metrics = QuickWinsAnalytics.concentration_risk_metrics(weights)
# High HHI = concentrated, low HHI = diversified
```

---

## 🔄 Prefect Flows (`src/advanced_analytics_flows.py`)

### Main Flow: `advanced_analytics_flow`
Orchestrates all advanced analytics.

**Inputs:**
```python
advanced_analytics_flow(
    tickers=["AAPL", "MSFT", "GOOGL"],
    weights={"AAPL": 0.4, "MSFT": 0.35, "GOOGL": 0.25},
    holdings={...},  # Optional: sector, dividend info
    option_positions=[...],  # Optional: options for Greeks
    bond_positions=[...]  # Optional: bonds for fixed income
)
```

**Output:**
```python
{
    "risk_metrics": {...},
    "optimization_metrics": {...},
    "quick_wins": {...},
    "options_analysis": {...},
    "fixed_income_analysis": {...},
    "report": "...",
    "timestamp": "2025-01-15T10:30:00"
}
```

**Tasks:**
- `fetch_historical_prices()` - Get 1-year price history
- `calculate_risk_metrics()` - VaR, beta, concentration
- `calculate_optimization_metrics()` - Efficient frontier
- `calculate_quick_wins()` - Sector, winners/losers, etc.
- `analyze_options_positions()` - Greeks aggregation
- `analyze_fixed_income_positions()` - Bond metrics
- `generate_advanced_report()` - Human-readable report

---

## 📊 Key Metrics Reference

### Risk Metrics
| Metric | Interpretation | Target |
|--------|---|---|
| VaR 95% | 95% chance loss < this amount | < 5% daily |
| Beta | Market sensitivity (β=1 matches market) | 0.8-1.2 |
| Volatility | Price variability (annualized) | < 20% for balanced |
| HHI | Concentration index (1=all in one, low=diversified) | < 0.15 |

### Optimization Outputs
| Metric | Use Case |
|--------|----------|
| Min Variance | Conservative, low risk |
| Max Sharpe | Best risk-adjusted return |
| Efficient Frontier | Visualization of risk-return tradeoff |

### Options Greeks
| Greek | Meaning | Monitor |
|-------|---------|---------|
| Delta | Directional exposure (-1 to +1) | Hedge if > ±0.7 |
| Theta | Daily time decay ($) | Positive if profitable on decay |
| Vega | Volatility sensitivity | Negative if vol expected to fall |

### Bond Metrics
| Metric | Interpretation |
|--------|---|
| YTM | Total return if held to maturity |
| Duration | Price sensitivity: 1% rate change = X% price change |
| Convexity | Non-linear price behavior |
| Credit Spread | Excess yield over risk-free rate |

---

## 🧪 Testing

Run all advanced analytics tests:
```bash
uv run pytest tests/test_advanced_analytics.py -v
```

Run specific test class:
```bash
uv run pytest tests/test_advanced_analytics.py::TestRiskAnalytics -v
```

---

## 💡 Common Workflows

### 1. Portfolio Risk Assessment
```python
from src.advanced_analytics_flows import advanced_analytics_flow

result = advanced_analytics_flow(
    tickers=["AAPL", "MSFT", "GOOGL"],
    weights={"AAPL": 0.4, "MSFT": 0.35, "GOOGL": 0.25}
)

risk = result["risk_metrics"]
print(f"Daily VaR 95%: {risk['var_95_daily']:.4f}")
print(f"Concentrated: {risk['is_concentrated']}")
```

### 2. Rebalancing Analysis
```python
from src.portfolio_optimization import PortfolioOptimizer

optimizer = PortfolioOptimizer(returns_df)
recommendations = optimizer.rebalancing_recommendations(
    current={"AAPL": 0.5, "MSFT": 0.5},
    target={"AAPL": 0.33, "MSFT": 0.33, "GOOGL": 0.34}
)

for ticker, rec in recommendations.items():
    print(f"{ticker}: {rec['action']} {rec['drift']*100:.2f}%")
```

### 3. Options Strategy Analysis
```python
from src.options_analysis import OptionsAnalysis

# Collar strategy: own stock, sell call, buy put
positions = [
    {"type": "call", "strike": 105, "quantity": -1},  # Short call
    {"type": "put", "strike": 95, "quantity": 1},      # Long put
]

analysis = OptionsAnalysis.analyze_position(positions, spot_price=100)
print(f"Delta: {analysis['portfolio_delta']:.4f}")  # Should be ~0 for collar
```

### 4. Bond Portfolio Duration
```python
from src.fixed_income_analysis import FixedIncomeAnalysis

# If rates rise 1%, portfolio price change:
price_change = FixedIncomeAnalysis.estimate_price_change(
    current_price=10000,
    yield_change=0.01,
    duration=5.5,
    convexity=42
)
print(f"Estimated loss: ${price_change['price_change']:.2f}")
```

---

## 🚀 Integration with Existing Flows

All advanced analytics automatically integrate with:
- `analytics_flows.py` - Enhanced analytics with risk/optimization
- `portfolio_flows.py` - Portfolio management orchestration
- `portfolio_technical.py` - Technical indicators + risk metrics
- `portfolio_fundamentals.py` - Fundamentals + optimization

No changes needed - just run existing flows to get advanced metrics!

---

## 📈 Performance Notes

- **Risk calculations**: ~500ms for 252 days of data
- **Optimization**: ~1-2s for 10+ assets (uses heuristics, not exact)
- **Greeks**: ~10ms per position
- **Bond calcs**: ~100ms per bond

All calculations cached where possible for Prefect flow efficiency.

---

## 🔗 See Also

- [FUTURE_WORK.md](../FUTURE_WORK.md) - Advanced features roadmap
- [docs/USAGE.md](USAGE.md) - General usage guide
- [tests/test_advanced_analytics.py](../tests/test_advanced_analytics.py) - Test examples
