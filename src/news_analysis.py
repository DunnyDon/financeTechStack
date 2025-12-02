"""
News scraping and NLP analysis for portfolio impact assessment.

Analyzes major world headlines from diverse news outlets and performs
sentiment analysis to assess potential impacts on portfolio holdings
across short-term, medium-term, and long-term horizons.
"""

import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import feedparser
import pandas as pd
import requests
from prefect import get_run_logger, task

try:
    from textblob import TextBlob
except ImportError:
    TextBlob = None

try:
    import nltk
    from nltk.sentiment import SentimentIntensityAnalyzer
    nltk.download('vader_lexicon', quiet=True)
    SIA = SentimentIntensityAnalyzer()
except (ImportError, LookupError):
    SIA = None

__all__ = [
    "scrape_news_headlines",
    "analyze_news_sentiment",
    "assess_portfolio_impact",
    "get_news_analysis_report",
]


# Major news outlets RSS feeds across the spectrum
# Only includes sources that have been verified to work
NEWS_SOURCES = {
    # Reliable general news sources
    "NPR": "https://feeds.npr.org/1001/rss.xml",
    "The Guardian World": "https://www.theguardian.com/world/rss",
    "HackerNews": "https://news.ycombinator.com/rss",
    "NPR Business": "https://feeds.npr.org/1004/rss.xml",
    "NPR Technology": "https://feeds.npr.org/1019/rss.xml",
    "The Guardian Business": "https://www.theguardian.com/business/rss",
    "The Guardian Tech": "https://www.theguardian.com/technology/rss",
    
    # International broadcasters
    "RTE News": "https://www.rte.ie/news/rss/news-headlines.xml",
    "CNN Top Stories": "http://rss.cnn.com/rss/cnn_topstories.rss",
    "CNN Business": "http://rss.cnn.com/rss/cnn_business.rss",
    "Fox News Top": "http://feeds.foxnews.com/foxnews/latest",
    "Fox Business": "http://feeds.foxnews.com/foxnews/business",
    "BBC News": "http://feeds.bbc.co.uk/news/rss.xml",
    "Al Jazeera English": "https://www.aljazeera.com/xml/rss/all.xml",
}

# Alternative/fallback sources to try if primary ones fail
FALLBACK_NEWS_SOURCES = {
    "Reddit r/stocks": "https://www.reddit.com/r/stocks/top.rss?t=day",
    "Reddit r/investing": "https://www.reddit.com/r/investing/top.rss?t=day",
    "Reddit r/news": "https://www.reddit.com/r/news/top.rss?t=day",
    "Reuters World": "https://www.reutersagency.com/feed/?taxonomy=best-topics&output=rss",
}

# Sector keywords for impact assessment
SECTOR_KEYWORDS = {
    "technology": ["AI", "chip", "semiconductor", "software", "cybersecurity", "cloud", "data", "tech"],
    "energy": ["oil", "gas", "renewable", "solar", "wind", "coal", "OPEC", "crude", "energy"],
    "finance": ["bank", "financial", "credit", "interest rate", "fed", "central bank", "monetary"],
    "healthcare": ["pharma", "healthcare", "hospital", "drug", "vaccine", "medical", "health"],
    "consumer": ["retail", "consumer", "shopping", "inflation", "prices", "e-commerce"],
    "transportation": ["airline", "automotive", "trucking", "shipping", "logistics", "cargo"],
    "real estate": ["housing", "property", "real estate", "construction", "mortgage", "rent"],
    "utilities": ["electricity", "water", "utility", "power grid", "infrastructure"],
}

# Geographic impact keywords
GEOGRAPHIC_KEYWORDS = {
    "US": ["United States", "America", "US", "USA", "Washington", "Wall Street"],
    "Europe": ["Europe", "EU", "eurozone", "UK", "Britain", "France", "Germany"],
    "Asia": ["Asia", "China", "India", "Japan", "Korea", "Southeast Asia"],
    "Emerging Markets": ["emerging", "developing", "Brazil", "Russia", "Mexico"],
}


