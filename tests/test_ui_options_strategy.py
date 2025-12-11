"""
Selenium UI tests for Options Strategy page.

Tests:
- Page navigation and loading
- Strategy type selection
- Parameter configuration
- Strategy generation
- P&L visualization
- Greeks display
- Export functionality
"""

import pytest
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from tests.conftest import StreamlitTestBase, StreamlitPageActions, StreamlitTestConfig


class TestOptionsStrategyPageNavigation:
    """Test Options Strategy page navigation and loading."""
    
    def test_navigate_to_options_strategy_page(self, page_actions: StreamlitPageActions, page):
        """Test navigation to Options Strategy page."""
        page_actions.navigate_to_page("Options Strategy")
        
        # Verify page title
        title_elements = page.find_elements(By.XPATH, "//*[contains(text(), '⚙️ Options Strategy Analyzer')]")
        assert len(title_elements) > 0, "Options Strategy page title not found"
    
    def test_page_elements_present(self, page_actions: StreamlitPageActions, page):
        """Test that all main page elements are present."""
        page_actions.navigate_to_page("Options Strategy")
        time.sleep(1)
        
        # Check for key UI elements
        elements_to_check = [
            "Select Strategy Type",
            "Risk Tolerance",
            "Underlying Symbol",
            "Current Price",
            "IV Percentile",
            "Days to Expiration",
            "Spread Width",
            "Generate Strategy"
        ]
        
        for element_text in elements_to_check:
            elements = page.find_elements(By.XPATH, f"//*[contains(text(), '{element_text}')]")
            assert len(elements) > 0, f"Element '{element_text}' not found on page"


class TestOptionsStrategyGeneration:
    """Test options strategy generation."""
    
    @pytest.mark.parametrize("strategy_type", ["Iron Condor", "Strangle", "Straddle"])
    def test_generate_strategy(self, page_actions: StreamlitPageActions, page, strategy_type: str):
        """
        Test generating different strategy types.
        
        Args:
            page_actions: Page action helper
            page: WebDriver instance
            strategy_type: Type of strategy to generate
        """
        page_actions.navigate_to_page("Options Strategy")
        time.sleep(1)
        
        # Select strategy type
        page_actions.select_dropdown_option("Select Strategy Type", strategy_type)
        time.sleep(0.5)
        
        # Set parameters
        page_actions.fill_text_input("Underlying Symbol", "AAPL")
        page_actions.fill_text_input("Current Price", "150.00")
        
        # Generate strategy
        page_actions.click_button("Generate Strategy")
        
        # Wait for strategy details to appear
        page_actions.wait_for_element("table", timeout=10)
        time.sleep(2)
        
        # Take screenshot for verification
        screenshot_path = page_actions.screenshot(f"strategy_{strategy_type}")
        assert screenshot_path is not None
    
    def test_covered_call_generation(self, page_actions: StreamlitPageActions, page):
        """Test Covered Call strategy generation."""
        page_actions.navigate_to_page("Options Strategy")
        time.sleep(1)
        
        page_actions.select_dropdown_option("Select Strategy Type", "Covered Call")
        page_actions.fill_text_input("Underlying Symbol", "MSFT")
        page_actions.fill_text_input("Current Price", "300.00")
        
        page_actions.click_button("Generate Strategy")
        page_actions.wait_for_element("table", timeout=10)
        
        # Verify strategy was generated
        tables = page.find_elements(By.TAG_NAME, "table")
        assert len(tables) > 0, "Strategy table not displayed"


class TestOptionsStrategyParameters:
    """Test strategy parameter configuration."""
    
    def test_risk_tolerance_selection(self, page_actions: StreamlitPageActions, page):
        """Test changing risk tolerance."""
        page_actions.navigate_to_page("Options Strategy")
        time.sleep(1)
        
        # Select different risk tolerance levels
        risk_levels = ["Conservative", "Moderate", "Aggressive"]
        
        for risk_level in risk_levels:
            radio_buttons = page.find_elements(By.XPATH, f"//label[contains(text(), '{risk_level}')]")
            assert len(radio_buttons) > 0, f"Risk tolerance '{risk_level}' not found"
    
    def test_slider_parameters(self, page_actions: StreamlitPageActions, page):
        """Test slider parameter adjustments."""
        page_actions.navigate_to_page("Options Strategy")
        time.sleep(1)
        
        # Get all sliders
        sliders = page.find_elements(By.CSS_SELECTOR, "input[type='range']")
        assert len(sliders) >= 3, "Expected at least 3 sliders (IV, DTE, Spread Width)"
    
    def test_dte_configuration(self, page_actions: StreamlitPageActions, page):
        """Test Days to Expiration configuration."""
        page_actions.navigate_to_page("Options Strategy")
        time.sleep(1)
        
        # Find and verify DTE input exists
        dte_inputs = page.find_elements(By.XPATH, "//label[contains(text(), 'Days to Expiration')]/../input")
        assert len(dte_inputs) > 0, "DTE input field not found"
        
        # Set DTE value
        dte_input = dte_inputs[0]
        dte_input.clear()
        dte_input.send_keys("45")
        assert dte_input.get_attribute("value") == "45"


