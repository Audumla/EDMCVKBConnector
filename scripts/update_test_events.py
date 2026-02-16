"""
Update test files to use new category event enum signals instead of old individual event signals.
"""

import re
import json
from pathlib import Path

# Load the mapping
with open("scripts/event_signal_mapping.json", "r", encoding="utf-8") as f:
    EVENT_MAPPING = json.load(f)

def update_test_file(filepath):
    """Update a single test file."""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    
    original_content = content
    changes = []
    
    # Pattern 1: assert signals["event_xxx"] is True
    for old_signal in EVENT_MAPPING:
        enum_id, enum_value = EVENT_MAPPING[old_signal]
        
        # Pattern: signals["event_xxx"] is True
        pattern1 = rf'signals\["{old_signal}"\]\s+is\s+True'
        replacement1 = f'signals["{enum_id}"] == "{enum_value}"'
        if re.search(pattern1, content):
            content = re.sub(pattern1, replacement1, content)
            changes.append(f"{old_signal} → {enum_id}={enum_value}")
        
        # Pattern: signals["event_xxx"]
        pattern2 = rf'signals\["{old_signal}"\]'
        replacement2 = f'signals["{enum_id}"]'
        # Only replace if not already replaced by pattern1
        remaining_matches = re.findall(pattern2, content)
        if remaining_matches:
            # Add comment about enum values
            content = re.sub(pattern2, replacement2 + f' # Now enum: use == "{enum_value}"', content, count=1)
            changes.append(f"{old_signal} → {enum_id} (check value)")
    
    if content != original_content:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        return len(changes), changes
    return 0, []

def main():
    test_dir = Path("test")
    test_files = list(test_dir.glob("test_*.py"))
    
    total_changes = 0
    for test_file in test_files:
        count, changes = update_test_file(test_file)
        if count > 0:
            print(f"\n✓ {test_file.name}: {count} changes")
            for change in changes[:5]:  # Show first 5
                print(f"  - {change}")
            if len(changes) > 5:
                print(f"  ... and {len(changes) - 5} more")
            total_changes += count
    
    print(f"\n✓ Total changes across all test files: {total_changes}")

if __name__ == "__main__":
    main()