@task(name="scrape_news_headlines")
def scrape_news_headlines(max_articles: int = 100, hours_back: int = 24) -> List[Dict]:
    """
    Scrape recent news headlines from multiple outlets with resilience.

    Args:
        max_articles: Maximum number of articles to retrieve
        hours_back: Only get articles from last N hours

    Returns:
        List of dictionaries with headline, source, URL, and timestamp
    """
    task_logger = get_run_logger()
    task_logger.info(f"Scraping news headlines from multiple sources...")

    articles = []
    cutoff_time = datetime.now() - timedelta(hours=hours_back)
    
    # Try primary sources first
    all_sources = {**NEWS_SOURCES, **FALLBACK_NEWS_SOURCES}
    successful_sources = 0
    failed_sources = []

    for source_name, feed_url in all_sources.items():
        try:
            task_logger.debug(f"Fetching from {source_name}...")
            
            # Parse feed (feedparser handles most timeouts internally)
            feed = feedparser.parse(feed_url)
            
            # Check for parse errors but continue anyway
            if feed.bozo and isinstance(feed.bozo_exception, feedparser.FeedParserDict):
                task_logger.debug(f"Feed parse issue for {source_name}")
                # Continue processing even with parse errors
            
            # Check if we got any entries
            if not feed.entries:
                task_logger.debug(f"No entries found for {source_name}")
                failed_sources.append(f"{source_name} (no entries)")
                continue
            
            source_articles = 0
            for entry in feed.entries[:25]:  # Limit per source
                try:
                    # Extract published time with fallback
                    pub_time = None
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        try:
                            pub_time = datetime(*entry.published_parsed[:6])
                        except (TypeError, ValueError):
                            pub_time = datetime.now()
                    else:
                        pub_time = datetime.now()
                    
                    # Skip old articles (more than hours_back old)
                    if pub_time < cutoff_time:
                        continue
                    
                    # Extract headline and summary with fallbacks
                    headline = entry.get("title", "").strip()
                    summary = entry.get("summary", "").strip()[:500]
                    url = entry.get("link", "").strip()
                    
                    # Skip empty headlines
                    if not headline:
                        continue
                    
                    article = {
                        "source": source_name,
                        "headline": headline,
                        "summary": summary,
                        "url": url,
                        "published_at": pub_time.isoformat(),
                        "scraped_at": datetime.now().isoformat(),
                    }
                    
                    articles.append(article)
                    source_articles += 1
                        
                except Exception as e:
                    task_logger.debug(f"Error parsing entry from {source_name}: {e}")
                    continue
            
            if source_articles > 0:
                task_logger.debug(f"Scraped {source_articles} articles from {source_name}")
                successful_sources += 1
        
        except requests.exceptions.Timeout:
            task_logger.debug(f"Timeout fetching from {source_name}")
            failed_sources.append(f"{source_name} (timeout)")
        except requests.exceptions.ConnectionError:
            task_logger.debug(f"Connection error fetching from {source_name}")
            failed_sources.append(f"{source_name} (connection error)")
        except Exception as e:
            task_logger.debug(f"Error scraping {source_name}: {type(e).__name__}: {e}")
            failed_sources.append(f"{source_name} ({type(e).__name__})")
    
    task_logger.info(
        f"Scraped {len(articles)} articles from {successful_sources}/{len(all_sources)} sources. "
        f"Failed: {len(failed_sources)}"
    )
    
    if failed_sources and successful_sources == 0:
        task_logger.warning(f"All sources failed to scrape")
    elif failed_sources and len(failed_sources) > 3:
        task_logger.debug(f"Some sources failed: {len(failed_sources)} sources")
    
    return articles[:max_articles]


