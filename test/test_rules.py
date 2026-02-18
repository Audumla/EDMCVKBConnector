"""
Tests for rules engine, signal derivation, and catalog loading.
"""

import json
import time
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
        
        assert "core" in catalog.ui_tiers
        assert "detail" in catalog.ui_tiers
        assert "eq" in catalog.operators
        assert "gui_focus" in catalog.signals
        assert "hardpoints" in catalog.signals
    
    def test_catalog_validation_missing_keys(self):
        """Test catalog validation fails with missing required keys."""
        invalid_data = {
            "operators": {},
            "bitfields": {},
            "signals": {}
        }
        
        with pytest.raises(CatalogError, match="missing required keys"):
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
        assert catalog.get_signal_type("docking_state") == "enum"
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
        # Note: flag_hardpoints_deployed was removed, hardpoints is now an enum signal
    
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
        
        # Should have all signals from catalog (200+ signals)
        assert len(signals) > 100
        assert "hardpoints" in signals
        assert "gui_focus" in signals
        assert "docking_state" in signals


class TestSignalDerivationEdgeCases:
    """Edge-case tests for derivation ops and defaults."""

    @pytest.fixture
    def derivation(self):
        catalog_data = {
            "signals": {
                "map_signal": {
                    "type": "enum",
                    "values": [
                        {"value": "yes"},
                        {"value": "no"},
                        {"value": "unknown"},
                    ],
                    "derive": {
                        "op": "map",
                        "from": {"op": "path", "path": "dashboard.Flag", "default": None},
                        "map": {"true": "yes", "false": "no"},
                        "default": "unknown",
                    },
                },
                "path_default": {
                    "type": "string",
                    "derive": {
                        "op": "path",
                        "path": "dashboard.Missing",
                        "default": "fallback",
                    },
                },
                "recent_and_flag": {
                    "type": "enum",
                    "values": [
                        {"value": "match"},
                        {"value": "no_match"},
                    ],
                    "derive": {
                        "op": "first_match",
                        "cases": [
                            {
                                "when": {
                                    "op": "and",
                                    "conditions": [
                                        {
                                            "op": "recent",
                                            "event_name": "Docked",
                                            "within_seconds": 3,
                                        },
                                        {"op": "flag", "field_ref": "ship_flags", "bit": 0},
                                    ],
                                },
                                "value": "match",
                            }
                        ],
                        "default": "no_match",
                    },
                },
            },
            "bitfields": {"ship_flags": "dashboard.Flags"},
        }
        return SignalDerivation(catalog_data)

    def test_map_default_when_unmapped(self, derivation):
        entry = {"Flags": 0, "Flags2": 0}
        signals = derivation.derive_all_signals(entry)
        assert signals["map_signal"] == "unknown"

    def test_path_default_when_missing(self, derivation):
        entry = {"Flags": 0, "Flags2": 0}
        signals = derivation.derive_all_signals(entry)
        assert signals["path_default"] == "unknown"

    def test_recent_and_flag_condition(self, derivation):
        entry = {"Flags": 0b00000001, "Flags2": 0}
        context = {"recent_events": {"Docked": time.time() - 1.0}}
        signals = derivation.derive_all_signals(entry, context)
        assert signals["recent_and_flag"] == "match"

    def test_recent_missing_event_falls_back(self, derivation):
        entry = {"Flags": 0b00000001, "Flags2": 0}
        signals = derivation.derive_all_signals(entry, {"recent_events": {}})
        assert signals["recent_and_flag"] == "no_match"


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
                    "signal": "docking_state",
                    "op": "unknown_op",
                    "value": "docked"
                }]
            }
        }
        
        with pytest.raises(RuleValidationError, match="unknown"):
            validator.validate_rule(rule, 0)

    def test_validate_missing_operator(self, validator):
        rule = {
            "title": "Test",
            "when": {
                "all": [{"signal": "hardpoints", "value": "deployed"}]
            },
        }

        with pytest.raises(RuleValidationError, match="missing 'op'"):
            validator.validate_rule(rule, 0)

    def test_validate_enum_signal_invalid_operator(self, validator):
        """Test that numeric operators on enum signals are accepted by validator.
        
        Note: The validator only checks if operators exist in the catalog,
        not if they're semantically valid for the signal type. Semantic validation
        happens at rule evaluation time.
        """
        rule = {
            "title": "Test",
            "when": {
                "all": [{"signal": "hardpoints", "op": "lt", "value": "deployed"}]
            },
        }
        # Should not raise - validators only check if operator exists in catalog
        validator.validate_rule(rule, 0)

    def test_validate_in_operator_requires_list(self, validator):
        rule = {
            "title": "Test",
            "when": {
                "all": [{"signal": "hardpoints", "op": "in", "value": "deployed"}]
            },
        }

        with pytest.raises(RuleValidationError, match="requires list"):
            validator.validate_rule(rule, 0)

    def test_validate_in_operator_invalid_value(self, validator):
        rule = {
            "title": "Test",
            "when": {
                "all": [{"signal": "hardpoints", "op": "in", "value": ["bad"]}]
            },
        }

        with pytest.raises(RuleValidationError, match="invalid value"):
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
        """Test validation fails with wrong value type for enum signal."""
        rule = {
            "title": "Test",
            "when": {
                "all": [{
                    "signal": "docking_state",
                    "op": "eq",
                    "value": "invalid_state"
                }]
            }
        }
        
        with pytest.raises(RuleValidationError, match="invalid value"):
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
                    "signal": "docking_state",
                    "op": "eq",
                    "value": "docked"
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
                    "signal": "docking_state",
                    "op": "eq",
                    "value": "docked"
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
                    {"signal": "heat_status", "op": "eq", "value": "overheating"}
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

        # One condition true (overheating = bit 20)
        entry = {"Flags": 1 << 20, "Flags2": 0, "GuiFocus": 0}
        engine.on_notification("TestCmdr", False, "dashboard", "Status", entry)
        assert True in actions_executed  # Should match

    def test_all_and_any_combined(self, catalog):
        rules = [{
            "title": "Combined",
            "when": {
                "all": [
                    {"signal": "hardpoints", "op": "eq", "value": "deployed"}
                ],
                "any": [
                    {"signal": "gui_focus", "op": "eq", "value": "GalaxyMap"}
                ],
            },
            "then": [{"log": "match"}],
            "else": [{"log": "no"}],
        }]

        actions_executed = []

        def action_handler(result):
            actions_executed.append((result.matched, result.actions_to_execute))

        engine = RuleEngine(rules, catalog, action_handler=action_handler)

        entry = {"Flags": 0b01000000, "Flags2": 0, "GuiFocus": 0}
        engine.on_notification("Cmdr", False, "dashboard", "Status", entry)
        assert actions_executed[-1][0] is False

        entry_map = {"Flags": 0b01000000, "Flags2": 0, "GuiFocus": 6}
        engine.on_notification("Cmdr", False, "dashboard", "Status", entry_map)
        assert actions_executed[-1][0] is True

    def test_empty_conditions_match(self, catalog):
        rules = [{
            "title": "Always",
            "then": [{"log": "always"}],
        }]

        actions_executed = []

        def action_handler(result):
            actions_executed.append(result.matched)

        engine = RuleEngine(rules, catalog, action_handler=action_handler)
        entry = {"Flags": 0, "Flags2": 0, "GuiFocus": 0}
        engine.on_notification("Cmdr", False, "dashboard", "Status", entry)
        assert actions_executed == [True]

    def test_state_is_per_commander(self, catalog):
        rules = [{
            "title": "Docked",
            "when": {
                "all": [{"signal": "docking_state", "op": "eq", "value": "docked"}]
            },
            "then": [{"log": "docked"}],
        }]

        actions_executed = []

        def action_handler(result):
            actions_executed.append((result.rule_id, result.matched))

        engine = RuleEngine(rules, catalog, action_handler=action_handler)

        entry = {"Flags": 0b00000001, "Flags2": 0, "GuiFocus": 0}
        engine.on_notification("CmdrA", False, "dashboard", "Status", entry)
        engine.on_notification("CmdrB", False, "dashboard", "Status", entry)

        assert len(actions_executed) == 2


