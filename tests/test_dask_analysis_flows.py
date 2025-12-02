"""
Tests for extended Dask analysis flows (technical, news, multi-source pricing).

Validates:
- Technical analysis parallelization
- News sentiment analysis parallelization
- Multi-source pricing in parallel
- Performance improvements
"""

import time
from typing import Dict, List

import pandas as pd
import pytest


class TestTechnicalAnalysisParallelization:
    """Test parallel technical indicator calculation."""

    @pytest.mark.skip(reason="Requires Dask cluster running")
    def test_single_security_technicals(self):
        """Test technical indicator calculation for one security."""
        from src.dask_analysis_flows import calculate_security_technicals
        from src.portfolio_prices import PriceFetcher

        # Fetch price data
        fetcher = PriceFetcher()
        price_data = fetcher.fetch_price("AAPL", asset_type="eq")

        assert price_data is not None, "Failed to fetch price data"

        # Calculate technicals
        result = calculate_security_technicals("AAPL", price_data)

        assert result is not None, "Technical calculation returned None"
        assert result["ticker"] == "AAPL"
        assert "technical_indicators" in result
        assert "summary" in result
        assert result["summary"]["sma_20"] is not None
        assert result["summary"]["rsi_14"] is not None

    @pytest.mark.skip(reason="Requires Dask cluster running")
    def test_multi_security_technicals_parallel_vs_sequential(self):
        """Compare parallel vs sequential technical analysis performance."""
        from src.dask_analysis_flows import calculate_security_technicals
        from src.portfolio_prices import PriceFetcher

        test_tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]
        fetcher = PriceFetcher()

        # Fetch all price data
        price_data_map = {}
        for ticker in test_tickers:
            price_data = fetcher.fetch_price(ticker, asset_type="eq")
            if price_data:
                price_data_map[ticker] = price_data

        assert len(price_data_map) > 0, "Failed to fetch any price data"

        # Sequential processing
        seq_start = time.time()
        seq_results = []
        for ticker, price_data in price_data_map.items():
            result = calculate_security_technicals(ticker, price_data)
            if result:
                seq_results.append(result)
        seq_duration = time.time() - seq_start

        # Parallel processing with Dask
        par_start = time.time()
        from src.dask_portfolio_flows import setup_dask_client, teardown_dask_client
        client = setup_dask_client("tcp://localhost:8786")

        futures = [
            client.submit(calculate_security_technicals, ticker, price_data)
            for ticker, price_data in price_data_map.items()
        ]
        par_results = client.gather(futures)
        par_results = [r for r in par_results if r]
        par_duration = time.time() - par_start

        teardown_dask_client()

        assert len(par_results) > 0, "No parallel results returned"
        assert len(seq_results) > 0, "No sequential results returned"

        speedup = seq_duration / par_duration
        print(f"\nTechnical Analysis Performance:")
        print(f"  Sequential: {seq_duration:.3f}s")
        print(f"  Parallel: {par_duration:.3f}s")
        print(f"  Speedup: {speedup:.2f}x")

        # Verify results match
        assert len(par_results) == len(seq_results), "Result count mismatch"


class TestNewsAnalysisParallelization:
    """Test parallel news sentiment analysis."""

    @pytest.mark.skip(reason="Requires Dask cluster running and news source")
    def test_single_security_news(self):
        """Test news analysis for one security."""
        from src.dask_analysis_flows import fetch_news_for_ticker

        result = fetch_news_for_ticker("AAPL")

        # May be None if no news available, but structure should be consistent
        if result:
            assert result["ticker"] == "AAPL"
            assert "article_count" in result
            assert "avg_sentiment" in result
            assert isinstance(result["articles"], list)

    @pytest.mark.skip(reason="Requires Dask cluster running and news source")
    def test_multi_security_news_parallel(self):
        """Test parallel news analysis for multiple securities."""
        from src.dask_analysis_flows import fetch_news_for_ticker
        from src.dask_portfolio_flows import setup_dask_client, teardown_dask_client

        test_tickers = ["AAPL", "MSFT", "GOOGL"]

        # Parallel processing
        client = setup_dask_client("tcp://localhost:8786")
        futures = client.map(fetch_news_for_ticker, test_tickers)
        results = client.gather(futures)
        teardown_dask_client()

        results = [r for r in results if r]

        # Check structure
        for result in results:
            assert "ticker" in result
            assert "article_count" in result
            assert "avg_sentiment" in result

        print(f"\nNews Analysis Results:")
        print(f"  Securities analyzed: {len(results)}")
        print(f"  Total articles: {sum(r['article_count'] for r in results)}")


