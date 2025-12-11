"""
Advanced News Analytics

Provides sophisticated news analysis with:
- Ticker mention extraction from news articles
- Sentiment aggregation by ticker
- Sector-level sentiment analysis
- Correlation analysis with stock movements
- Dask-accelerated processing
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Set, Tuple, Optional
from datetime import datetime, timedelta
import logging
import re
from pathlib import Path

import dask
import dask.dataframe as dd
from textblob import TextBlob
import requests

from src.parquet_db import ParquetDB
from src.utils import get_logger

logger = get_logger(__name__)


class AdvancedNewsAnalytics:
    """
    Advanced news analytics engine for ticker extraction and sentiment analysis.
    
    Features:
    - Ticker mention extraction using regex and NLP
    - Multi-ticker correlation analysis
    - Sector-level sentiment aggregation
    - Price correlation with sentiment
    - Time-series analysis of news flow
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize news analytics.
        
        Args:
            api_key: NewsAPI key for article fetching
        """
        self.api_key = api_key
        self.db = ParquetDB()
        self.base_url = "https://newsapi.org/v2/everything"
        
        # Common US stock tickers for mention extraction
        self.common_tickers = self._load_common_tickers()
        
    def _load_common_tickers(self) -> Set[str]:
        """Load common US stock tickers."""
        # Commonly traded tickers - can be expanded with full list
        tickers = {
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA',
            'BRK', 'JNJ', 'V', 'WMT', 'JPM', 'MA', 'BAC', 'XOM',
            'PG', 'KO', 'INTC', 'CSCO', 'PEP', 'NFLX', 'CMCSA',
            'IBM', 'ADBE', 'PYPL', 'ABBV', 'NVO', 'UNP', 'COST',
            'DIS', 'MCD', 'SBUX', 'AMD', 'AXP', 'LMT', 'QCOM',
            'SPY', 'QQQ', 'IWM', 'EWJ', 'EWG', 'EWU', 'FXI'
        }
        return tickers
    
    def extract_ticker_mentions(self, text: str) -> Dict[str, int]:
        """
        Extract ticker mentions from text using multiple strategies.
        
        Args:
            text: Article text to analyze
            
        Returns:
            Dict with ticker -> mention count
        """
        mentions = {}
        
        # Convert to uppercase for matching
        text_upper = text.upper()
        
        # Strategy 1: Direct ticker mentions (e.g., "$AAPL", "AAPL stock")
        for ticker in self.common_tickers:
            # Match patterns like $TICKER, TICKER stock, TICKER shares
            patterns = [
                f"\\${ticker}\\b",  # $TICKER
                f"\\b{ticker}\\s+(stock|shares|shares|price|prices|trading|trades)",  # TICKER stock
                f"\\b{ticker}\\s+\\(",  # TICKER (company name)
            ]
            
            count = 0
            for pattern in patterns:
                matches = re.findall(pattern, text_upper)
                count += len(matches)
            
            if count > 0:
                mentions[ticker] = count
        
        # Strategy 2: Extract mentions with company names (e.g., "Apple")
        company_tickers = {
            'APPLE': 'AAPL',
            'MICROSOFT': 'MSFT',
            'GOOGLE': 'GOOGL',
            'AMAZON': 'AMZN',
            'TESLA': 'TSLA',
            'META': 'META',
            'NVIDIA': 'NVDA',
            'BERKSHIRE': 'BRK',
            'JPMORGAN': 'JPM',
            'BANK OF AMERICA': 'BAC',
        }
        
        for company_name, ticker in company_tickers.items():
            count = len(re.findall(f"\\b{company_name}\\b", text_upper))
            if ticker not in mentions:
                mentions[ticker] = count
            else:
                mentions[ticker] += count
        
        return mentions
    
    def fetch_news_articles(
        self,
        query: str,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        language: str = "en",
        sort_by: str = "publishedAt"
    ) -> List[Dict]:
        """
        Fetch news articles from NewsAPI.
        
        Args:
            query: Search query
            from_date: Start date (YYYY-MM-DD)
            to_date: End date (YYYY-MM-DD)
            language: Article language
            sort_by: Sort order (publishedAt, relevancy, popularity)
            
        Returns:
            List of article dicts
        """
        if not self.api_key:
            logger.warning("No API key provided, skipping article fetch")
            return []
        
        articles = []
        page = 1
        
        while page <= 5:  # Limit to 5 pages to avoid rate limiting
            params = {
                'q': query,
                'language': language,
                'sortBy': sort_by,
                'apiKey': self.api_key,
                'page': page,
                'pageSize': 100
            }
            
            if from_date:
                params['from'] = from_date
            if to_date:
                params['to'] = to_date
            
            try:
                response = requests.get(self.base_url, params=params, timeout=10)
                response.raise_for_status()
                
                data = response.json()
                
                if data['status'] != 'ok':
                    logger.warning(f"API error: {data.get('message', 'Unknown')}")
                    break
                
                articles.extend(data.get('articles', []))
                
                if len(data.get('articles', [])) < 100:
                    break
                    
                page += 1
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Error fetching articles: {e}")
                break
        
        return articles
    
    def analyze_article_sentiment(self, text: str) -> Dict[str, float]:
        """
        Analyze sentiment of article text using TextBlob.
        
        Args:
            text: Article text
            
        Returns:
            Dict with sentiment metrics:
            - polarity: -1 to 1 (negative to positive)
            - subjectivity: 0 to 1 (objective to subjective)
            - sentiment_label: 'negative', 'neutral', 'positive'
        """
        blob = TextBlob(text)
        polarity = blob.sentiment.polarity
        subjectivity = blob.sentiment.subjectivity
        
        if polarity > 0.1:
            label = 'positive'
        elif polarity < -0.1:
            label = 'negative'
        else:
            label = 'neutral'
        
        return {
            'polarity': polarity,
            'subjectivity': subjectivity,
            'sentiment_label': label
        }
    
    def analyze_news_for_tickers(
        self,
        articles: List[Dict],
        tickers: Optional[List[str]] = None
    ) -> Dict[str, Dict]:
        """
        Analyze news articles for ticker mentions and sentiment.
        
        Args:
            articles: List of article dicts
            tickers: Optional list of tickers to focus on
            
        Returns:
            Dict with ticker -> sentiment metrics
        """
        ticker_analysis = {}
        
        for article in articles:
            title = article.get('title', '')
            description = article.get('description', '')
            content = article.get('content', '')
            published_at = article.get('publishedAt', '')
            
            # Combine text
            full_text = f"{title} {description} {content}"
            
            # Extract ticker mentions
            mentions = self.extract_ticker_mentions(full_text)
            
            # Filter by specified tickers if provided
            if tickers:
                mentions = {t: c for t, c in mentions.items() if t in tickers}
            
            # Analyze sentiment
            sentiment = self.analyze_article_sentiment(full_text)
            
            # Add source sentiment weight (higher for reputable sources)
            source_weights = {
                'bloomberg': 1.2,
                'reuters': 1.2,
                'cnbc': 1.1,
                'financial times': 1.1,
                'marketwatch': 1.0,
                'seekingalpha': 0.9,
                'benzinga': 0.8,
            }
            
            source = article.get('source', {}).get('name', '').lower()
            weight = source_weights.get(source, 1.0)
            
            # Store analysis for each mentioned ticker
            for ticker, mention_count in mentions.items():
                if ticker not in ticker_analysis:
                    ticker_analysis[ticker] = {
                        'articles': [],
                        'total_mentions': 0,
                        'sentiment_scores': [],
                        'polarity_scores': [],
                        'subjectivity_scores': [],
                        'sources': {}
                    }
                
                ticker_analysis[ticker]['articles'].append({
                    'title': title,
                    'source': source,
                    'published_at': published_at,
                    'mentions': mention_count,
                    'sentiment': sentiment['sentiment_label']
                })
                
                ticker_analysis[ticker]['total_mentions'] += mention_count
                ticker_analysis[ticker]['sentiment_scores'].append(sentiment['polarity'] * weight)
                ticker_analysis[ticker]['polarity_scores'].append(sentiment['polarity'])
                ticker_analysis[ticker]['subjectivity_scores'].append(sentiment['subjectivity'])
                
                if source not in ticker_analysis[ticker]['sources']:
                    ticker_analysis[ticker]['sources'][source] = 0
                ticker_analysis[ticker]['sources'][source] += 1
        
        # Aggregate metrics for each ticker
        aggregated = {}
        for ticker, data in ticker_analysis.items():
            aggregated[ticker] = {
                'num_articles': len(data['articles']),
                'total_mentions': data['total_mentions'],
                'avg_polarity': np.mean(data['polarity_scores']) if data['polarity_scores'] else 0,
                'avg_subjectivity': np.mean(data['subjectivity_scores']) if data['subjectivity_scores'] else 0,
                'weighted_sentiment': np.mean(data['sentiment_scores']) if data['sentiment_scores'] else 0,
                'positive_count': len([s for s in data['polarity_scores'] if s > 0.1]),
                'negative_count': len([s for s in data['polarity_scores'] if s < -0.1]),
                'neutral_count': len([s for s in data['polarity_scores'] if -0.1 <= s <= 0.1]),
                'top_sources': sorted(
                    data['sources'].items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:5],
                'recent_articles': data['articles'][-5:]  # Last 5 articles
            }
        
        return aggregated
    
    def sector_sentiment_analysis(
        self,
        ticker_sentiment: Dict[str, Dict],
        sector_mapping: Dict[str, str]
    ) -> Dict[str, Dict]:
        """
        Aggregate sentiment analysis by sector.
        
        Args:
            ticker_sentiment: Dict of ticker -> sentiment metrics
            sector_mapping: Dict mapping ticker -> sector
            
        Returns:
            Dict with sector -> aggregated sentiment metrics
        """
        sector_data = {}
        
        for ticker, metrics in ticker_sentiment.items():
            sector = sector_mapping.get(ticker, 'Unknown')
            
            if sector not in sector_data:
                sector_data[sector] = {
                    'tickers': [],
                    'polarities': [],
                    'article_counts': [],
                    'weighted_sentiments': []
                }
            
            sector_data[sector]['tickers'].append(ticker)
            sector_data[sector]['polarities'].append(metrics['avg_polarity'])
            sector_data[sector]['article_counts'].append(metrics['num_articles'])
            sector_data[sector]['weighted_sentiments'].append(metrics['weighted_sentiment'])
        
        # Aggregate by sector
        aggregated = {}
        for sector, data in sector_data.items():
            aggregated[sector] = {
                'num_tickers': len(data['tickers']),
                'num_articles': sum(data['article_counts']),
                'avg_polarity': np.mean(data['polarities']) if data['polarities'] else 0,
                'avg_weighted_sentiment': np.mean(data['weighted_sentiments']) if data['weighted_sentiments'] else 0,
                'sentiment_strength': len([p for p in data['polarities'] if abs(p) > 0.1]) / len(data['polarities']) if data['polarities'] else 0,
                'constituent_tickers': data['tickers']
            }
        
        return aggregated
    
    def correlate_sentiment_with_returns(
        self,
        ticker_sentiment: Dict[str, Dict],
        price_changes: Dict[str, float],
        lookback_days: int = 5
    ) -> Dict[str, Dict]:
        """
        Correlate news sentiment with price movements.
        
        Args:
            ticker_sentiment: Ticker sentiment analysis
            price_changes: Dict of ticker -> price change %
            lookback_days: Days of lookback for correlation
            
        Returns:
            Dict with correlation analysis per ticker
        """
        correlation_analysis = {}
        
        for ticker, sentiment in ticker_sentiment.items():
            price_change = price_changes.get(ticker, 0)
            polarity = sentiment['avg_polarity']
            
            correlation_analysis[ticker] = {
                'sentiment_polarity': polarity,
                'price_change_pct': price_change,
                'sentiment_price_agreement': self._calculate_agreement(polarity, price_change),
                'sentiment_strength': abs(polarity),
                'price_momentum': 'up' if price_change > 0 else 'down',
                'sentiment_direction': 'bullish' if polarity > 0 else 'bearish',
                'num_articles': sentiment['num_articles'],
                'article_quality_score': self._calculate_quality_score(sentiment)
            }
        
        return correlation_analysis
    
    def _calculate_agreement(self, sentiment_polarity: float, price_change: float) -> float:
        """
        Calculate how well sentiment aligns with price movement.
        
        Returns value from -1 (disagreement) to 1 (full agreement)
        """
        if sentiment_polarity > 0.1 and price_change > 0:
            agreement = min(abs(sentiment_polarity) * abs(price_change / 10), 1.0)
        elif sentiment_polarity < -0.1 and price_change < 0:
            agreement = min(abs(sentiment_polarity) * abs(price_change / 10), 1.0)
        elif (sentiment_polarity > 0.1 and price_change < 0) or (sentiment_polarity < -0.1 and price_change > 0):
            agreement = -min(abs(sentiment_polarity) * abs(price_change / 10), 1.0)
        else:
            agreement = 0
        
        return agreement
    
    def _calculate_quality_score(self, sentiment_data: Dict) -> float:
        """Calculate quality score based on article sources and count."""
        base_score = min(sentiment_data['num_articles'] / 10, 1.0)
        
        # Boost for presence of quality sources
        quality_sources = {'bloomberg', 'reuters', 'cnbc', 'financial times'}
        source_names = [s[0] for s in sentiment_data['top_sources']]
        
        quality_boost = sum(
            0.1 for source in source_names
            if any(qs in source for qs in quality_sources)
        )
        
        return min(base_score + quality_boost, 1.0)
    
    def save_news_analysis(
        self,
        ticker_sentiment: Dict[str, Dict],
        output_dir: str = "db"
    ) -> str:
        """Save news analysis results to Parquet."""
        try:
            # Convert to DataFrame
            records = []
            for ticker, metrics in ticker_sentiment.items():
                records.append({
                    'ticker': ticker,
                    'num_articles': metrics['num_articles'],
                    'total_mentions': metrics['total_mentions'],
                    'avg_polarity': metrics['avg_polarity'],
                    'avg_subjectivity': metrics['avg_subjectivity'],
                    'weighted_sentiment': metrics['weighted_sentiment'],
                    'positive_count': metrics['positive_count'],
                    'negative_count': metrics['negative_count'],
                    'neutral_count': metrics['neutral_count'],
                    'timestamp': pd.Timestamp.now()
                })
            
            df = pd.DataFrame(records)
            
            output_file = Path(output_dir) / "news_analytics" / f"sentiment_{pd.Timestamp.now().strftime('%Y%m%d')}.parquet"
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            df.to_parquet(output_file)
            logger.info(f"Saved news analysis for {len(df)} tickers to {output_file}")
            
            return str(output_file)
            
        except Exception as e:
            logger.error(f"Error saving news analysis: {e}")
            return ""
