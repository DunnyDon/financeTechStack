#!/usr/bin/env python3
"""
Example: News-informed portfolio analysis.

This script demonstrates how to use the news analysis feature to assess
the impact of world headlines on your portfolio holdings.
"""

import json
from src.news_flows import news_informed_analytics_flow
from src.portfolio_holdings import Holdings

def main():
    """Run news-informed analytics and display results."""
    
    print("\n" + "="*70)
    print("PORTFOLIO NEWS IMPACT ANALYSIS")
    print("="*70)
    
    # Run the full analysis
    print("\nRunning news-informed analytics flow...")
    result = news_informed_analytics_flow(send_email_report=False, include_news=True)
    
    # Display portfolio summary
    print("\n" + "-"*70)
    print("PORTFOLIO SUMMARY")
    print("-"*70)
    
    portfolio_info = result.get('portfolio_info', {})
    weights = result.get('portfolio_weights', {})
    
    print(f"Total Portfolio Value: €{weights.get('total_value_eur', 0):,.2f}")
    print("\nAsset Class Allocation:")
    for asset_class, data in sorted(
        weights.get('by_asset_class', {}).items(),
        key=lambda x: x[1]['weight_percent'],
        reverse=True
    ):
        print(f"  {asset_class.title():20s} {data['weight_percent']:6.1f}% (€{data['value_eur']:>12,.0f})")
    
    # Display news analysis
    news_analysis = result.get('news_analysis', {})
    if news_analysis:
        print("\n" + "-"*70)
        print("NEWS SENTIMENT ANALYSIS")
        print("-"*70)
        
        impact = news_analysis.get('impact_summary', {})
        print(f"\nArticles Analyzed: {news_analysis.get('articles_analyzed', 0)}")
        print(f"Sectors Affected: {len(impact.get('by_sector', {}))}")
        
        # Timeframe breakdown
        print("\nSentiment by Timeframe:")
        for timeframe in ['short_term', 'medium_term', 'long_term']:
            counts = impact.get('by_timeframe', {}).get(timeframe, {})
            print(f"\n  {timeframe.replace('_', ' ').title()}:")
            print(f"    Bullish:  {counts.get('bullish', 0):3d}")
            print(f"    Bearish:  {counts.get('bearish', 0):3d}")
            print(f"    Neutral:  {counts.get('neutral', 0):3d}")
        
        # Sector impact
        print("\nTop Sectors by Volume:")
        sectors_by_articles = sorted(
            impact.get('by_sector', {}).items(),
            key=lambda x: (x[1].get('bullish_count', 0) + x[1].get('bearish_count', 0)),
            reverse=True
        )
        
        for sector, data in sectors_by_articles[:5]:
            total_articles = data.get('bullish_count', 0) + data.get('bearish_count', 0)
            print(f"\n  {sector.title()}:")
            print(f"    Bullish: {data.get('bullish_count', 0):2d}")
            print(f"    Bearish: {data.get('bearish_count', 0):2d}")
        
        # Key risks
        risks = impact.get('key_risks', [])
        if risks:
            print("\nKey Risks (Bearish Sectors):")
            for i, risk in enumerate(risks[:3], 1):
                print(f"  {i}. {risk['sector'].title()}: {risk['bearish_articles']} bearish articles")
        
        # Key opportunities
        opportunities = impact.get('key_opportunities', [])
        if opportunities:
            print("\nKey Opportunities (Bullish Sectors):")
            for i, opp in enumerate(opportunities[:3], 1):
                print(f"  {i}. {opp['sector'].title()}: {opp['bullish_articles']} bullish articles")
        
        # Print full report
        print("\n" + "-"*70)
        print("FULL NEWS ANALYSIS REPORT")
        print("-"*70)
        print(news_analysis.get('report', 'No report available'))
    
    # Display technical signals
    tech_signals = result.get('technical_signals', {})
    if tech_signals:
        print("\n" + "-"*70)
        print("TECHNICAL SIGNALS")
        print("-"*70)
        print(f"Bullish Signals: {tech_signals.get('macd_bullish', 0)}")
        print(f"Bearish Signals: {tech_signals.get('macd_bearish', 0)}")
        print(f"Bollinger Oversold: {tech_signals.get('bollinger_oversold', 0)}")
        print(f"Bollinger Overbought: {tech_signals.get('bollinger_overbought', 0)}")
    
    print("\n" + "="*70 + "\n")

if __name__ == "__main__":
    main()
