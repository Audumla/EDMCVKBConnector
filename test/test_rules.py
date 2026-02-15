"""
Tests for rules engine, signal derivation, and catalog loading.
"""

import json
import pytest
from pathlib import Path

from edmcruleengine.signals_catalog import SignalsCatalog, CatalogError, generate_id_from_title
from edmcruleengine.signal_derivation import SignalDerivation
from edmcruleengine.rules_engine import RuleEngine, RuleValidator, RuleValidationError
from edmcruleengine.rule_loader import load_rules_file, RuleLoadError


class TestSignalsCatalog:
    """Test signals catalog loading and validation."""
    
    def test_load_catalog_from_file(self):
        """Test loading catalog from signals_catalog.json."""
        catalog_path = Path(__file__).parent.parent / "signals_catalog.json"
        catalog = SignalsCatalog.from_file(catalog_path)
        
        assert catalog.version == 1
        assert "core" in catalog.ui_tiers
        assert "detail" in catalog.ui_tiers
        assert "eq" in catalog.operators
        assert "gui_focus" in catalog.signals
        assert "hardpoints" in catalog.signals
    
    def test_catalog_validation_missing_version(self):
        """Test catalog validation fails with missing version."""
        invalid_data = {
            "ui_tiers": {},
            "operators": {},
            "bitfields": {},
            "signals": {}
        }
        
        with pytest.raises(CatalogError, match="version"):
            SignalsCatalog(invalid_data)
    
    def test_catalog_validation_wrong_version(self):
        """Test catalog validation fails with wrong version."""
        invalid_data = {
            "version": 2,
            "ui_tiers": {"core": {}, "detail": {}},
            "operators": {},
            "bitfields": {},
            "signals": {}
        }
        
        with pytest.raises(CatalogError, match="Incompatible catalog version"):
            SignalsCatalog(invalid_data)
    
    def test_catalog_signal_exists(self):
        """Test signal existence checking."""
        catalog_path = Path(__file__).parent.parent / "signals_catalog.json"
        catalog = SignalsCatalog.from_file(catalog_path)
        
        assert catalog.signal_exists("hardpoints")
        assert catalog.signal_exists("gui_focus")
        assert not catalog.signal_exists("nonexistent_signal")
    
    def test_catalog_get_signal_type(self):
        """Test getting signal type."""
        catalog_path = Path(__file__).parent.parent / "signals_catalog.json"
        catalog = SignalsCatalog.from_file(catalog_path)
        
        assert catalog.get_signal_type("hardpoints") == "enum"
        assert catalog.get_signal_type("flag_docked") == "bool"
        assert catalog.get_signal_type("nonexistent") is None
    
    def test_catalog_get_signal_values(self):
        """Test getting enum signal values."""
        catalog_path = Path(__file__).parent.parent / "signals_catalog.json"
        catalog = SignalsCatalog.from_file(catalog_path)
        
        hardpoints_values = catalog.get_signal_values("hardpoints")
        assert "deployed" in hardpoints_values
        assert "retracted" in hardpoints_values
        
        # Bool signals should return None
        assert catalog.get_signal_values("docked") is None
    
    def test_catalog_core_and_detail_signals(self):
        """Test filtering signals by tier."""
        catalog_path = Path(__file__).parent.parent / "signals_catalog.json"
        catalog = SignalsCatalog.from_file(catalog_path)
        
        core_signals = catalog.get_core_signals()
        detail_signals = catalog.get_detail_signals()
        
        assert "hardpoints" in core_signals or "hardpoints" in detail_signals
        assert len(core_signals) > 0
        assert len(detail_signals) > 0


class TestGenerateIdFromTitle:
    """Test ID generation from title."""
    
    def test_generate_id_from_title(self):
        """Test basic ID generation."""
        id1 = generate_id_from_title("Hardpoints Deployed")
        id2 = generate_id_from_title("Galaxy Map Opened")
        
        assert id1 != id2
        assert id1 == "hardpoints-deployed"
        assert id2 == "galaxy-map-opened"
    
    def test_generate_id_deterministic(self):
        """Test ID generation is deterministic."""
        id1 = generate_id_from_title("Test Rule")
        id2 = generate_id_from_title("Test Rule")
        
        assert id1 == id2
        assert id1 == "test-rule"
    
    def test_generate_id_collision_handling(self):
        """Test collision handling with numeric suffixes."""
        used_ids = set()
        id1 = generate_id_from_title("Test", used_ids)
        id2 = generate_id_from_title("Test", used_ids)
        id3 = generate_id_from_title("Test", used_ids)
        
        assert id1 == "test"
        assert id2 == "test-2"
        assert id3 == "test-3"
        assert len(used_ids) == 3


