"""
Test nested signal structure.
Verifies that signals organised in the nested dot-notation hierarchy
are accessible and carry the expected metadata.
"""

import pytest
from src.edmcruleengine.signals_catalog import SignalsCatalog


def test_nested_signals_flattened():
    """Verify nested signals are properly flattened."""
    catalog = SignalsCatalog.from_plugin_dir(".")
    
    # Check that nested signals exist with dot notation
    assert catalog.signal_exists("commander_ranks.combat")
    assert catalog.signal_exists("commander_ranks.trade")
    assert catalog.signal_exists("commander_ranks.explore")
    assert catalog.signal_exists("commander_ranks.empire")
    assert catalog.signal_exists("commander_ranks.federation")
    
    assert catalog.signal_exists("commander_progress.by_rank_type.combat")
    assert catalog.signal_exists("commander_progress.by_rank_type.trade")
    assert catalog.signal_exists("commander_progress.by_rank_type.explore")
    assert catalog.signal_exists("commander_progress.by_rank_type.cqc")
    
    assert catalog.signal_exists("commander_progress.by_faction.empire")
    assert catalog.signal_exists("commander_progress.by_faction.federation")


def test_signal_retrieval_via_new_names():
    """Verify signals can be retrieved using new nested names."""
    catalog = SignalsCatalog.from_plugin_dir(".")
    
    # Get signals using new nested names
    combat_rank = catalog.get_signal("commander_ranks.combat")
    assert combat_rank is not None
    assert combat_rank["type"] == "enum"
    assert combat_rank["title"] == "Combat rank"
    
    combat_progress = catalog.get_signal("commander_progress.by_rank_type.combat")
    assert combat_progress is not None
    assert combat_progress["type"] == "number"
    assert combat_progress["title"] == "Combat rank progress"


def test_all_refactored_signals_have_metadata():
    """Verify all refactored signals have complete metadata."""
    catalog = SignalsCatalog.from_plugin_dir(".")
    
    required_fields = ["type", "title", "ui", "derive"]
    
    # Check new nested signals
    nested_names = [
        "commander_ranks.combat",
        "commander_ranks.trade",
        "commander_ranks.explore",
        "commander_ranks.empire",
        "commander_ranks.federation",
        "commander_progress.by_rank_type.combat",
        "commander_progress.by_rank_type.trade",
        "commander_progress.by_rank_type.explore",
        "commander_progress.by_rank_type.cqc",
        "commander_progress.by_faction.empire",
        "commander_progress.by_faction.federation",
    ]
    
    for signal_name in nested_names:
        signal = catalog.get_signal(signal_name)
        assert signal is not None, f"Signal {signal_name} not found"
        for field in required_fields:
            assert field in signal, f"Signal {signal_name} missing field {field}"


def test_nested_signals_have_category_and_subcategory():
    """Verify nested signals maintain category and subcategory metadata."""
    catalog = SignalsCatalog.from_plugin_dir(".")
    
    # Rank signals should have "Rank" subcategory
    rank_signals = [
        "commander_ranks.combat",
        "commander_ranks.trade",
        "commander_ranks.explore",
        "commander_ranks.empire",
        "commander_ranks.federation",
    ]
    
    for signal_name in rank_signals:
        signal = catalog.get_signal(signal_name)
        assert signal["ui"]["category"] == "Commander"
        assert signal["ui"]["subcategory"] == "Rank"
    
    # Rank progress signals should have "Rank Progress" subcategory
    rank_progress_signals = [
        "commander_progress.by_rank_type.combat",
        "commander_progress.by_rank_type.trade",
        "commander_progress.by_rank_type.explore",
        "commander_progress.by_rank_type.cqc",
    ]
    
    for signal_name in rank_progress_signals:
        signal = catalog.get_signal(signal_name)
        assert signal["ui"]["category"] == "Commander"
        assert signal["ui"]["subcategory"] == "Rank"
    
    # Faction progress signals should also have "Rank" subcategory (merged under Rank)
    faction_progress_signals = [
        "commander_progress.by_faction.empire",
        "commander_progress.by_faction.federation",
    ]
    
    for signal_name in faction_progress_signals:
        signal = catalog.get_signal(signal_name)
        assert signal["ui"]["category"] == "Commander"
        assert signal["ui"]["subcategory"] == "Rank"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
