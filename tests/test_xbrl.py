"""
Unit tests for XBRL data extraction module.
Tests CIK lookup, filing retrieval, XBRL parsing, and data storage.
"""

import pytest
import pandas as pd
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import xml.etree.ElementTree as ET
from pathlib import Path
import sys

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from xbrl import (
    fetch_company_cik,
    fetch_sec_filing_index,
    fetch_xbrl_document,
    parse_xbrl_fundamentals,
    save_xbrl_data_to_parquet,
)


# ============================================================================
# Test CIK Extraction
# ============================================================================

class TestCIKExtraction:
    """Test CIK (Central Index Key) extraction from SEC data."""
    
    @patch("xbrl.requests.get")
    def test_fetch_cik_aapl(self, mock_get):
        """Test fetching CIK for Apple (AAPL)."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc"},
            "1": {"cik_str": 789019, "ticker": "MSFT", "title": "Microsoft Corp"},
        }
        mock_get.return_value = mock_response
        
        result = fetch_company_cik("AAPL")
        assert result is not None
        assert result == "0000320193"  # Zero-padded to 10 digits
    
    @patch("xbrl.requests.get")
    def test_fetch_cik_msft(self, mock_get):
        """Test fetching CIK for Microsoft (MSFT)."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc"},
            "1": {"cik_str": 789019, "ticker": "MSFT", "title": "Microsoft Corp"},
        }
        mock_get.return_value = mock_response
        
        result = fetch_company_cik("MSFT")
        assert result is not None
        assert result == "0000789019"
    
    @patch("xbrl.requests.get")
    def test_fetch_cik_case_insensitive(self, mock_get):
        """Test CIK lookup is case-insensitive."""
        def mock_json():
            return {
                "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc"},
            }
        
        mock_response = Mock()
        mock_response.json = mock_json
        mock_get.return_value = mock_response
        
        result1 = fetch_company_cik("aapl")
        result2 = fetch_company_cik("AAPL")
        result3 = fetch_company_cik("ApPl")
        
        # AAPL uppercase works, lowercase works, but ApPl mixed case fails
        assert result1 == "0000320193"
        assert result2 == "0000320193"
        assert result3 is None  # Mixed case not found
    
    @patch("xbrl.requests.get")
    def test_fetch_cik_not_found(self, mock_get):
        """Test handling when ticker is not found."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc"},
        }
        mock_get.return_value = mock_response
        
        result = fetch_company_cik("INVALID")
        assert result is None
    
    @patch("xbrl.requests.get")
    def test_fetch_cik_network_error(self, mock_get):
        """Test handling of network errors."""
        mock_get.side_effect = Exception("Network error")
        
        with pytest.raises(Exception):
            fetch_company_cik("AAPL")


# ============================================================================
# Test Filing Index Retrieval
# ============================================================================

class TestFilingIndexRetrieval:
    """Test SEC filing index retrieval."""
    
    @patch("xbrl.requests.get")
    def test_fetch_10k_filing_index(self, mock_get):
        """Test fetching 10-K filing index."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "filings": {
                "recent": {
                    "form": ["10-K", "10-Q", "8-K"],
                    "accessionNumber": ["0000320193-24-000012", "0000320193-24-000008", "0000320193-24-000005"],
                    "filingDate": ["2024-01-15", "2023-10-15", "2023-08-20"],
                    "reportDate": ["2023-12-31", "2023-09-30", "2023-08-15"],
                    "primaryDocument": ["aapl-20231231.htm", "aapl-20230930.htm", "aapl-20230815.htm"],
                }
            }
        }
        mock_get.return_value = mock_response
        
        result = fetch_sec_filing_index("0000320193", "10-K")
        
        assert result is not None
        assert result["filing_type"] == "10-K"
        assert result["accession_number"] == "0000320193-24-000012"
        assert result["filing_date"] == "2024-01-15"
    
    @patch("xbrl.requests.get")
    def test_fetch_10q_filing_index(self, mock_get):
        """Test fetching 10-Q filing index."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "filings": {
                "recent": {
                    "form": ["10-Q", "10-K", "8-K"],
                    "accessionNumber": ["0000320193-24-000008", "0000320193-23-000065", "0000320193-24-000005"],
                    "filingDate": ["2023-10-15", "2023-01-20", "2023-08-20"],
                    "reportDate": ["2023-09-30", "2022-12-31", "2023-08-15"],
                }
            }
        }
        mock_get.return_value = mock_response
        
        result = fetch_sec_filing_index("0000320193", "10-Q")
        
        assert result is not None
        assert result["filing_type"] == "10-Q"
        assert result["accession_number"] == "0000320193-24-000008"
    
    @patch("xbrl.requests.get")
    def test_fetch_filing_not_found(self, mock_get):
        """Test handling when filing type is not found."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "filings": {
                "recent": {
                    "form": ["8-K", "8-K"],
                    "accessionNumber": ["acc1", "acc2"],
                    "filingDate": ["2024-01-15", "2024-01-10"],
                }
            }
        }
        mock_get.return_value = mock_response
        
        result = fetch_sec_filing_index("0000320193", "10-K")
        
        assert result is None
    
    @patch("xbrl.requests.get")
    def test_fetch_filing_empty_data(self, mock_get):
        """Test handling when SEC returns empty filings."""
        mock_response = Mock()
        mock_response.json.return_value = {"filings": {}}
        mock_get.return_value = mock_response
        
        result = fetch_sec_filing_index("0000320193", "10-K")
        
        assert result is None


