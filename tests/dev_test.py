"""
Development testing script with EDMC environment setup.

This script sets up the Python path to include the actual EDMarketConnector
installation, allowing you to test with real EDMC modules.
"""

import os
import sys
from pathlib import Path


def setup_edmc_environment():
    """
    Set up Python path to include EDMarketConnector.
    
    Looks for EDMarketConnector at ../EDMarketConnector relative to workspace.
    """
    workspace_root = Path(__file__).parent.parent
    edmc_path = workspace_root.parent / "EDMarketConnector"
    
    if edmc_path.exists():
        print(f"[OK] Found EDMarketConnector at: {edmc_path}")
        if str(edmc_path) not in sys.path:
            sys.path.insert(0, str(edmc_path))
            print(f"[OK] Added to Python path")
        return True
    else:
        print(f"[WARN] EDMarketConnector not found at: {edmc_path}")
        print(f"  Expected location: ../EDMarketConnector")
        print(f"  Clone with: git clone https://github.com/EDCD/EDMarketConnector.git ../EDMarketConnector")
        return False


def test_edmc_imports():
    """Test that EDMC modules can be imported."""
    print("\nTesting EDMC module imports...")
    
    modules_to_test = [
        "config",
        "stats",
        "l10n",
    ]
    
    for module_name in modules_to_test:
        try:
            __import__(module_name)
            print(f"  [OK] {module_name}")
        except ImportError as e:
            print(f"  [FAIL] {module_name}: {e}")


def main():
    """Run development tests with EDMC environment."""
    print("="*60)
    print("EDMCVKBConnector Development Test Setup")
    print("="*60)
    
    # Set up EDMC environment
    edmc_available = setup_edmc_environment()
    
    # Test imports
    if edmc_available:
        test_edmc_imports()
    
    # Add src to path for our modules
    workspace_root = Path(__file__).parent.parent
    src_path = workspace_root / "src"
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))
    
    print("\n" + "="*60)
    print("Running Unit Tests")
    print("="*60)
    
    # Run unit tests
    import subprocess
    result = subprocess.run(
        [sys.executable, str(Path(__file__).parent / "test_config.py")],
        cwd=str(workspace_root),
    )
    
    if result.returncode == 0:
        print("\n[OK] Unit tests passed!")
        
        print("\n" + "="*60)
        print("Running Integration Tests")
        print("="*60)
        
        # Run integration tests
        result = subprocess.run(
            [sys.executable, str(Path(__file__).parent / "test_integration.py")],
            cwd=str(workspace_root),
        )
        
        if result.returncode == 0:
            print("\n[OK] Integration tests passed!")
            
            print("\n" + "="*60)
            print("Running VKB Server Integration Tests")
            print("="*60)
            
            # Run VKB server tests
            result = subprocess.run(
                [sys.executable, str(Path(__file__).parent / "test_vkb_server_integration.py")],
                cwd=str(workspace_root / "tests"),
            )
            
            if result.returncode == 0:
                print("\n[OK] VKB server tests passed!")
                
                print("\n" + "="*60)
                print("Running Comprehensive Rules Engine Tests")
                print("="*60)
                
                # Run rules engine tests
                result = subprocess.run(
                    [sys.executable, str(Path(__file__).parent / "test_rules_comprehensive.py")],
                    cwd=str(workspace_root / "tests"),
                )
                
                if result.returncode == 0:
                    print("\n[OK] Rules engine tests passed!")
                else:
                    print("\n[FAIL] Rules engine tests failed")
                    return 1
            else:
                print("\n[FAIL] VKB server tests failed")
                return 1
        else:
            print("\n[FAIL] Integration tests failed")
            return 1
    else:
        print("\n[FAIL] Unit tests failed")
        return 1
    
    print("\n" + "="*60)
    print("[SUCCESS] All development tests passed!")
    print("="*60)
    print("\nNext steps:")
    print("1. Start mock VKB server: python tests/mock_vkb_server.py 60")
    print("2. Test with real EDMC or use mock server")
    print("3. See TESTING.md for detailed testing options")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