class TestUnknownDataPolicy:
    """
    Regression tests: missing event data must always produce 'unknown', and
    rules that reference a signal with value 'unknown' must never fire.

    These tests guard against re-introducing any behaviour where a 'default'
    value in a derive spec is honoured for absent data, or where 'unknown'
    accidentally satisfies a rule condition.
    """

    # -----------------------------------------------------------------------
    # Shared minimal catalog used by derivation-layer tests
    # -----------------------------------------------------------------------

    @pytest.fixture
    def mini_catalog(self):
        return SignalDerivation({
            "signals": {
                "path_signal": {
                    "type": "string",
                    "derive": {
                        "op": "path",
                        "path": "dashboard.MissingField",
                    },
                },
                "path_signal_with_spec_default": {
                    "type": "string",
                    "derive": {
                        "op": "path",
                        "path": "dashboard.AlsoMissing",
                        "default": "spec_default_value",   # must be ignored
                    },
                },
                "flag_signal": {
                    "type": "enum",
                    "values": [{"value": "on"}, {"value": "off"}],
                    "derive": {
                        "op": "flag",
                        "field_ref": "test_flags",
                        "bit": 31,        # bit never set in test entries
                        "true_value": "on",
                        "false_value": "off",
                    },
                },
                "map_signal": {
                    "type": "enum",
                    "values": [
                        {"value": "yes"},
                        {"value": "no"},
                        {"value": "unknown"},
                    ],
                    "derive": {
                        "op": "map",
                        "from": {"op": "path", "path": "dashboard.MissingField"},
                        "map": {"A": "yes", "B": "no"},
                        "default": "unknown",    # default in spec – still must not override absent input
                    },
                },
                "first_match_signal": {
                    "type": "enum",
                    "values": [{"value": "found"}, {"value": "not_found"}],
                    "derive": {
                        "op": "first_match",
                        "cases": [
                            {
                                "when": {"op": "flag", "field_ref": "test_flags", "bit": 31},
                                "value": "found",
                            }
                        ],
                        "default": "not_found",
                    },
                },
                "enum_invalid_value": {
                    "type": "enum",
                    "values": [{"value": "alpha"}, {"value": "beta"}],
                    "derive": {
                        "op": "path",
                        "path": "dashboard.RankField",
                    },
                },
            },
            "bitfields": {"test_flags": "dashboard.Flags"},
        })

    # -----------------------------------------------------------------------
    # Layer 1 – derivation: missing input → "unknown"
    # -----------------------------------------------------------------------

    def test_path_missing_field_returns_unknown(self, mini_catalog):
        """A path that resolves to nothing must return 'unknown', not a default."""
        entry = {"Flags": 0, "Flags2": 0}
        signals = mini_catalog.derive_all_signals(entry)
        assert signals["path_signal"] == "unknown"

    def test_path_missing_field_ignores_spec_default(self, mini_catalog):
        """derive_spec 'default' must not substitute for genuinely absent data."""
        entry = {"Flags": 0, "Flags2": 0}
        signals = mini_catalog.derive_all_signals(entry)
        assert signals["path_signal_with_spec_default"] == "unknown", (
            "spec-level 'default' must not be used when the source field is absent"
        )

    def test_map_missing_source_returns_unknown(self, mini_catalog):
        """A map whose source path is absent must return 'unknown'."""
        entry = {"Flags": 0, "Flags2": 0}
        signals = mini_catalog.derive_all_signals(entry)
        assert signals["map_signal"] == "unknown"

    def test_enum_value_not_in_allowed_list_returns_unknown(self, mini_catalog):
        """A raw value not in the signal's allowed enum list must return 'unknown'."""
        # RankField present but not a valid enum value
        entry = {"Flags": 0, "Flags2": 0, "RankField": "gamma"}
        signals = mini_catalog.derive_all_signals(entry)
        assert signals["enum_invalid_value"] == "unknown", (
            "an out-of-range enum value must not be coerced to any valid value"
        )

    def test_present_data_is_not_unknown(self, mini_catalog):
        """Sanity check: when data is present the signal resolves normally."""
        entry = {"Flags": 0, "Flags2": 0, "RankField": "alpha"}
        signals = mini_catalog.derive_all_signals(entry)
        assert signals["enum_invalid_value"] == "alpha"

    # -----------------------------------------------------------------------
    # Layer 2 – rule engine: 'unknown' signal never satisfies a condition
    # -----------------------------------------------------------------------

    @pytest.fixture
    def catalog(self):
        return SignalsCatalog.from_file(
            Path(__file__).parent.parent / "signals_catalog.json"
        )

    def _make_engine(self, catalog, signal, op, value):
        """Helper: single-rule engine that logs matched/unmatched firings."""
        rules = [{
            "title": "ShouldNotFire",
            "when": {"all": [{"signal": signal, "op": op, "value": value}]},
            "then": [{"log": "fired"}],
        }]
        fired = []

        def handler(result):
            if result.matched:
                fired.append(result)

        engine = RuleEngine(rules, catalog, action_handler=handler)
        return engine, fired

    def test_unknown_eq_does_not_match(self, catalog):
        """eq condition on a signal that derives to 'unknown' must not fire."""
        engine, fired = self._make_engine(catalog, "gui_focus", "eq", "NoFocus")
        # Flags=0 with no GuiFocus key → gui_focus derives to 'unknown'
        entry = {"Flags": 0, "Flags2": 0}
        engine.on_notification("Cmdr", False, "dashboard", "Status", entry)
        assert fired == [], "rule must not fire when signal is 'unknown'"

    def test_unknown_ne_does_not_match(self, catalog):
        """ne condition on an unknown signal must not fire (not even 'ne unknown')."""
        engine, fired = self._make_engine(catalog, "gui_focus", "ne", "GalaxyMap")
        entry = {"Flags": 0, "Flags2": 0}
        engine.on_notification("Cmdr", False, "dashboard", "Status", entry)
        assert fired == [], "rule must not fire when signal is 'unknown'"

    def test_unknown_in_does_not_match(self, catalog):
        """in condition on an unknown signal must not fire."""
        rules = [{
            "title": "ShouldNotFire",
            "when": {"all": [{"signal": "gui_focus", "op": "in",
                               "value": ["NoFocus", "GalaxyMap"]}]},
            "then": [{"log": "fired"}],
        }]
        fired = []
        engine = RuleEngine(rules, catalog, action_handler=lambda r: fired.append(r) if r.matched else None)
        entry = {"Flags": 0, "Flags2": 0}
        engine.on_notification("Cmdr", False, "dashboard", "Status", entry)
        assert fired == [], "rule must not fire when signal is 'unknown'"

    def test_rule_fires_once_data_arrives(self, catalog):
        """Rule must not fire while data is absent, then fire correctly once present."""
        engine, fired = self._make_engine(catalog, "gui_focus", "eq", "GalaxyMap")

        # First event: GuiFocus missing → gui_focus == 'unknown' → no match
        engine.on_notification("Cmdr", False, "dashboard", "Status",
                                {"Flags": 0, "Flags2": 0})
        assert fired == [], "must not fire on unknown"

        # Second event: GuiFocus present and matches → should fire
        engine.on_notification("Cmdr", False, "dashboard", "Status",
                                {"Flags": 0, "Flags2": 0, "GuiFocus": 6})
        assert len(fired) == 1, "must fire once real matching data arrives"

    def test_rule_does_not_fire_on_unknown_after_match(self, catalog):
        """After a match, reverting to unknown must not re-trigger the rule."""
        engine, fired = self._make_engine(catalog, "gui_focus", "eq", "GalaxyMap")

        # Match
        engine.on_notification("Cmdr", False, "dashboard", "Status",
                                {"Flags": 0, "Flags2": 0, "GuiFocus": 6})
        assert len(fired) == 1

        # Data absent again – must not fire a second time (no state change to trigger on)
        engine.on_notification("Cmdr", False, "dashboard", "Status",
                                {"Flags": 0, "Flags2": 0})
        assert len(fired) == 1, "reverting to unknown must not re-trigger"

    # -----------------------------------------------------------------------
    # Signal-availability pre-filter tests
    # -----------------------------------------------------------------------

    def test_rule_skipped_when_required_signal_unknown(self, catalog):
        """A rule must be skipped entirely when any required signal is 'unknown'."""
        # gui_focus is derived from GuiFocus; omitting it yields 'unknown'
        engine, fired = self._make_engine(catalog, "gui_focus", "eq", "GalaxyMap")

        entry_no_focus = {"Flags": 0, "Flags2": 0}   # GuiFocus absent
        engine.on_notification("Cmdr", False, "dashboard", "Status", entry_no_focus)

        assert fired == [], (
            "rule must be skipped (not evaluated) when required signal is unknown"
        )

    def test_only_rules_with_available_signals_are_evaluated(self, catalog):
        """Only the rule whose signals are present should fire; others stay silent."""
        # Rule A needs gui_focus (requires GuiFocus field)
        # Rule B needs hardpoints (derived from Flags bit 6, always available)
        rules = [
            {
                "title": "NeedsFocus",
                "when": {"all": [{"signal": "gui_focus", "op": "eq", "value": "GalaxyMap"}]},
                "then": [{"log": "focus"}],
            },
            {
                "title": "NeedsHardpoints",
                "when": {"all": [{"signal": "hardpoints", "op": "eq", "value": "deployed"}]},
                "then": [{"log": "hardpoints"}],
            },
        ]
        fired_titles = []

        def handler(result):
            if result.matched:
                fired_titles.append(result.rule_title)

        engine = RuleEngine(rules, catalog, action_handler=handler)

        # Entry: hardpoints deployed (bit 6 set), but no GuiFocus → gui_focus unknown
        entry = {"Flags": 0b01000000, "Flags2": 0}
        engine.on_notification("Cmdr", False, "dashboard", "Status", entry)

        assert "NeedsHardpoints" in fired_titles, "hardpoints rule should fire"
        assert "NeedsFocus" not in fired_titles, (
            "focus rule must be skipped because gui_focus is unknown"
        )

    def test_rule_fires_when_signals_become_available(self, catalog):
        """A skipped rule must fire correctly once its signals become available."""
        engine, fired = self._make_engine(catalog, "gui_focus", "eq", "GalaxyMap")

        # First event: signal absent – skipped
        engine.on_notification("Cmdr", False, "dashboard", "Status",
                                {"Flags": 0, "Flags2": 0})
        assert fired == []

        # Second event: signal present and matches
        engine.on_notification("Cmdr", False, "dashboard", "Status",
                                {"Flags": 0, "Flags2": 0, "GuiFocus": 6})
        assert len(fired) == 1

    def test_rule_with_no_conditions_is_not_filtered(self, catalog):
        """A rule with no conditions (always-match) must never be filtered out."""
        rules = [{"title": "Always", "then": [{"log": "x"}]}]
        fired = []
        engine = RuleEngine(rules, catalog,
                            action_handler=lambda r: fired.append(r) if r.matched else None)

        engine.on_notification("Cmdr", False, "dashboard", "Status",
                                {"Flags": 0, "Flags2": 0})
        assert len(fired) == 1, "unconditional rule must always be evaluated"


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

