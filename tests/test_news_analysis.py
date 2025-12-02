"""
Tests for news scraping and sentiment analysis.

Includes RSS feed health checks and sentiment analysis validation.
"""

import pytest
from src.news_analysis import (
    analyze_news_sentiment,
    assess_portfolio_impact,
    scrape_news_headlines,
    NEWS_SOURCES,
    FALLBACK_NEWS_SOURCES,
)


@pytest.mark.asyncio
async def test_scrape_news_headlines():
    """
    Test news headline scraping from multiple RSS sources.
    
    Validates:
    - RSS feeds are accessible
    - Articles contain required fields
    - System tolerates individual feed failures
    - Scrapes 150+ articles from 13-15 sources
    """
    articles = scrape_news_headlines(max_articles=500, hours_back=24)
    
    # Articles list should be populated
    assert isinstance(articles, list)
    assert len(articles) > 0, "Expected articles from RSS feeds"
    
    # Should scrape substantial volume (150+ typical)
    assert len(articles) >= 50, f"Expected at least 50 articles, got {len(articles)}"
    
    # Verify article structure
    for article in articles[:5]:  # Check first few articles
        assert "headline" in article, "Article missing 'headline' field"
        assert "source" in article, "Article missing 'source' field"
        assert "url" in article, "Article missing 'url' field"
        assert "scraped_at" in article, "Article missing 'scraped_at' field"
        assert len(article["headline"]) > 0, "Headline should not be empty"


def test_rss_feed_configuration():
    """
    Test that RSS feed sources are properly configured.
    
    Validates:
    - Primary news sources defined
    - Fallback sources available
    - All sources have valid URLs
    """
    # Check primary sources
    assert len(NEWS_SOURCES) > 0, "No primary news sources configured"
    assert len(NEWS_SOURCES) >= 14, f"Expected 14+ primary sources, found {len(NEWS_SOURCES)}"
    
    # Check fallback sources
    assert len(FALLBACK_NEWS_SOURCES) > 0, "No fallback news sources configured"
    
    # Validate URL format
    for name, url in NEWS_SOURCES.items():
        assert isinstance(name, str), f"Source name should be string: {name}"
        assert isinstance(url, str), f"Source URL should be string: {url}"
        assert url.startswith("http"), f"Invalid URL format: {url}"
    
    for name, url in FALLBACK_NEWS_SOURCES.items():
        assert isinstance(name, str), f"Fallback source name should be string: {name}"
        assert isinstance(url, str), f"Fallback source URL should be string: {url}"
        assert url.startswith("http"), f"Invalid URL format: {url}"


@pytest.mark.asyncio
async def test_analyze_news_sentiment():
    """Test sentiment analysis on news articles."""
    test_articles = [
        {
            "headline": "Stock market surges to record highs amid strong economic growth",
            "summary": "Markets rally on positive economic indicators",
            "source": "Test",
            "url": "test.com",
        },
        {
            "headline": "Economic downturn expected as inflation rises",
            "summary": "Central banks warn of stagflation risks",
            "source": "Test",
            "url": "test.com",
        },
        {
            "headline": "Tech earnings meet expectations",
            "summary": "Major tech companies report quarterly results",
            "source": "Test",
            "url": "test.com",
        },
    ]
    
    analyzed = analyze_news_sentiment(test_articles)
    
    assert len(analyzed) == 3
    
    # Check sentiment classifications
    assert analyzed[0]["sentiment_classification"] in ["bullish", "neutral", "bearish"]
    assert analyzed[1]["sentiment_classification"] in ["bullish", "neutral", "bearish"]
    assert analyzed[2]["sentiment_classification"] in ["bullish", "neutral", "bearish"]
    
    # Check sentiment scores
    assert -1 <= analyzed[0]["sentiment_score"] <= 1
    assert "affected_sectors" in analyzed[0]


@pytest.mark.asyncio
async def test_sentiment_classification():
    """Test that sentiment classification is correct."""
    bullish_article = {
        "headline": "Markets soar to record heights on positive outlook",
        "summary": "Strong growth expected",
        "source": "Test",
        "url": "test.com",
    }
    
    bearish_article = {
        "headline": "Market crash feared as recession looms",
        "summary": "Economic collapse predicted",
        "source": "Test",
        "url": "test.com",
    }
    
    analyzed_bullish = analyze_news_sentiment([bullish_article])
    analyzed_bearish = analyze_news_sentiment([bearish_article])
    
    # Bullish sentiment should be positive
    assert analyzed_bullish[0]["sentiment_score"] > 0
    
    # Bearish sentiment should be negative
    assert analyzed_bearish[0]["sentiment_score"] < 0


@pytest.mark.asyncio
async def test_sector_identification():
    """Test identification of affected sectors."""
    tech_article = {
        "headline": "Semiconductor shortage impacts chip manufacturers",
        "summary": "AI and chip demand continues to surge",
        "source": "Test",
        "url": "test.com",
    }
    
    energy_article = {
        "headline": "OPEC cuts oil production amid energy transition",
        "summary": "Renewable energy investment increases",
        "source": "Test",
        "url": "test.com",
    }
    
    analyzed_tech = analyze_news_sentiment([tech_article])
    analyzed_energy = analyze_news_sentiment([energy_article])
    
    # Check sector identification
    assert len(analyzed_tech[0]["affected_sectors"]) > 0
    assert "technology" in analyzed_tech[0]["affected_sectors"]
    
    assert len(analyzed_energy[0]["affected_sectors"]) > 0
    assert "energy" in analyzed_energy[0]["affected_sectors"]


def test_portfolio_impact_assessment():
    """Test portfolio impact assessment from analyzed articles."""
    import pandas as pd
    
    test_articles = [
        {
            "headline": "Tech stocks rally on AI optimism",
            "summary": "AI growth accelerates",
            "sentiment_classification": "bullish",
            "sentiment_score": 0.8,
            "affected_sectors": ["technology"],
            "affected_regions": ["US"],
        },
        {
            "headline": "Oil prices surge on geopolitical tensions",
            "summary": "Energy prices increase",
            "sentiment_classification": "bearish",
            "sentiment_score": -0.6,
            "affected_sectors": ["energy"],
            "affected_regions": ["Middle East"],
        },
    ]
    
    test_holdings = pd.DataFrame({
        "sym": ["MSFT", "AAPL", "XOM", "CVX"],
        "asset": ["eq", "eq", "eq", "eq"],
        "ccy": ["USD", "USD", "USD", "USD"],
    })
    
    impact = assess_portfolio_impact(test_articles, test_holdings)
    
    assert "by_timeframe" in impact
    assert "by_sector" in impact
    assert "key_risks" in impact
    assert "key_opportunities" in impact
    assert impact["articles_analyzed"] == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
