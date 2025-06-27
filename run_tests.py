#!/usr/bin/env python3
"""
Test runner script for the Trade-Up Engine test suite

Usage:
    python run_tests.py                    # Run all tests
    python run_tests.py unit              # Run only unit tests
    python run_tests.py integration       # Run only integration tests
    python run_tests.py coverage          # Run with coverage report
    python run_tests.py specific.test     # Run specific test
"""
import sys
import subprocess
import os


def run_command(cmd):
    """Run a command and return the result"""
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True)
    return result.returncode


def main():
    # Ensure we're in the project root
    project_root = os.path.dirname(os.path.abspath(__file__))
    os.chdir(project_root)
    
    # Default pytest args
    pytest_args = [
        "-v",                    # Verbose output
        "--tb=short",           # Shorter traceback format
        "--strict-markers",     # Strict marker checking
        "-p no:warnings",       # Disable warnings
    ]
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "unit":
            # Run only unit tests
            pytest_args.append("tests/unit/")
        elif command == "integration":
            # Run only integration tests
            pytest_args.append("tests/integration/")
        elif command == "coverage":
            # Run with coverage
            pytest_args.extend([
                "--cov=app",
                "--cov=engine",
                "--cov=data",
                "--cov=config",
                "--cov-report=term-missing",
                "--cov-report=html",
                "--cov-report=xml"
            ])
        elif command == "fast":
            # Run fast tests only (exclude slow integration tests)
            pytest_args.extend(["-m", "not slow"])
        elif command == "failed":
            # Re-run only failed tests
            pytest_args.append("--lf")
        elif command.endswith(".py") or "::" in command:
            # Run specific test file or test
            pytest_args.append(command)
        else:
            # Assume it's a test pattern
            pytest_args.extend(["-k", command])
    
    # Build the full pytest command
    cmd = f"pytest {' '.join(pytest_args)}"
    
    # Run pytest
    exit_code = run_command(cmd)
    
    # If coverage was requested, show the report location
    if "coverage" in sys.argv and exit_code == 0:
        print("\n" + "="*60)
        print("Coverage report generated!")
        print("HTML report: htmlcov/index.html")
        print("="*60)
    
    return exit_code


if __name__ == "__main__":
    sys.exit(main())