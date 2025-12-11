# Prefect News Sentiment Integration

## Overview

The news sentiment analysis feature now integrates with Prefect for task-level logging and observability while maintaining full Streamlit compatibility.

## Architecture

### New Module: `src/news_analysis_streamlit.py`

This module provides:

1. **Direct Functions (Streamlit-compatible)**
   - `scrape_news_articles()` - RSS feed parsing without Prefect context
   - `analyze_sentiment()` - TextBlob sentiment analysis
   - `get_portfolio_mentions()` - Symbol mention detection
   - `analyze_news_sentiment_streamlit()` - Main function for Streamlit calls

2. **Prefect Flow (Optional Logging)**
   - `news_sentiment_analysis_flow()` - Orchestrates all tasks with Prefect logging
   - `scrape_news_task()` - Prefect task for scraping
   - `analyze_sentiment_task()` - Prefect task for sentiment analysis

## How It Works

### In Streamlit (app.py)

```python
from src.news_analysis_streamlit import news_sentiment_analysis_flow

# Call the flow - works both with and without Prefect context
articles, stats = news_sentiment_analysis_flow(
    max_articles=100,
    hours_back=24,
    symbols=['AAPL', 'MSFT', ...]
)
```

**Returns:**
- `articles`: List of dictionaries with article data and sentiment scores
- `stats`: Dictionary with aggregated statistics:
  - `total_articles`: Total count
  - `avg_sentiment`: Mean sentiment score (-1 to 1)
  - `positive_count`: Articles with positive sentiment
  - `negative_count`: Articles with negative sentiment
  - `neutral_count`: Articles with neutral sentiment
  - `portfolio_mentions`: Dict of symbol -> mention count
  - `sources_count`: Number of successful news sources

### Prefect Logging

When Prefect is running:
1. Each task is logged individually with execution time and status
2. Results from each task are visible in the Prefect UI (http://localhost:4200)
3. Historical runs are recorded for auditing and debugging
4. Errors are automatically captured with stack traces

### Data Processing

1. **Scraping Phase**
   - Fetches RSS feeds from 6 major financial news sources:
     - Reuters, Bloomberg, CNBC, MarketWatch, Financial Times, Yahoo Finance
   - Filters articles by publication time (last N hours)
   - Handles parsing errors gracefully

2. **Sentiment Analysis Phase**
   - Uses TextBlob for polarity analysis (-1 to +1 scale)
   - Fallback to keyword-based sentiment if TextBlob unavailable
   - Classifies as: Positive (>0.1), Negative (<-0.1), Neutral

3. **Portfolio Mapping Phase**
   - Checks titles and summaries for symbol mentions
   - Case-insensitive matching
   - Counts multiple mentions per symbol

## Integration Points

### Dashboard Display (app.py)

The Advanced Analytics > News tab now:
- Shows real-time sentiment metrics
- Displays sentiment distribution pie chart
- Lists articles filtered by sentiment
- Shows portfolio mentions with counts
- Links to Prefect UI for execution details

### Prefect Server

Auto-starts with the dashboard:
- **Port**: 4200
- **Command**: `uv run python -m prefect server start`
- **Auto-cleanup**: Kills Prefect when dashboard stops

### Monitoring

Users can:
1. Click "📋 Prefect Logs" button in Advanced Analytics
2. Navigate to http://localhost:4200
3. View task execution details, logs, and historical runs
4. Debug any issues in the news scraping pipeline

## Error Handling

**Graceful Degradation:**
- If a news source fails to respond, skips to next source
- If sentiment analysis library missing, uses keyword fallback
- If Prefect unavailable, still works without logging
- If no articles found, shows informative message

**User Feedback:**
- Success messages show article count and sources
- Error messages provide actionable tips
- Info messages link to Prefect logs for debugging

## Configuration

No additional configuration needed. The module automatically:
- Detects if Prefect is installed and available
- Falls back to direct execution if needed
- Uses standard logging for both modes
- Caches nothing (fresh data on each run)

## Testing

To test the news sentiment flow:

```bash
# Test direct function (Streamlit mode)
python -c "
from src.news_analysis_streamlit import analyze_news_sentiment_streamlit
articles, stats = analyze_news_sentiment_streamlit(max_articles=10, hours_back=24)
print(f'Found {stats[\"total_articles\"]} articles')
print(f'Sentiment: {stats[\"avg_sentiment\"]:.2f}')
"

# Test with Prefect (optional)
python -c "
from src.news_analysis_streamlit import news_sentiment_analysis_flow
articles, stats = news_sentiment_analysis_flow(max_articles=10, hours_back=24)
print(f'Flow completed: {stats[\"total_articles\"]} articles')
"
```

## Performance

- **Scraping**: ~2-5 seconds for all 6 sources (parallel would be faster)
- **Sentiment Analysis**: ~0.1 seconds per article
- **Total**: Typically 3-8 seconds depending on article count and feed responsiveness
- **Logging Overhead**: Minimal when Prefect task logging is active

## Future Improvements

Potential enhancements:
- Parallel scraping of multiple sources
- Caching of articles to reduce API calls
- More advanced NLP models for sentiment
- Watchlist-specific news filtering
- Email alerts for significant sentiment shifts
