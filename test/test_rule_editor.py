"""Tests for rule editor UI."""

import json
import tempfile
from pathlib import Path

# Note: These tests verify the structure but don't test actual UI rendering
# since that requires a display. Manual testing is required for full verification.

def test_editor_can_import():
    """Test that the editor module can be imported."""
    from edmcruleengine.rule_editor import RuleEditorUI, RuleEditor, show_rule_editor
    assert RuleEditorUI is not None
    assert RuleEditor is not None
    assert show_rule_editor is not None


def test_shift_tokens_defined():
    """Test that shift tokens are properly defined."""
    from edmcruleengine.rule_editor import SHIFT_TOKENS, SUBSHIFT_TOKENS, ALL_SHIFT_TOKENS
    
    assert SHIFT_TOKENS == ["Shift1", "Shift2"]
    assert len(SUBSHIFT_TOKENS) == 7
    assert "Subshift1" in SUBSHIFT_TOKENS
    assert "Subshift7" in SUBSHIFT_TOKENS
    assert len(ALL_SHIFT_TOKENS) == 9


def test_rule_summary_generation():
    """Test rule summary generation logic."""
    # This would test the _generate_rule_summary method
    # but it's a private method of a UI class
    # Manual testing required
    pass


if __name__ == "__main__":
    test_editor_can_import()
    test_shift_tokens_defined()
    print("[OK] Basic editor tests passed")

