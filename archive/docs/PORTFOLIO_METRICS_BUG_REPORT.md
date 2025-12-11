# Portfolio Metrics Bug Report & Fix

## Issue Summary

**Problem:** The landing page displayed incorrect portfolio metrics:
- **Portfolio Increase:** Only $20 (should be much higher based on holdings)
- **Total P&L %:** Only 0.03% (should reflect actual market performance)

## Root Cause Analysis

The bug was in the price data pipeline. Here's what was happening:

### 1. **Price Fetching Issue**
When `run_data_update_flows()` fetched prices for all portfolio symbols:
```python
for idx, ticker in enumerate(tickers):
    price_data = price_fetcher.fetch_price(ticker, asset_type=asset_type)
    if price_data:
        all_prices.append(price_data)
```

Each `fetch_price()` call returned a dict with its own `timestamp` field set to `datetime.now()`.

### 2. **Timestamp Problem**
Since these calls happened in a loop taking several seconds, each price dict got a **different timestamp**:
- Price 1: `2025-12-10 22:29:16.456844`
- Price 2: `2025-12-10 22:29:16.509084`
- Price 3: `2025-12-10 22:29:16.553216`
- ... and so on

### 3. **Data Retrieval Bug**
When the `fetch_latest_prices()` function tried to get current prices:
```python
latest_date = prices_df['timestamp'].max()  # Gets the LAST timestamp
latest_prices = prices_df[prices_df['timestamp'] == latest_date]  # Only 1 record!
```

It would only return the **single last record** (only GLD had a price on the latest timestamp).

### 4. **Fallback to Cost Basis**
With only 1 symbol having a price, the `enrich_holdings_with_prices()` function used the fallback:
```python
df['current_price'] = df['current_price'].fillna(df['bep'])  # Use break-even price
```

This meant:
- `current_value = qty × bep` (same as cost basis)
- `pnl_absolute = current_value - value_at_cost = 0`
- Only GLD showed any P&L because it was the only one with actual price data

### 5. **Database State**
The prices table in ParquetDB contained 957 records across 168 different timestamps, but each timestamp had only 1 record:
```
timestamp                       count
2025-12-10 22:29:16.456844      1    (AAPL)
2025-12-10 22:29:16.509084      1    (BA)
2025-12-10 22:29:16.553216      1    (GM)
...
2025-12-10 22:29:16.960846      1    (GLD)  ← Latest timestamp
```

## The Fix

**File:** `/Users/conordonohue/Desktop/TechStack/app.py` (lines 180-204)

Changed from:
```python
# Each price gets its own timestamp - BUG!
if 'timestamp' in prices_df.columns:
    prices_df['timestamp'] = pd.to_datetime(prices_df['timestamp'])
else:
    prices_df['timestamp'] = datetime.now()
```

To:
```python
# Use a single batch timestamp for all prices - FIXED!
batch_timestamp = datetime.now()
prices_df['timestamp'] = batch_timestamp

# Also map column names properly
if 'open' in prices_df.columns and 'open_price' not in prices_df.columns:
    prices_df['open_price'] = prices_df['open']
if 'high' in prices_df.columns and 'high_price' not in prices_df.columns:
    prices_df['high_price'] = prices_df['high']
if 'low' in prices_df.columns and 'low_price' not in prices_df.columns:
    prices_df['low_price'] = prices_df['low']
if 'close' in prices_df.columns and 'close_price' not in prices_df.columns:
    prices_df['close_price'] = prices_df['close']
```

## What This Fixes

1. ✅ **All prices get the same timestamp** - When you click "Update Price Data", all 48 symbols will now share one batch timestamp
2. ✅ **`fetch_latest_prices()` returns all prices** - Since all prices have the same timestamp, the max() filter will return all of them
3. ✅ **Portfolio P&L correctly calculated** - Current values will use actual market prices, not cost basis
4. ✅ **Portfolio increase shows real gains/losses** - Based on actual price movements

## Testing the Fix

1. **Delete stale price data** (recommended, but not required):
   ```bash
   rm -rf db/prices/
   ```

2. **Click "🔄 Update Price Data"** on the landing page

3. **Verify** the metrics update correctly with real market prices

## Expected Results After Fix

After running the price update with the fix:
- Portfolio value will reflect current market prices
- Total P&L will show actual gains/losses (positive or negative)
- Total P&L % will accurately reflect portfolio performance
- All 48 symbols will have current price data

## Impact

- **Files Changed:** 1 (`app.py`)
- **Lines Changed:** ~25 lines
- **Risk Level:** Low (data pipeline fix, no schema changes)
- **Testing:** Manual - run price update and verify metrics

## Notes

- The scipy/scikit-learn imports were also added to `pyproject.toml` in a separate fix for the backtesting engine
- This fix ensures the price data structure is consistent and retrievable
- Future enhancements could include batch timestamp validation and logging