@task(name="analyze_news_sentiment")
def analyze_news_sentiment(articles: List[Dict]) -> List[Dict]:
    """
    Perform sentiment analysis on news headlines and summaries.

    Args:
        articles: List of article dictionaries

    Returns:
        List of articles with added sentiment scores and classifications
    """
    task_logger = get_run_logger()
    task_logger.info(f"Analyzing sentiment for {len(articles)} articles...")

    analyzed = []
    
    for article in articles:
        try:
            text = f"{article['headline']} {article['summary']}"
            
            # Calculate sentiment scores
            scores = {"compound": 0, "positive": 0, "negative": 0, "neutral": 0}
            
            if SIA:
                scores = SIA.polarity_scores(text)
            elif TextBlob:
                polarity = TextBlob(text).sentiment.polarity
                scores["compound"] = polarity
                scores["positive"] = max(0, polarity)
                scores["negative"] = max(0, -polarity)
                scores["neutral"] = 1 - abs(polarity)
            
            # Classify sentiment
            compound = scores.get("compound", 0)
            if compound >= 0.05:
                sentiment = "bullish"
            elif compound <= -0.05:
                sentiment = "bearish"
            else:
                sentiment = "neutral"
            
            article["sentiment_score"] = compound
            article["sentiment_classification"] = sentiment
            article["sentiment_details"] = scores
            
            # Identify affected sectors
            text_lower = text.lower()
            affected_sectors = []
            for sector, keywords in SECTOR_KEYWORDS.items():
                if any(kw.lower() in text_lower for kw in keywords):
                    affected_sectors.append(sector)
            article["affected_sectors"] = affected_sectors
            
            # Identify geographic regions
            affected_regions = []
            for region, keywords in GEOGRAPHIC_KEYWORDS.items():
                if any(kw.lower() in text_lower for kw in keywords):
                    affected_regions.append(region)
            article["affected_regions"] = affected_regions
            
            analyzed.append(article)
        
        except Exception as e:
            task_logger.warning(f"Error analyzing sentiment for article: {e}")
            article["sentiment_score"] = 0
            article["sentiment_classification"] = "unknown"
            article["affected_sectors"] = []
            article["affected_regions"] = []
            analyzed.append(article)
    
    task_logger.info(f"Sentiment analysis completed for {len(analyzed)} articles")
    return analyzed