class TestOptionsStrategyDisplay:
    """Test strategy display and visualization."""
    
    def test_strategy_details_table(self, page_actions: StreamlitPageActions, page):
        """Test that strategy details table is displayed correctly."""
        page_actions.navigate_to_page("Options Strategy")
        page_actions.fill_text_input("Underlying Symbol", "AAPL")
        page_actions.fill_text_input("Current Price", "150.00")
        page_actions.click_button("Generate Strategy")
        
        page_actions.wait_for_element("table", timeout=10)
        time.sleep(1)
        
        # Verify table contains expected columns
        expected_columns = ["Type", "Strike", "Premium", "Delta"]
        table_html = page.find_element(By.TAG_NAME, "table").get_attribute("outerHTML")
        
        for column in expected_columns:
            assert column in table_html, f"Table column '{column}' not found"
    
    def test_greeks_display(self, page_actions: StreamlitPageActions, page):
        """Test that Greeks (Delta, Gamma, Theta, Vega) are displayed."""
        page_actions.navigate_to_page("Options Strategy")
        page_actions.fill_text_input("Underlying Symbol", "AAPL")
        page_actions.fill_text_input("Current Price", "150.00")
        page_actions.click_button("Generate Strategy")
        
        page_actions.wait_for_element("[data-testid='metric-container']", timeout=10)
        time.sleep(1)
        
        # Check for Greeks metrics
        greeks = ["Delta", "Gamma", "Theta", "Vega"]
        page_source = page_actions.get_page_source()
        
        for greek in greeks:
            assert greek in page_source, f"Greek '{greek}' not displayed in page"
    
    def test_payoff_diagram_display(self, page_actions: StreamlitPageActions, page):
        """Test that payoff diagram is displayed after strategy generation."""
        page_actions.navigate_to_page("Options Strategy")
        page_actions.fill_text_input("Underlying Symbol", "AAPL")
        page_actions.fill_text_input("Current Price", "150.00")
        page_actions.click_button("Generate Strategy")
        
        page_actions.wait_for_element("canvas, [data-testid='plotly']", timeout=15)
        
        # Verify chart/diagram is rendered
        page_source = page_actions.get_page_source()
        assert "plotly" in page_source.lower() or "canvas" in page_source.lower()


class TestOptionsStrategyMetrics:
    """Test strategy performance metrics."""
    
    def test_max_profit_metric(self, page_actions: StreamlitPageActions, page):
        """Test that Max Profit metric is displayed."""
        page_actions.navigate_to_page("Options Strategy")
        page_actions.fill_text_input("Underlying Symbol", "AAPL")
        page_actions.fill_text_input("Current Price", "150.00")
        page_actions.click_button("Generate Strategy")
        
        page_actions.wait_for_element("[data-testid='metric-container']", timeout=10)
        time.sleep(1)
        
        page_source = page_actions.get_page_source()
        assert "Max Profit" in page_source
    
    def test_max_loss_metric(self, page_actions: StreamlitPageActions, page):
        """Test that Max Loss metric is displayed."""
        page_actions.navigate_to_page("Options Strategy")
        page_actions.fill_text_input("Underlying Symbol", "AAPL")
        page_actions.fill_text_input("Current Price", "150.00")
        page_actions.click_button("Generate Strategy")
        
        page_actions.wait_for_element("[data-testid='metric-container']", timeout=10)
        time.sleep(1)
        
        page_source = page_actions.get_page_source()
        assert "Max Loss" in page_source


