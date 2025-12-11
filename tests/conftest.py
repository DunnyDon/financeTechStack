"""
Pytest configuration and fixtures for Streamlit UI testing with Selenium.

Provides:
- WebDriver setup and teardown
- Streamlit app server fixtures
- Common page element selectors and helpers
- Test utilities for UI automation
"""

import os
import sys
import time
import subprocess
import pytest
from pathlib import Path
from typing import Generator, Optional
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class StreamlitTestConfig:
    """Configuration for Streamlit testing."""
    
    # Server settings
    STREAMLIT_HOST = "127.0.0.1"
    STREAMLIT_PORT = 8501
    STREAMLIT_BASE_URL = f"http://{STREAMLIT_HOST}:{STREAMLIT_PORT}"
    
    # Selenium settings
    HEADLESS = os.getenv("HEADLESS_BROWSER", "true").lower() == "true"
    BROWSER_WIDTH = 1920
    BROWSER_HEIGHT = 1080
    IMPLICIT_WAIT = 10
    EXPLICIT_WAIT = 20
    
    # Test data
    TEST_DATA_DIR = PROJECT_ROOT / "tests" / "test_data"
    SCREENSHOTS_DIR = PROJECT_ROOT / "tests" / "screenshots"
    REPORTS_DIR = PROJECT_ROOT / "tests" / "reports"
    
    # Timeouts
    APP_STARTUP_TIMEOUT = 30
    ELEMENT_TIMEOUT = 20
    CLICK_TIMEOUT = 5


class StreamlitTestBase:
    """Base class for Streamlit UI tests."""
    
    # Streamlit element selectors (common across all pages)
    class Selectors:
        """Common Streamlit element selectors."""
        SIDEBAR = "div[data-testid='stSidebar']"
        MAIN_CONTENT = "div[data-testid='stMainBlockContainer']"
        METRIC = "div[data-testid='metric-container']"
        BUTTON = "button"
        TEXT_INPUT = "input[type='text']"
        NUMBER_INPUT = "input[type='number']"
        SELECTBOX = "div[data-testid='stSelectbox']"
        SLIDER = "div[data-testid='stSlider']"
        RADIO = "div[data-testid='stRadio']"
        EXPANDER = "details"
        DATAFRAME = "table"
        SUCCESS_MESSAGE = "[data-testid='stSuccess']"
        ERROR_MESSAGE = "[data-testid='stError']"
        WARNING_MESSAGE = "[data-testid='stWarning']"
        INFO_MESSAGE = "[data-testid='stInfo']"
        
        # Options Strategy page specific
        STRATEGY_TYPE_SELECT = "select, [data-testid='stSelectbox']"
        RISK_TOLERANCE_SLIDER = "[data-testid='stSlider']"
        SYMBOL_INPUT = "input[placeholder*='Symbol']"
        CURRENT_PRICE_INPUT = "input[placeholder*='Current Price']"
        IV_PERCENTILE_SLIDER = "[data-testid='stSlider']"
        GENERATE_STRATEGY_BUTTON = "button:contains('Generate Strategy')"
        STRATEGY_DETAILS_TABLE = "table"
        PAYOFF_DIAGRAM = "canvas, [data-testid='plotly']"
        
        # Tax Optimization page specific
        TAX_CONFIG_SLIDERS = "[data-testid='stSlider']"
        TAX_FILING_STATUS = "[data-testid='stSelectbox']"
        CARRYFORWARD_INPUT = "input[type='number']"
        INPUT_METHOD_RADIO = "[data-testid='stRadio']"
        HOLDINGS_TABLE = "table"
        ANALYZE_TAX_BUTTON = "button:contains('Analyze Tax Opportunities')"
        OPPORTUNITY_EXPANDER = "details"
        HARVEST_BUTTON = "button:contains('Approve Harvest')"


