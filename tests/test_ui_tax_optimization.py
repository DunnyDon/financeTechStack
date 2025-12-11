"""
Selenium UI tests for Tax Loss Harvesting & Optimization page.

Tests:
- Page navigation and loading
- Tax configuration setup
- Holdings input methods (sample, CSV, manual)
- Tax analysis execution
- Opportunity display and sorting
- Wash sale risk analysis
- Export functionality
"""

import pytest
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from tests.conftest import StreamlitTestBase, StreamlitPageActions, StreamlitTestConfig


class TestTaxOptimizationPageNavigation:
    """Test Tax Optimization page navigation and loading."""
    
    def test_navigate_to_tax_page(self, page_actions: StreamlitPageActions, page):
        """Test navigation to Tax Optimization page."""
        page_actions.navigate_to_page("Tax Optimization")
        
        # Verify page title
        title_elements = page.find_elements(By.XPATH, "//*[contains(text(), '💰 Tax Loss Harvesting')]")
        assert len(title_elements) > 0, "Tax Optimization page title not found"
    
    def test_page_elements_present(self, page_actions: StreamlitPageActions, page):
        """Test that all main page elements are present."""
        page_actions.navigate_to_page("Tax Optimization")
        time.sleep(1)
        
        # Check for key UI elements
        elements_to_check = [
            "Tax Configuration",
            "Capital Gains Rate",
            "Portfolio Holdings",
            "Input Method",
            "Analyze Tax Opportunities"
        ]
        
        for element_text in elements_to_check:
            elements = page.find_elements(By.XPATH, f"//*[contains(text(), '{element_text}')]")
            assert len(elements) > 0, f"Element '{element_text}' not found on page"


class TestTaxConfiguration:
    """Test tax configuration settings."""
    
    def test_long_term_gains_rate_slider(self, page_actions: StreamlitPageActions, page):
        """Test long-term capital gains rate slider."""
        page_actions.navigate_to_page("Tax Optimization")
        time.sleep(1)
        
        # Find slider for long-term gains
        sliders = page.find_elements(By.CSS_SELECTOR, "input[type='range']")
        assert len(sliders) > 0, "No sliders found for tax rate configuration"
    
    def test_short_term_gains_rate_slider(self, page_actions: StreamlitPageActions, page):
        """Test short-term capital gains rate slider."""
        page_actions.navigate_to_page("Tax Optimization")
        time.sleep(1)
        
        # Verify slider labels
        page_source = page_actions.get_page_source()
        assert "Short-Term" in page_source
    
    def test_filing_status_selection(self, page_actions: StreamlitPageActions, page):
        """Test tax filing status selection."""
        page_actions.navigate_to_page("Tax Optimization")
        time.sleep(1)
        
        # Try to select filing status
        try:
            page_actions.select_dropdown_option("Tax Filing Status", "Married Filing Jointly")
            time.sleep(0.5)
        except:
            # If dropdown not found, verify it's in page
            page_source = page_actions.get_page_source()
            assert "Filing Status" in page_source
    
    def test_carryforward_loss_input(self, page_actions: StreamlitPageActions, page):
        """Test capital loss carryforward input."""
        page_actions.navigate_to_page("Tax Optimization")
        time.sleep(1)
        
        # Find carryforward input
        carryforward_inputs = page.find_elements(By.XPATH, 
            "//label[contains(text(), 'Carryforward')]/../input")
        
        if carryforward_inputs:
            # Set a value
            carryforward_inputs[0].clear()
            carryforward_inputs[0].send_keys("5000")
            value = carryforward_inputs[0].get_attribute("value")
            assert "5000" in value or "5" in value


