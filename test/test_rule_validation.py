"""
Test rule validation function.
"""

import sys
from pathlib import Path

# Add source paths
plugin_root = Path(__file__).parent.parent
src_path = plugin_root / "src"
sys.path.insert(0, str(src_path))

from edmcruleengine.rule_validation import validate_rule

def test_valid_rule():
    """Test that a valid rule passes validation."""
    rule = {
        "id": "test_rule",
        "enabled": True,
        "when": {
            "source": "dashboard",
            "event": "Status",
            "all": [
                {
                    "flags": {
                        "all_of": ["FlagsLandingGearDown"]
                    }
                }
            ]
        },
        "then": {
            "vkb_set_shift": ["Subshift3"],
            "log": "Landing gear down"
        },
        "else": {
            "vkb_clear_shift": ["Subshift3"]
        }
    }
    
    is_valid, error = validate_rule(rule)
    assert is_valid, f"Valid rule failed validation: {error}"
    print("✓ Valid rule passes validation")

def test_empty_id():
    """Test that empty ID is rejected."""
    rule = {
        "id": "",
        "when": {},
        "then": {}
    }
    
    is_valid, error = validate_rule(rule)
    assert not is_valid, "Empty ID should fail validation"
    assert "Rule ID" in error
    print("✓ Empty ID is rejected")

def test_missing_id():
    """Test that missing ID is rejected."""
    rule = {
        "when": {},
        "then": {}
    }
    
    is_valid, error = validate_rule(rule)
    assert not is_valid, "Missing ID should fail validation"
    assert "Rule ID" in error
    print("✓ Missing ID is rejected")

def test_invalid_when_type():
    """Test that invalid when type is rejected."""
    rule = {
        "id": "test",
        "when": "invalid",
        "then": {}
    }
    
    is_valid, error = validate_rule(rule)
    assert not is_valid, "Invalid when type should fail validation"
    assert "When clause" in error
    print("✓ Invalid when type is rejected")

def test_invalid_shift_flags():
    """Test that invalid shift flags are rejected."""
    rule = {
        "id": "test",
        "when": {},
        "then": {
            "vkb_set_shift": "not_a_list"
        }
    }
    
    is_valid, error = validate_rule(rule)
    assert not is_valid, "Invalid shift flags should fail validation"
    assert "vkb_set_shift" in error
    print("✓ Invalid shift flags are rejected")

def test_minimal_rule():
    """Test that minimal rule is valid."""
    rule = {
        "id": "minimal",
    }
    
    is_valid, error = validate_rule(rule)
    assert is_valid, f"Minimal rule should be valid: {error}"
    print("✓ Minimal rule is valid")

def test_complex_rule():
    """Test complex rule with all features."""
    rule = {
        "id": "complex_rule",
        "enabled": True,
        "when": {
            "source": ["dashboard", "journal"],
            "event": ["Status", "FSDJump"],
            "all": [
                {"flags": {"all_of": ["FlagsLandingGearDown"]}},
                {"gui_focus": {"equals": "GuiFocusNoFocus"}}
            ],
            "any": [
                {"flags2": {"any_of": ["Flags2OnFoot"]}},
                {"field": {"name": "FuelLevel", "gt": 50}}
            ]
        },
        "then": {
            "vkb_set_shift": ["Shift1", "Subshift1"],
            "vkb_clear_shift": ["Shift2"],
            "log": "Complex condition matched"
        },
        "else": {
            "vkb_clear_shift": ["Shift1", "Subshift1"],
            "vkb_set_shift": ["Shift2"],
            "log": "Complex condition not matched"
        }
    }
    
    is_valid, error = validate_rule(rule)
    assert is_valid, f"Complex rule should be valid: {error}"
    print("✓ Complex rule is valid")

if __name__ == "__main__":
    print("Testing rule validation...\n")
    
    all_passed = True
    
    try:
        test_valid_rule()
        test_empty_id()
        test_missing_id()
        test_invalid_when_type()
        test_invalid_shift_flags()
        test_minimal_rule()
        test_complex_rule()
        
        print("\n✓ All validation tests passed!")
        sys.exit(0)
        
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
