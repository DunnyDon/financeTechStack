"""
Prefect integration for test execution and monitoring.
Runs pytest tests as Prefect tasks with built-in logging and error handling.
"""

import subprocess
import json
from datetime import datetime
from pathlib import Path
from prefect import flow, task, get_run_logger
import pandas as pd


@task(retries=2, retry_delay_seconds=5)
def run_pytest_tests(test_file: str = "test_sec_scraper.py", verbose: bool = True) -> dict:
    """
    Run pytest tests and capture results.
    
    Args:
        test_file: Path to the test file to run
        verbose: Whether to run pytest in verbose mode
        
    Returns:
        Dictionary containing test results and metrics
    """
    logger = get_run_logger()
    logger.info(f"Starting pytest execution for {test_file}")
    
    try:
        # Build pytest command with uv run
        cmd = ["uv", "run", "--with", "pytest", "python", "-m", "pytest", test_file, "--tb=short"]
        
        if verbose:
            cmd.append("-v")
        
        # Run pytest
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        logger.info(f"Pytest exit code: {result.returncode}")
        logger.info(f"Pytest stdout:\n{result.stdout}")
        
        if result.stderr:
            logger.warning(f"Pytest stderr:\n{result.stderr}")
        
        # Parse results
        test_results = {
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "timestamp": datetime.now().isoformat(),
        }
        
        # Try to read JSON report if pytest-json-report is available
        try:
            report_file = Path("test_report.json")
            if report_file.exists():
                with open(report_file, "r") as f:
                    test_results["report"] = json.load(f)
                logger.info("Loaded pytest JSON report")
        except Exception as e:
            logger.warning(f"Could not load JSON report: {e}")
        
        # Extract metrics from stdout
        if "passed" in result.stdout:
            import re
            match = re.search(r"(\d+) passed", result.stdout)
            if match:
                test_results["passed_count"] = int(match.group(1))
            
            match = re.search(r"(\d+) failed", result.stdout)
            if match:
                test_results["failed_count"] = int(match.group(1))
        
        logger.info(f"Test execution completed with exit code: {result.returncode}")
        return test_results
        
    except subprocess.TimeoutExpired:
        logger.error("Pytest execution timed out after 300 seconds")
        raise
    except Exception as e:
        logger.error(f"Error running pytest: {e}")
        raise


@task
def validate_test_results(test_results: dict) -> bool:
    """
    Validate that tests passed.
    
    Args:
        test_results: Results dictionary from run_pytest_tests
        
    Returns:
        True if tests passed, False otherwise
    """
    logger = get_run_logger()
    
    exit_code = test_results.get("exit_code", 1)
    passed_count = test_results.get("passed_count", 0)
    failed_count = test_results.get("failed_count", 0)
    
    logger.info(f"Test Results: {passed_count} passed, {failed_count} failed")
    
    if exit_code == 0:
        logger.info("✓ All tests passed!")
        return True
    else:
        logger.error("✗ Tests failed!")
        return False


@task
def generate_test_report(test_results: dict, output_file: str = "test_results.json") -> str:
    """
    Generate a test report from results.
    
    Args:
        test_results: Results dictionary from run_pytest_tests
        output_file: Path to save the report
        
    Returns:
        Path to the generated report file
    """
    logger = get_run_logger()
    logger.info(f"Generating test report: {output_file}")
    
    try:
        report = {
            "execution_time": test_results.get("timestamp"),
            "exit_code": test_results.get("exit_code"),
            "passed_count": test_results.get("passed_count", 0),
            "failed_count": test_results.get("failed_count", 0),
            "output": test_results.get("stdout", ""),
        }
        
        with open(output_file, "w") as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Test report saved to {output_file}")
        return output_file
        
    except Exception as e:
        logger.error(f"Error generating test report: {e}")
        raise


