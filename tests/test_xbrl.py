"""
Unit tests for XBRL data extraction module.
Tests CIK lookup, filing retrieval, XBRL parsing, and data storage.

Note: Tests for fetch_company_cik and fetch_sec_filing_index that require
network mocking are handled in test_sec_scraper.py. These tests focus on
XBRL parsing and data storage which can be tested with mock data.
"""

import pytest
import pandas as pd
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import xml.etree.ElementTree as ET
from pathlib import Path
import sys

# Add parent directory to path to enable package imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.xbrl import (
    fetch_company_cik,
    fetch_sec_filing_index,
    fetch_xbrl_document,
    parse_xbrl_fundamentals,
    save_xbrl_data_to_parquet,
)


# ============================================================================
# Test CIK Extraction (skipped - see test_sec_scraper.py for proper mocking)
# ============================================================================

class TestCIKExtraction:
    """Test CIK (Central Index Key) extraction from SEC data."""
    
    @pytest.mark.skip(reason="Network mocking for Prefect tasks - see test_sec_scraper.py")
    @patch("src.xbrl.requests.get")
    def test_fetch_cik_aapl(self, mock_get):
        """Test fetching CIK for Apple (AAPL)."""
        pass
    
    @pytest.mark.skip(reason="Network mocking for Prefect tasks - see test_sec_scraper.py")
    @patch("src.xbrl.requests.get")
    def test_fetch_cik_msft(self, mock_get):
        """Test fetching CIK for Microsoft (MSFT)."""
        pass
    
    @pytest.mark.skip(reason="Network mocking for Prefect tasks - see test_sec_scraper.py")
    @patch("src.xbrl.requests.get")
    def test_fetch_cik_case_insensitive(self, mock_get):
        """Test CIK lookup is case-insensitive."""
        pass
    
    @pytest.mark.skip(reason="Network mocking for Prefect tasks - see test_sec_scraper.py")
    @patch("src.xbrl.requests.get")
    def test_fetch_cik_not_found(self, mock_get):
        """Test handling when ticker is not found."""
        pass
    
    @pytest.mark.skip(reason="Network mocking for Prefect tasks - see test_sec_scraper.py")
    @patch("src.xbrl.requests.get")
    def test_fetch_cik_network_error(self, mock_get):
        """Test handling of network errors."""
        pass


# ============================================================================
# Test Filing Index Retrieval (skipped - see test_sec_scraper.py)
# ============================================================================

class TestFilingIndexRetrieval:
    """Test SEC filing index retrieval."""
    
    @pytest.mark.skip(reason="Network mocking for Prefect tasks - see test_sec_scraper.py")
    @patch("src.xbrl.requests.get")
    def test_fetch_10k_filing_index(self, mock_get):
        """Test fetching 10-K filing index."""
        pass
    
    @pytest.mark.skip(reason="Network mocking for Prefect tasks - see test_sec_scraper.py")
    @patch("src.xbrl.requests.get")
    def test_fetch_10q_filing_index(self, mock_get):
        """Test fetching 10-Q filing index."""
        pass
    
    @pytest.mark.skip(reason="Network mocking for Prefect tasks - see test_sec_scraper.py")
    @patch("src.xbrl.requests.get")
    def test_fetch_filing_not_found(self, mock_get):
        """Test handling when filing type is not found."""
        pass
    
    @pytest.mark.skip(reason="Network mocking for Prefect tasks - see test_sec_scraper.py")
    @patch("src.xbrl.requests.get")
    def test_fetch_filing_empty_data(self, mock_get):
        """Test handling when SEC returns empty filings."""
        pass


# ============================================================================
# Test XBRL Document Parsing (Unit tests for parser)
# ============================================================================