@task(name="assess_portfolio_impact")
def assess_portfolio_impact(
    analyzed_articles: List[Dict],
    holdings_df: pd.DataFrame
) -> Dict:
    """
    Assess potential impact of news on portfolio holdings.

    Args:
        analyzed_articles: Articles with sentiment analysis
        holdings_df: Portfolio holdings with asset class and sector info

    Returns:
        Dictionary with impact assessments
    """
    task_logger = get_run_logger()
    task_logger.info("Assessing portfolio impact from news...")

    try:
        # Build holdings mapping by sector and asset class
        holdings_by_sector = {}
        holdings_by_asset = {}
        
        for _, holding in holdings_df.iterrows():
            asset = holding.get("asset", "unknown")
            # sector = holding.get("sector", holding.get("exchange", "unknown"))
            
            if asset not in holdings_by_asset:
                holdings_by_asset[asset] = []
            holdings_by_asset[asset].append(holding)
        
        # Analyze impact by sector
        impact_by_sector = {}
        impact_by_timeframe = {
            "short_term": {"bullish": 0, "bearish": 0, "neutral": 0},
            "medium_term": {"bullish": 0, "bearish": 0, "neutral": 0},
            "long_term": {"bullish": 0, "bearish": 0, "neutral": 0},
        }
        
        # Keywords for timeframe classification
        short_term_keywords = ["crash", "plunge", "surge", "spike", "today", "urgent", "emergency"]
        medium_term_keywords = ["week", "month", "quarter", "outlook", "guidance", "forecast"]
        long_term_keywords = ["trend", "structural", "decade", "strategic", "transformation"]
        
        for article in analyzed_articles:
            sentiment = article.get("sentiment_classification", "neutral")
            text_lower = article["headline"].lower()
            
            # Classify timeframe impact
            timeframes = ["long_term"]  # Default to long-term
            if any(kw in text_lower for kw in short_term_keywords):
                timeframes = ["short_term"]
            elif any(kw in text_lower for kw in medium_term_keywords):
                timeframes = ["medium_term"]
            
            # Count sentiment by timeframe
            for timeframe in timeframes:
                impact_by_timeframe[timeframe][sentiment] += 1
            
            # Assess sector impact
            for sector in article.get("affected_sectors", []):
                if sector not in impact_by_sector:
                    impact_by_sector[sector] = {
                        "articles": [],
                        "avg_sentiment": 0,
                        "bullish_count": 0,
                        "bearish_count": 0,
                    }
                
                impact_by_sector[sector]["articles"].append(article["headline"])
                impact_by_sector[sector]["bullish_count"] += (1 if sentiment == "bullish" else 0)
                impact_by_sector[sector]["bearish_count"] += (1 if sentiment == "bearish" else 0)
                impact_by_sector[sector]["avg_sentiment"] = article.get("sentiment_score", 0)
        
        # Calculate portfolio exposure to affected sectors
        portfolio_exposure = {}
        for asset_type in holdings_by_asset.keys():
            portfolio_exposure[asset_type] = len(holdings_by_asset[asset_type])
        
        impact_summary = {
            "timestamp": datetime.now().isoformat(),
            "articles_analyzed": len(analyzed_articles),
            "by_sector": impact_by_sector,
            "by_timeframe": impact_by_timeframe,
            "portfolio_exposure": portfolio_exposure,
            "key_risks": [],
            "key_opportunities": [],
        }
        
        # Identify key risks and opportunities
        for sector, impact in impact_by_sector.items():
            if impact["bearish_count"] > impact["bullish_count"]:
                impact_summary["key_risks"].append({
                    "sector": sector,
                    "bearish_articles": impact["bearish_count"],
                    "headline": impact["articles"][-1] if impact["articles"] else "N/A"
                })
            elif impact["bullish_count"] > impact["bearish_count"]:
                impact_summary["key_opportunities"].append({
                    "sector": sector,
                    "bullish_articles": impact["bullish_count"],
                    "headline": impact["articles"][-1] if impact["articles"] else "N/A"
                })
        
        task_logger.info(f"Portfolio impact assessment completed")
        return impact_summary
    
    except Exception as e:
        task_logger.error(f"Error assessing portfolio impact: {e}")
        return {"error": str(e)}


def get_news_analysis_report(impact_summary: Dict) -> str:
    """
    Generate a human-readable news analysis report.

    Args:
        impact_summary: Dictionary from assess_portfolio_impact

    Returns:
        Formatted text report
    """
    report = f"""
=== NEWS IMPACT ANALYSIS REPORT ===
Generated: {impact_summary.get('timestamp', 'N/A')}
Articles Analyzed: {impact_summary.get('articles_analyzed', 0)}

SENTIMENT BREAKDOWN BY TIMEFRAME:
"""
    
    for timeframe, counts in impact_summary.get("by_timeframe", {}).items():
        report += f"\n{timeframe.replace('_', ' ').title()}:"
        report += f"\n  Bullish: {counts.get('bullish', 0)}"
        report += f"\n  Bearish: {counts.get('bearish', 0)}"
        report += f"\n  Neutral: {counts.get('neutral', 0)}"
    
    report += "\n\nSECTOR IMPACT:"
    for sector, impact in impact_summary.get("by_sector", {}).items():
        report += f"\n\n{sector.title()}:"
        report += f"\n  Bullish: {impact.get('bullish_count', 0)}"
        report += f"\n  Bearish: {impact.get('bearish_count', 0)}"
        if impact.get("articles"):
            report += f"\n  Latest: {impact['articles'][-1][:80]}..."
    
    report += "\n\nKEY RISKS:"
    for risk in impact_summary.get("key_risks", [])[:5]:
        report += f"\n  • {risk['sector'].title()}: {risk['bearish_articles']} bearish articles"
        report += f"\n    → {risk['headline'][:70]}..."
    
    report += "\n\nKEY OPPORTUNITIES:"
    for opp in impact_summary.get("key_opportunities", [])[:5]:
        report += f"\n  • {opp['sector'].title()}: {opp['bullish_articles']} bullish articles"
        report += f"\n    → {opp['headline'][:70]}..."
    
    return report