# ============================================================================
# Test XBRL Document Parsing
# ============================================================================

class TestXBRLParsing:
    """Test XBRL document parsing and data extraction."""
    
    def test_parse_xbrl_valid_data(self):
        """Test parsing valid XBRL data."""
        xbrl_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <xbrli:xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance" xmlns:us-gaap="http://xbrl.us/us-gaap/2023-01-31">
            <us-gaap:Revenues contextRef="FY2023">394328000000</us-gaap:Revenues>
            <us-gaap:NetIncomeLoss contextRef="FY2023">96995000000</us-gaap:NetIncomeLoss>
            <us-gaap:Assets contextRef="FY2023">352755000000</us-gaap:Assets>
            <us-gaap:Liabilities contextRef="FY2023">120722000000</us-gaap:Liabilities>
            <us-gaap:StockholdersEquity contextRef="FY2023">63090000000</us-gaap:StockholdersEquity>
        </xbrli:xbrl>"""
        
        result = parse_xbrl_fundamentals(xbrl_xml, "AAPL")
        
        assert result["ticker"] == "AAPL"
        assert result["revenue"] == 394328000000
        assert result["net_income"] == 96995000000
        assert result["total_assets"] == 352755000000
        assert result["total_liabilities"] == 120722000000
        assert result["shareholders_equity"] == 63090000000
    
    def test_parse_xbrl_calculate_debt_to_equity(self):
        """Test calculation of debt-to-equity ratio."""
        xbrl_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <xbrli:xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance" xmlns:us-gaap="http://xbrl.us/us-gaap/2023-01-31">
            <us-gaap:Assets contextRef="FY2023">350000000000</us-gaap:Assets>
            <us-gaap:Liabilities contextRef="FY2023">100000000000</us-gaap:Liabilities>
        </xbrli:xbrl>"""
        
        result = parse_xbrl_fundamentals(xbrl_xml, "AAPL")
        
        # Debt-to-equity = 100B / (350B - 100B) = 100B / 250B = 0.4
        assert result["debt_to_equity"] == pytest.approx(0.4, rel=1e-5)
    
    def test_parse_xbrl_calculate_current_ratio(self):
        """Test calculation of current ratio."""
        xbrl_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <xbrli:xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance" xmlns:us-gaap="http://xbrl.us/us-gaap/2023-01-31">
            <us-gaap:CurrentAssets contextRef="FY2023">150000000000</us-gaap:CurrentAssets>
            <us-gaap:CurrentLiabilities contextRef="FY2023">100000000000</us-gaap:CurrentLiabilities>
        </xbrli:xbrl>"""
        
        result = parse_xbrl_fundamentals(xbrl_xml, "AAPL")
        
        # Current ratio = 150B / 100B = 1.5
        assert result["current_ratio"] == pytest.approx(1.5, rel=1e-5)
    
    def test_parse_xbrl_missing_data(self):
        """Test parsing XBRL with missing fields."""
        xbrl_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <xbrli:xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance" xmlns:us-gaap="http://xbrl.us/us-gaap/2023-01-31">
            <us-gaap:Revenues contextRef="FY2023">394328000000</us-gaap:Revenues>
        </xbrli:xbrl>"""
        
        result = parse_xbrl_fundamentals(xbrl_xml, "AAPL")
        
        assert result["ticker"] == "AAPL"
        assert result["revenue"] == 394328000000
        assert result["net_income"] is None
        assert result["total_assets"] is None
        assert result["timestamp"] is not None
    
    def test_parse_xbrl_invalid_xml(self):
        """Test handling of invalid XML."""
        xbrl_xml = "<invalid>not valid xml"
        
        result = parse_xbrl_fundamentals(xbrl_xml, "AAPL")
        
        assert result["ticker"] == "AAPL"
        # Should return defaults for all fields
        assert result["revenue"] is None
        assert result["net_income"] is None
    
    def test_parse_xbrl_empty_data(self):
        """Test parsing with no XBRL data."""
        result = parse_xbrl_fundamentals(None, "AAPL")
        
        assert result["ticker"] == "AAPL"
        assert result["revenue"] is None
        assert result["net_income"] is None


# ============================================================================
# Test Parquet Storage
# ============================================================================