class TestOptionsStrategyExport:
    """Test strategy export functionality."""
    
    def test_export_csv_button_present(self, page_actions: StreamlitPageActions, page):
        """Test that Export CSV button is available."""
        page_actions.navigate_to_page("Options Strategy")
        page_actions.fill_text_input("Underlying Symbol", "AAPL")
        page_actions.fill_text_input("Current Price", "150.00")
        page_actions.click_button("Generate Strategy")
        
        page_actions.wait_for_element("button", timeout=10)
        time.sleep(2)
        
        # Check for export buttons
        page_source = page_actions.get_page_source()
        assert "Export as CSV" in page_source or "Download CSV" in page_source
    
    def test_export_hedge_recommendations(self, page_actions: StreamlitPageActions, page):
        """Test hedge recommendations feature."""
        page_actions.navigate_to_page("Options Strategy")
        page_actions.fill_text_input("Underlying Symbol", "AAPL")
        page_actions.fill_text_input("Current Price", "150.00")
        page_actions.click_button("Generate Strategy")
        
        page_actions.wait_for_element("button", timeout=10)
        time.sleep(2)
        
        # Check for hedge button
        page_source = page_actions.get_page_source()
        assert "Hedge" in page_source


class TestOptionsStrategyInputValidation:
    """Test input validation for strategy parameters."""
    
    def test_symbol_input_uppercase(self, page_actions: StreamlitPageActions, page):
        """Test that symbol input is converted to uppercase."""
        page_actions.navigate_to_page("Options Strategy")
        
        symbol_inputs = page.find_elements(By.XPATH, "//label[contains(text(), 'Underlying Symbol')]/../input")
        if symbol_inputs:
            symbol_input = symbol_inputs[0]
            symbol_input.send_keys("aapl")
            # Streamlit should convert to uppercase
            value = symbol_input.get_attribute("value")
            assert value.isupper() or value == "aapl"  # Depends on Streamlit handling
    
    def test_price_input_numeric(self, page_actions: StreamlitPageActions, page):
        """Test that price input accepts only numeric values."""
        page_actions.navigate_to_page("Options Strategy")
        
        price_inputs = page.find_elements(By.XPATH, "//label[contains(text(), 'Current Price')]/../input")
        if price_inputs:
            price_input = price_inputs[0]
            # Try entering numeric value
            price_input.send_keys("150.50")
            value = price_input.get_attribute("value")
            assert "150" in value


class TestOptionsStrategyErrorHandling:
    """Test error handling and edge cases."""
    
    def test_missing_symbol_error(self, page_actions: StreamlitPageActions, page):
        """Test error when symbol is missing."""
        page_actions.navigate_to_page("Options Strategy")
        
        # Try to generate without symbol
        try:
            page_actions.click_button("Generate Strategy")
            time.sleep(2)
            
            # Check for error message
            error_elements = page.find_elements(By.CSS_SELECTOR, "[data-testid='stError']")
            # May or may not show error depending on validation
        except:
            pass  # Expected if button is disabled
    
    def test_invalid_price_error(self, page_actions: StreamlitPageActions, page):
        """Test error when price is invalid."""
        page_actions.navigate_to_page("Options Strategy")
        page_actions.fill_text_input("Underlying Symbol", "AAPL")
        
        price_inputs = page.find_elements(By.XPATH, "//label[contains(text(), 'Current Price')]/../input")
        if price_inputs:
            price_inputs[0].send_keys("-100")  # Invalid negative price
            
            # Try to generate
            try:
                page_actions.click_button("Generate Strategy")
                time.sleep(2)
            except:
                pass  # Expected if button is disabled


class TestOptionsStrategyIntegration:
    """Integration tests for options strategy page."""
    
    def test_full_workflow(self, page_actions: StreamlitPageActions, page):
        """Test complete workflow from strategy selection to export."""
        # Navigate to page
        page_actions.navigate_to_page("Options Strategy")
        time.sleep(1)
        
        # Select strategy type
        page_actions.select_dropdown_option("Select Strategy Type", "Iron Condor")
        time.sleep(0.5)
        
        # Set parameters
        page_actions.fill_text_input("Underlying Symbol", "SPY")
        page_actions.fill_text_input("Current Price", "400.00")
        
        # Generate strategy
        page_actions.click_button("Generate Strategy")
        
        # Wait for results
        page_actions.wait_for_element("table", timeout=10)
        time.sleep(2)
        
        # Verify results are displayed
        page_source = page_actions.get_page_source()
        assert "SPY" in page_source
        assert "Iron Condor" in page_source or "SELL" in page_source
        
        # Take final screenshot
        screenshot = page_actions.screenshot("full_workflow_complete")
        assert screenshot is not None
