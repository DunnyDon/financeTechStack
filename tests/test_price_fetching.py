#!/usr/bin/env python3
"""Test price fetching for holdings symbols."""

from src.portfolio_holdings import Holdings
from src.portfolio_prices import PriceFetcher

# Load holdings
print("Loading holdings from holdings.csv...")
holdings = Holdings()
symbols = holdings.get_unique_symbols()
print(f"✓ Loaded {len(symbols)} unique symbols: {symbols}")

# Fetch prices
print("\nFetching prices for all symbols...")
fetcher = PriceFetcher()

prices_fetched = 0
prices_missing = 0

for symbol in symbols:
    price_data = fetcher.fetch_price(symbol, "eq")
    if price_data:
        print(f"✓ {symbol}: ${price_data.get('price', 'N/A')}")
        prices_fetched += 1
    else:
        print(f"✗ {symbol}: Price not available")
        prices_missing += 1

print(f"\n✓ Successfully fetched prices for {prices_fetched}/{len(symbols)} symbols")
if prices_missing > 0:
    print(f"✗ {prices_missing} symbols failed to fetch (API rate limiting or unavailable)")

# Summary
print("\nPortfolio Summary:")
summary = holdings.get_summary()
print(f"  Total holdings: {summary['total_holdings']}")
print(f"  Total quantity: {summary['total_quantity']}")
print(f"  Total cost basis: €{summary['total_cost_basis']:.2f}")