class TestSignalDerivation:
    """Test signal derivation from raw data."""
    
    @pytest.fixture
    def catalog(self):
        """Load catalog for tests."""
        catalog_path = Path(__file__).parent.parent / "signals_catalog.json"
        return SignalsCatalog.from_file(catalog_path)
    
    @pytest.fixture
    def derivation(self, catalog):
        """Create derivation engine."""
        return SignalDerivation(catalog._data)
    
    def test_derive_bool_signal(self, derivation):
        """Test deriving a boolean signal from flags."""
        entry = {"Flags": 0b01000000, "Flags2": 0}  # Bit 6 = hardpoints
        
        signals = derivation.derive_all_signals(entry)
        
        # Check hardpoints enum signal (derived from bit 6)
        assert signals["hardpoints"] == "deployed"
        # Check docking_state (no docked flag, should be in_space)
        assert signals["docking_state"] == "in_space"
    
    def test_derive_enum_signal_from_flag(self, derivation):
        """Test deriving enum signal from flag."""
        entry = {"Flags": 0b01000000, "Flags2": 0}  # Bit 6 = hardpoints
        
        signals = derivation.derive_all_signals(entry)
        
        # When bit 6 is set, hardpoints are deployed
        assert signals["hardpoints"] == "deployed"
        # Check individual flag signals exist (v2 has flag_* variants)
        assert "flag_hardpoints_deployed" in signals
    
    def test_derive_enum_signal_from_path(self, derivation):
        """Test deriving enum signal from path."""
        # The path in catalog is "dashboard.GuiFocus" but for testing we use flat entry
        # So we need to nest it properly
        entry = {"Flags": 0, "Flags2": 0, "GuiFocus": 6}  # Galaxy map
        
        signals = derivation.derive_all_signals(entry)
        
        # Should map 6 -> "GalaxyMap"
        assert signals["gui_focus"] == "GalaxyMap"
    
    def test_derive_first_match_signal(self, derivation):
        """Test deriving signal with first_match logic."""
        # Docking state: bit 0 = docked, bit 1 = landed
        entry_docked = {"Flags": 0b00000001, "Flags2": 0}
        entry_landed = {"Flags": 0b00000010, "Flags2": 0}
        entry_space = {"Flags": 0, "Flags2": 0}
        
        signals_docked = derivation.derive_all_signals(entry_docked)
        signals_landed = derivation.derive_all_signals(entry_landed)
        signals_space = derivation.derive_all_signals(entry_space)
        
        assert signals_docked["docking_state"] == "docked"
        assert signals_landed["docking_state"] == "landed"
        assert signals_space["docking_state"] == "in_space"
    
    def test_derive_all_signals_complete(self, derivation):
        """Test that all signals derive without error."""
        entry = {
            "Flags": 0,
            "Flags2": 0,
            "GuiFocus": 0
        }
        
        signals = derivation.derive_all_signals(entry)
        
        # Should have all signals from v2 catalog (200+ signals)
        assert len(signals) > 100  # V2 has 200+ signals
        assert "hardpoints" in signals
        assert "gui_focus" in signals
        assert "docking_state" in signals


