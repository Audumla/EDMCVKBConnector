"""Quick-start testing script - run all tests and show options."""

import subprocess
import sys
from pathlib import Path


def run_test(name, script_path):
    """Run a test script and return success status."""
    print(f"\n{'='*60}")
    print(f"Running: {name}")
    print('='*60)
    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=str(script_path.parent.parent),
            capture_output=False,
        )
        return result.returncode == 0
    except Exception as e:
        print(f"[FATAL] Failed to run {name}: {e}")
        return False


def main():
    """Run all tests."""
    project_root = Path(__file__).parent.parent
    tests_dir = project_root / "tests"
    
    print("\n" + "EDMCVKBConnector Test Suite".center(60, "="))
    
    results = {}
    
    # Run unit tests
    results["Unit Tests"] = run_test(
        "Unit Tests (Config, VKBClient, EventHandler, MessageFormatter)",
        tests_dir / "test_config.py"
    )
    
    # Run integration tests
    results["Integration Tests"] = run_test(
        "Integration Tests (Event Flow, Shift State, Error Handling)",
        tests_dir / "test_integration.py"
    )

    # Run comprehensive rules tests (file-backed rules + positive/negative paths)
    results["Rules Tests"] = run_test(
        "Rules Tests (File-backed rules, positive/negative outcomes)",
        tests_dir / "test_rules_comprehensive.py"
    )

    # Run rule loading tests (default and override file behavior)
    results["Rule Loading"] = run_test(
        "Rule Loading Tests (rules.json default + override path + invalid file)",
        tests_dir / "test_rule_loading.py"
    )
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY".center(60))
    print("="*60)
    
    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "[FATAL] FAILED"
        print(f"{test_name:.<40} {status}")
    
    all_passed = all(results.values())
    
    print("\n" + "="*60)
    if all_passed:
        print("✅ ALL TESTS PASSED!".center(60))
    else:
        print("[FATAL] SOME TESTS FAILED".center(60))
    print("="*60)
    
    # Show next steps
    print("\n📚 NEXT STEPS:\n")
    print("1. UNIT TESTS ONLY (local development):")
    print("   python tests/test_config.py\n")
    
    print("2. INTEGRATION TESTS (simulated VKB client):")
    print("   python tests/test_integration.py\n")
    
    print("3. MOCK VKB SERVER (without real hardware):")
    print("   # Terminal 1: Start server")
    print("   python tests/mock_vkb_server.py 60\n")
    print("   # Terminal 2: Run integration tests")
    print("   python tests/test_integration.py\n")
    
    print("4. REAL EDMC TESTING:")
    print("   - Copy plugin to EDMC plugins directory:")
    print("     mklink /D \"%APPDATA%\\EDMarketConnector\\plugins\\edmcvkbconnector\" \\")
    print("     \"h:\\development\\projects\\EDMCVKBConnector\"\n")
    print("   - Restart EDMC")
    print("   - Check logs in EDMC")
    print("   - Monitor Events in EDMC Log panel\n")
    
    print("5. FULL END-TO-END TEST:")
    print("   python tests/mock_vkb_server.py &")
    print("   # Start EDMC and play Elite Dangerous")
    print("   # Watch for shift state changes in mock server output\n")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
