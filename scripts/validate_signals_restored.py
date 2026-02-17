#!/usr/bin/env python3
"""
Validate that all signals have been properly restored and reorganized.

This script checks that:
1. All original signals still exist (either at top level or reorganized)
2. Hierarchical organization is correct
3. No signals were lost in the reorganization
"""

from pathlib import Path
from edmcruleengine.signals_catalog import SignalsCatalog

# Signals that were deleted and then restored under Commander parent
RESTORED_SIGNALS = {
    # Progress signals - now under commander_progress_*
    "commander_progress_combat": "original: combat_progress",
    "commander_progress_trade": "original: trade_progress",
    "commander_progress_explore": "original: explore_progress",
    "commander_progress_empire": "original: empire_progress",
    "commander_progress_federation": "original: federation_progress",
    "commander_progress_cqc": "original: cqc_progress",
    
    # Rank signals - now under commander_rank_*
    "commander_rank_combat": "original: combat_rank",
    "commander_rank_trade": "original: trade_rank",
    "commander_rank_explore": "original: explore_rank",
    "commander_rank_empire": "original: empire_rank",
    "commander_rank_federation": "original: federation_rank",
    
    # Promotion signals - expanded from progress_event
    "commander_promotion.combat": "new: expanded from progress_event",
    "commander_promotion.trade": "new: expanded from progress_event",
    "commander_promotion.explore": "new: expanded from progress_event",
    "commander_promotion.empire": "new: expanded from progress_event",
    "commander_promotion.federation": "new: expanded from progress_event",
    "commander_promotion.soldier": "new: expanded from progress_event",
    "commander_promotion.exobiologist": "new: expanded from progress_event",
    "commander_promotion.mercenary": "new: expanded from progress_event",
    "commander_promotion.cqc": "new: expanded from progress_event",
    
    # Activity signals
    "commander_activity_social": "original: misc_event",
    
    # Merged signals (existed before, still exist)
    "mission_event": "merged with mission_activity",
    "on_foot_location": "merged from foot_location",
    "financial_activity": "moved to Commander category",
}

# Signals that were completely removed (intentional)
COMPLETELY_REMOVED = {
    "presence": "functionality in transport",
    "vehicle": "functionality in transport",
    "mission_activity": "merged into mission_event",
    "progress_event": "expanded into commander_promotion.* (9 signals)",
    "misc_event": "split into commander_activity_social",
    "foot_location": "merged into on_foot_location",
}

def main():
    """Validate signal restoration."""
    print("=" * 70)
    print("SIGNALS CATALOG RESTORATION VALIDATION")
    print("=" * 70)
    
    # Load catalog
    try:
        plugin_dir = Path(__file__).parent.parent
        catalog = SignalsCatalog.from_plugin_dir(str(plugin_dir))
    except Exception as e:
        print(f"❌ Failed to load catalog: {e}")
        return False
    
    # Get all signals from catalog
    all_signals = set(catalog.signals.keys())
    
    print(f"\nTotal signals in catalog: {len(all_signals)}")
    
    # Check restored signals
    print("\n" + "-" * 70)
    print("RESTORED SIGNALS (reorganized under Commander parent):")
    print("-" * 70)
    restored_found = []
    restored_missing = []
    
    for signal_name, description in RESTORED_SIGNALS.items():
        if signal_name in all_signals:
            signal_info = catalog.signals[signal_name]
            print(f"✓ {signal_name:<35} ({description})")
            print(f"  Category: {signal_info.get('ui', {}).get('category', 'N/A')}")
            restored_found.append(signal_name)
        else:
            print(f"✗ {signal_name:<35} MISSING! ({description})")
            restored_missing.append(signal_name)
    
    # Check removed signals
    print("\n" + "-" * 70)
    print("COMPLETELY REMOVED SIGNALS (intentional):")
    print("-" * 70)
    removed_correct = []
    removed_not_removed = []
    
    for signal_name, reason in COMPLETELY_REMOVED.items():
        if signal_name not in all_signals:
            print(f"✓ {signal_name:<35} removed correctly ({reason})")
            removed_correct.append(signal_name)
        else:
            print(f"✗ {signal_name:<35} STILL EXISTS! ({reason})")
            removed_not_removed.append(signal_name)
    
    # Summary
    print("\n" + "=" * 70)
    print("VALIDATION SUMMARY:")
    print("=" * 70)
    print(f"✓ Restored signals found:       {len(restored_found)}/{len(RESTORED_SIGNALS)}")
    print(f"✗ Restored signals missing:     {len(restored_missing)}/{len(RESTORED_SIGNALS)}")
    print(f"✓ Removed signals confirmed:    {len(removed_correct)}/{len(COMPLETELY_REMOVED)}")
    print(f"✗ Removed signals still exist:  {len(removed_not_removed)}/{len(COMPLETELY_REMOVED)}")
    print("=" * 70)
    
    # Success check
    success = (
        len(restored_missing) == 0 and
        len(removed_not_removed) == 0
    )
    
    if success:
        print("\n✅ All signals properly restored and reorganized!")
        print("\nOrganization structure:")
        print("  - commander_progress_* → rank progression values")
        print("  - commander_rank_* → rank enum values")
        print("  - commander_activity_* → special events")
        print("  - mission_event → includes mission_activity values")
        print("  - on_foot_location → merged from foot_location")
        print("  - financial_activity → moved to Commander category")
        return True
    else:
        print("\n❌ Some signals are missing or still present!")
        if restored_missing:
            print(f"\nMissing restored signals: {restored_missing}")
        if removed_not_removed:
            print(f"\nSignals that should be removed: {removed_not_removed}")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
