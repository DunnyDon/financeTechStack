"""
News analysis flow for Prefect orchestration.

Integrates news scraping and sentiment analysis into the portfolio
analytics pipeline to assess market impacts.
"""

from typing import Dict, Optional

import pandas as pd
from prefect import flow, get_run_logger

from .analytics_flows import enhanced_analytics_flow
from .analytics_report import AnalyticsReporter, send_analytics_email
from .news_analysis import (
    analyze_news_sentiment,
    assess_portfolio_impact,
    get_news_analysis_report,
    scrape_news_headlines,
)
from .portfolio_holdings import Holdings

__all__ = ["news_informed_analytics_flow"]


@flow(name="news_informed_analytics_flow")
def news_informed_analytics_flow(
    send_email_report: bool = False,
    email: Optional[str] = None,
    include_news: bool = True,
) -> Dict:
    """
    Enhanced analytics flow that incorporates news sentiment analysis.

    Args:
        send_email_report: Whether to send email report
        email: Email address for report delivery
        include_news: Whether to include news analysis

    Returns:
        Dictionary with analytics results including news impact
    """
    flow_logger = get_run_logger()
    flow_logger.info("Starting news-informed analytics flow...")

    try:
        # Get standard analytics
        analytics_result = enhanced_analytics_flow(
            send_email_report=False,  # We'll handle email separately
            email=email,
        )

        if not include_news:
            return analytics_result

        # Scrape and analyze news
        flow_logger.info("Incorporating news analysis...")

        articles = scrape_news_headlines(max_articles=500, hours_back=24)
        if not articles:
            flow_logger.warning("No articles scraped, skipping news analysis")
            return analytics_result

        analyzed_articles = analyze_news_sentiment(articles)

        # Load holdings for impact assessment
        holdings = Holdings("holdings.csv")
        holdings_df = holdings.all_holdings

        impact_summary = assess_portfolio_impact(analyzed_articles, holdings_df)

        # Generate report
        news_report = get_news_analysis_report(impact_summary)
        flow_logger.info("News analysis completed")

        # Combine results
        result = {
            **analytics_result,
            "news_analysis": {
                "impact_summary": impact_summary,
                "articles_analyzed": len(analyzed_articles),
                "report": news_report,
            },
        }

        # Send email with news analysis if requested
        if send_email_report:
            flow_logger.info("Sending analytics email with news analysis...")
            
            # Extract data from analytics result
            pnl_data = None
            technical_data = None
            fundamental_data = None
            portfolio_weights = None
            
            if result.get("pnl_data"):
                try:
                    pnl_data = pd.DataFrame(result["pnl_data"])
                except Exception:
                    pass
            
            # Get portfolio weights
            portfolio_weights = result.get("portfolio_weights", {})
            
            # Send email with news analysis (email from config if not provided)
            email_success = send_analytics_email(
                pnl_data=pnl_data,
                technical_data=technical_data,
                fundamental_data=fundamental_data,
                portfolio_weights=portfolio_weights,
                email=email,  # Will use config.csv report_email if None
                news_analysis=result.get("news_analysis"),
            )
            
            if email_success:
                recipient = email or "configured email"
                flow_logger.info(f"Analytics email with news analysis sent to {recipient}")
            else:
                flow_logger.warning("Failed to send analytics email")

        return result

    except Exception as e:
        flow_logger.error(f"Error in news-informed analytics flow: {e}")
        raise