@pytest.fixture(scope="session")
def streamlit_server() -> Generator[str, None, None]:
    """
    Start Streamlit server for testing.
    
    Yields:
        Base URL of the running Streamlit app
    """
    # Create necessary directories
    for dir_path in [StreamlitTestConfig.TEST_DATA_DIR, 
                     StreamlitTestConfig.SCREENSHOTS_DIR,
                     StreamlitTestConfig.REPORTS_DIR]:
        dir_path.mkdir(parents=True, exist_ok=True)
    
    # Check if server is already running
    try:
        import requests
        requests.get(StreamlitTestConfig.STREAMLIT_BASE_URL, timeout=2)
        print(f"Streamlit server already running at {StreamlitTestConfig.STREAMLIT_BASE_URL}")
        yield StreamlitTestConfig.STREAMLIT_BASE_URL
        return
    except:
        pass
    
    # Start Streamlit server
    print(f"Starting Streamlit server on {StreamlitTestConfig.STREAMLIT_HOST}:{StreamlitTestConfig.STREAMLIT_PORT}...")
    
    server_process = subprocess.Popen(
        [
            sys.executable, "-m", "streamlit", "run",
            str(PROJECT_ROOT / "app.py"),
            f"--server.port={StreamlitTestConfig.STREAMLIT_PORT}",
            f"--server.address={StreamlitTestConfig.STREAMLIT_HOST}",
            "--logger.level=error",
            "--client.showErrorDetails=false"
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(PROJECT_ROOT)
    )
    
    # Wait for server to start
    import requests
    start_time = time.time()
    while time.time() - start_time < StreamlitTestConfig.APP_STARTUP_TIMEOUT:
        try:
            response = requests.get(StreamlitTestConfig.STREAMLIT_BASE_URL, timeout=2)
            if response.status_code == 200:
                print("✅ Streamlit server ready")
                break
        except:
            time.sleep(0.5)
    else:
        server_process.terminate()
        raise TimeoutError(f"Streamlit server failed to start within {StreamlitTestConfig.APP_STARTUP_TIMEOUT} seconds")
    
    yield StreamlitTestConfig.STREAMLIT_BASE_URL
    
    # Cleanup
    print("Shutting down Streamlit server...")
    server_process.terminate()
    server_process.wait(timeout=5)


@pytest.fixture
def chrome_driver(streamlit_server: str) -> Generator[webdriver.Chrome, None, None]:
    """
    Create and configure Chrome WebDriver for testing.
    
    Args:
        streamlit_server: URL of running Streamlit server
    
    Yields:
        Configured Chrome WebDriver instance
    """
    options = ChromeOptions()
    
    if StreamlitTestConfig.HEADLESS:
        options.add_argument("--headless=new")
    
    options.add_argument(f"--window-size={StreamlitTestConfig.BROWSER_WIDTH},{StreamlitTestConfig.BROWSER_HEIGHT}")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-plugins")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    
    driver.implicitly_wait(StreamlitTestConfig.IMPLICIT_WAIT)
    
    yield driver
    
    driver.quit()


@pytest.fixture
def wait(chrome_driver: webdriver.Chrome) -> WebDriverWait:
    """
    Create explicit wait helper for elements.
    
    Args:
        chrome_driver: Chrome WebDriver instance
    
    Returns:
        Configured WebDriverWait instance
    """
    return WebDriverWait(chrome_driver, StreamlitTestConfig.EXPLICIT_WAIT)


@pytest.fixture
def page(chrome_driver: webdriver.Chrome, streamlit_server: str):
    """
    Navigate to home page before each test.
    
    Args:
        chrome_driver: Chrome WebDriver instance
        streamlit_server: Base URL of Streamlit app
    """
    chrome_driver.get(streamlit_server)
    time.sleep(2)  # Allow page to fully load
    return chrome_driver


class StreamlitPageActions:
    """Common Streamlit page action helpers."""
    
    def __init__(self, driver: webdriver.Chrome, wait: WebDriverWait):
        """
        Initialize page actions helper.
        
        Args:
            driver: Chrome WebDriver instance
            wait: WebDriverWait instance
        """
        self.driver = driver
        self.wait = wait
    
    def navigate_to_page(self, page_name: str) -> None:
        """
        Navigate to a page using sidebar menu.
        
        Args:
            page_name: Name of the page to navigate to
        """
        # Open sidebar if needed
        try:
            sidebar = self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, StreamlitTestBase.Selectors.SIDEBAR))
            )
        except:
            pass
        
        # Find and click menu item
        menu_items = self.driver.find_elements(By.XPATH, f"//button[contains(text(), '{page_name}')]")
        if menu_items:
            self.wait.until(EC.element_to_be_clickable(menu_items[0])).click()
            time.sleep(1)
        else:
            raise ValueError(f"Menu item '{page_name}' not found")
    
    def click_button(self, button_text: str) -> None:
        """
        Click a button by text.
        
        Args:
            button_text: Text of the button to click
        """
        buttons = self.driver.find_elements(By.XPATH, f"//button[contains(text(), '{button_text}')]")
        if buttons:
            self.wait.until(EC.element_to_be_clickable(buttons[0])).click()
        else:
            raise ValueError(f"Button '{button_text}' not found")
    
    def fill_text_input(self, label: str, text: str) -> None:
        """
        Fill a text input field.
        
        Args:
            label: Label of the input field
            text: Text to enter
        """
        inputs = self.driver.find_elements(By.XPATH, f"//label[contains(text(), '{label}')]/..//input")
        if inputs:
            input_field = self.wait.until(EC.presence_of_element_located((By.XPATH, f"//label[contains(text(), '{label}')]/..//input")))
            input_field.clear()
            input_field.send_keys(text)
        else:
            raise ValueError(f"Input field with label '{label}' not found")
    
    def select_dropdown_option(self, label: str, option: str) -> None:
        """
        Select an option from dropdown.
        
        Args:
            label: Label of the dropdown
            option: Option text to select
        """
        try:
            # Click to open dropdown
            dropdown = self.driver.find_element(By.XPATH, f"//label[contains(text(), '{label}')]/..//div[@role='button']")
            self.wait.until(EC.element_to_be_clickable(dropdown)).click()
            time.sleep(0.5)
            
            # Click option
            options = self.driver.find_elements(By.XPATH, f"//div[@role='option'][contains(text(), '{option}')]")
            if options:
                self.wait.until(EC.element_to_be_clickable(options[0])).click()
            else:
                raise ValueError(f"Option '{option}' not found in dropdown")
        except Exception as e:
            raise ValueError(f"Failed to select option '{option}' from dropdown '{label}': {e}")
    
    def set_slider_value(self, label: str, value: int) -> None:
        """
        Set slider to specific value.
        
        Args:
            label: Label of the slider
            value: Value to set (0-100)
        """
        try:
            # Find slider container
            slider_container = self.driver.find_element(By.XPATH, f"//label[contains(text(), '{label}')]/../div")
            
            # Find the slider input
            slider_input = slider_container.find_element(By.CSS_SELECTOR, "input[type='range']")
            
            # Set value
            self.driver.execute_script(
                f"arguments[0].value = {value}; arguments[0].dispatchEvent(new Event('change', {{ bubbles: true }}))",
                slider_input
            )
            time.sleep(0.5)
        except Exception as e:
            raise ValueError(f"Failed to set slider '{label}' to {value}: {e}")
    
    def get_metric_value(self, metric_label: str) -> str:
        """
        Get the value of a metric.
        
        Args:
            metric_label: Label of the metric
        
        Returns:
            Metric value as string
        """
        try:
            metric = self.driver.find_element(By.XPATH, f"//*[contains(text(), '{metric_label}')]/../following-sibling::*")
            return metric.text
        except:
            raise ValueError(f"Metric '{metric_label}' not found")
    
    def wait_for_element(self, css_selector: str, timeout: Optional[int] = None) -> None:
        """
        Wait for element to be present.
        
        Args:
            css_selector: CSS selector of element
            timeout: Timeout in seconds (uses default if None)
        """
        if timeout is None:
            timeout = StreamlitTestConfig.ELEMENT_TIMEOUT
        
        WebDriverWait(self.driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, css_selector))
        )
    
    def screenshot(self, name: str) -> str:
        """
        Take a screenshot of current page.
        
        Args:
            name: Name for the screenshot file
        
        Returns:
            Path to saved screenshot
        """
        filename = f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        filepath = StreamlitTestConfig.SCREENSHOTS_DIR / filename
        self.driver.save_screenshot(str(filepath))
        return str(filepath)
    
    def get_page_source(self) -> str:
        """
        Get current page HTML source.
        
        Returns:
            Page HTML source
        """
        return self.driver.page_source


@pytest.fixture
def page_actions(chrome_driver: webdriver.Chrome, wait: WebDriverWait) -> StreamlitPageActions:
    """
    Create page actions helper for test.
    
    Args:
        chrome_driver: Chrome WebDriver instance
        wait: WebDriverWait instance
    
    Returns:
        StreamlitPageActions instance
    """
    return StreamlitPageActions(chrome_driver, wait)
