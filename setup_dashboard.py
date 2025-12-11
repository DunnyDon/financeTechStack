#!/usr/bin/env python
"""
Dashboard installation and setup verification script.

This script checks all dependencies and helps set up the analytics dashboard.
"""

import sys
import subprocess
from pathlib import Path


def print_header(text):
    """Print a formatted header."""
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70 + "\n")


def check_python_version():
    """Check if Python version is 3.13+"""
    print_header("Checking Python Version")
    
    version = sys.version_info
    print(f"Python {version.major}.{version.minor}.{version.micro}")
    
    if version.major < 3 or (version.major == 3 and version.minor < 13):
        print("❌ Python 3.13+ required")
        print(f"   Current: {version.major}.{version.minor}")
        return False
    
    print("✅ Python version OK")
    return True


def check_package(package_name, import_name=None):
    """Check if a package is installed."""
    if import_name is None:
        import_name = package_name
    
    try:
        __import__(import_name)
        print(f"✅ {package_name}")
        return True
    except ImportError:
        print(f"❌ {package_name} - NOT INSTALLED")
        return False


def check_dependencies():
    """Check all required dependencies."""
    print_header("Checking Dependencies")
    
    required = {
        "streamlit": "streamlit",
        "streamlit-option-menu": "streamlit_option_menu",
        "pandas": "pandas",
        "numpy": "numpy",
    }
    
    all_ok = True
    for package, import_name in required.items():
        if not check_package(package, import_name):
            all_ok = False
    
    return all_ok


def check_optional_dependencies():
    """Check optional but recommended dependencies."""
    print_header("Checking Optional Dependencies (Recommended)")
    
    optional = {
        "plotly": "plotly",
        "altair": "altair",
        "scipy": "scipy",
        "scikit-learn": "sklearn",
    }
    
    installed = []
    missing = []
    
    for package, import_name in optional.items():
        if check_package(package, import_name):
            installed.append(package)
        else:
            missing.append(package)
    
    if missing:
        print(f"\n⚠️  Missing optional packages: {', '.join(missing)}")
        print("   Install with: pip install " + " ".join(missing))
    
    return len(missing) == 0


def check_project_structure():
    """Check if project structure exists."""
    print_header("Checking Project Structure")
    
    required_dirs = [
        "src",
        "src/backtesting",
        "docs",
        "examples",
        "tests",
    ]
    
    all_ok = True
    for dir_path in required_dirs:
        if Path(dir_path).exists():
            print(f"✅ {dir_path}/")
        else:
            print(f"❌ {dir_path}/ - NOT FOUND")
            all_ok = False
    
    return all_ok


def check_app_exists():
    """Check if app.py exists."""
    print_header("Checking Dashboard Files")
    
    app_path = Path("app.py")
    if app_path.exists():
        print(f"✅ app.py exists ({app_path.stat().st_size} bytes)")
        return True
    else:
        print("❌ app.py - NOT FOUND")
        return False


def install_dependencies():
    """Install missing dependencies."""
    print_header("Installing Dependencies")
    
    print("Installing Streamlit and dependencies...")
    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install",
            "streamlit", "streamlit-option-menu", "pandas", "numpy"
        ])
        print("\n✅ Core dependencies installed")
        return True
    except subprocess.CalledProcessError:
        print("\n❌ Installation failed")
        return False


def install_optional():
    """Install optional dependencies."""
    print_header("Installing Optional Dependencies")
    
    print("Installing visualization and analysis packages...")
    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install",
            "plotly", "altair", "scipy", "scikit-learn"
        ])
        print("\n✅ Optional dependencies installed")
        return True
    except subprocess.CalledProcessError:
        print("\n❌ Optional installation failed (non-critical)")
        return False


def print_setup_instructions():
    """Print setup instructions."""
    print_header("Setup Instructions")
    
    print("""
1. Install Dependencies (if needed):
   
   uv pip install streamlit streamlit-option-menu
   
   Or with pip:
   
   pip install streamlit streamlit-option-menu

2. Configure Settings:
   
   - Open the dashboard and go to Settings
   - Add your API keys for data sources
   - Configure email for reports
   - Select data sources

3. Run the Dashboard:
   
   ./run_dashboard.sh
   
   Or directly:
   
   streamlit run app.py

4. Access the Dashboard:
   
   Open http://localhost:8501 in your browser

5. Explore Features:
   
   - Home: Overview and quick stats
   - Portfolio Analytics: P&L and technical analysis
   - News & Sentiment: Market news and impact
   - Backtesting: Test strategies on historical data
   - Help & Glossary: Learn concepts and metrics
   - Settings: Configure data sources and preferences
""")


def print_next_steps():
    """Print next steps after setup."""
    print_header("Next Steps")
    
    print("""
After installation, try these:

1. Read the Documentation:
   - docs/DASHBOARD_GUIDE.md - Full dashboard documentation
   - DASHBOARD_QUICK_START.md - 30-second quick start
   - docs/BACKTESTING_FRAMEWORK_GUIDE.md - Backtesting guide

2. Explore the Dashboard:
   - Click through each section
   - Read the Help & Glossary section
   - Try a backtest with sample data

3. Configure for Your Portfolio:
   - Update Settings with your API keys
   - Configure your preferred currency and email
   - Enable/disable data sources

4. Monitor Your Portfolio:
   - Check Portfolio Analytics daily
   - Review News & Sentiment for market context
   - Set up automated email reports

5. Develop Strategies:
   - Use Backtesting to validate strategies
   - Test different parameters
   - Use Walk-Forward validation for robustness

6. Production Use:
   - Configure scheduled reports
   - Set up alerts for key thresholds
   - Integrate with portfolio management workflow
""")


def main():
    """Run all checks and setup."""
    print("\n")
    print("╔════════════════════════════════════════════════════════════════════╗")
    print("║         Finance TechStack Dashboard - Setup Verification          ║")
    print("╚════════════════════════════════════════════════════════════════════╝")
    
    checks = [
        ("Python Version", check_python_version),
        ("Dependencies", check_dependencies),
        ("Project Structure", check_project_structure),
        ("Dashboard Files", check_app_exists),
    ]
    
    results = {}
    for check_name, check_func in checks:
        results[check_name] = check_func()
    
    # Check optional
    check_optional_dependencies()
    
    print_header("Summary")
    
    all_required_ok = all(results.values())
    
    if all_required_ok:
        print("✅ All required checks passed!")
        print("   Dashboard is ready to run.")
    else:
        print("❌ Some required checks failed:")
        for check_name, result in results.items():
            status = "✅" if result else "❌"
            print(f"   {status} {check_name}")
    
    print_setup_instructions()
    
    if all_required_ok:
        print_next_steps()
    
    print_header("Quick Commands")
    
    print("""
Start the dashboard:
  ./run_dashboard.sh
  
  or
  
  streamlit run app.py

View documentation:
  cat docs/DASHBOARD_GUIDE.md
  cat DASHBOARD_QUICK_START.md

Run backtesting examples:
  python run_examples.py 1
  python run_examples.py 4

Check backtest setup:
  python test_backtesting_setup.py
""")
    
    return 0 if all_required_ok else 1


if __name__ == "__main__":
    sys.exit(main())