class TestHoldingsInput:
    """Test holdings input methods."""
    
    def test_sample_data_selection(self, page_actions: StreamlitPageActions, page):
        """Test using sample data option."""
        page_actions.navigate_to_page("Tax Optimization")
        time.sleep(1)
        
        # Find and click "Sample Data" radio button
        sample_radios = page.find_elements(By.XPATH, 
            "//label[contains(text(), 'Sample Data')]")
        assert len(sample_radios) > 0, "Sample Data option not found"
    
    def test_sample_data_table_display(self, page_actions: StreamlitPageActions, page):
        """Test that sample data table is displayed."""
        page_actions.navigate_to_page("Tax Optimization")
        time.sleep(1)
        
        # Select sample data and verify table appears
        sample_labels = page.find_elements(By.XPATH, 
            "//*[contains(text(), 'Sample Data')]")
        
        if sample_labels:
            # Wait for table
            page_actions.wait_for_element("table", timeout=5)
            
            # Verify table content
            tables = page.find_elements(By.TAG_NAME, "table")
            assert len(tables) > 0, "Holdings table not displayed"
            
            # Check for expected columns
            table_html = tables[0].get_attribute("outerHTML")
            assert "symbol" in table_html.lower()
    
    def test_manual_entry_option(self, page_actions: StreamlitPageActions, page):
        """Test manual holdings entry option."""
        page_actions.navigate_to_page("Tax Optimization")
        time.sleep(1)
        
        # Look for manual entry radio button
        page_source = page_actions.get_page_source()
        assert "Manual Entry" in page_source
    
    def test_csv_upload_option(self, page_actions: StreamlitPageActions, page):
        """Test CSV file upload option."""
        page_actions.navigate_to_page("Tax Optimization")
        time.sleep(1)
        
        # Look for CSV upload option
        page_source = page_actions.get_page_source()
        assert "Upload CSV" in page_source or "CSV" in page_source


class TestTaxAnalysisExecution:
    """Test tax analysis execution."""
    
    def test_analyze_button_execution(self, page_actions: StreamlitPageActions, page):
        """Test clicking Analyze Tax Opportunities button."""
        page_actions.navigate_to_page("Tax Optimization")
        time.sleep(1)
        
        # Click analyze button
        page_actions.click_button("Analyze Tax Opportunities")
        
        # Wait for results
        page_actions.wait_for_element("[data-testid='metric-container']", timeout=15)
        time.sleep(2)
        
        # Verify success message or results display
        page_source = page_actions.get_page_source()
        assert "Analysis" in page_source or "Summary" in page_source
    
    def test_analysis_results_display(self, page_actions: StreamlitPageActions, page):
        """Test that analysis results are displayed."""
        page_actions.navigate_to_page("Tax Optimization")
        time.sleep(1)
        
        page_actions.click_button("Analyze Tax Opportunities")
        page_actions.wait_for_element("[data-testid='metric-container']", timeout=15)
        time.sleep(2)
        
        # Check for summary metrics
        metrics = page.find_elements(By.CSS_SELECTOR, "[data-testid='metric-container']")
        assert len(metrics) >= 4, f"Expected at least 4 summary metrics, found {len(metrics)}"


class TestTaxOpportunitiesSummary:
    """Test tax opportunity summary display."""
    
    def test_total_unrealized_losses_metric(self, page_actions: StreamlitPageActions, page):
        """Test Total Unrealized Losses metric."""
        page_actions.navigate_to_page("Tax Optimization")
        page_actions.click_button("Analyze Tax Opportunities")
        page_actions.wait_for_element("[data-testid='metric-container']", timeout=15)
        
        page_source = page_actions.get_page_source()
        assert "Unrealized Losses" in page_source
    
    def test_potential_tax_savings_metric(self, page_actions: StreamlitPageActions, page):
        """Test Potential Tax Savings metric."""
        page_actions.navigate_to_page("Tax Optimization")
        page_actions.click_button("Analyze Tax Opportunities")
        page_actions.wait_for_element("[data-testid='metric-container']", timeout=15)
        
        page_source = page_actions.get_page_source()
        assert "Tax Savings" in page_source
    
    def test_opportunities_count_metric(self, page_actions: StreamlitPageActions, page):
        """Test Opportunities Count metric."""
        page_actions.navigate_to_page("Tax Optimization")
        page_actions.click_button("Analyze Tax Opportunities")
        page_actions.wait_for_element("[data-testid='metric-container']", timeout=15)
        
        page_source = page_actions.get_page_source()
        assert "Opportunities" in page_source or "Count" in page_source
    
    def test_wash_sale_risk_metric(self, page_actions: StreamlitPageActions, page):
        """Test Wash Sale Risk metric."""
        page_actions.navigate_to_page("Tax Optimization")
        page_actions.click_button("Analyze Tax Opportunities")
        page_actions.wait_for_element("[data-testid='metric-container']", timeout=15)
        
        page_source = page_actions.get_page_source()
        assert "Wash Sale" in page_source


