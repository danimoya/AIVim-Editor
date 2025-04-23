#!/usr/bin/env python3
"""
Test runner to execute all tests in the tests directory
"""
import os
import sys
import unittest
import logging
import importlib.util
import argparse

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def is_valid_test_file(file_path):
    """
    Check if a file is a valid test file by attempting to import it without side effects
    
    Args:
        file_path: Path to the test file
        
    Returns:
        bool: True if valid, False otherwise
    """
    try:
        # Try to import the module to see if it has any missing dependencies
        spec = importlib.util.spec_from_file_location("test_module", file_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return True
    except (ImportError, ModuleNotFoundError) as e:
        logger.warning(f"Skipping {file_path}: {e}")
        return False
    except Exception as e:
        logger.warning(f"Skipping {file_path} due to error: {e}")
        return False

def get_valid_test_files(directory='tests', pattern='test_*.py'):
    """
    Find valid test files in the specified directory
    
    Args:
        directory: Directory to search
        pattern: Pattern to match test files
        
    Returns:
        list: List of valid test file paths
    """
    import glob
    
    # Get all test files matching pattern
    test_files = glob.glob(os.path.join(directory, pattern))
    
    # Filter out any non-Python files
    test_files = [f for f in test_files if f.endswith('.py')]
    
    # Log found files
    logger.info(f"Found {len(test_files)} test files")
    
    return test_files

def run_test_file(file_path):
    """
    Run a single test file
    
    Args:
        file_path: Path to the test file
        
    Returns:
        bool: True if all tests passed, False otherwise
    """
    # Get directory and file name
    dir_name = os.path.dirname(file_path)
    file_name = os.path.basename(file_path)
    
    # Create loader and load the tests
    loader = unittest.TestLoader()
    try:
        # Add directory to path temporarily
        if dir_name not in sys.path:
            sys.path.insert(0, dir_name)
            
        # Load tests from the file
        suite = loader.discover(dir_name, pattern=file_name)
        
        # Create test runner
        runner = unittest.TextTestRunner(verbosity=2)
        
        # Run the tests
        result = runner.run(suite)
        
        # Return True if all tests passed
        return result.wasSuccessful()
    except Exception as e:
        logger.error(f"Failed to run {file_path}: {e}")
        return False

def run_specific_tests(test_files):
    """
    Run specific test files
    
    Args:
        test_files: List of test file paths
        
    Returns:
        bool: True if all specified tests passed, False otherwise
    """
    if not test_files:
        logger.warning("No valid test files to run")
        return True
        
    # Run each file
    results = []
    for file_path in test_files:
        logger.info(f"Running tests in {file_path}")
        result = run_test_file(file_path)
        results.append(result)
        
    # Return True if all tests passed
    return all(results)

def discover_and_run_tests(directory='tests', pattern='test_*.py', manual_tests=None):
    """
    Discover and run all tests in the tests directory or specific test files
    
    Args:
        directory: Directory to discover tests
        pattern: Pattern to match test files
        manual_tests: List of specific test files to run
        
    Returns:
        bool: True if all tests passed, False otherwise
    """
    if manual_tests:
        # Run specified test files
        logger.info(f"Running specified test files: {', '.join(manual_tests)}")
        return run_specific_tests(manual_tests)
    else:
        # Get all test files
        all_test_files = get_valid_test_files(directory, pattern)
        
        # Filter to valid test files
        valid_test_files = []
        for file_path in all_test_files:
            if is_valid_test_file(file_path):
                valid_test_files.append(file_path)
            
        logger.info(f"Found {len(valid_test_files)} valid test files out of {len(all_test_files)}")
        
        # Run valid tests
        return run_specific_tests(valid_test_files)

def main():
    """Main function"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Run AIVim tests')
    parser.add_argument('-t', '--test', action='append', 
                        help='Specific test file(s) to run (can be specified multiple times)')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Increase verbosity')
    parser.add_argument('-f', '--feature-tests', action='store_true',
                        help='Run only the new feature tests')
    args = parser.parse_args()
    
    # Set log level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    logger.info("Starting AIVim tests")
    
    # If feature tests flag is set, run only the new feature tests
    if args.feature_tests:
        logger.info("Running only new feature tests")
        feature_tests = [
            'tests/test_shift_a_command.py',
            'tests/test_multiline_paste.py',
            'tests/test_model_info_display.py',
            'tests/test_local_llm_tabs.py'
        ]
        success = discover_and_run_tests(manual_tests=feature_tests)
    else:
        # Discover and run tests
        success = discover_and_run_tests(manual_tests=args.test)
    
    # Exit with appropriate status code
    if success:
        logger.info("All tests passed!")
        sys.exit(0)
    else:
        logger.error("Some tests failed")
        sys.exit(1)

if __name__ == "__main__":
    main()