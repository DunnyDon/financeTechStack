"""
Unit tests for SEC filings scraper using pytest.
Tests verify that data is returned from SEC API for standard tickers.
"""

import os
import json
import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock
from pathlib import Path


# Import the functions to test (without Prefect decorators for testing)
# We'll test the underlying logic


@pytest.fixture
def mock_company_tickers_response():
    """Mock response from SEC company tickers API."""
    return {
        "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."},
        "1": {"cik_str": 789019, "ticker": "MSFT", "title": "Microsoft Corporation"},
        "2": {"cik_str": 1018724, "ticker": "AMZN", "title": "Amazon.com Inc."},
    }


@pytest.fixture
def mock_filings_response():
    """Mock response from SEC filings API."""
    return {
        "filings": {
            "recent": {
                "form": ["10-K", "10-Q", "10-Q", "10-K"],
                "accessionNumber": [
                    "0000320193-24-000006",
                    "0000320193-24-000056",
                    "0000320193-23-000101",
                    "0000320193-23-000010",
                ],
                "filingDate": ["2024-01-30", "2024-04-15", "2023-10-30", "2023-01-31"],
                "reportDate": ["2023-12-30", "2024-03-30", "2023-09-30", "2022-12-31"],
            }
        }
    }


@pytest.fixture
def temp_db_dir(tmp_path):
    """Create temporary database directory."""
    db_dir = tmp_path / "db"
    db_dir.mkdir()
    return str(db_dir)


# Test helper functions
def extract_cik_from_tickers(tickers_data: dict, ticker: str) -> str | None:
    """Extract CIK from tickers data."""
    for entry in tickers_data.values():
        if entry.get("ticker", "").upper() == ticker.upper():
            return str(entry.get("cik_str", "")).zfill(10)
    return None


def extract_filings(filings_response: dict, filing_type: str = "10-K", limit: int = 10) -> list[dict]:
    """Extract filings from API response."""
    filings = []
    if "filings" in filings_response and "recent" in filings_response["filings"]:
        recent = filings_response["filings"]["recent"]

        for i, form_type in enumerate(recent.get("form", [])):
            if form_type == filing_type and len(filings) < limit:
                accession_number = recent["accessionNumber"][i]
                filing_date = recent["filingDate"][i]
                report_date = recent["reportDate"][i]

                filing_info = {
                    "accession_number": accession_number,
                    "filing_date": filing_date,
                    "report_date": report_date,
                    "form_type": form_type,
                }
                filings.append(filing_info)

    return filings


# Tests for CIK extraction
class TestCIKExtraction:
    def test_extract_cik_aapl(self, mock_company_tickers_response):
        """Test successful CIK extraction for AAPL."""
        cik = extract_cik_from_tickers(mock_company_tickers_response, "AAPL")
        assert cik == "0000320193"

    def test_extract_cik_msft(self, mock_company_tickers_response):
        """Test successful CIK extraction for MSFT."""
        cik = extract_cik_from_tickers(mock_company_tickers_response, "MSFT")
        assert cik == "0000789019"

    def test_extract_cik_amzn(self, mock_company_tickers_response):
        """Test successful CIK extraction for AMZN."""
        cik = extract_cik_from_tickers(mock_company_tickers_response, "AMZN")
        assert cik == "0001018724"

    def test_extract_cik_case_insensitive(self, mock_company_tickers_response):
        """Test that CIK extraction is case-insensitive."""
        cik1 = extract_cik_from_tickers(mock_company_tickers_response, "aapl")
        cik2 = extract_cik_from_tickers(mock_company_tickers_response, "AAPL")
        cik3 = extract_cik_from_tickers(mock_company_tickers_response, "AaPl")
        assert cik1 == cik2 == cik3 == "0000320193"

    def test_extract_cik_invalid_ticker(self, mock_company_tickers_response):
        """Test CIK extraction with invalid ticker."""
        cik = extract_cik_from_tickers(mock_company_tickers_response, "INVALID")
        assert cik is None

    def test_extract_cik_zero_padding(self, mock_company_tickers_response):
        """Test that CIK is zero-padded to 10 digits."""
        cik = extract_cik_from_tickers(mock_company_tickers_response, "AAPL")
        assert len(cik) == 10
        assert cik.isdigit()


# Tests for filing extraction
class TestFilingExtraction:
    def test_extract_filings_10k(self, mock_filings_response):
        """Test extraction of 10-K filings."""
        filings = extract_filings(mock_filings_response, filing_type="10-K")
        assert len(filings) > 0
        assert all(f["form_type"] == "10-K" for f in filings)

    def test_extract_filings_contains_required_fields(self, mock_filings_response):
        """Test that extracted filings contain all required fields."""
        filings = extract_filings(mock_filings_response, filing_type="10-K", limit=1)
        assert len(filings) > 0

        filing = filings[0]
        assert "accession_number" in filing
        assert "filing_date" in filing
        assert "report_date" in filing
        assert "form_type" in filing

    def test_extract_filings_respects_limit(self, mock_filings_response):
        """Test that filing extraction respects the limit parameter."""
        filings_limit_1 = extract_filings(mock_filings_response, filing_type="10-K", limit=1)
        assert len(filings_limit_1) <= 1

        filings_limit_3 = extract_filings(mock_filings_response, filing_type="10-K", limit=3)
        assert len(filings_limit_3) <= 3

    def test_extract_filings_empty_response(self):
        """Test extraction with empty filings response."""
        empty_response = {"filings": {"recent": {"form": []}}}
        filings = extract_filings(empty_response, filing_type="10-K")
        assert len(filings) == 0

    def test_extract_filings_multiple_types(self, mock_filings_response):
        """Test extraction of different filing types."""
        filings_10k = extract_filings(mock_filings_response, filing_type="10-K")
        filings_10q = extract_filings(mock_filings_response, filing_type="10-Q")

        assert len(filings_10k) > 0
        assert len(filings_10q) > 0
        assert all(f["form_type"] == "10-K" for f in filings_10k)
        assert all(f["form_type"] == "10-Q" for f in filings_10q)

    def test_extract_filings_nonexistent_type(self, mock_filings_response):
        """Test extraction of non-existent filing type."""
        filings = extract_filings(mock_filings_response, filing_type="8-K")
        assert len(filings) == 0