class TestRuleValidator:
    """Test rule validation."""
    
    @pytest.fixture
    def catalog(self):
        """Load catalog for tests."""
        catalog_path = Path(__file__).parent.parent / "signals_catalog.json"
        return SignalsCatalog.from_file(catalog_path)
    
    @pytest.fixture
    def validator(self, catalog):
        """Create validator."""
        return RuleValidator(catalog)
    
    def test_validate_valid_rule(self, validator):
        """Test validating a valid rule."""
        rule = {
            "title": "Test Rule",
            "when": {
                "all": [
                    {
                        "signal": "hardpoints",
                        "op": "eq",
                        "value": "deployed"
                    }
                ]
            },
            "then": [{"vkb_set_shift": ["Shift1"]}]
        }
        
        # Should not raise
        validator.validate_rule(rule, 0)
    
    def test_validate_missing_title(self, validator):
        """Test validation fails without title."""
        rule = {"when": {}}
        
        with pytest.raises(RuleValidationError, match="title"):
            validator.validate_rule(rule, 0)
    
    def test_validate_unknown_signal(self, validator):
        """Test validation fails with unknown signal."""
        rule = {
            "title": "Test",
            "when": {
                "all": [{
                    "signal": "unknown_signal",
                    "op": "eq",
                    "value": True
                }]
            }
        }
        
        with pytest.raises(RuleValidationError, match="unknown signal"):
            validator.validate_rule(rule, 0)
    
    def test_validate_unknown_operator(self, validator):
        """Test validation fails with unknown operator."""
        rule = {
            "title": "Test",
            "when": {
                "all": [{
                    "signal": "flag_docked",
                    "op": "unknown_op",
                    "value": True
                }]
            }
        }
        
        with pytest.raises(RuleValidationError, match="unknown"):
            validator.validate_rule(rule, 0)
    
    def test_validate_enum_value_not_in_list(self, validator):
        """Test validation fails with invalid enum value."""
        rule = {
            "title": "Test",
            "when": {
                "all": [{
                    "signal": "hardpoints",
                    "op": "eq",
                    "value": "invalid_value"
                }]
            }
        }
        
        with pytest.raises(RuleValidationError, match="invalid value"):
            validator.validate_rule(rule, 0)
    
    def test_validate_bool_signal_wrong_type(self, validator):
        """Test validation fails with wrong value type for bool signal."""
        rule = {
            "title": "Test",
            "when": {
                "all": [{
                    "signal": "flag_docked",
                    "op": "eq",
                    "value": "not_a_boolean"
                }]
            }
        }
        
        with pytest.raises(RuleValidationError, match="boolean"):
            validator.validate_rule(rule, 0)