class TestMultiSourcePricingParallelization:
    """Test parallel multi-source price fetching."""

    @pytest.mark.skip(reason="Requires Dask cluster running")
    def test_single_security_multi_source_price(self):
        """Test price fetch for one security."""
        from src.dask_analysis_flows import fetch_price_from_multiple_sources

        result = fetch_price_from_multiple_sources("AAPL")

        assert result is not None, "Failed to fetch price"
        assert result["ticker"] == "AAPL"
        assert "price_data" in result
        assert "source" in result
        assert result["price_data"].get("close") is not None

    @pytest.mark.skip(reason="Requires Dask cluster running")
    def test_multi_security_prices_parallel_vs_sequential(self):
        """Compare parallel vs sequential multi-source price fetching."""
        from src.dask_analysis_flows import fetch_price_from_multiple_sources
        from src.dask_portfolio_flows import setup_dask_client, teardown_dask_client

        test_tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]

        # Sequential
        seq_start = time.time()
        seq_results = []
        for ticker in test_tickers:
            result = fetch_price_from_multiple_sources(ticker)
            if result:
                seq_results.append(result)
        seq_duration = time.time() - seq_start

        # Parallel
        par_start = time.time()
        client = setup_dask_client("tcp://localhost:8786")
        futures = client.map(fetch_price_from_multiple_sources, test_tickers)
        par_results = client.gather(futures)
        par_duration = time.time() - par_start
        teardown_dask_client()

        par_results = [r for r in par_results if r]

        assert len(par_results) > 0, "No parallel results"
        assert len(seq_results) > 0, "No sequential results"

        speedup = seq_duration / par_duration
        print(f"\nMulti-Source Pricing Performance:")
        print(f"  Sequential: {seq_duration:.3f}s")
        print(f"  Parallel: {par_duration:.3f}s")
        print(f"  Speedup: {speedup:.2f}x")


class TestAnalysisFlowsIntegration:
    """Test full Prefect flows with Dask parallelization."""

    @pytest.mark.skip(reason="Requires full infrastructure")
    def test_technical_analysis_flow(self):
        """Test technical analysis Prefect flow."""
        from src.dask_analysis_flows import dask_portfolio_technical_analysis_flow

        result = dask_portfolio_technical_analysis_flow(
            tickers=["AAPL", "MSFT", "GOOGL"],
            dask_scheduler="tcp://localhost:8786",
        )

        assert result["status"] == "success", f"Flow failed: {result}"
        assert result["securities_analyzed"] > 0
        assert "technical_summary" in result
        assert "timestamp" in result

    @pytest.mark.skip(reason="Requires full infrastructure")
    def test_news_analysis_flow(self):
        """Test news analysis Prefect flow."""
        from src.dask_analysis_flows import dask_news_analysis_flow

        result = dask_news_analysis_flow(
            tickers=["AAPL", "MSFT"],
            dask_scheduler="tcp://localhost:8786",
        )

        assert result["status"] == "success", f"Flow failed: {result}"
        assert "timestamp" in result

    @pytest.mark.skip(reason="Requires full infrastructure")
    def test_multi_source_pricing_flow(self):
        """Test multi-source pricing Prefect flow."""
        from src.dask_analysis_flows import dask_multi_source_pricing_flow

        result = dask_multi_source_pricing_flow(
            tickers=["AAPL", "MSFT", "GOOGL"],
            dask_scheduler="tcp://localhost:8786",
        )

        assert result["status"] == "success", f"Flow failed: {result}"
        assert result["securities_fetched"] > 0
        assert "prices" in result
        assert len(result["prices"]) > 0


class TestParallelizationBenchmarks:
    """Benchmark different parallelization strategies."""

    @pytest.mark.skip(reason="Requires Dask cluster running")
    def test_scaling_with_workers(self):
        """Test performance scaling with different worker counts."""
        from src.dask_analysis_flows import fetch_price_from_multiple_sources
        from src.dask_portfolio_flows import setup_dask_client, teardown_dask_client

        test_tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "META", "NVDA", "AMD"]

        # Current cluster (2 workers)
        client = setup_dask_client("tcp://localhost:8786")

        start = time.time()
        futures = client.map(fetch_price_from_multiple_sources, test_tickers)
        results = client.gather(futures)
        duration = time.time() - start

        teardown_dask_client()

        print(f"\nScaling Test (2 workers, {len(test_tickers)} tickers):")
        print(f"  Duration: {duration:.3f}s")
        print(f"  Results: {len([r for r in results if r])}/{len(test_tickers)}")


class TestAggregationFunctions:
    """Test result aggregation from Dask workers."""

    def test_aggregate_technical_results(self):
        """Test technical results aggregation."""
        from src.dask_analysis_flows import aggregate_technical_results

        # Mock results
        mock_results = [
            {
                "ticker": "AAPL",
                "summary": {
                    "sma_20": 150.5,
                    "rsi_14": 65.2,
                    "bollinger_upper": 155.0,
                }
            },
            {
                "ticker": "MSFT",
                "summary": {
                    "sma_20": 380.0,
                    "rsi_14": 45.1,
                    "bollinger_upper": 390.0,
                }
            },
        ]

        result = aggregate_technical_results(mock_results)

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2
        assert "ticker" in result.columns
        assert "sma_20" in result.columns
        assert "rsi_14" in result.columns

    def test_aggregate_news_results(self):
        """Test news results aggregation."""
        from src.dask_analysis_flows import aggregate_news_results

        mock_results = [
            {
                "ticker": "AAPL",
                "article_count": 5,
                "avg_sentiment": 0.2,
            },
            {
                "ticker": "MSFT",
                "article_count": 3,
                "avg_sentiment": -0.1,
            },
        ]

        result = aggregate_news_results(mock_results)

        assert isinstance(result, dict)
        assert result["total_articles"] == 8
        assert result["securities_with_news"] == 2
        assert result["positive_sentiment"] == 1
        assert result["negative_sentiment"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-k", "not skip"])
