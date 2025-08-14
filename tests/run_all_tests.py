#!/usr/bin/env python3
"""
Main test runner for OneMinuta
Run all tests or specific test categories
"""

import os
import sys
import subprocess
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def run_test(test_name: str, test_path: str) -> bool:
    """Run a single test and return success status"""
    print(f"\n{'='*60}")
    print(f"Running: {test_name}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(
            [sys.executable, test_path],
            capture_output=False,
            text=True,
            cwd=project_root
        )
        return result.returncode == 0
    except Exception as e:
        print(f"❌ Error running {test_name}: {e}")
        return False

def main():
    """Main test runner"""
    import argparse
    
    parser = argparse.ArgumentParser(description="OneMinuta Test Runner")
    parser.add_argument("--category", choices=["all", "unit", "chatbot", "integration", "quick"],
                       default="quick", help="Test category to run")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    print("🧪 OneMinuta Test Suite")
    print("=" * 60)
    
    tests_dir = Path(__file__).parent
    results = []
    
    if args.category in ["all", "quick", "chatbot"]:
        # Chatbot tests
        if args.category == "quick":
            # Quick tests - no external APIs required
            chatbot_tests = [
                ("Minimal Test", tests_dir / "chatbot" / "test_chatbot_minimal.py"),
            ]
        else:
            # Full tests
            chatbot_tests = [
                ("Structure Test", tests_dir / "chatbot" / "test_chatbot_structure.py"),
                ("Mock Test", tests_dir / "chatbot" / "test_chatbot_mock.py"),
                ("NLP Extraction", tests_dir / "chatbot" / "run_nlp_tests.py"),
            ]
            
            if args.category == "all":
                # Add comprehensive tests for full run
                chatbot_tests.append(("Full Chatbot Test", tests_dir / "chatbot" / "test_chatbot.py"))
        
        for test_name, test_path in chatbot_tests:
            if test_path.exists():
                success = run_test(test_name, str(test_path))
                results.append((test_name, success))
    
    if args.category in ["all", "unit"]:
        # Unit tests
        unit_test_dirs = [
            tests_dir / "unit" / "analytics",
            tests_dir / "unit" / "collector",
            tests_dir / "unit" / "geo-spherical",
        ]
        
        for test_dir in unit_test_dirs:
            if test_dir.exists():
                test_name = f"Unit Tests: {test_dir.name}"
                # Run pytest on the directory
                try:
                    result = subprocess.run(
                        ["pytest", str(test_dir), "-v" if args.verbose else "-q"],
                        capture_output=False,
                        cwd=project_root
                    )
                    results.append((test_name, result.returncode == 0))
                except FileNotFoundError:
                    print(f"⚠️ pytest not found, skipping {test_name}")
    
    if args.category in ["all", "integration"]:
        # Integration tests
        print("\n📝 Integration Tests")
        print("Telegram Bot Test requires manual setup:")
        print(f"  python {tests_dir / 'integration' / 'start_telegram_chatbot_test.py'}")
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 Test Summary")
    print("=" * 60)
    
    if results:
        passed = sum(1 for _, success in results if success)
        total = len(results)
        
        for test_name, success in results:
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"  {status}: {test_name}")
        
        print(f"\nTotal: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All tests passed!")
            return 0
        else:
            print(f"⚠️ {total - passed} test(s) failed")
            return 1
    else:
        print("No tests were run")
        return 0

if __name__ == "__main__":
    sys.exit(main())