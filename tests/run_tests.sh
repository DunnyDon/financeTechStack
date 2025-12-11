#!/bin/bash
# Quick start script for Streamlit UI testing

set -e

echo "🧪 Streamlit UI Test Suite - Quick Start"
echo "=========================================="

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check Python
echo -e "${BLUE}Checking Python installation...${NC}"
python --version

# Check if venv exists and activate
if [ -d ".venv" ]; then
    echo -e "${BLUE}Activating virtual environment...${NC}"
    source .venv/bin/activate
fi

# Install test dependencies
echo -e "${BLUE}Installing test dependencies...${NC}"
pip install -q -r tests/requirements-test.txt

# Create test directories
echo -e "${BLUE}Creating test directories...${NC}"
mkdir -p tests/screenshots
mkdir -p tests/reports
mkdir -p tests/test_data

# Display options
echo ""
echo -e "${YELLOW}Select test mode:${NC}"
echo ""
echo "1) Run all tests (headless)"
echo "2) Run options strategy tests"
echo "3) Run tax optimization tests"
echo "4) Run all tests with UI (not headless)"
echo "5) Run tests with coverage report"
echo "6) Run specific test (enter test name)"
echo "7) Exit"
echo ""
read -p "Enter choice [1-7]: " choice

case $choice in
    1)
        echo -e "${BLUE}Running all tests in headless mode...${NC}"
        HEADLESS_BROWSER=true pytest tests/ -v
        ;;
    2)
        echo -e "${BLUE}Running Options Strategy tests...${NC}"
        HEADLESS_BROWSER=true pytest tests/test_ui_options_strategy.py -v
        ;;
    3)
        echo -e "${BLUE}Running Tax Optimization tests...${NC}"
        HEADLESS_BROWSER=true pytest tests/test_ui_tax_optimization.py -v
        ;;
    4)
        echo -e "${BLUE}Running tests with UI visible...${NC}"
        HEADLESS_BROWSER=false pytest tests/ -v -s
        ;;
    5)
        echo -e "${BLUE}Running tests with coverage...${NC}"
        HEADLESS_BROWSER=true pytest tests/ -v --cov=src --cov-report=html
        echo -e "${GREEN}Coverage report generated in htmlcov/index.html${NC}"
        ;;
    6)
        read -p "Enter test name pattern (e.g., test_navigate): " test_pattern
        echo -e "${BLUE}Running tests matching: $test_pattern${NC}"
        HEADLESS_BROWSER=true pytest tests/ -v -k "$test_pattern"
        ;;
    7)
        echo "Exiting..."
        exit 0
        ;;
    *)
        echo -e "${YELLOW}Invalid choice${NC}"
        exit 1
        ;;
esac

# Show results summary
echo ""
echo -e "${GREEN}Test run completed!${NC}"
echo ""
echo "📊 Test artifacts:"
echo "  - Screenshots: tests/screenshots/"
echo "  - Reports: tests/reports/"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo "  1. Review test output above"
echo "  2. Check screenshots in tests/screenshots/ for visual verification"
echo "  3. View coverage report: open htmlcov/index.html"
echo ""