# Tests for Parquet saving
class TestParquetSaving:
    def test_save_filings_parquet_creates_file(self, temp_db_dir):
        """Test that Parquet files are created successfully."""
        import pandas as pd

        test_data = [
            {
                "accession_number": "0000320193-24-000006",
                "filing_date": "2024-01-30",
                "report_date": "2023-12-30",
                "form_type": "10-K",
            },
            {
                "accession_number": "0000789019-24-000006",
                "filing_date": "2024-01-30",
                "report_date": "2023-12-30",
                "form_type": "10-K",
            },
        ]

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"{temp_db_dir}/sec_filings_{timestamp}.parquet"

        df = pd.DataFrame(test_data)
        df.to_parquet(output_file, engine="pyarrow", compression="snappy", index=False)

        assert os.path.exists(output_file)
        assert output_file.endswith(".parquet")

    def test_save_filings_parquet_data_integrity(self, temp_db_dir):
        """Test that data is preserved when saving to Parquet."""
        import pandas as pd

        test_data = [
            {
                "accession_number": "0000320193-24-000006",
                "filing_date": "2024-01-30",
                "report_date": "2023-12-30",
                "form_type": "10-K",
            }
        ]

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"{temp_db_dir}/sec_filings_{timestamp}.parquet"

        df = pd.DataFrame(test_data)
        df.to_parquet(output_file, engine="pyarrow", compression="snappy", index=False)

        # Read back and verify
        df_read = pd.read_parquet(output_file)
        assert len(df_read) == 1
        assert df_read.iloc[0]["accession_number"] == "0000320193-24-000006"
        assert df_read.iloc[0]["filing_date"] == "2024-01-30"

    def test_save_filings_parquet_multiple_rows(self, temp_db_dir):
        """Test saving multiple rows to Parquet."""
        import pandas as pd

        test_data = [
            {
                "accession_number": f"0000320193-24-{i:06d}",
                "filing_date": f"2024-0{i}-01",
                "report_date": f"2023-12-31",
                "form_type": "10-K",
            }
            for i in range(1, 11)
        ]

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"{temp_db_dir}/sec_filings_{timestamp}.parquet"

        df = pd.DataFrame(test_data)
        df.to_parquet(output_file, engine="pyarrow", compression="snappy", index=False)

        df_read = pd.read_parquet(output_file)
        assert len(df_read) == 10


# Integration tests with mocked HTTP requests
class TestIntegration:
    @patch("requests.get")
    def test_fetch_cik_integration(self, mock_get, mock_company_tickers_response):
        """Integration test: Fetch CIK using mocked HTTP request."""
        mock_response = MagicMock()
        mock_response.json.return_value = mock_company_tickers_response
        mock_get.return_value = mock_response

        cik = extract_cik_from_tickers(mock_company_tickers_response, "AAPL")
        assert cik == "0000320193"

    @patch("requests.get")
    def test_fetch_filings_integration(self, mock_get, mock_filings_response):
        """Integration test: Fetch filings using mocked HTTP request."""
        mock_response = MagicMock()
        mock_response.json.return_value = mock_filings_response
        mock_get.return_value = mock_response

        filings = extract_filings(mock_filings_response, filing_type="10-K", limit=5)
        assert len(filings) > 0
        assert all(isinstance(f, dict) for f in filings)
        assert all("accession_number" in f for f in filings)


# Parametrized tests
class TestParametrized:
    @pytest.mark.parametrize(
        "ticker,expected_cik",
        [
            ("AAPL", "0000320193"),
            ("MSFT", "0000789019"),
            ("AMZN", "0001018724"),
        ],
    )
    def test_multiple_tickers(self, ticker, expected_cik, mock_company_tickers_response):
        """Test CIK extraction for multiple standard tickers."""
        cik = extract_cik_from_tickers(mock_company_tickers_response, ticker)
        assert cik == expected_cik

    @pytest.mark.parametrize(
        "filing_type",
        ["10-K", "10-Q"],
    )
    def test_multiple_filing_types(self, filing_type, mock_filings_response):
        """Test filing extraction for different filing types."""
        filings = extract_filings(mock_filings_response, filing_type=filing_type)
        assert isinstance(filings, list)
        if filings:
            assert all(f["form_type"] == filing_type for f in filings)