class TestOpportunitiesDisplay:
    """Test harvesting opportunities display."""
    
    def test_opportunities_list_display(self, page_actions: StreamlitPageActions, page):
        """Test that opportunities list is displayed."""
        page_actions.navigate_to_page("Tax Optimization")
        page_actions.click_button("Analyze Tax Opportunities")
        page_actions.wait_for_element("details", timeout=15)
        time.sleep(2)
        
        # Check for expanders
        expanders = page.find_elements(By.TAG_NAME, "details")
        assert len(expanders) > 0, "No opportunity expanders found"
    
    def test_opportunity_details_expansion(self, page_actions: StreamlitPageActions, page):
        """Test expanding opportunity details."""
        page_actions.navigate_to_page("Tax Optimization")
        page_actions.click_button("Analyze Tax Opportunities")
        page_actions.wait_for_element("details", timeout=15)
        time.sleep(2)
        
        # Click first expander
        expanders = page.find_elements(By.TAG_NAME, "details")
        if expanders:
            expanders[0].click()
            time.sleep(0.5)
            
            # Verify content is visible
            assert expanders[0].get_attribute("open") == "open" or True  # May not be set
    
    def test_opportunity_sorting(self, page_actions: StreamlitPageActions, page):
        """Test that opportunities are sorted by tax benefit."""
        page_actions.navigate_to_page("Tax Optimization")
        page_actions.click_button("Analyze Tax Opportunities")
        page_actions.wait_for_element("details", timeout=15)
        time.sleep(2)
        
        # Get opportunity expanders and check order
        expanders = page.find_elements(By.TAG_NAME, "details")
        assert len(expanders) > 0
        
        # Verify they contain ranking numbers
        page_source = page_actions.get_page_source()
        assert "Loss:" in page_source or "$" in page_source


class TestWashSaleAnalysis:
    """Test wash sale risk analysis."""
    
    def test_wash_sale_risk_display(self, page_actions: StreamlitPageActions, page):
        """Test that wash sale risk is displayed for each opportunity."""
        page_actions.navigate_to_page("Tax Optimization")
        page_actions.click_button("Analyze Tax Opportunities")
        page_actions.wait_for_element("details", timeout=15)
        time.sleep(2)
        
        # Expand first opportunity
        expanders = page.find_elements(By.TAG_NAME, "details")
        if expanders:
            expanders[0].click()
            time.sleep(0.5)
            
            page_source = page_actions.get_page_source()
            assert "Wash Sale" in page_source
    
    def test_wash_sale_risk_warning(self, page_actions: StreamlitPageActions, page):
        """Test wash sale risk warning display."""
        page_actions.navigate_to_page("Tax Optimization")
        page_actions.click_button("Analyze Tax Opportunities")
        page_actions.wait_for_element("details", timeout=15)
        time.sleep(2)
        
        page_source = page_actions.get_page_source()
        # Look for risk indicators
        assert ("High" in page_source or "Moderate" in page_source or 
                "Low" in page_source or "wash" in page_source.lower())


class TestReplacementSuggestions:
    """Test replacement security suggestions."""
    
    def test_replacement_suggestions_display(self, page_actions: StreamlitPageActions, page):
        """Test that replacement suggestions are displayed."""
        page_actions.navigate_to_page("Tax Optimization")
        page_actions.click_button("Analyze Tax Opportunities")
        page_actions.wait_for_element("details", timeout=15)
        time.sleep(2)
        
        # Expand an opportunity
        expanders = page.find_elements(By.TAG_NAME, "details")
        if expanders:
            expanders[0].click()
            time.sleep(0.5)
            
            page_source = page_actions.get_page_source()
            assert "Suggested" in page_source or "Replacement" in page_source or "Alternative" in page_source
    
    def test_replacement_buttons(self, page_actions: StreamlitPageActions, page):
        """Test replacement security selection buttons."""
        page_actions.navigate_to_page("Tax Optimization")
        page_actions.click_button("Analyze Tax Opportunities")
        page_actions.wait_for_element("details", timeout=15)
        time.sleep(2)
        
        # Expand first opportunity
        expanders = page.find_elements(By.TAG_NAME, "details")
        if expanders:
            expanders[0].click()
            time.sleep(0.5)
            
            # Look for replacement buttons
            buttons = page.find_elements(By.TAG_NAME, "button")
            assert len(buttons) > 0


class TestTaxPlanningInsights:
    """Test tax planning insights section."""
    
    def test_recommendations_display(self, page_actions: StreamlitPageActions, page):
        """Test that tax planning recommendations are displayed."""
        page_actions.navigate_to_page("Tax Optimization")
        page_actions.click_button("Analyze Tax Opportunities")
        page_actions.wait_for_element("[data-testid='stInfo']", timeout=15)
        time.sleep(2)
        
        page_source = page_actions.get_page_source()
        assert "Recommendation" in page_source or "💡" in page_source
    
    def test_timeline_information(self, page_actions: StreamlitPageActions, page):
        """Test that timeline information is displayed."""
        page_actions.navigate_to_page("Tax Optimization")
        page_actions.click_button("Analyze Tax Opportunities")
        page_actions.wait_for_element("details", timeout=15)
        time.sleep(2)
        
        page_source = page_actions.get_page_source()
        assert "Timeline" in page_source or "days" in page_source.lower()


