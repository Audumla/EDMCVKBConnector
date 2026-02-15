"""
Tests for multi-source signal derivation using production-like data.

Tests the new multi-source signal system that combines:
- Dashboard flags (Status.json ~1Hz updates)
- Journal events (event-driven)
- Recent event tracking (time-windowed)
- Complex derive operations (and, or, recent)
"""

import json
import time
import pytest
from pathlib import Path

from edmcruleengine.signals_catalog import SignalsCatalog
from edmcruleengine.signal_derivation import SignalDerivation


class TestMultiSourceSignalDerivation:
    """Test multi-source signal derivation with production-like data."""
    
    @pytest.fixture
    def catalog(self):
        """Load catalog for tests."""
        catalog_path = Path(__file__).parent.parent / "signals_catalog.json"
        return SignalsCatalog.from_file(catalog_path)
    
    @pytest.fixture
    def derivation(self, catalog):
        """Create derivation engine."""
        return SignalDerivation(catalog._data)
    
    def test_dashboard_only_signals(self, derivation):
        """Test signals derived from dashboard flags only."""
        # Simulate Status.json update with ship in space, hardpoints deployed
        entry = {
            "event": "Status",
            "Flags": 0b01000000,  # Bit 6 = hardpoints deployed
            "Flags2": 0,
            "GuiFocus": 0,
            "Pips": [4, 4, 4],
            "Fuel": {"FuelMain": 16.0, "FuelReservoir": 0.63}
        }
        
        signals = derivation.derive_all_signals(entry)
        
        # Check hardpoints signal (enum from flag)
        assert "hardpoints" in signals
        assert signals["hardpoints"] == "deployed"
        
        # Check GUI focus (enum from path)
        assert signals["gui_focus"] == "NoFocus"
        
        # Check docking state (no recent events, should be based on flags only)
        assert signals["docking_state"] == "in_space"
    
    def test_docked_state_dashboard_flag(self, derivation):
        """Test docked state derived from dashboard flag."""
        entry = {
            "event": "Status",
            "Flags": 0b00000001,  # Bit 0 = docked
            "Flags2": 0,
            "GuiFocus": 5,  # Station services
            "Pips": [4, 4, 4]
        }
        
        signals = derivation.derive_all_signals(entry)
        
        # Should show docked based on flag
        assert signals["docking_state"] == "docked"
        assert signals["gui_focus"] == "StationServices"
    
    def test_landed_state_dashboard_flag(self, derivation):
        """Test landed state derived from dashboard flag."""
        entry = {
            "event": "Status",
            "Flags": 0b00000010,  # Bit 1 = landed
            "Flags2": 0,
            "GuiFocus": 0
        }
        
        signals = derivation.derive_all_signals(entry)
        
        # Should show landed based on flag
        assert signals["docking_state"] == "landed"
    
    def test_just_docked_edge_detection(self, derivation):
        """Test 'just docked' edge detection with recent event."""
        # Simulate dashboard status showing docked flag
        entry = {
            "event": "Status",
            "Flags": 0b00000001,  # Bit 0 = docked
            "Flags2": 0,
            "GuiFocus": 5
        }
        
        # Context shows Docked event occurred 1 second ago
        context = {
            "recent_events": {
                "Docked": time.time() - 1.0  # 1 second ago
            }
        }
        
        signals = derivation.derive_all_signals(entry, context)
        
        # Should show "just_docked" because flag is set AND event is recent
        assert signals["docking_state"] == "just_docked"
    
    def test_just_docked_expired(self, derivation):
        """Test that 'just docked' expires after time window."""
        entry = {
            "event": "Status",
            "Flags": 0b00000001,  # Bit 0 = docked
            "Flags2": 0,
            "GuiFocus": 5
        }
        
        # Context shows Docked event occurred 5 seconds ago (outside 3s window)
        context = {
            "recent_events": {
                "Docked": time.time() - 5.0  # 5 seconds ago
            }
        }
        
        signals = derivation.derive_all_signals(entry, context)
        
        # Should revert to "docked" (not "just_docked") as event is too old
        assert signals["docking_state"] == "docked"
    
    def test_just_undocked_recent_event_only(self, derivation):
        """Test 'just undocked' detection from recent event."""
        entry = {
            "event": "Status",
            "Flags": 0,  # No docked flag
            "Flags2": 0,
            "GuiFocus": 0
        }
        
        context = {
            "recent_events": {
                "Undocked": time.time() - 1.0  # 1 second ago
            }
        }
        
        signals = derivation.derive_all_signals(entry, context)
        
        # Should show "just_undocked"
        assert signals["docking_state"] == "just_undocked"
    
    def test_just_landed_edge_detection(self, derivation):
        """Test 'just landed' edge detection."""
        entry = {
            "event": "Status",
            "Flags": 0b00000010,  # Bit 1 = landed
            "Flags2": 0,
            "GuiFocus": 0
        }
        
        context = {
            "recent_events": {
                "Touchdown": time.time() - 1.0
            }
        }
        
        signals = derivation.derive_all_signals(entry, context)
        
        assert signals["docking_state"] == "just_landed"
    
    def test_just_lifted_off_recent_event(self, derivation):
        """Test 'just lifted off' detection."""
        entry = {
            "event": "Status",
            "Flags": 0,  # Not landed
            "Flags2": 0,
            "GuiFocus": 0
        }
        
        context = {
            "recent_events": {
                "Liftoff": time.time() - 2.0
            }
        }
        
        signals = derivation.derive_all_signals(entry, context)
        
        assert signals["docking_state"] == "just_lifted_off"
    
    def test_multiple_recent_events_priority(self, derivation):
        """Test that first_match respects priority order."""
        entry = {
            "event": "Status",
            "Flags": 0b00000001,  # Docked flag set
            "Flags2": 0,
            "GuiFocus": 5
        }
        
        # Both Docked and Touchdown are recent
        context = {
            "recent_events": {
                "Docked": time.time() - 1.0,
                "Touchdown": time.time() - 0.5
            }
        }
        
        signals = derivation.derive_all_signals(entry, context)
        
        # Should prioritize just_docked over just_landed based on first_match order
        assert signals["docking_state"] == "just_docked"


