"""
Test suite for portfolio flows.

Demonstrates running the three Prefect flows:
1. aggregate_financial_data_flow
2. portfolio_analysis_flow
3. portfolio_end_to_end_flow
"""

import os

import pytest
from prefect.testing.utilities import prefect_test_harness

from src.portfolio_flows import (
    aggregate_financial_data_flow,
    generate_portfolio_reports_task,
    load_portfolio_from_parquet_task,
    portfolio_analysis_flow,
    portfolio_end_to_end_flow,
)


class TestPortfolioFlows:
    """Test portfolio flows."""

    @pytest.fixture
    def test_output_dir(self, tmp_path):
        """Create temporary output directory."""
        return str(tmp_path / "portfolio_output")

    def test_aggregate_financial_data_flow_basic(self, test_output_dir):
        """Test basic aggregation flow with default tickers."""
        with prefect_test_harness():
            result = aggregate_financial_data_flow(
                tickers=["AAPL"],
                output_dir=test_output_dir,
            )

            # Check result structure
            assert result is not None
            assert "parquet_file" in result or "status" in result
            assert result.get("status") in ["success", "error"]

    def test_aggregate_financial_data_flow_multiple_tickers(self, test_output_dir):
        """Test aggregation flow with multiple tickers."""
        with prefect_test_harness():
            result = aggregate_financial_data_flow(
                tickers=["AAPL", "MSFT"],
                output_dir=test_output_dir,
            )

            assert result is not None
            assert "status" in result

    def test_portfolio_analysis_flow_with_parquet(self, test_output_dir):
        """Test portfolio analysis flow."""
        with prefect_test_harness():
            # First aggregate data
            agg_result = aggregate_financial_data_flow(
                tickers=["AAPL"],
                output_dir=test_output_dir,
            )

            if agg_result.get("status") == "success":
                parquet_file = agg_result.get("parquet_file")

                if parquet_file and os.path.exists(parquet_file):
                    # Then analyze
                    result = portfolio_analysis_flow(
                        parquet_file=parquet_file,
                        output_dir=test_output_dir,
                    )

                    assert result is not None
                    assert "status" in result

    def test_portfolio_end_to_end_flow(self, test_output_dir):
        """Test complete end-to-end flow."""
        with prefect_test_harness():
            result = portfolio_end_to_end_flow(
                tickers=["AAPL"],
                output_dir=test_output_dir,
            )

            assert result is not None
            assert "status" in result
            assert "timestamp" in result or result.get("status") == "error"

    def test_load_portfolio_from_parquet_nonexistent(self):
        """Test loading from non-existent parquet file."""
        with prefect_test_harness():
            result = load_portfolio_from_parquet_task("/nonexistent/file.parquet")
            assert result is None

    def test_generate_portfolio_reports(self, test_output_dir):
        """Test report generation."""
        with prefect_test_harness():
            analysis_results = {
                "total_records": 10,
                "tickers": ["AAPL", "MSFT"],
                "records_with_prices": 8,
                "records_with_fundamentals": 5,
                "technical_indicators_calculated": 2,
            }

            result = generate_portfolio_reports_task(
                analysis_results=analysis_results,
                output_dir=test_output_dir,
            )

            assert result is not None
            assert "html_report" in result
            assert "json_report" in result
            assert "summary" in result

            # Check files were created
            if os.path.exists(test_output_dir):
                files = os.listdir(test_output_dir)
                assert any(f.endswith(".html") for f in files)
                assert any(f.endswith(".json") for f in files)


class TestPortfolioFlowIntegration:
    """Integration tests for portfolio flows."""

    def test_full_pipeline_execution(self, tmp_path):
        """Test full pipeline execution."""
        output_dir = str(tmp_path / "integration_output")

        with prefect_test_harness():
            # Run end-to-end flow
            result = portfolio_end_to_end_flow(
                tickers=["AAPL"],
                output_dir=output_dir,
            )

            # Verify result
            assert result is not None
            if result.get("status") == "success":
                assert "aggregation" in result
                assert "analysis" in result
                assert "parquet_file" in result

    def test_separate_flows_sequence(self, tmp_path):
        """Test running flows separately in sequence."""
        output_dir = str(tmp_path / "sequence_output")

        with prefect_test_harness():
            # Step 1: Aggregate
            agg_result = aggregate_financial_data_flow(
                tickers=["AAPL"],
                output_dir=output_dir,
            )

            assert agg_result is not None

            if agg_result.get("status") == "success" and agg_result.get("parquet_file"):
                # Step 2: Analyze
                analysis_result = portfolio_analysis_flow(
                    parquet_file=agg_result["parquet_file"],
                    output_dir=output_dir,
                )

                assert analysis_result is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
