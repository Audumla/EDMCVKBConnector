"""
EDMC Integration Tests - Validate actual Elite Dangerous event flow.

Tests the complete path from EDMC journal events through the event handler
to signal derivation and rule evaluation, ensuring all components work
correctly with real Elite Dangerous data.
"""

import json
import time
import pytest
from pathlib import Path
from unittest.mock import Mock, call

from edmcruleengine.event_handler import EventHandler
from edmcruleengine.config import Config
from edmcruleengine.signals_catalog import SignalsCatalog


class TestEDMCIntegration:
    """Test complete EDMC event processing flow."""
    
    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return Config()
    
    @pytest.fixture
    def handler(self, config):
        """Create event handler with mocked VKB client."""
        handler = EventHandler(config, plugin_dir=str(Path(__file__).parent.parent))
        handler.vkb_client.send_event = Mock(return_value=True)
        handler.vkb_client.connect = Mock(return_value=True)
        return handler
    
    def test_event_tracking_lifecycle(self, handler):
        """Test that events are tracked and pruned correctly."""
        # Send first event
        handler.handle_event("Docked", {"StationName": "Test Station"}, source="journal")
        
        # Verify event is tracked
        assert "Docked" in handler._recent_events
        docked_time = handler._recent_events["Docked"]
        assert docked_time > 0
        
        # Send another event
        time.sleep(0.1)
        handler.handle_event("Undocked", {"StationName": "Test Station"}, source="journal")
        
        # Both should be tracked
        assert "Docked" in handler._recent_events
        assert "Undocked" in handler._recent_events
        assert handler._recent_events["Undocked"] > docked_time
        
        # Manually set old timestamp (simulate 10 seconds passing)
        handler._recent_events["Docked"] = time.time() - 10
        
        # Send new event to trigger pruning
        handler.handle_event("FSDJump", {"StarSystem": "Sol"}, source="journal")
        
        # Old event should be pruned (> 5 second window)
        assert "Docked" not in handler._recent_events
        assert "Undocked" in handler._recent_events  # Still recent
        assert "FSDJump" in handler._recent_events
    
    def test_context_building(self, handler):
        """Test that context is built correctly for signal derivation."""
        # Track some events
        handler.handle_event("DockingRequested", {"StationName": "Jameson"}, source="journal")
        time.sleep(0.05)
        handler.handle_event("DockingGranted", {"StationName": "Jameson", "LandingPad": 7}, source="journal")
        
        # Verify context is available with recent events
        assert "DockingRequested" in handler._recent_events
        assert "DockingGranted" in handler._recent_events
        
        # Context should have timestamps
        assert handler._recent_events["DockingRequested"] < handler._recent_events["DockingGranted"]
    
    def test_docking_sequence_with_signals(self, handler):
        """Test complete docking sequence generates correct signals."""
        # Create a test rule that triggers on docking
        rules_content = {
            "rules": [{
                "id": "test_docking",
                "description": "Test docking detection",
                "condition": {"signal": "docking_state", "equals": "just_docked"},
                "actions": [{"vkb_set_shift": ["Shift1"]}]
            }]
        }
        
        # Write temporary rules file
        rules_path = Path(__file__).parent / "temp_docking_rules.json"
        with open(rules_path, "w") as f:
            json.dump(rules_content, f)
        
        try:
            handler.config.set("rules_path", str(rules_path))
            handler._load_rules()
            
            # Reset VKB mock
            handler.vkb_client.send_event.reset_mock()
            
            # Step 1: Request docking
            handler.handle_event(
                "DockingRequested",
                {
                    "timestamp": "2026-02-16T12:00:00Z",
                    "event": "DockingRequested",
                    "StationName": "Jameson Memorial"
                },
                source="journal"
            )
            
            # Step 2: Docking granted (small delay)
            time.sleep(0.1)
            handler.handle_event(
                "DockingGranted",
                {
                    "timestamp": "2026-02-16T12:00:05Z",
                    "event": "DockingGranted",
                    "StationName": "Jameson Memorial",
                    "LandingPad": 7
                },
                source="journal"
            )
            
            # Step 3: Dashboard shows docked flag + recent Docked event
            time.sleep(0.1)
            handler.handle_event(
                "Docked",
                {
                    "timestamp": "2026-02-16T12:00:15Z",
                    "event": "Docked",
                    "StationName": "Jameson Memorial",
                    "StationType": "Coriolis"
                },
                source="journal"
            )
            
            # Simulate dashboard update showing docked flag
            time.sleep(0.1)
            handler.handle_event(
                "Status",
                {
                    "timestamp": "2026-02-16T12:00:16Z",
                    "event": "Status",
                    "Flags": 0b00000001,  # Bit 0 = docked
                    "Flags2": 0,
                    "GuiFocus": 5,  # Station services
                    "Pips": [4, 4, 4],
                    "Fuel": {"FuelMain": 16.0, "FuelReservoir": 0.63}
                },
                source="dashboard"
            )
            
            # VKB command should have been sent for docking
            # (Rule triggers when docking_state == just_docked)
            assert handler.vkb_client.send_event.called
            
        finally:
            # Cleanup
            if rules_path.exists():
                rules_path.unlink()
    
    def test_fsd_jump_sequence(self, handler):
        """Test FSD jump sequence with multi-source signals."""
        # Step 1: StartJump event
        handler.handle_event(
            "StartJump",
            {
                "timestamp": "2026-02-16T13:00:00Z",
                "event": "StartJump",
                "JumpType": "Hyperspace",
                "StarSystem": "Sol",
                "SystemAddress": 10477373803,
                "StarClass": "G"
            },
            source="journal"
        )
        
        # Verify event tracking
        assert "StartJump" in handler._recent_events
        
        # Step 2: FSD charging flag on dashboard
        time.sleep(0.1)
        handler.handle_event(
            "Status",
            {
                "timestamp": "2026-02-16T13:00:01Z",
                "event": "Status",
                "Flags": 0b00000000000100000000000000000000,  # Bit 17 = FSD Charging
                "Flags2": 0,
                "GuiFocus": 0,
                "Pips": [4, 4, 4]
            },
            source="dashboard"
        )
        
        # Step 3: FSD jump flag (during jump)
        time.sleep(0.5)
        handler.handle_event(
            "Status",
            {
                "timestamp": "2026-02-16T13:00:08Z",
                "event": "Status",
                "Flags": 0b01000000000000000000000000000000,  # Bit 30 = FSD Jump
                "Flags2": 0,
                "GuiFocus": 0,
                "Pips": [4, 4, 4]
            },
            source="dashboard"
        )
        
        # Step 4: FSDJump event (arrival)
        time.sleep(0.5)
        handler.handle_event(
            "FSDJump",
            {
                "timestamp": "2026-02-16T13:00:10Z",
                "event": "FSDJump",
                "StarSystem": "Sol",
                "SystemAddress": 10477373803,
                "StarPos": [0.0, 0.0, 0.0],
                "JumpDist": 0.0,
                "FuelUsed": 0.916290,
                "FuelLevel": 15.083710
            },
            source="journal"
        )
        
        # Verify both events tracked
        assert "StartJump" in handler._recent_events
        assert "FSDJump" in handler._recent_events
        
        # FSDJump should be more recent
        assert handler._recent_events["FSDJump"] > handler._recent_events["StartJump"]
    
    def test_combat_sequence_with_damage(self, handler):
        """Test combat sequence with damage tracking."""
        # Step 1: Under attack
        handler.handle_event(
            "UnderAttack",
            {
                "timestamp": "2026-02-16T14:00:00Z",
                "event": "UnderAttack",
                "Target": "You"
            },
            source="journal"
        )
        
        assert "UnderAttack" in handler._recent_events
        
        # Step 2: Hull damage
        time.sleep(0.1)
        handler.handle_event(
            "HullDamage",
            {
                "timestamp": "2026-02-16T14:00:02Z",
                "event": "HullDamage",
                "Health": 0.85,
                "PlayerPilot": True,
                "Fighter": False
            },
            source="journal"
        )
        
        assert "HullDamage" in handler._recent_events
        
        # Step 3: Shields down
        time.sleep(0.1)
        handler.handle_event(
            "ShieldState",
            {
                "timestamp": "2026-02-16T14:00:03Z",
                "event": "ShieldState",
                "ShieldsUp": False
            },
            source="journal"
        )
        
        assert "ShieldState" in handler._recent_events
        
        # All combat events should be tracked
        assert len(handler._recent_events) >= 3
    
    def test_supercruise_transitions(self, handler):
        """Test supercruise entry and exit with signals."""
        # Step 1: Enter supercruise
        handler.handle_event(
            "SupercruiseEntry",
            {
                "timestamp": "2026-02-16T15:00:00Z",
                "event": "SupercruiseEntry",
                "StarSystem": "LHS 3447",
                "SystemAddress": 33656303199641
            },
            source="journal"
        )
        
        assert "SupercruiseEntry" in handler._recent_events
        
        # Step 2: Dashboard shows supercruise flag
        time.sleep(0.1)
        handler.handle_event(
            "Status",
            {
                "timestamp": "2026-02-16T15:00:01Z",
                "event": "Status",
                "Flags": 0b00000000000000000000000000010000,  # Bit 4 = Supercruise
                "Flags2": 0,
                "GuiFocus": 0,
                "Pips": [4, 4, 4]
            },
            source="dashboard"
        )
        
        # Step 3: Exit supercruise
        time.sleep(1.0)
        handler.handle_event(
            "SupercruiseExit",
            {
                "timestamp": "2026-02-16T15:01:00Z",
                "event": "SupercruiseExit",
                "StarSystem": "LHS 3447",
                "SystemAddress": 33656303199641,
                "Body": "Trevithick Dock",
                "BodyType": "Station"
            },
            source="journal"
        )
        
        assert "SupercruiseExit" in handler._recent_events
        
        # Step 4: Dashboard clears supercruise flag
        time.sleep(0.1)
        handler.handle_event(
            "Status",
            {
                "timestamp": "2026-02-16T15:01:01Z",
                "event": "Status",
                "Flags": 0b00000000,  # No supercruise flag
                "Flags2": 0,
                "GuiFocus": 0,
                "Pips": [4, 4, 4]
            },
            source="dashboard"
        )
        
        # Both transition events should be tracked
        assert "SupercruiseEntry" in handler._recent_events
        assert "SupercruiseExit" in handler._recent_events
    
    def test_event_window_timing(self, handler):
        """Test that event window works correctly."""
        # Default window is 5 seconds
        assert handler._event_window_seconds == 5
        
        # Track an event
        handler.handle_event("Scan", {"BodyName": "Earth"}, source="journal")
        assert "Scan" in handler._recent_events
        
        # Manually age the event to 6 seconds old
        handler._recent_events["Scan"] = time.time() - 6
        
        # Trigger pruning with new event
        handler.handle_event("FSSDiscoveryScan", {"BodyCount": 10}, source="journal")
        
        # Old event should be gone
        assert "Scan" not in handler._recent_events
        assert "FSSDiscoveryScan" in handler._recent_events
    
    def test_dashboard_vs_journal_source(self, handler):
        """Test that only journal events are tracked, not dashboard."""
        # Send dashboard event (Status updates)
        handler.handle_event(
            "Status",
            {
                "timestamp": "2026-02-16T16:00:00Z",
                "event": "Status",
                "Flags": 0,
                "Flags2": 0,
                "GuiFocus": 0,
                "Pips": [4, 4, 4]
            },
            source="dashboard"
        )
        
        # Status events from dashboard should NOT be tracked
        assert "Status" not in handler._recent_events
        
        # Send journal event
        handler.handle_event(
            "Docked",
            {
                "timestamp": "2026-02-16T16:00:01Z",
                "event": "Docked",
                "StationName": "Test"
            },
            source="journal"
        )
        
        # Journal events SHOULD be tracked
        assert "Docked" in handler._recent_events
    
    def test_exploration_sequence(self, handler):
        """Test exploration event sequence."""
        # Step 1: FSS honk
        handler.handle_event(
            "FSSDiscoveryScan",
            {
                "timestamp": "2026-02-16T17:00:00Z",
                "event": "FSSDiscoveryScan",
                "Progress": 0.500000,
                "BodyCount": 12,
                "NonBodyCount": 3
            },
            source="journal"
        )
        
        assert "FSSDiscoveryScan" in handler._recent_events
        
        # Step 2: Discover signals
        time.sleep(0.2)
        handler.handle_event(
            "FSSSignalDiscovered",
            {
                "timestamp": "2026-02-16T17:00:05Z",
                "event": "FSSSignalDiscovered",
                "SignalName": "$FIXED_EVENT_CAPSHIP;",
                "IsStation": False
            },
            source="journal"
        )
        
        assert "FSSSignalDiscovered" in handler._recent_events
        
        # Step 3: Scan body
        time.sleep(0.2)
        handler.handle_event(
            "Scan",
            {
                "timestamp": "2026-02-16T17:00:10Z",
                "event": "Scan",
                "ScanType": "Detailed",
                "BodyName": "Earth",
                "BodyID": 3,
                "PlanetClass": "Earthlike body",
                "Landable": False
            },
            source="journal"
        )
        
        assert "Scan" in handler._recent_events
        
        # Step 4: SAA scan
        time.sleep(0.2)
        handler.handle_event(
            "SAAScanComplete",
            {
                "timestamp": "2026-02-16T17:00:20Z",
                "event": "SAAScanComplete",
                "BodyName": "Earth",
                "BodyID": 3,
                "ProbesUsed": 6,
                "EfficiencyTarget": 8
            },
            source="journal"
        )
        
        assert "SAAScanComplete" in handler._recent_events
        
        # All exploration events tracked
        assert len(handler._recent_events) == 4
    
    def test_mission_lifecycle(self, handler):
        """Test mission acceptance through completion."""
        # Accept mission
        handler.handle_event(
            "MissionAccepted",
            {
                "timestamp": "2026-02-16T18:00:00Z",
                "event": "MissionAccepted",
                "Faction": "Pilots Federation",
                "Name": "Mission_Delivery",
                "MissionID": 123456,
                "Commodity": "$Gold_Name;",
                "Count": 10
            },
            source="journal"
        )
        
        assert "MissionAccepted" in handler._recent_events
        
        # Complete mission
        time.sleep(0.5)
        handler.handle_event(
            "MissionCompleted",
            {
                "timestamp": "2026-02-16T18:15:00Z",
                "event": "MissionCompleted",
                "Faction": "Pilots Federation",
                "Name": "Mission_Delivery",
                "MissionID": 123456,
                "Reward": 75000
            },
            source="journal"
        )
        
        assert "MissionCompleted" in handler._recent_events
    
    def test_trading_workflow(self, handler):
        """Test commodity trading sequence."""
        # Buy commodities
        handler.handle_event(
            "MarketBuy",
            {
                "timestamp": "2026-02-16T19:00:00Z",
                "event": "MarketBuy",
                "MarketID": 128666762,
                "Type": "gold",
                "Count": 10,
                "BuyPrice": 9000,
                "TotalCost": 90000
            },
            source="journal"
        )
        
        assert "MarketBuy" in handler._recent_events
        
        # Sell commodities
        time.sleep(0.5)
        handler.handle_event(
            "MarketSell",
            {
                "timestamp": "2026-02-16T19:10:00Z",
                "event": "MarketSell",
                "MarketID": 128666763,
                "Type": "gold",
                "Count": 10,
                "SellPrice": 10000,
                "TotalSale": 100000
            },
            source="journal"
        )
        
        assert "MarketSell" in handler._recent_events
    
    def test_real_journal_sequence(self, handler):
        """Test with a realistic journal event sequence."""
        # Simulate a complete gaming loop
        events = [
            ("LoadGame", {
                "timestamp": "2026-02-16T20:00:00Z",
                "event": "LoadGame",
                "Commander": "TestCmdr",
                "Ship": "CobraMkIII",
                "ShipID": 1,
                "Credits": 500000
            }),
            ("Location", {
                "timestamp": "2026-02-16T20:00:01Z",
                "event": "Location",
                "Docked": True,
                "StationName": "Jameson Memorial",
                "StarSystem": "Shinrarta Dezhra",
                "SystemAddress": 3932277478106
            }),
            ("Undocked", {
                "timestamp": "2026-02-16T20:00:30Z",
                "event": "Undocked",
                "StationName": "Jameson Memorial"
            }),
            ("StartJump", {
                "timestamp": "2026-02-16T20:01:00Z",
                "event": "StartJump",
                "JumpType": "Supercruise"
            }),
            ("SupercruiseEntry", {
                "timestamp": "2026-02-16T20:01:05Z",
                "event": "SupercruiseEntry",
                "StarSystem": "Shinrarta Dezhra",
                "SystemAddress": 3932277478106
            }),
            ("FSSDiscoveryScan", {
                "timestamp": "2026-02-16T20:01:10Z",
                "event": "FSSDiscoveryScan",
                "Progress": 1.0,
                "BodyCount": 8,
                "NonBodyCount": 2
            }),
            ("SupercruiseExit", {
                "timestamp": "2026-02-16T20:02:00Z",
                "event": "SupercruiseExit",
                "StarSystem": "Shinrarta Dezhra",
                "SystemAddress": 3932277478106,
                "Body": "Planet A",
                "BodyType": "Planet"
            }),
        ]
        
        # Process all events
        for event_type, event_data in events:
            handler.handle_event(event_type, event_data, source="journal")
            time.sleep(0.01)  # Small delay between events
        
        # Verify tracking
        # Older events (LoadGame, Location) should still be in window
        assert "LoadGame" in handler._recent_events or "Undocked" in handler._recent_events
        # Recent events should definitely be there
        assert "SupercruiseExit" in handler._recent_events
        assert "FSSDiscoveryScan" in handler._recent_events