class TestRuleEngine:
    """Test rules engine."""
    
    @pytest.fixture
    def catalog(self):
        """Load catalog."""
        catalog_path = Path(__file__).parent.parent / "signals_catalog.json"
        return SignalsCatalog.from_file(catalog_path)
    
    def test_rule_matching_simple(self, catalog):
        """Test simple rule matching."""
        rules = [{
            "title": "Hardpoints",
            "when": {
                "all": [{
                    "signal": "hardpoints",
                    "op": "eq",
                    "value": "deployed"
                }]
            },
            "then": [{"vkb_set_shift": ["Shift1"]}],
            "else": [{"vkb_clear_shift": ["Shift1"]}]
        }]
        
        actions_executed = []
        
        def action_handler(result):
            actions_executed.append((result.matched, result.actions_to_execute))
        
        engine = RuleEngine(rules, catalog, action_handler=action_handler)
        
        # First evaluation: hardpoints deployed
        entry = {"Flags": 0b01000000, "Flags2": 0, "GuiFocus": 0}
        engine.on_notification("TestCmdr", False, "dashboard", "Status", entry)
        
        # Should execute 'then' actions
        assert len(actions_executed) == 1
        assert actions_executed[0][0] is True  # matched
        assert len(actions_executed[0][1]) > 0  # has actions
    
    def test_edge_triggering_no_spam(self, catalog):
        """Test edge triggering prevents action spam."""
        rules = [{
            "title": "Test",
            "when": {
                "all": [{
                    "signal": "flag_docked",
                    "op": "eq",
                    "value": True
                }]
            },
            "then": [{"vkb_set_shift": ["Shift1"]}]
        }]
        
        actions_executed = []
        
        def action_handler(result):
            actions_executed.append(result.matched)
        
        engine = RuleEngine(rules, catalog, action_handler=action_handler)
        
        # Send same state multiple times
        entry = {"Flags": 0b00000001, "Flags2": 0, "GuiFocus": 0}  # Docked
        
        engine.on_notification("TestCmdr", False, "dashboard", "Status", entry)
        assert len(actions_executed) == 1
        
        engine.on_notification("TestCmdr", False, "dashboard", "Status", entry)
        assert len(actions_executed) == 1  # No new actions!
        
        engine.on_notification("TestCmdr", False, "dashboard", "Status", entry)
        assert len(actions_executed) == 1  # Still no new actions!
    
    def test_edge_triggering_then_and_else(self, catalog):
        """Test edge triggering with then and else."""
        rules = [{
            "title": "Test",
            "when": {
                "all": [{
                    "signal": "flag_docked",
                    "op": "eq",
                    "value": True
                }]
            },
            "then": [{"log": "docked"}],
            "else": [{"log": "undocked"}]
        }]
        
        actions_executed = []
        
        def action_handler(result):
            actions_executed.append((result.matched, len(result.actions_to_execute)))
        
        engine = RuleEngine(rules, catalog, action_handler=action_handler)
        
        # Start undocked
        entry_undocked = {"Flags": 0, "Flags2": 0, "GuiFocus": 0}
        engine.on_notification("TestCmdr", False, "dashboard", "Status", entry_undocked)
        assert len(actions_executed) == 1
        assert actions_executed[0] == (False, 1)  # else action
        
        # Dock
        entry_docked = {"Flags": 0b00000001, "Flags2": 0, "GuiFocus": 0}
        engine.on_notification("TestCmdr", False, "dashboard", "Status", entry_docked)
        assert len(actions_executed) == 2
        assert actions_executed[1] == (True, 1)  # then action
        
        # Stay docked
        engine.on_notification("TestCmdr", False, "dashboard", "Status", entry_docked)
        assert len(actions_executed) == 2  # No new action
        
        # Undock
        engine.on_notification("TestCmdr", False, "dashboard", "Status", entry_undocked)
        assert len(actions_executed) == 3
        assert actions_executed[2] == (False, 1)  # else action
    
    def test_any_condition(self, catalog):
        """Test ANY condition logic."""
        rules = [{
            "title": "Emergency",
            "when": {
                "any": [
                    {"signal": "flag_in_danger", "op": "eq", "value": True},
                    {"signal": "flag_overheating", "op": "eq", "value": True}
                ]
            },
            "then": [{"log": "emergency"}]
        }]
        
        actions_executed = []
        
        def action_handler(result):
            if result.actions_to_execute:
                actions_executed.append(result.matched)
        
        engine = RuleEngine(rules, catalog, action_handler=action_handler)
        
        # Neither condition true
        entry = {"Flags": 0, "Flags2": 0, "GuiFocus": 0}
        engine.on_notification("TestCmdr", False, "dashboard", "Status", entry)
        # First eval fires else, so we get one action
        
        # One condition true (in_danger = bit 22)
        entry = {"Flags": 1 << 22, "Flags2": 0, "GuiFocus": 0}
        engine.on_notification("TestCmdr", False, "dashboard", "Status", entry)
        assert True in actions_executed  # Should match


class TestRuleLoader:
    """Test rule file loading."""
    
    def test_load_array_format(self, tmp_path):
        """Test loading array format rules."""
        rules_file = tmp_path / "rules.json"
        rules_file.write_text(json.dumps([
            {"title": "Rule 1"},
            {"title": "Rule 2"}
        ]))
        
        rules = load_rules_file(rules_file)
        
        assert len(rules) == 2
        assert rules[0]["title"] == "Rule 1"
    
    def test_load_wrapped_format(self, tmp_path):
        """Test loading wrapped format rules."""
        rules_file = tmp_path / "rules.json"
        rules_file.write_text(json.dumps({
            "rules": [
                {"title": "Rule 1"},
                {"title": "Rule 2"}
            ]
        }))
        
        rules = load_rules_file(rules_file)
        
        assert len(rules) == 2
        assert rules[0]["title"] == "Rule 1"
    
    def test_load_missing_file(self, tmp_path):
        """Test loading non-existent file fails."""
        rules_file = tmp_path / "nonexistent.json"
        
        with pytest.raises(RuleLoadError, match="not found"):
            load_rules_file(rules_file)
    
    def test_load_invalid_json(self, tmp_path):
        """Test loading invalid JSON fails."""
        rules_file = tmp_path / "rules.json"
        rules_file.write_text("{invalid json")
        
        with pytest.raises(RuleLoadError, match="Invalid JSON"):
            load_rules_file(rules_file)

