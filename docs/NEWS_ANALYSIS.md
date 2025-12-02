# News Analysis & Sentiment Integration

## Overview

The news analysis module scrapes headlines from major news outlets across the spectrum and performs NLP sentiment analysis to assess potential impacts on your portfolio holdings across different time horizons.

## Features

### 1. Multi-Source News Scraping
- **Primary Sources** (15 feeds, verified & working):
  - NPR (2 feeds): General + Business news
  - The Guardian (3 feeds): World, Business, Technology
  - BBC News, Al Jazeera, RTE, Reuters
  - CNN (2 feeds): Top Stories, Business
  - Fox News (2 feeds): Top Stories, Business
  - HackerNews, Reddit (3 feeds): Stocks, Investing, News

- **Fallback Sources** (4 feeds, for redundancy):
  - Reddit communities with active discussion
  - Additional Reuters feeds

- Automatically filters recent articles (configurable lookback period)
- Built-in resilience: fails gracefully if individual sources are unavailable
- Typical coverage: 150-250 articles per run from 13-15 working sources

### 2. Sentiment Analysis
- **VADER Sentiment Analysis**: Uses NLTK's SentimentIntensityAnalyzer for financial text
- **Polarity Classification**: 
  - Bullish (score ≥ 0.05)
  - Bearish (score ≤ -0.05)
  - Neutral (between -0.05 and 0.05)
- **Sentiment Scores**: Ranges from -1.0 (most negative) to +1.0 (most positive)

### 3. Sector & Geographic Identification
- Automatically identifies affected sectors from headlines:
  - Technology (AI, semiconductors, software, etc.)
  - Energy (oil, gas, renewable, OPEC, etc.)
  - Finance (banks, interest rates, fed, etc.)
  - Healthcare (pharma, vaccines, hospitals, etc.)
  - Consumer (retail, inflation, shopping, etc.)
  - Transportation (airlines, automotive, shipping, etc.)
  - Real Estate (housing, property, construction, etc.)
  - Utilities (electricity, power grid, infrastructure, etc.)

- Geographic impact detection:
  - US market impact
  - European impact
  - Asia-Pacific impact
  - Emerging markets impact

### 4. Timeframe Classification
News articles are classified by impact horizon:
- **Short-term** (immediate market reactions): Keywords like "crash", "surge", "today", "urgent"
- **Medium-term** (quarterly outlook): Keywords like "week", "month", "quarter", "guidance"
- **Long-term** (structural trends): Keywords like "trend", "strategic", "decade", "transformation"

### 5. Portfolio Impact Assessment
- Analyzes how news impacts your specific portfolio composition
- Identifies key risks (sectors with more bearish than bullish articles)
- Identifies key opportunities (sectors with more bullish than bearish articles)
- Provides exposure metrics by asset type

## Testing RSS Feed Health

### Run Feed Status Check

```bash
# Quick test: scrape headlines and verify feeds are working
uv run pytest tests/test_news_analysis.py::test_scrape_news_headlines -v

# Full news analysis test suite
uv run pytest tests/test_news_analysis.py -v
```

### Expected Results

- **test_scrape_news_headlines**: Validates that feeds return articles (150+ expected)
- **test_analyze_news_sentiment**: Confirms sentiment analysis on real data
- **test_sentiment_classification**: Validates bullish/bearish classification
- **test_sector_identification**: Ensures sector detection works
- **test_portfolio_impact_assessment**: Verifies portfolio correlation

### What to Do If Tests Fail

**Issue: No articles scraped**
- Individual feed timeouts are expected (some sources may be slow)
- System falls back to other sources automatically
- If <50 articles after 10 seconds, check internet connection
- Verify no network/firewall blocking RSS feeds

**Issue: Sentiment analysis errors**
- Ensure NLTK data downloaded: `python -m nltk.downloader vader_lexicon`
- TextBlob provides fallback if NLTK unavailable
- Run: `uv run python -c "from nltk.sentiment import SentimentIntensityAnalyzer; print('OK')"`

