"""
Convenience script for running different test scenarios with Prefect.
Provides easy access to various test execution modes.
"""

import sys
from test_integration import (
    run_all_tests,
    run_test_classes,
    run_coverage_tests,
    comprehensive_testing_flow,
)


def print_menu():
    """Print the test execution menu."""
    print("\n" + "="*60)
    print("SEC SCRAPER - TEST EXECUTION MENU")
    print("="*60)
    print("1. Run all tests (quick)")
    print("2. Run individual test classes (granular)")
    print("3. Run comprehensive testing (full)")
    print("4. Run coverage analysis")
    print("5. Exit")
    print("="*60 + "\n")


def main():
    """Main menu for test execution."""
    while True:
        print_menu()
        choice = input("Select an option (1-5): ").strip()

        if choice == "1":
            print("\n" + "="*60)
            print("RUNNING ALL TESTS")
            print("="*60 + "\n")
            results = run_all_tests()
            print(f"\n✓ Test Suite Status: {results['flow_status'].upper()}")
            print(f"✓ Tests Passed: {results['tests_passed']}")
            print(f"✓ Report File: {results['report_file']}")

        elif choice == "2":
            print("\n" + "="*60)
            print("RUNNING INDIVIDUAL TEST CLASSES")
            print("="*60 + "\n")
            results = run_test_classes()
            for test_class, result in results.items():
                status = "✓ PASSED" if result["exit_code"] == 0 else "✗ FAILED"
                print(f"{status}: {test_class}")

        elif choice == "3":
            print("\n" + "="*60)
            print("RUNNING COMPREHENSIVE TESTING")
            print("="*60 + "\n")
            results = comprehensive_testing_flow()
            print(f"\n✓ Overall Status: {results['overall_status'].upper()}")
            print(f"✓ Execution Time: {results['timestamp']}")

        elif choice == "4":
            print("\n" + "="*60)
            print("RUNNING COVERAGE ANALYSIS")
            print("="*60 + "\n")
            results = run_coverage_tests()
            print(f"\n✓ Coverage Analysis Complete")
            print(f"✓ Exit Code: {results['exit_code']}")

        elif choice == "5":
            print("\nExiting test runner. Goodbye!")
            sys.exit(0)

        else:
            print("Invalid option. Please select 1-5.")


if __name__ == "__main__":
    main()