class TestProductionJournalSequences:
    """Test realistic journal event sequences."""
    
    @pytest.fixture
    def catalog(self):
        """Load catalog."""
        catalog_path = Path(__file__).parent.parent / "signals_catalog.json"
        return SignalsCatalog.from_file(catalog_path)
    
    @pytest.fixture
    def derivation(self, catalog):
        """Create derivation engine."""
        return SignalDerivation(catalog._data)
    
    def test_docking_sequence(self, derivation):
        """Test complete docking sequence from approach to docked."""
        # Step 1: Approaching station, request docking
        context1 = {
            "recent_events": {
                "DockingRequested": time.time()
            }
        }
        entry1 = {"Flags": 0, "Flags2": 0, "GuiFocus": 0}
        signals1 = derivation.derive_all_signals(entry1, context1)
        assert signals1["docking_state"] == "in_space"
        
        # Step 2: Docking granted
        context2 = {
            "recent_events": {
                "DockingGranted": time.time()
            }
        }
        signals2 = derivation.derive_all_signals(entry1, context2)
        assert signals2["docking_state"] == "in_space"
        
        # Step 3: Just docked - event + flag
        context3 = {
            "recent_events": {
                "Docked": time.time()
            }
        }
        entry3 = {"Flags": 0b00000001, "Flags2": 0, "GuiFocus": 5}
        signals3 = derivation.derive_all_signals(entry3, context3)
        assert signals3["docking_state"] == "just_docked"
        
        # Step 4: 5 seconds later, event expired
        context4 = {
            "recent_events": {
                "Docked": time.time() - 5.0
            }
        }
        signals4 = derivation.derive_all_signals(entry3, context4)
        assert signals4["docking_state"] == "docked"
    
    def test_fsd_jump_sequence(self, derivation):
        """Test FSD jump sequence."""
        # In supercruise
        entry_sc = {
            "Flags": 0b00010000,  # Bit 4 = supercruise
            "Flags2": 0,
            "GuiFocus": 0
        }
        signals_sc = derivation.derive_all_signals(entry_sc)
        assert signals_sc["supercruise_state"] == "on"
        
        # FSD charging for jump
        entry_charging = {
            "Flags": 0b00010000 | 0b00100000000000000000,  # SC + FSD charging (bit 17)
            "Flags2": 0,
            "GuiFocus": 0
        }
        signals_charging = derivation.derive_all_signals(entry_charging)
        # Should still be in supercruise
        assert signals_charging["supercruise_state"] == "on"
        
        # Just completed jump
        context_jumped = {
            "recent_events": {
                "FSDJump": time.time()
            }
        }
        entry_jumped = {
            "Flags": 0b00010000,  # Back in supercruise
            "Flags2": 0,
            "GuiFocus": 0
        }
        signals_jumped = derivation.derive_all_signals(entry_jumped, context_jumped)
        assert signals_jumped["supercruise_state"] == "on"
    
    def test_combat_scenario(self, derivation):
        """Test combat flag transitions."""
        # Hardpoints retracted, shields up
        entry1 = {
            "Flags": 0b00001000,  # Bit 3 = shields up
            "Flags2": 0,
            "GuiFocus": 0
        }
        signals1 = derivation.derive_all_signals(entry1)
        assert signals1["hardpoints"] == "retracted"
        
        # Deploy hardpoints
        entry2 = {
            "Flags": 0b01001000,  # Shields + hardpoints (bit 6)
            "Flags2": 0,
            "GuiFocus": 0
        }
        signals2 = derivation.derive_all_signals(entry2)
        assert signals2["hardpoints"] == "deployed"
        
        # Under attack (recent event)
        context3 = {
            "recent_events": {
                "UnderAttack": time.time()
            }
        }
        signals3 = derivation.derive_all_signals(entry2, context3)
        assert signals3["hardpoints"] == "deployed"