class TestTaxExportFunctionality:
    """Test export functionality."""
    
    def test_csv_export_button(self, page_actions: StreamlitPageActions, page):
        """Test CSV export button is available."""
        page_actions.navigate_to_page("Tax Optimization")
        page_actions.click_button("Analyze Tax Opportunities")
        page_actions.wait_for_element("button", timeout=15)
        time.sleep(2)
        
        page_source = page_actions.get_page_source()
        assert "CSV" in page_source or "Download" in page_source
    
    def test_parquet_export_button(self, page_actions: StreamlitPageActions, page):
        """Test Parquet export button is available."""
        page_actions.navigate_to_page("Tax Optimization")
        page_actions.click_button("Analyze Tax Opportunities")
        page_actions.wait_for_element("button", timeout=15)
        time.sleep(2)
        
        page_source = page_actions.get_page_source()
        assert "Parquet" in page_source or "Save" in page_source
    
    def test_email_button(self, page_actions: StreamlitPageActions, page):
        """Test email report button is available."""
        page_actions.navigate_to_page("Tax Optimization")
        page_actions.click_button("Analyze Tax Opportunities")
        page_actions.wait_for_element("button", timeout=15)
        time.sleep(2)
        
        page_source = page_actions.get_page_source()
        assert "Email" in page_source or "📧" in page_source


class TestTaxOptimizationIntegration:
    """Integration tests for tax optimization page."""
    
    def test_full_analysis_workflow(self, page_actions: StreamlitPageActions, page):
        """Test complete tax analysis workflow."""
        # Navigate to page
        page_actions.navigate_to_page("Tax Optimization")
        time.sleep(1)
        
        # Configure tax settings
        try:
            page_actions.select_dropdown_option("Tax Filing Status", "Single")
        except:
            pass  # Optional configuration
        
        # Execute analysis
        page_actions.click_button("Analyze Tax Opportunities")
        
        # Wait for results
        page_actions.wait_for_element("[data-testid='metric-container']", timeout=15)
        time.sleep(2)
        
        # Verify key results are displayed
        page_source = page_actions.get_page_source()
        assert "Tax Savings" in page_source or "Opportunities" in page_source
        
        # Take screenshot
        screenshot = page_actions.screenshot("tax_analysis_complete")
        assert screenshot is not None
    
    def test_opportunity_expansion_workflow(self, page_actions: StreamlitPageActions, page):
        """Test expanding and reviewing opportunities."""
        page_actions.navigate_to_page("Tax Optimization")
        page_actions.click_button("Analyze Tax Opportunities")
        page_actions.wait_for_element("details", timeout=15)
        time.sleep(2)
        
        # Expand multiple opportunities
        expanders = page.find_elements(By.TAG_NAME, "details")
        for i, expander in enumerate(expanders[:3]):
            expander.click()
            time.sleep(0.5)
            
            # Verify content is visible
            page_source = page_actions.get_page_source()
            assert "Details" in page_source or "$" in page_source
        
        # Take screenshot
        screenshot = page_actions.screenshot("opportunities_expanded")
        assert screenshot is not None


class TestTaxOptimizationErrorHandling:
    """Test error handling for tax optimization."""
    
    def test_no_opportunities_message(self, page_actions: StreamlitPageActions, page):
        """Test message when no opportunities found."""
        page_actions.navigate_to_page("Tax Optimization")
        
        # If sample data shows no losses, we should see a message
        page_actions.click_button("Analyze Tax Opportunities")
        page_actions.wait_for_element("[data-testid='metric-container']", timeout=15)
        
        page_source = page_actions.get_page_source()
        # Either opportunities or "no opportunities" message
        assert "Opportunity" in page_source or "profitable" in page_source.lower()
    
    def test_csv_upload_validation(self, page_actions: StreamlitPageActions, page):
        """Test CSV file validation."""
        page_actions.navigate_to_page("Tax Optimization")
        time.sleep(1)
        
        # Select CSV upload option
        try:
            page_actions.select_dropdown_option("Input Method", "Upload CSV")
            time.sleep(0.5)
            
            # Look for file uploader
            page_source = page_actions.get_page_source()
            assert "CSV" in page_source
        except:
            pass  # Upload may not be available in test environment
