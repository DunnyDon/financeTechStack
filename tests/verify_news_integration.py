#!/usr/bin/env python
"""
Verification script for Prefect news sentiment integration.
Demonstrates both direct and Prefect flow execution paths.
"""

import sys
import os

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_direct_function():
    """Test the direct Streamlit-compatible function."""
    print("\n" + "="*60)
    print("TEST 1: Direct Function (Streamlit Mode)")
    print("="*60)
    
    try:
        from src.news_analysis_streamlit import analyze_news_sentiment_streamlit
        
        print("Fetching news articles (limited to 5 for testing)...")
        articles, stats = analyze_news_sentiment_streamlit(
            max_articles=5,
            hours_back=24,
            symbols=['AAPL', 'MSFT']
        )
        
        print(f"\n✓ Success!")
        print(f"  - Articles found: {stats['total_articles']}")
        print(f"  - Average sentiment: {stats['avg_sentiment']:.2f}")
        print(f"  - Positive: {stats['positive_count']}")
        print(f"  - Negative: {stats['negative_count']}")
        print(f"  - Neutral: {stats['neutral_count']}")
        print(f"  - Sources: {stats['sources_count']}")
        if stats['portfolio_mentions']:
            print(f"  - Portfolio mentions: {stats['portfolio_mentions']}")
        
        if articles:
            print(f"\nSample article:")
            article = articles[0]
            print(f"  Title: {article['title'][:80]}...")
            print(f"  Source: {article['source']}")
            print(f"  Sentiment: {article['sentiment_label']} ({article['sentiment_score']:.2f})")
        
        return True
        
    except Exception as e:
        print(f"\n✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_prefect_flow():
    """Test the Prefect flow integration."""
    print("\n" + "="*60)
    print("TEST 2: Prefect Flow (with Logging)")
    print("="*60)
    
    try:
        from src.news_analysis_streamlit import news_sentiment_analysis_flow
        
        print("Executing Prefect flow (limited to 5 articles)...")
        print("(Flow logging will be visible in Prefect UI at http://localhost:4200)")
        
        articles, stats = news_sentiment_analysis_flow(
            max_articles=5,
            hours_back=24,
            symbols=['AAPL', 'MSFT']
        )
        
        print(f"\n✓ Success!")
        print(f"  - Articles found: {stats['total_articles']}")
        print(f"  - Average sentiment: {stats['avg_sentiment']:.2f}")
        print(f"  - Positive: {stats['positive_count']}")
        print(f"  - Negative: {stats['negative_count']}")
        print(f"  - Neutral: {stats['neutral_count']}")
        print(f"  - Sources: {stats['sources_count']}")
        
        if stats['total_articles'] > 0:
            print("\n📋 Check Prefect UI at http://localhost:4200 for detailed task logs")
        
        return True
        
    except Exception as e:
        print(f"\n✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_imports():
    """Test that all required imports work."""
    print("\n" + "="*60)
    print("TEST 0: Module Imports")
    print("="*60)
    
    try:
        print("Checking imports...")
        from src.news_analysis_streamlit import (
            scrape_news_articles,
            analyze_sentiment,
            get_portfolio_mentions,
            analyze_news_sentiment_streamlit,
            news_sentiment_analysis_flow
        )
        print("✓ All functions imported successfully")
        
        # Check optional dependencies
        try:
            from textblob import TextBlob
            print("✓ TextBlob available (sentiment analysis enabled)")
        except ImportError:
            print("⚠ TextBlob not available (using keyword fallback)")
        
        try:
            import feedparser
            print("✓ feedparser available (RSS parsing enabled)")
        except ImportError:
            print("✗ feedparser missing (news scraping will fail)")
            return False
        
        try:
            from prefect import flow, task
            print("✓ Prefect available (task logging enabled)")
        except ImportError:
            print("⚠ Prefect not available (will use direct execution)")
        
        return True
        
    except Exception as e:
        print(f"✗ Import failed: {e}")
        return False


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("PREFECT NEWS SENTIMENT INTEGRATION - VERIFICATION")
    print("="*60)
    
    # Test imports first
    if not test_imports():
        print("\n❌ Import tests failed. Cannot continue.")
        sys.exit(1)
    
    # Test direct function
    direct_ok = test_direct_function()
    
    # Test Prefect flow
    prefect_ok = test_prefect_flow()
    
    # Summary
    print("\n" + "="*60)
    print("VERIFICATION SUMMARY")
    print("="*60)
    print(f"Direct Function (Streamlit):  {'✓ PASS' if direct_ok else '✗ FAIL'}")
    print(f"Prefect Flow Integration:     {'✓ PASS' if prefect_ok else '✗ FAIL'}")
    
    if direct_ok or prefect_ok:
        print("\n✓ News sentiment analysis is working!")
        print("\nNext steps:")
        print("1. Start the dashboard: ./run_dashboard.sh")
        print("2. Navigate to Advanced Analytics > News tab")
        print("3. Click '📰 Fetch News & Sentiment'")
        print("4. Check Prefect logs at http://localhost:4200 for details")
    else:
        print("\n✗ Some tests failed. Check the output above for details.")
        sys.exit(1)


if __name__ == '__main__':
    main()