class TestSignalResolutionWithRealData:
    """Test that signals resolve correctly with real Elite Dangerous data."""
    
    @pytest.fixture
    def handler(self, config):
        """Create handler."""
        handler = EventHandler(config, plugin_dir=str(Path(__file__).parent.parent))
        handler.vkb_client.send_event = Mock(return_value=True)
        handler.vkb_client.connect = Mock(return_value=True)
        return handler
    
    @pytest.fixture
    def config(self):
        """Create config."""
        return Config()
    
    def test_all_event_types_resolve(self, handler):
        """Test that a variety of event types all resolve without errors."""
        # Mix of different event types
        test_events = [
            ("FileHeader", {"event": "FileHeader", "part": 1}),
            ("LoadGame", {"event": "LoadGame", "Commander": "Test"}),
            ("Location", {"event": "Location", "StarSystem": "Sol"}),
            ("FSDJump", {"event": "FSDJump", "StarSystem": "LHS 3447"}),
            ("Docked", {"event": "Docked", "StationName": "Station"}),
            ("Undocked", {"event": "Undocked", "StationName": "Station"}),
            ("Scan", {"event": "Scan", "BodyName": "Earth"}),
            ("MarketBuy", {"event": "MarketBuy", "Type": "gold", "Count": 1}),
            ("MissionAccepted", {"event": "MissionAccepted", "MissionID": 1}),
            ("Bounty", {"event": "Bounty", "TotalReward": 1000}),
            ("UnderAttack", {"event": "UnderAttack", "Target": "You"}),
            ("FuelScoop", {"event": "FuelScoop", "Scooped": 1.0, "Total": 8.0}),
            ("CollectCargo", {"event": "CollectCargo", "Type": "gold"}),
            ("Repair", {"event": "Repair", "Item": "hull"}),
            ("Loadout", {"event": "Loadout", "Ship": "sidewinder"}),
        ]
        
        # All events should process without errors
        for event_type, event_data in test_events:
            try:
                handler.handle_event(event_type, event_data, source="journal")
            except Exception as e:
                pytest.fail(f"Event {event_type} failed to process: {e}")
        
        # Verify events were tracked
        assert len(handler._recent_events) > 0
    
    def test_event_signals_are_generated(self, handler):
        """Test that event-type signals are properly generated."""
        # Send an event that has an event-type signal
        handler.handle_event(
            "Docked",
            {
                "timestamp": "2026-02-16T21:00:00Z",
                "event": "Docked",
                "StationName": "Test Station",
                "StationType": "Coriolis"
            },
            source="journal"
        )
        
        # Verify rule engine has access to signal derivation
        assert handler.rule_engine is not None
        assert handler.rule_engine.signal_derivation is not None
        
        # Derive signals manually to verify
        from edmcruleengine.signal_derivation import SignalDerivation
        import time
        
        derivation = SignalDerivation(handler.catalog._data)
        event_data = {
            "event": "Docked",
            "StationName": "Test Station"
        }
        
        # Build context with recent event
        context = {"recent_events": {event_data["event"]: time.time()}}
        signals = derivation.derive_all_signals(event_data, context)
        
        # Should have travel_event signal set to docked
        assert signals["travel_event"] == "docked"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
