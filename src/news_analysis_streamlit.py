"""
Streamlit-compatible news analysis with optional Prefect flow integration.

This module provides news scraping and sentiment analysis that works directly
in Streamlit while optionally logging to Prefect for monitoring.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

import feedparser
import numpy as np
import pandas as pd

try:
    from textblob import TextBlob
    HAS_TEXTBLOB = True
except ImportError:
    HAS_TEXTBLOB = False

try:
    from prefect import flow, task, get_run_logger
    HAS_PREFECT = True
except ImportError:
    HAS_PREFECT = False


# Setup logging
logger = logging.getLogger(__name__)

# News sources
NEWS_SOURCES = {
    "Reuters": "https://www.reuters.com/finance",
    "Bloomberg": "https://feeds.bloomberg.com/markets/news.rss",
    "CNBC": "https://feeds.cnbc.com/id/100003114/rss.xml",
    "MarketWatch": "https://feeds.marketwatch.com/marketwatch/topstories/",
    "Financial Times": "https://feeds.ft.com/world",
    "Yahoo Finance": "https://feeds.finance.yahoo.com/rss/2.0/headline",
}


def scrape_news_articles(max_articles: int = 100, hours_back: int = 24) -> List[Dict]:
    """
    Scrape news articles from RSS feeds.
    
    Args:
        max_articles: Maximum number of articles to retrieve
        hours_back: Only get articles from last N hours
    
    Returns:
        List of article dictionaries
    """
    articles = []
    cutoff_time = datetime.now() - timedelta(hours=hours_back)
    
    successful_sources = 0
    failed_sources = []
    
    for source_name, feed_url in NEWS_SOURCES.items():
        try:
            # Parse RSS feed
            feed = feedparser.parse(feed_url)
            
            if not feed.entries:
                failed_sources.append(source_name)
                continue
            
            source_articles = 0
            for entry in feed.entries[:15]:  # Limit per source
                try:
                    # Extract published time
                    pub_time = datetime.now()
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        try:
                            pub_time = datetime(*entry.published_parsed[:6])
                        except (TypeError, ValueError):
                            pass
                    
                    # Skip old articles
                    if pub_time < cutoff_time:
                        continue
                    
                    headline = entry.get("title", "").strip()
                    summary = entry.get("summary", "").strip()[:300]
                    url = entry.get("link", "").strip()
                    
                    if not headline:
                        continue
                    
                    articles.append({
                        "source": source_name,
                        "title": headline,
                        "summary": summary,
                        "link": url,
                        "published": pub_time.strftime("%Y-%m-%d %H:%M"),
                    })
                    source_articles += 1
                    
                except Exception as e:
                    logger.debug(f"Error parsing entry from {source_name}: {e}")
                    continue
            
            if source_articles > 0:
                successful_sources += 1
        
        except Exception as e:
            logger.debug(f"Error scraping {source_name}: {e}")
            failed_sources.append(source_name)
            continue
    
    logger.info(f"Scraped {len(articles)} articles from {successful_sources}/{len(NEWS_SOURCES)} sources")
    
    return articles[:max_articles]


def analyze_sentiment(articles: List[Dict]) -> List[Dict]:
    """
    Analyze sentiment of article titles.
    
    Args:
        articles: List of article dictionaries
    
    Returns:
        Articles with sentiment scores added
    """
    if HAS_TEXTBLOB:
        # Use TextBlob for sentiment analysis
        for article in articles:
            text_to_analyze = f"{article['title']} {article['summary']}"
            blob = TextBlob(text_to_analyze)
            sentiment = blob.sentiment.polarity  # -1 to 1
            article['sentiment_score'] = sentiment
            article['sentiment_label'] = 'Positive' if sentiment > 0.1 else 'Negative' if sentiment < -0.1 else 'Neutral'
    else:
        # Fallback: basic keyword-based sentiment
        positive_words = {'gain', 'up', 'rise', 'surge', 'bullish', 'profit', 'growth', 'beat', 'rally', 'recovery'}
        negative_words = {'fall', 'down', 'drop', 'crash', 'bearish', 'loss', 'decline', 'miss', 'plunge', 'correction'}
        
        for article in articles:
            title_lower = article['title'].lower()
            pos_count = sum(1 for word in positive_words if word in title_lower)
            neg_count = sum(1 for word in negative_words if word in title_lower)
            
            if pos_count > neg_count:
                article['sentiment_score'] = 0.5
                article['sentiment_label'] = 'Positive'
            elif neg_count > pos_count:
                article['sentiment_score'] = -0.5
                article['sentiment_label'] = 'Negative'
            else:
                article['sentiment_score'] = 0.0
                article['sentiment_label'] = 'Neutral'
    
    return articles


def get_portfolio_mentions(articles: List[Dict], symbols: List[str]) -> Dict[str, int]:
    """
    Find mentions of portfolio symbols in articles.
    
    Args:
        articles: List of article dictionaries
        symbols: List of portfolio symbols
    
    Returns:
        Dictionary of symbol -> mention count
    """
    portfolio_mentions = {}
    
    for symbol in symbols:
        count = sum(1 for a in articles if symbol.lower() in a['title'].lower() or symbol.lower() in a['summary'].lower())
        if count > 0:
            portfolio_mentions[symbol] = count
    
    return portfolio_mentions


def analyze_news_sentiment_streamlit(
    max_articles: int = 100,
    hours_back: int = 24,
    symbols: List[str] = None
) -> Tuple[List[Dict], Dict]:
    """
    Main function for Streamlit-compatible news sentiment analysis.
    
    Args:
        max_articles: Maximum number of articles
        hours_back: Hours to look back
        symbols: Portfolio symbols to track
    
    Returns:
        Tuple of (articles with sentiment, statistics dictionary)
    """
    # Scrape articles
    articles = scrape_news_articles(max_articles=max_articles, hours_back=hours_back)
    
    if not articles:
        return [], {
            'total_articles': 0,
            'avg_sentiment': 0,
            'positive_count': 0,
            'negative_count': 0,
            'neutral_count': 0,
            'portfolio_mentions': {},
        }
    
    # Analyze sentiment
    articles = analyze_sentiment(articles)
    
    # Calculate statistics
    sentiments = [a.get('sentiment_score', 0) for a in articles]
    avg_sentiment = float(np.mean(sentiments)) if sentiments else 0
    positive_count = sum(1 for a in articles if a['sentiment_label'] == 'Positive')
    negative_count = sum(1 for a in articles if a['sentiment_label'] == 'Negative')
    neutral_count = len(articles) - positive_count - negative_count
    
    # Get portfolio mentions
    portfolio_mentions = {}
    if symbols:
        portfolio_mentions = get_portfolio_mentions(articles, symbols)
    
    stats = {
        'total_articles': len(articles),
        'avg_sentiment': avg_sentiment,
        'positive_count': positive_count,
        'negative_count': negative_count,
        'neutral_count': neutral_count,
        'portfolio_mentions': portfolio_mentions,
        'sources_count': len(set(a['source'] for a in articles)),
    }
    
    return articles, stats


# Prefect flow wrapper (optional, for when running with Prefect)
if HAS_PREFECT:
    @task(name="scrape_news_task")
    def scrape_news_task(max_articles: int = 100, hours_back: int = 24) -> List[Dict]:
        """Prefect task for scraping news."""
        return scrape_news_articles(max_articles=max_articles, hours_back=hours_back)
    
    @task(name="analyze_sentiment_task")
    def analyze_sentiment_task(articles: List[Dict]) -> List[Dict]:
        """Prefect task for sentiment analysis."""
        return analyze_sentiment(articles)
    
    @flow(name="news_sentiment_analysis_flow")
    def news_sentiment_analysis_flow(
        max_articles: int = 100,
        hours_back: int = 24,
        symbols: List[str] = None
    ) -> Tuple[List[Dict], Dict]:
        """
        Prefect flow for news sentiment analysis with logging.
        
        Args:
            max_articles: Maximum number of articles
            hours_back: Hours to look back
            symbols: Portfolio symbols to track
        
        Returns:
            Tuple of (articles with sentiment, statistics dictionary)
        """
        flow_logger = get_run_logger()
        
        flow_logger.info(f"Starting news sentiment analysis (max_articles={max_articles}, hours_back={hours_back})")
        
        # Scrape articles
        articles = scrape_news_task(max_articles=max_articles, hours_back=hours_back)
        flow_logger.info(f"Scraped {len(articles)} articles")
        
        if not articles:
            flow_logger.warning("No articles found")
            return [], {
                'total_articles': 0,
                'avg_sentiment': 0,
                'positive_count': 0,
                'negative_count': 0,
                'neutral_count': 0,
                'portfolio_mentions': {},
            }
        
        # Analyze sentiment
        articles = analyze_sentiment_task(articles)
        flow_logger.info("Sentiment analysis complete")
        
        # Calculate statistics
        sentiments = [a.get('sentiment_score', 0) for a in articles]
        avg_sentiment = float(np.mean(sentiments)) if sentiments else 0
        positive_count = sum(1 for a in articles if a['sentiment_label'] == 'Positive')
        negative_count = sum(1 for a in articles if a['sentiment_label'] == 'Negative')
        neutral_count = len(articles) - positive_count - negative_count
        
        flow_logger.info(f"Sentiment distribution: {positive_count} positive, {neutral_count} neutral, {negative_count} negative")
        
        # Get portfolio mentions
        portfolio_mentions = {}
        if symbols:
            portfolio_mentions = get_portfolio_mentions(articles, symbols)
            if portfolio_mentions:
                flow_logger.info(f"Portfolio mentions found: {portfolio_mentions}")
        
        stats = {
            'total_articles': len(articles),
            'avg_sentiment': avg_sentiment,
            'positive_count': positive_count,
            'negative_count': negative_count,
            'neutral_count': neutral_count,
            'portfolio_mentions': portfolio_mentions,
            'sources_count': len(set(a['source'] for a in articles)),
        }
        
        flow_logger.info(f"News sentiment analysis complete - {len(articles)} articles analyzed")
        
        return articles, stats
else:
    # Fallback if Prefect is not available
    def news_sentiment_analysis_flow(
        max_articles: int = 100,
        hours_back: int = 24,
        symbols: List[str] = None
    ) -> Tuple[List[Dict], Dict]:
        """Fallback function when Prefect is not available."""
        return analyze_news_sentiment_streamlit(
            max_articles=max_articles,
            hours_back=hours_back,
            symbols=symbols
        )
