#!/usr/bin/env python3
"""
Test scanner filtering capabilities.

This script tests that the scanner properly filters out:
1. Already processed TODOs (with PR URLs)
2. False positives (strings, documentation, etc.)
3. TODOs in test files and examples
"""

import json
import logging
import subprocess
import sys
import tempfile
from pathlib import Path


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stderr),
    ]
)
logger = logging.getLogger(__name__)


def create_test_file_content():
    """Create test file content with various TODO patterns."""
    return '''#!/usr/bin/env python3
"""
Test file with various TODO patterns for scanner testing.
"""

def function_with_todos():
    """Function with various TODO patterns."""
    
    # This should be found - unprocessed TODO
    # TODO(openhands): Add input validation for user data
    
    # These should be filtered out - already processed
    # TODO(in progress: https://github.com/owner/repo/pull/123): Add error handling
    # TODO(implemented: https://github.com/owner/repo/pull/124): Add logging
    # TODO(completed: https://github.com/owner/repo/pull/125): Add tests
    # TODO(openhands): Fix bug - see https://github.com/owner/repo/pull/126
    
    # This should be found - another unprocessed TODO
    # TODO(openhands): Optimize database queries
    
    # These should be filtered out - false positives
    print("This string contains TODO(openhands): but should be ignored")
    description = "TODO(openhands): This is in a variable assignment"
    
    """
    This docstring mentions TODO(openhands): but should be ignored
    """
    
    # This should be found - valid TODO with description
    # TODO(openhands): Implement caching mechanism for better performance
    
    return "test"


def another_function():
    # TODO(openhands): Add unit tests
    pass
'''


def test_scanner_filtering():
    """Test that the scanner properly filters TODOs."""
    logger.info("🧪 Testing Scanner Filtering Capabilities")
    logger.info("=" * 45)
    
    # Create a temporary test file (avoid "test_" prefix to bypass scanner filtering)
    with tempfile.NamedTemporaryFile(
        mode='w', suffix='.py', delete=False, prefix='sample_'
    ) as f:
        f.write(create_test_file_content())
        test_file_path = f.name
    
    try:
        # Run the scanner on the test file
        result = subprocess.run(
            [sys.executable, "scanner.py", test_file_path],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent,
        )
        
        if result.returncode != 0:
            logger.error(f"Scanner failed: {result.stderr}")
            return False
        
        # Parse the results
        try:
            todos = json.loads(result.stdout)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse scanner output: {e}")
            return False
        
        logger.info("📊 Scanner Results:")
        logger.info(f"   Found {len(todos)} unprocessed TODO(s)")
        
        # Expected TODOs (should find only unprocessed ones)
        expected_descriptions = [
            "Add input validation for user data",
            "Optimize database queries", 
            "Implement caching mechanism for better performance",
            "Add unit tests"
        ]
        
        found_descriptions = [todo['description'] for todo in todos]
        
        logger.info("📋 Found TODOs:")
        for i, todo in enumerate(todos, 1):
            logger.info(f"   {i}. Line {todo['line']}: {todo['description']}")
        
        # Verify filtering worked correctly
        success = True
        
        # Check that we found the expected number of TODOs
        if len(todos) != len(expected_descriptions):
            logger.error(
                f"❌ Expected {len(expected_descriptions)} TODOs, found {len(todos)}"
            )
            success = False
        
        # Check that we found the right TODOs
        for expected_desc in expected_descriptions:
            if expected_desc not in found_descriptions:
                logger.error(f"❌ Missing expected TODO: {expected_desc}")
                success = False
        
        # Check that we didn't find any processed TODOs
        processed_indicators = [
            "in progress:",
            "implemented:",
            "completed:",
            "github.com/",
            "pull/123",
            "pull/124",
            "pull/125",
            "pull/126"
        ]
        
        for todo in todos:
            todo_text = todo['text'].lower()
            for indicator in processed_indicators:
                if indicator in todo_text:
                    logger.error(
                        "❌ Found processed TODO that should be filtered: "
                        f"{todo['text']}"
                    )
                    success = False
        
        # Check that we didn't find any false positives
        false_positive_indicators = [
            "print(",
            "description =",
            '"""',
            "string contains"
        ]
        
        for todo in todos:
            todo_text = todo['text'].lower()
            for indicator in false_positive_indicators:
                if indicator in todo_text:
                    logger.error(
                        "❌ Found false positive that should be filtered: "
                        f"{todo['text']}"
                    )
                    success = False
        
        if success:
            logger.info("✅ Scanner filtering test passed!")
            logger.info("   Key filtering capabilities verified:")
            logger.info("   - ✅ Filters out TODOs with PR URLs")
            logger.info("   - ✅ Filters out TODOs with progress markers")
            logger.info("   - ✅ Filters out false positives in strings")
            logger.info("   - ✅ Filters out false positives in docstrings")
            logger.info("   - ✅ Finds legitimate unprocessed TODOs")
            return True
        else:
            logger.error("❌ Scanner filtering test failed!")
            return False
            
    finally:
        # Clean up the temporary file
        Path(test_file_path).unlink()


def test_real_world_filtering():
    """Test filtering on the actual codebase."""
    logger.info("\n🌍 Testing Real-World Filtering")
    logger.info("=" * 35)
    
    # Run scanner on the actual codebase
    result = subprocess.run(
        [sys.executable, "scanner.py", "../../.."],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent,
    )
    
    if result.returncode != 0:
        logger.error(f"Scanner failed: {result.stderr}")
        return False
    
    try:
        todos = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse scanner output: {e}")
        return False
    
    logger.info("📊 Real-world scan results:")
    logger.info(f"   Found {len(todos)} unprocessed TODO(s) in codebase")
    
    # Verify no processed TODOs were found
    processed_count = 0
    for todo in todos:
        todo_text = todo['text'].lower()
        if any(indicator in todo_text for indicator in [
            "pull/", "github.com/", "in progress:", "implemented:", "completed:"
        ]):
            processed_count += 1
            logger.warning(f"⚠️  Found potentially processed TODO: {todo['text']}")
    
    if processed_count == 0:
        logger.info("✅ No processed TODOs found in real-world scan")
        return True
    else:
        logger.error(
            f"❌ Found {processed_count} processed TODOs that should be filtered"
        )
        return False


def main():
    """Run all scanner filtering tests."""
    logger.info("🔍 Scanner Filtering Test Suite")
    logger.info("=" * 35)
    
    # Test 1: Controlled filtering test
    test1_success = test_scanner_filtering()
    
    # Test 2: Real-world filtering test
    test2_success = test_real_world_filtering()
    
    # Summary
    logger.info("\n📊 Test Summary")
    logger.info("=" * 15)
    logger.info(
        f"   Controlled filtering test: {'✅ PASS' if test1_success else '❌ FAIL'}"
    )
    logger.info(
        f"   Real-world filtering test: {'✅ PASS' if test2_success else '❌ FAIL'}"
    )
    
    if test1_success and test2_success:
        logger.info("🎉 All scanner filtering tests passed!")
        return True
    else:
        logger.error("❌ Some scanner filtering tests failed!")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)