@task
def run_specific_test_class(test_file: str, test_class: str) -> dict:
    """
    Run a specific test class.
    
    Args:
        test_file: Path to the test file
        test_class: Test class name (e.g., 'TestCIKExtraction')
        
    Returns:
        Test results dictionary
    """
    logger = get_run_logger()
    logger.info(f"Running test class: {test_class}")
    
    try:
        cmd = [
            "uv",
            "run",
            "--with",
            "pytest",
            "python",
            "-m",
            "pytest",
            f"{test_file}::{test_class}",
            "-v",
            "--tb=short",
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        
        logger.info(f"Test class {test_class} exit code: {result.returncode}")
        
        test_results = {
            "test_class": test_class,
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "timestamp": datetime.now().isoformat(),
        }
        
        return test_results
        
    except Exception as e:
        logger.error(f"Error running test class {test_class}: {e}")
        raise


@task
def run_parametrized_tests(test_file: str, test_name: str) -> dict:
    """
    Run parametrized tests.
    
    Args:
        test_file: Path to the test file
        test_name: Parametrized test name (e.g., 'test_multiple_tickers')
        
    Returns:
        Test results dictionary
    """
    logger = get_run_logger()
    logger.info(f"Running parametrized test: {test_name}")
    
    try:
        cmd = [
            "uv",
            "run",
            "--with",
            "pytest",
            "python",
            "-m",
            "pytest",
            f"{test_file}",
            "-k",
            test_name,
            "-v",
            "--tb=short",
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        
        logger.info(f"Parametrized test {test_name} exit code: {result.returncode}")
        
        test_results = {
            "test_name": test_name,
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "timestamp": datetime.now().isoformat(),
        }
        
        return test_results
        
    except Exception as e:
        logger.error(f"Error running parametrized test {test_name}: {e}")
        raise


@flow(name="SEC Scraper Test Suite")
def run_all_tests() -> dict:
    """
    Main flow to run all tests with monitoring and reporting.
    
    Returns:
        Summary of all test results
    """
    logger = get_run_logger()
    logger.info("Starting SEC Scraper Test Suite")
    
    # Run all tests
    test_results = run_pytest_tests("test_sec_scraper.py", verbose=True)
    
    # Validate results
    tests_passed = validate_test_results(test_results)
    
    # Generate report
    report_file = generate_test_report(test_results)
    
    summary = {
        "flow_status": "success" if tests_passed else "failed",
        "tests_passed": tests_passed,
        "report_file": report_file,
        "test_details": test_results,
        "execution_time": test_results.get("timestamp"),
    }
    
    logger.info(f"Test suite execution complete: {summary['flow_status']}")
    return summary


@flow(name="SEC Scraper Test Classes")
def run_test_classes() -> dict:
    """
    Flow to run individual test classes for granular monitoring.
    
    Returns:
        Results for each test class
    """
    logger = get_run_logger()
    logger.info("Starting individual test class runs")
    
    test_classes = [
        "TestCIKExtraction",
        "TestFilingExtraction",
        "TestParquetSaving",
        "TestIntegration",
        "TestParametrized",
    ]
    
    results = {}
    for test_class in test_classes:
        logger.info(f"Running {test_class}...")
        result = run_specific_test_class("test_sec_scraper.py", test_class)
        results[test_class] = result
    
    logger.info("All test classes completed")
    return results


@flow(name="SEC Scraper Test Coverage")
def run_coverage_tests() -> dict:
    """
    Flow to run tests with coverage reporting.
    
    Returns:
        Coverage and test results
    """
    logger = get_run_logger()
    logger.info("Starting test coverage analysis")
    
    try:
        cmd = [
            "uv",
            "run",
            "--with",
            "pytest,pytest-cov",
            "python",
            "-m",
            "pytest",
            "test_sec_scraper.py",
            "--cov=.",
            "--cov-report=term",
            "-v",
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        logger.info(f"Coverage analysis exit code: {result.returncode}")
        logger.info(f"Coverage report:\n{result.stdout}")
        
        coverage_results = {
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "timestamp": datetime.now().isoformat(),
        }
        
        return coverage_results
        
    except Exception as e:
        logger.error(f"Error running coverage tests: {e}")
        raise


@flow(name="SEC Scraper Comprehensive Testing")
def comprehensive_testing_flow() -> dict:
    """
    Comprehensive flow that runs all tests, validates, and generates reports.
    
    Returns:
        Complete testing summary
    """
    logger = get_run_logger()
    logger.info("Starting comprehensive testing flow")
    
    # Run all tests
    all_tests_result = run_all_tests()
    
    # Run individual test classes
    class_results = run_test_classes()
    
    # Prepare summary
    summary = {
        "timestamp": datetime.now().isoformat(),
        "all_tests": all_tests_result,
        "test_classes": class_results,
        "overall_status": all_tests_result["flow_status"],
    }
    
    logger.info("Comprehensive testing flow completed")
    return summary


def main():
    """Run the comprehensive testing flow."""
    print("\n" + "="*60)
    print("SEC SCRAPER - PREFECT TEST INTEGRATION")
    print("="*60 + "\n")
    
    # Run comprehensive tests
    results = comprehensive_testing_flow()
    
    # Print summary
    print("\n" + "="*60)
    print("TEST EXECUTION SUMMARY")
    print("="*60)
    print(f"Overall Status: {results['overall_status'].upper()}")
    print(f"Execution Time: {results['timestamp']}")
    print(f"Report File: {results['all_tests'].get('report_file', 'N/A')}")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
