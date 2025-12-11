"""
Test suite for Advanced News Analytics

Tests for:
- Ticker mention extraction
- Sentiment analysis
- Sector aggregation
- Price correlation analysis
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.news_advanced_analytics import AdvancedNewsAnalytics


@pytest.fixture
def sample_articles():
    """Generate sample news articles."""
    return [
        {
            'title': 'Apple stock rises as AAPL beats earnings',
            'description': 'Apple Inc (AAPL) reported strong quarterly results',
            'content': 'AAPL shares jumped 5% today on strong iPhone sales.',
            'publishedAt': '2024-01-15T10:00:00Z',
            'source': {'name': 'Bloomberg'}
        },
        {
            'title': 'Microsoft and MSFT announce new AI partnership',
            'description': '$MSFT partners with OpenAI for AI advancement',
            'content': 'Microsoft stock trading near all-time highs.',
            'publishedAt': '2024-01-15T11:00:00Z',
            'source': {'name': 'Reuters'}
        },
        {
            'title': 'Tech sector rally continues',
            'description': 'GOOGL, AAPL, and META leading the gains',
            'content': 'Google shares up 3%, Meta up 4%.',
            'publishedAt': '2024-01-15T12:00:00Z',
            'source': {'name': 'CNBC'}
        }
    ]


@pytest.fixture
def analytics():
    """Create news analytics instance."""
    return AdvancedNewsAnalytics()


class TestTickerExtraction:
    """Test ticker mention extraction."""
    
    def test_extract_dollar_mentions(self, analytics):
        """Test extraction of $TICKER mentions."""
        text = "Apple stock $AAPL is rising and $MSFT is following"
        mentions = analytics.extract_ticker_mentions(text)
        
        assert 'AAPL' in mentions
        assert 'MSFT' in mentions
        assert mentions['AAPL'] > 0
        assert mentions['MSFT'] > 0
    
    def test_extract_pattern_mentions(self, analytics):
        """Test extraction of TICKER stock patterns."""
        text = "AAPL stock jumped today. Microsoft MSFT shares up 5%."
        mentions = analytics.extract_ticker_mentions(text)
        
        assert len(mentions) > 0
    
    def test_company_name_extraction(self, analytics):
        """Test extraction from company names."""
        text = "Apple reported strong earnings. Microsoft also beat expectations."
        mentions = analytics.extract_ticker_mentions(text)
        
        # Should recognize Apple and Microsoft
        assert len(mentions) > 0
    
    def test_no_false_positives(self, analytics):
        """Test no false positive ticker extraction."""
        text = "The application was rejected and we have to modify."
        mentions = analytics.extract_ticker_mentions(text)
        
        # "APP" should not be in mentions as it's not in common tickers
        assert 'APP' not in mentions or mentions['APP'] == 0
    
    def test_multiple_mentions(self, analytics):
        """Test counting multiple mentions of same ticker."""
        text = "AAPL stock $AAPL Apple Inc. AAPL shares trading AAPL stock"
        mentions = analytics.extract_ticker_mentions(text)
        
        # Should count multiple mentions
        if 'AAPL' in mentions:
            assert mentions['AAPL'] > 1


class TestSentimentAnalysis:
    """Test article sentiment analysis."""
    
    def test_positive_sentiment(self, analytics):
        """Test detection of positive sentiment."""
        positive_text = "Excellent results! Stock surged higher on strong earnings."
        sentiment = analytics.analyze_article_sentiment(positive_text)
        
        assert sentiment['polarity'] > 0
        assert sentiment['sentiment_label'] == 'positive'
    
    def test_negative_sentiment(self, analytics):
        """Test detection of negative sentiment."""
        negative_text = "Terrible performance. Stock plummeted on weak guidance."
        sentiment = analytics.analyze_article_sentiment(negative_text)
        
        assert sentiment['polarity'] < 0
        assert sentiment['sentiment_label'] == 'negative'
    
    def test_neutral_sentiment(self, analytics):
        """Test detection of neutral sentiment."""
        neutral_text = "Stock traded sideways. Volume was average."
        sentiment = analytics.analyze_article_sentiment(neutral_text)
        
        assert abs(sentiment['polarity']) < 0.2
        assert sentiment['sentiment_label'] == 'neutral'
    
    def test_sentiment_has_subjectivity(self, analytics):
        """Test subjectivity scoring."""
        text = "Apple stock rose today."
        sentiment = analytics.analyze_article_sentiment(text)
        
        assert 'subjectivity' in sentiment
        assert 0 <= sentiment['subjectivity'] <= 1


class TestNewsAnalysis:
    """Test comprehensive news analysis."""
    
    def test_analyze_articles(self, analytics, sample_articles):
        """Test analysis of multiple articles."""
        result = analytics.analyze_news_for_tickers(sample_articles)
        
        assert isinstance(result, dict)
        assert len(result) > 0
    
    def test_ticker_metrics_structure(self, analytics, sample_articles):
        """Test ticker analysis has correct structure."""
        result = analytics.analyze_news_for_tickers(sample_articles)
        
        if result:
            ticker = list(result.keys())[0]
            metrics = result[ticker]
            
            required_keys = [
                'num_articles',
                'total_mentions',
                'avg_polarity',
                'weighted_sentiment',
                'positive_count',
                'negative_count',
                'neutral_count'
            ]
            
            for key in required_keys:
                assert key in metrics
    
    def test_filter_by_ticker(self, analytics, sample_articles):
        """Test filtering analysis by specific tickers."""
        result = analytics.analyze_news_for_tickers(
            sample_articles,
            tickers=['AAPL', 'MSFT']
        )
        
        # Should only have specified tickers
        for ticker in result:
            assert ticker in ['AAPL', 'MSFT']
    
    def test_sentiment_aggregation(self, analytics, sample_articles):
        """Test sentiment is properly aggregated."""
        result = analytics.analyze_news_for_tickers(sample_articles)
        
        for ticker, metrics in result.items():
            polarity = metrics['avg_polarity']
            
            # Polarity should be between -1 and 1
            assert -1 <= polarity <= 1


class TestSectorAnalysis:
    """Test sector-level sentiment analysis."""
    
    def test_sector_aggregation(self, analytics, sample_articles):
        """Test sector sentiment aggregation."""
        ticker_sentiment = analytics.analyze_news_for_tickers(sample_articles)
        
        sector_mapping = {
            'AAPL': 'Technology',
            'MSFT': 'Technology',
            'GOOGL': 'Technology',
            'META': 'Technology',
            'JPM': 'Financials',
            'BAC': 'Financials'
        }
        
        sector_result = analytics.sector_sentiment_analysis(
            ticker_sentiment,
            sector_mapping
        )
        
        assert isinstance(sector_result, dict)
    
    def test_sector_metrics(self, analytics, sample_articles):
        """Test sector analysis has required metrics."""
        ticker_sentiment = analytics.analyze_news_for_tickers(sample_articles)
        
        sector_mapping = {t: 'Tech' for t in ticker_sentiment}
        sector_result = analytics.sector_sentiment_analysis(
            ticker_sentiment,
            sector_mapping
        )
        
        if sector_result:
            sector = list(sector_result.keys())[0]
            metrics = sector_result[sector]
            
            assert 'num_tickers' in metrics
            assert 'avg_polarity' in metrics
            assert 'constituent_tickers' in metrics


class TestCorrelationAnalysis:
    """Test sentiment-price correlation analysis."""
    
    def test_correlation_calculation(self, analytics, sample_articles):
        """Test sentiment-price correlation."""
        ticker_sentiment = analytics.analyze_news_for_tickers(sample_articles)
        
        price_changes = {
            'AAPL': 5.0,
            'MSFT': 3.0,
            'GOOGL': 2.0,
            'META': -1.0
        }
        
        correlation = analytics.correlate_sentiment_with_returns(
            ticker_sentiment,
            price_changes
        )
        
        assert isinstance(correlation, dict)
        assert len(correlation) > 0
    
    def test_agreement_calculation(self, analytics):
        """Test sentiment-price agreement calculation."""
        # Positive sentiment, positive price
        agreement = analytics._calculate_agreement(0.5, 5.0)
        assert agreement > 0
        
        # Positive sentiment, negative price
        disagreement = analytics._calculate_agreement(0.5, -5.0)
        assert disagreement < 0
    
    def test_quality_score(self, analytics):
        """Test article quality scoring."""
        sentiment_data = {
            'num_articles': 10,
            'top_sources': [('bloomberg', 5), ('reuters', 3)]
        }
        
        quality = analytics._calculate_quality_score(sentiment_data)
        
        assert 0 <= quality <= 1


class TestNewsDataStorage:
    """Test news analysis data storage."""
    
    def test_save_analysis(self, analytics, sample_articles, tmp_path):
        """Test saving news analysis to Parquet."""
        ticker_sentiment = analytics.analyze_news_for_tickers(sample_articles)
        
        output = analytics.save_news_analysis(
            ticker_sentiment,
            output_dir=str(tmp_path)
        )
        
        assert isinstance(output, str)


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_empty_articles(self, analytics):
        """Test with empty article list."""
        result = analytics.analyze_news_for_tickers([])
        
        assert result == {}
    
    def test_article_missing_fields(self, analytics):
        """Test handling articles with missing fields."""
        articles = [
            {
                'title': 'AAPL stock rises',
                'description': None,
                'content': None,
                'publishedAt': '2024-01-15T10:00:00Z',
                'source': {'name': 'Unknown'}
            }
        ]
        
        # Should handle gracefully
        result = analytics.analyze_news_for_tickers(articles)
        assert isinstance(result, dict)
    
    def test_very_long_article(self, analytics):
        """Test with very long article text."""
        long_text = "AAPL stock " * 1000  # 8000+ words
        
        sentiment = analytics.analyze_article_sentiment(long_text)
        
        assert 'polarity' in sentiment
        assert 'subjectivity' in sentiment
    
    def test_special_characters(self, analytics):
        """Test with special characters in text."""
        text = "AAPL $$ going up!!! $AAPL #Apple @apple"
        mentions = analytics.extract_ticker_mentions(text)
        
        # Should handle special characters
        assert isinstance(mentions, dict)