class TestXBRLParsing:
    """Test XBRL document parsing and data extraction."""
    
    def test_parse_xbrl_valid_data(self):
        """Test parsing valid XBRL data from SEC JSON API."""
        # SEC returns JSON with facts structure
        xbrl_data = {
            "facts": {
                "us-gaap": {
                    "Revenues": {
                        "units": {
                            "USD": [
                                {"val": 394328000000, "filed": "2024-01-30"}
                            ]
                        }
                    },
                    "NetIncomeLoss": {
                        "units": {
                            "USD": [
                                {"val": 96995000000, "filed": "2024-01-30"}
                            ]
                        }
                    },
                    "Assets": {
                        "units": {
                            "USD": [
                                {"val": 352755000000, "filed": "2024-01-30"}
                            ]
                        }
                    },
                    "Liabilities": {
                        "units": {
                            "USD": [
                                {"val": 120722000000, "filed": "2024-01-30"}
                            ]
                        }
                    },
                    "StockholdersEquity": {
                        "units": {
                            "USD": [
                                {"val": 231033000000, "filed": "2024-01-30"}
                            ]
                        }
                    },
                }
            }
        }
        
        result = parse_xbrl_fundamentals(xbrl_data, "AAPL")
        
        assert result["ticker"] == "AAPL"
        assert result["revenue"] == 394328000000
        assert result["net_income"] == 96995000000
        assert result["total_assets"] == 352755000000
        assert result["total_liabilities"] == 120722000000
        assert result["shareholders_equity"] == 231033000000
    
    def test_parse_xbrl_calculate_debt_to_equity(self):
        """Test calculation of debt-to-equity ratio."""
        xbrl_data = {
            "facts": {
                "us-gaap": {
                    "Assets": {
                        "units": {
                            "USD": [
                                {"val": 350000000000, "filed": "2024-01-30"}
                            ]
                        }
                    },
                    "Liabilities": {
                        "units": {
                            "USD": [
                                {"val": 100000000000, "filed": "2024-01-30"}
                            ]
                        }
                    },
                }
            }
        }
        
        result = parse_xbrl_fundamentals(xbrl_data, "AAPL")
        
        # Debt-to-equity = 100B / (350B - 100B) = 100B / 250B = 0.4
        assert result["debt_to_equity"] == pytest.approx(0.4, rel=1e-5)
    
    def test_parse_xbrl_calculate_current_ratio(self):
        """Test calculation of current ratio."""
        xbrl_data = {
            "facts": {
                "us-gaap": {
                    "CurrentAssets": {
                        "units": {
                            "USD": [
                                {"val": 150000000000, "filed": "2024-01-30"}
                            ]
                        }
                    },
                    "CurrentLiabilities": {
                        "units": {
                            "USD": [
                                {"val": 100000000000, "filed": "2024-01-30"}
                            ]
                        }
                    },
                }
            }
        }
        
        result = parse_xbrl_fundamentals(xbrl_data, "AAPL")
        
        # Current ratio = 150B / 100B = 1.5
        assert result["current_ratio"] == pytest.approx(1.5, rel=1e-5)
    
    def test_parse_xbrl_missing_data(self):
        """Test parsing XBRL with missing fields."""
        xbrl_data = {
            "facts": {
                "us-gaap": {
                    "Revenues": {
                        "units": {
                            "USD": [
                                {"val": 394328000000, "filed": "2024-01-30"}
                            ]
                        }
                    },
                }
            }
        }
        
        result = parse_xbrl_fundamentals(xbrl_data, "AAPL")
        
        assert result["ticker"] == "AAPL"
        assert result["revenue"] == 394328000000
        assert result["net_income"] is None
        assert result["total_assets"] is None
        assert result["timestamp"] is not None
    
    def test_parse_xbrl_invalid_xml(self):
        """Test handling of invalid data."""
        # Pass invalid data structure
        xbrl_data = {"invalid": "data"}
        
        result = parse_xbrl_fundamentals(xbrl_data, "AAPL")
        
        # Should return defaults, not raise an error
        assert result["ticker"] == "AAPL"
        assert result["revenue"] is None
    
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
        xbrl_data = {
            "facts": {
                "us-gaap": {
                    "Revenues": {
                        "units": {
                            "USD": [
                                {"val": 394328000000, "filed": "2024-01-30"}
                            ]
                        }
                    },
                    "NetIncomeLoss": {
                        "units": {
                            "USD": [
                                {"val": 96995000000, "filed": "2024-01-30"}
                            ]
                        }
                    },
                    "Assets": {
                        "units": {
                            "USD": [
                                {"val": 352755000000, "filed": "2024-01-30"}
                            ]
                        }
                    },
                    "Liabilities": {
                        "units": {
                            "USD": [
                                {"val": 120722000000, "filed": "2024-01-30"}
                            ]
                        }
                    },
                    "StockholdersEquity": {
                        "units": {
                            "USD": [
                                {"val": 231033000000, "filed": "2024-01-30"}
                            ]
                        }
                    },
                }
            }
        }
        
        result = parse_xbrl_fundamentals(xbrl_data, "AAPL")
        
        # Verify all required fields are present
        required_fields = [
            "ticker", "revenue", "net_income", "total_assets", 
            "total_liabilities", "shareholders_equity", "timestamp"
        ]
        for field in required_fields:
            assert field in result
        
        assert result["ticker"] == "AAPL"
        assert result["revenue"] == 394328000000
        assert result["net_income"] == 96995000000
    
    def test_xbrl_data_structure_msft(self):
        """Test XBRL data structure for MSFT."""
        xbrl_data = {
            "facts": {
                "us-gaap": {
                    "Revenues": {
                        "units": {
                            "USD": [
                                {"val": 211915000000, "filed": "2024-01-30"}
                            ]
                        }
                    },
                    "NetIncomeLoss": {
                        "units": {
                            "USD": [
                                {"val": 72361000000, "filed": "2024-01-30"}
                            ]
                        }
                    },
                    "Assets": {
                        "units": {
                            "USD": [
                                {"val": 411975000000, "filed": "2024-01-30"}
                            ]
                        }
                    },
                    "Liabilities": {
                        "units": {
                            "USD": [
                                {"val": 216406000000, "filed": "2024-01-30"}
                            ]
                        }
                    },
                    "StockholdersEquity": {
                        "units": {
                            "USD": [
                                {"val": 195569000000, "filed": "2024-01-30"}
                            ]
                        }
                    },
                }
            }
        }
        
        result = parse_xbrl_fundamentals(xbrl_data, "MSFT")
        
        assert result["ticker"] == "MSFT"
        assert result["revenue"] == 211915000000
        assert result["net_income"] == 72361000000


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