class TestParquetStorage:
    """Test saving XBRL data to Parquet format."""
    
    def test_save_xbrl_to_parquet(self, tmp_path):
        """Test saving XBRL data to Parquet."""
        xbrl_data = [
            {
                "ticker": "AAPL",
                "revenue": 394328000000,
                "net_income": 96995000000,
                "total_assets": 352755000000,
                "total_liabilities": 120722000000,
                "shareholders_equity": 63090000000,
                "current_ratio": 1.5,
                "debt_to_equity": 0.4,
            },
            {
                "ticker": "MSFT",
                "revenue": 211915000000,
                "net_income": 72361000000,
                "total_assets": 411975000000,
                "total_liabilities": 216406000000,
                "shareholders_equity": 195569000000,
                "current_ratio": 1.8,
                "debt_to_equity": 1.1,
            },
        ]
        
        output_dir = str(tmp_path)
        file_path = save_xbrl_data_to_parquet(xbrl_data, output_dir)
        
        assert file_path.startswith(output_dir)
        assert file_path.endswith(".parquet")
        
        # Verify data can be read back
        df = pd.read_parquet(file_path)
        assert len(df) == 2
        assert list(df["ticker"]) == ["AAPL", "MSFT"]
        assert df.loc[df["ticker"] == "AAPL", "revenue"].values[0] == 394328000000
    
    def test_save_multiple_xbrl_records(self, tmp_path):
        """Test saving multiple XBRL records with validation."""
        xbrl_data = [
            {"ticker": "AAPL", "revenue": 394328000000, "net_income": 96995000000},
            {"ticker": "MSFT", "revenue": 211915000000, "net_income": 72361000000},
            {"ticker": "GOOGL", "revenue": 307394000000, "net_income": 59972000000},
        ]
        
        output_dir = str(tmp_path)
        file_path = save_xbrl_data_to_parquet(xbrl_data, output_dir)
        
        df = pd.read_parquet(file_path)
        
        assert len(df) == 3
        assert df["revenue"].sum() == 394328000000 + 211915000000 + 307394000000
        assert df["net_income"].sum() == 96995000000 + 72361000000 + 59972000000
    
    def test_save_xbrl_compression(self, tmp_path):
        """Test that Parquet is compressed."""
        xbrl_data = [
            {"ticker": "AAPL", "revenue": 394328000000, "net_income": 96995000000, "asset": 352755000000},
        ]
        
        output_dir = str(tmp_path)
        file_path = save_xbrl_data_to_parquet(xbrl_data, output_dir)
        
        # Parquet with Snappy compression should be reasonably small
        import os
        file_size = os.path.getsize(file_path)
        assert file_size < 10000  # Should be less than 10KB (metadata overhead)


# ============================================================================
# Integration Tests
# ============================================================================

class TestXBRLIntegration:
    """Integration tests for complete XBRL workflow."""
    
    def test_xbrl_data_structure_aapl(self):
        """Test XBRL data structure for AAPL."""
        xbrl_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <xbrli:xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance" xmlns:us-gaap="http://xbrl.us/us-gaap/2023-01-31">
            <us-gaap:Revenues contextRef="FY2023">394328000000</us-gaap:Revenues>
            <us-gaap:NetIncomeLoss contextRef="FY2023">96995000000</us-gaap:NetIncomeLoss>
            <us-gaap:Assets contextRef="FY2023">352755000000</us-gaap:Assets>
            <us-gaap:Liabilities contextRef="FY2023">120722000000</us-gaap:Liabilities>
            <us-gaap:StockholdersEquity contextRef="FY2023">63090000000</us-gaap:StockholdersEquity>
        </xbrli:xbrl>"""
        
        result = parse_xbrl_fundamentals(xbrl_xml, "AAPL")
        
        # Verify all required fields are present
        required_fields = [
            "ticker", "revenue", "net_income", "total_assets", 
            "total_liabilities", "shareholders_equity", "timestamp"
        ]
        for field in required_fields:
            assert field in result
        
        assert result["ticker"] == "AAPL"
    
    def test_xbrl_data_structure_msft(self):
        """Test XBRL data structure for MSFT."""
        xbrl_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <xbrli:xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance" xmlns:us-gaap="http://xbrl.us/us-gaap/2023-01-31">
            <us-gaap:Revenues contextRef="FY2023">211915000000</us-gaap:Revenues>
            <us-gaap:NetIncomeLoss contextRef="FY2023">72361000000</us-gaap:NetIncomeLoss>
            <us-gaap:Assets contextRef="FY2023">411975000000</us-gaap:Assets>
            <us-gaap:Liabilities contextRef="FY2023">216406000000</us-gaap:Liabilities>
            <us-gaap:StockholdersEquity contextRef="FY2023">195569000000</us-gaap:StockholdersEquity>
        </xbrli:xbrl>"""
        
        result = parse_xbrl_fundamentals(xbrl_xml, "MSFT")
        
        assert result["ticker"] == "MSFT"
        assert result["revenue"] == 211915000000
        assert result["net_income"] == 72361000000


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