class TestRealJournalData:
    """Test with real journal file data."""
    
    @pytest.fixture
    def catalog(self):
        """Load catalog."""
        catalog_path = Path(__file__).parent.parent / "signals_catalog.json"
        return SignalsCatalog.from_file(catalog_path)
    
    @pytest.fixture
    def derivation(self, catalog):
        """Create derivation engine."""
        return SignalDerivation(catalog._data)
    
    @pytest.fixture
    def journal_events(self):
        """Load real journal events from fixture."""
        journal_path = Path(__file__).parent / "fixtures" / "Journal.2026-02-13T120000.01.log"
        events = []
        with open(journal_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        events.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
        return events
    
    def test_process_real_journal_events(self, derivation, journal_events):
        """Test processing real journal events."""
        print(f"\nProcessing {len(journal_events)} real journal events...")
        
        recent_events = {}
        successful_signals = []
        
        for event in journal_events:
            event_name = event.get("event")
            if not event_name:
                continue
            
            # Track event timestamp
            recent_events[event_name] = time.time()
            
            # Prune old events (older than 5 seconds)
            cutoff = time.time() - 5.0
            recent_events = {k: v for k, v in recent_events.items() if v >= cutoff}
            
            # Build context
            context = {"recent_events": recent_events}
            
            # Derive signals
            try:
                signals = derivation.derive_all_signals(event, context)
                successful_signals.append((event_name, len(signals)))
                
                # Validate key signals
                assert "gui_focus" in signals
                assert "docking_state" in signals
                
                print(f"  ✓ {event_name}: {len(signals)} signals derived")
                
            except Exception as e:
                print(f"  ✗ {event_name}: Failed - {e}")
                raise
        
        print(f"\n✓ Successfully processed {len(successful_signals)} events")
        assert len(successful_signals) >= 8  # Should process at least 8 events
    
    def test_docked_event_from_real_journal(self, derivation, journal_events):
        """Test Docked event processing."""
        # Find Docked event in real journal
        docked_event = next((e for e in journal_events if e.get("event") == "Docked"), None)
        assert docked_event is not None, "Docked event not found in journal"
        
        # Simulate the context
        context = {
            "recent_events": {
                "Docked": time.time()
            }
        }
        
        # Add dashboard flags showing docked state
        docked_event["Flags"] = 0b00000001
        docked_event["Flags2"] = 0
        docked_event["GuiFocus"] = 5
        
        signals = derivation.derive_all_signals(docked_event, context)
        
        # Should detect just_docked state
        assert signals["docking_state"] == "just_docked"
        
        print(f"\n✓ Docked event: station={docked_event.get('StationName')}, type={docked_event.get('StationType')}")
    
    def test_fsd_jump_from_real_journal(self, derivation, journal_events):
        """Test FSDJump event processing."""
        # Find FSDJump event
        jump_event = next((e for e in journal_events if e.get("event") == "FSDJump"), None)
        assert jump_event is not None, "FSDJump event not found in journal"
        
        context = {
            "recent_events": {
                "FSDJump": time.time()
            }
        }
        
        # Add dashboard flags showing supercruise
        jump_event["Flags"] = 0b00010000  # Bit 4 = supercruise
        jump_event["Flags2"] = 0
        jump_event["GuiFocus"] = 0
        
        signals = derivation.derive_all_signals(jump_event, context)
        
        # Verify key signals
        assert signals["supercruise_state"] == "on"
        
        system = jump_event.get("StarSystem")
        jump_dist = jump_event.get("JumpDist")
        print(f"\n✓ FSDJump: system={system}, distance={jump_dist:.2f}ly")


class TestOperators:
    """Test new derivation operators (recent, and, or)."""
    
    @pytest.fixture
    def catalog(self):
        """Load catalog."""
        catalog_path = Path(__file__).parent.parent / "signals_catalog.json"
        return SignalsCatalog.from_file(catalog_path)
    
    @pytest.fixture
    def derivation(self, catalog):
        """Create derivation engine."""
        return SignalDerivation(catalog._data)
    
    def test_recent_operator(self, derivation):
        """Test the 'recent' operator."""
        # Event within window
        context_recent = {
            "recent_events": {
                "Docked": time.time() - 1.0
            }
        }
        entry = {"Flags": 0, "Flags2": 0}
        
        # The signal derivation will use recent operator internally
        # We can verify it works through docking_state signal
        signals = derivation.derive_all_signals(entry, context_recent)
        # Without docked flag, should not trigger just_docked
        assert signals["docking_state"] != "just_docked"
        
        # But with flag + recent event, should trigger
        entry["Flags"] = 0b00000001
        signals2 = derivation.derive_all_signals(entry, context_recent)
        assert signals2["docking_state"] == "just_docked"
    
    def test_and_operator(self, derivation):
        """Test the 'and' operator in docking_state."""
        # just_docked requires BOTH recent event AND flag
        entry = {"Flags": 0b00000001, "Flags2": 0, "GuiFocus": 0}
        
        # Case 1: Event recent, flag set → just_docked
        context1 = {"recent_events": {"Docked": time.time() - 1.0}}
        signals1 = derivation.derive_all_signals(entry, context1)
        assert signals1["docking_state"] == "just_docked"
        
        # Case 2: Event recent, flag NOT set → NOT just_docked
        entry2 = {"Flags": 0, "Flags2": 0, "GuiFocus": 0}
        signals2 = derivation.derive_all_signals(entry2, context1)
        assert signals2["docking_state"] != "just_docked"
        
        # Case 3: Event NOT recent, flag set → NOT just_docked
        context3 = {"recent_events": {"Docked": time.time() - 10.0}}
        signals3 = derivation.derive_all_signals(entry, context3)
        assert signals3["docking_state"] != "just_docked"
    
    def test_or_operator_fallback(self, derivation):
        """Test OR-like behavior with first_match fallbacks."""
        # docking_state uses first_match which acts like OR with priority
        entry = {"Flags": 0, "Flags2": 0}
        
        # Multiple recent events - first match wins
        context = {
            "recent_events": {
                "Undocked": time.time() - 1.0,
                "Liftoff": time.time() - 0.5
            }
        }
        
        signals = derivation.derive_all_signals(entry, context)
        # Undocked is checked first in first_match, so it wins
        assert signals["docking_state"] == "just_undocked"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
