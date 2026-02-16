"""
Fix test_all_events.py to pass context with recent_events to signal derivation.

Updates all tests to:
1. Import time module
2. Build context dict with recent_events before calling derive_all_signals
3. Pass context parameter to derive_all_signals
"""

import re
from pathlib import Path


def fix_test_file():
    """Update test_all_events.py with context parameter."""
    test_file = Path(__file__).parent.parent / "test" / "test_all_events.py"
    
    content = test_file.read_text(encoding='utf-8')
    original = content
    
    # Pattern: signals = derivation.derive_all_signals(event)
    # Replace with context setup + pass context
    pattern = r'(        )(signals = derivation\.derive_all_signals\(event\))'
    
    replacement = r'\1# Build context with recent event\n\1context = {"recent_events": {event["event"]: time.time()}}\n\1signals = derivation.derive_all_signals(event, context)'
    
    content = re.sub(pattern, replacement, content)
    
    if content != original:
        test_file.write_text(content, encoding='utf-8')
        
        # Count changes
        changes = content.count('context = {"recent_events":')
        print(f"✓ Updated {changes} test methods to include context parameter")
        print(f"  Each test now builds context with recent_events before calling derive_all_signals")
        return changes
    else:
        print("No changes needed")
        return 0


if __name__ == "__main__":
    print("Fixing test_all_events.py to use context parameter...")
    print()
    
    changes = fix_test_file()
    
    print()
    print(f"✓ Test file updated successfully with {changes} changes")
    print()
    print("Next steps:")
    print("  1. Review the changes in test/test_all_events.py")
    print("  2. Run tests to validate: pytest test/test_all_events.py")