**Issue: Sector/region detection failing**
- Check `SECTOR_KEYWORDS` and `GEOGRAPHIC_KEYWORDS` in `src/news_analysis.py`
- Verify keywords match your portfolio's industry focus
- Add custom sectors/regions as needed

### Monitoring Feed Health

The news scraper logs which feeds work/fail:
```
18:17:53.482 | INFO | Scraped 193 articles from 13/18 sources. Failed: 4
```

This is normal - typically 2-4 sources timeout or are unavailable. The system:
- Uses 15 primary feeds for redundancy
- Falls back to 4 additional sources if needed
- Continues analysis with whatever articles are successfully retrieved

### RSS Feed Sources

**Working (Verified Dec 2025):**
- NPR (https://feeds.npr.org/1001/rss.xml, https://feeds.npr.org/1004/rss.xml, https://feeds.npr.org/1019/rss.xml)
- The Guardian (world, business, tech)
- BBC News (http://feeds.bbc.co.uk/news/rss.xml)
- CNN Top Stories (http://rss.cnn.com/rss/cnn_topstories.rss)
- Reuters (Reuters World feed)
- RTE News (https://www.rte.ie/news/rss/news-headlines.xml)
- Al Jazeera (https://www.aljazeera.com/xml/rss/all.xml)
- HackerNews, Fox News, Reddit feeds

**Timeout Issues (Set Aside for Future):**
- CBC News: Feeds hang (technical issue, not added to primary sources)
- Consider alternative if needed

---

## Usage

### Quick Start: Run News Analysis

```bash
# Run news analysis as part of enhanced analytics
uv run python -c "
from src.news_flows import news_informed_analytics_flow
result = news_informed_analytics_flow(send_email_report=False, include_news=True)
print(result['news_analysis']['report'])
"
```

### Standalone News Analysis

```python
from src.news_analysis import (
    scrape_news_headlines,
    analyze_news_sentiment,
    assess_portfolio_impact,
    get_news_analysis_report,
)
from src.portfolio_holdings import Holdings

# Step 1: Scrape headlines
articles = scrape_news_headlines(max_articles=50, hours_back=24)

# Step 2: Analyze sentiment
analyzed = analyze_news_sentiment(articles)

# Step 3: Assess portfolio impact
holdings = Holdings('holdings.csv')
impact = assess_portfolio_impact(analyzed, holdings.all_holdings)

# Step 4: Generate report
report = get_news_analysis_report(impact)
print(report)
```

## Output Example

```
=== NEWS IMPACT ANALYSIS REPORT ===
Generated: 2025-12-01T16:10:53.293016
Articles Analyzed: 30

SENTIMENT BREAKDOWN BY TIMEFRAME:

Long Term:
  Bullish: 9
  Bearish: 14
  Neutral: 6

Short Term:
  Bullish: 0
  Bearish: 0
  Neutral: 0

SECTOR IMPACT:

Technology:
  Bullish: 2
  Bearish: 12
  Latest: Five tech giants report earnings beat but outlook cautious...

Energy:
  Bullish: 3
  Bearish: 1
  Latest: Oil surges as OPEC production cuts take effect...

KEY RISKS:
  • Technology: 12 bearish articles
    → Semiconductor shortage concerns amid AI chip demand slowdown...
  • Healthcare: 4 bearish articles
    → Drug pricing pressures mount as legislation advances...

KEY OPPORTUNITIES:
  • Energy: 3 bullish articles
    → Renewable investments accelerate amid green energy transition...
  • Consumer: 1 bullish articles
    → Retail sales beat expectations despite economic concerns...
```

## API Reference

### `scrape_news_headlines(max_articles=100, hours_back=24)`
Scrapes recent headlines from configured news sources.

**Parameters:**
- `max_articles` (int): Maximum number of articles to return (default: 100)
- `hours_back` (int): Only retrieve articles from last N hours (default: 24)

**Returns:** List of article dictionaries with keys:
- `headline`: Article title
- `summary`: Article summary (first 500 chars)
- `source`: News outlet name
- `url`: Article URL
- `published_at`: Publication timestamp
- `scraped_at`: Scrape timestamp

### `analyze_news_sentiment(articles)`
Performs sentiment analysis on article headlines and summaries.

**Parameters:**
- `articles` (list): List of article dictionaries from scraper

**Returns:** Enhanced articles with added sentiment data:
- `sentiment_score`: Float between -1.0 and 1.0
- `sentiment_classification`: "bullish", "bearish", or "neutral"
- `sentiment_details`: Dict with detailed VADER scores
- `affected_sectors`: List of identified sectors
- `affected_regions`: List of identified geographic regions

### `assess_portfolio_impact(analyzed_articles, holdings_df)`
Correlates analyzed news with portfolio holdings to assess impact.

**Parameters:**
- `analyzed_articles` (list): Output from analyze_news_sentiment
- `holdings_df` (DataFrame): Portfolio holdings from Holdings class

**Returns:** Impact summary dictionary with:
- `by_sector`: Sentiment breakdown by affected sector
- `by_timeframe`: Sentiment breakdown by short/medium/long term
- `portfolio_exposure`: Asset type exposure metrics
- `key_risks`: High-bearish-count sectors
- `key_opportunities`: High-bullish-count sectors

### `get_news_analysis_report(impact_summary)`
Generates human-readable text report from impact summary.

**Parameters:**
- `impact_summary` (dict): Output from assess_portfolio_impact

**Returns:** Formatted text report suitable for display or email

## Integration with Existing Analytics

The news analysis integrates seamlessly with the portfolio analytics pipeline:

```python
from src.news_flows import news_informed_analytics_flow

# Runs standard analytics + news analysis
result = news_informed_analytics_flow(
    send_email_report=True,
    email="your@email.com",
    include_news=True,
)

# Result contains:
# - All standard analytics metrics (P&L, technical indicators, etc.)
# - news_analysis section with:
#   - impact_summary: Detailed impact data
#   - articles_analyzed: Count of articles
#   - report: Text report
```

## Customization

### Add Custom News Sources
Edit `NEWS_SOURCES` dict in `src/news_analysis.py`:

```python
NEWS_SOURCES = {
    "Your Source": "https://example.com/feed.xml",
    ...
}
```

### Adjust Sector Keywords
Modify `SECTOR_KEYWORDS` to customize sector detection:

```python
SECTOR_KEYWORDS = {
    "your_sector": ["keyword1", "keyword2", ...],
    ...
}
```

### Configure Sentiment Thresholds
Change sentiment classification thresholds in `analyze_news_sentiment()`:

```python
if compound >= 0.05:  # Adjust this threshold
    sentiment = "bullish"
```

## Performance Notes

- **Scraping**: ~1-2 seconds per 10-20 articles (depends on network)
- **Sentiment Analysis**: ~0.1 seconds per article
- **Portfolio Impact**: ~0.5 seconds for 100 articles + 50 holdings
- **Total Runtime**: ~5-10 seconds for full analysis

## Dependencies

- `feedparser`: RSS feed parsing
- `nltk`: Sentiment analysis (VADER)
- `textblob`: Fallback sentiment analysis
- `pandas`: Data manipulation
- `prefect`: Task orchestration

All dependencies are included in main `pyproject.toml`.

## Future Enhancements

- [ ] Add fine-tuned financial BERT models for better financial sentiment
- [ ] Implement company/ticker specific news filtering
- [ ] Add historical sentiment trends
- [ ] Integration with price movement data for validation
- [ ] Multi-language news support
- [ ] Real-time news alerts for portfolio holdings
