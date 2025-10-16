#!/usr/bin/env python3
"""
Simple local test for TODO management workflow components.
"""

import json
import subprocess
import sys
from pathlib import Path


def test_scanner():
    """Test the scanner component."""
    print("🔍 Testing TODO scanner...")

    # Run the scanner
    result = subprocess.run(
        [sys.executable, "scanner.py", "../../.."],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent,
    )

    if result.returncode != 0:
        print(f"❌ Scanner failed: {result.stderr}")
        return False, []

    # Parse the JSON output (ignore stderr which has logging)
    try:
        todos = json.loads(result.stdout)
        print(f"✅ Scanner found {len(todos)} TODO(s)")

        if todos:
            print("📋 Found TODOs:")
            for todo in todos:
                print(f"   - {todo['file']}:{todo['line']} - {todo['description']}")

        return True, todos
    except json.JSONDecodeError as e:
        print(f"❌ Failed to parse scanner output: {e}")
        print(f"   stdout: {result.stdout}")
        print(f"   stderr: {result.stderr}")
        return False, []


def test_workflow_components():
    """Test the workflow components."""
    print("🧪 Testing TODO Management Workflow Components")
    print("=" * 50)

    # Test scanner
    scanner_success, todos = test_scanner()

    if not scanner_success:
        print("❌ Scanner test failed")
        return False

    if not todos:
        print("⚠️  No TODOs found to process")
        return True

    print("\n✅ All components tested successfully!")
    print("📊 Summary:")
    print(f"   - Scanner: ✅ Working ({len(todos)} TODOs found)")
    print("   - Agent: ⏭️  Skipped (requires full OpenHands setup)")

    return True


if __name__ == "__main__":
    success = test_workflow_components()
    sys.exit(0 if success else 1)
