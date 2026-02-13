"""Comprehensive rules tests using file-backed rule fixtures."""

import json
import sys
from pathlib import Path
from unittest.mock import Mock

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from edmcvkbconnector.config import DEFAULTS
from edmcvkbconnector.event_handler import EventHandler
from edmcvkbconnector.rules_engine import RuleMatchResult, decode_dashboard, rule_evaluate


FIXTURES_DIR = Path(__file__).parent / "fixtures"
RULES_FILE = FIXTURES_DIR / "rules_comprehensive.json"
PAYLOADS_FILE = FIXTURES_DIR / "edmc_notifications.json"


class TestConfig:
    """Minimal config stub for deterministic tests."""

    def __init__(self, **overrides):
        self._values = dict(DEFAULTS)
        self._values.update(overrides)

    def get(self, key, default=None):
        return self._values.get(key, default)


def load_rules(path: Path = RULES_FILE):
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    assert isinstance(data, list), "Rules fixture must be a list"
    return data


def load_payloads(path: Path = PAYLOADS_FILE):
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    assert isinstance(data, dict), "Payload fixture must be a dict"
    return data


def get_rule(rule_id: str):
    for rule in load_rules():
        if rule.get("id") == rule_id:
            return rule
    raise AssertionError(f"Missing rule id in fixture: {rule_id}")


def evaluate(rule_id: str, *, source: str, event_type: str, entry: dict):
    rule = get_rule(rule_id)
    decoded = decode_dashboard(entry)
    return rule_evaluate(
        rule,
        source=source,
        event_type=event_type,
        entry=entry,
        decoded=decoded,
    )


def payload(group: str, name: str) -> dict:
    data = load_payloads()
    return dict(data[group][name])


def create_handler_with_fixture_rules():
    cfg = TestConfig(rules_path=str(RULES_FILE), event_types=[])
    handler = EventHandler(cfg, plugin_dir=str(FIXTURES_DIR))
    handler.vkb_client.send_event = Mock(return_value=True)
    handler.vkb_client.connect = Mock(return_value=False)
    return handler


def test_positive_rules():
    assert evaluate(
        "dashboard_hardpoints",
        source="dashboard",
        event_type="Status",
        entry={"event": "Status", "Flags": 1 << 6, "Flags2": 0, "GuiFocus": 0},
    ) == RuleMatchResult.MATCH

    assert evaluate(
        "dashboard_galaxy_map",
        source="dashboard",
        event_type="Status",
        entry={"event": "Status", "Flags": 0, "Flags2": 0, "GuiFocus": 6},
    ) == RuleMatchResult.MATCH

    assert evaluate(
        "journal_fsd_jump_far",
        source="journal",
        event_type="FSDJump",
        entry={"event": "FSDJump", "JumpDist": 12.5},
    ) == RuleMatchResult.MATCH

    assert evaluate(
        "journal_location_empire",
        source="journal",
        event_type="Location",
        entry={"event": "Location", "StarSystem": "Empire Prime"},
    ) == RuleMatchResult.MATCH

    assert evaluate(
        "dashboard_emergency_any",
        source="dashboard",
        event_type="Status",
        entry={"event": "Status", "Flags": 1 << 22, "Flags2": 0, "GuiFocus": 0},
    ) == RuleMatchResult.MATCH

    assert evaluate(
        "journal_event_list_filter",
        source="journal",
        event_type="StartJump",
        entry={"event": "StartJump"},
    ) == RuleMatchResult.MATCH

    print("[OK] Positive rule evaluations passed")


def test_negative_rule_outcomes():
    assert evaluate(
        "journal_fsd_jump_far",
        source="journal",
        event_type="FSDJump",
        entry={"event": "FSDJump", "JumpDist": 3.0},
    ) == RuleMatchResult.NO_MATCH

    assert evaluate(
        "journal_location_empire",
        source="journal",
        event_type="Location",
        entry={"event": "Location", "StarSystem": "Sol"},
    ) == RuleMatchResult.NO_MATCH

    assert evaluate(
        "journal_event_list_filter",
        source="journal",
        event_type="Docked",
        entry={"event": "Docked"},
    ) == RuleMatchResult.NO_MATCH

    assert evaluate(
        "journal_fsd_jump_far",
        source="dashboard",
        event_type="FSDJump",
        entry={"event": "FSDJump", "JumpDist": 12.0},
    ) == RuleMatchResult.NO_MATCH

    assert evaluate(
        "journal_missing_field_indeterminate",
        source="journal",
        event_type="Location",
        entry={"event": "Location", "StarSystem": "Achenar"},
    ) == RuleMatchResult.INDETERMINATE

    print("[OK] Negative outcomes (no-match/indeterminate) passed")


def test_edmc_like_journal_payloads():
    assert evaluate(
        "journal_fsd_jump_far",
        source="journal",
        event_type="FSDJump",
        entry=payload("journal", "fsd_jump_far"),
    ) == RuleMatchResult.MATCH

    assert evaluate(
        "journal_jumpdist_gte_boundary",
        source="journal",
        event_type="FSDJump",
        entry=payload("journal", "fsd_jump_exact"),
    ) == RuleMatchResult.MATCH

    assert evaluate(
        "journal_jumpdist_gte_boundary",
        source="journal",
        event_type="FSDJump",
        entry=payload("journal", "fsd_jump_short"),
    ) == RuleMatchResult.NO_MATCH

    assert evaluate(
        "journal_fuel_lte_boundary",
        source="journal",
        event_type="FuelScoop",
        entry=payload("journal", "fuel_scoop_low"),
    ) == RuleMatchResult.MATCH

    assert evaluate(
        "journal_fuel_lte_boundary",
        source="journal",
        event_type="FuelScoop",
        entry=payload("journal", "fuel_scoop_high"),
    ) == RuleMatchResult.NO_MATCH

    assert evaluate(
        "journal_exists_false_match",
        source="journal",
        event_type="Location",
        entry=payload("journal", "location_no_body"),
    ) == RuleMatchResult.MATCH

    print("[OK] EDMC-like journal payload tests passed")


def test_edmc_like_status_dashboard_payloads():
    assert evaluate(
        "status_combat_posture",
        source="dashboard",
        event_type="Status",
        entry=payload("status_dashboard", "combat_posture"),
    ) == RuleMatchResult.MATCH

    assert evaluate(
        "status_combat_posture",
        source="dashboard",
        event_type="Status",
        entry=payload("status_dashboard", "neutral"),
    ) == RuleMatchResult.NO_MATCH

    assert evaluate(
        "dashboard_emergency_any",
        source="dashboard",
        event_type="Status",
        entry=payload("status_dashboard", "emergency_flag"),
    ) == RuleMatchResult.MATCH

    assert evaluate(
        "dashboard_emergency_any",
        source="dashboard",
        event_type="Status",
        entry=payload("status_dashboard", "emergency_low_health"),
    ) == RuleMatchResult.MATCH

    print("[OK] EDMC-like status/dashboard payload tests passed")


def test_state_transition_rules_for_status_stream():
    handler = create_handler_with_fixture_rules()

    # Initial neutral status snapshot.
    handler.handle_event(
        "Status",
        payload("status_dashboard", "neutral"),
        source="dashboard",
        cmdr="TestCmdr",
        is_beta=False,
    )

    # Transition to hardpoints only should trigger changed_to_true rule.
    handler.handle_event(
        "Status",
        payload("status_dashboard", "hardpoints_only"),
        source="dashboard",
        cmdr="TestCmdr",
        is_beta=False,
    )
    assert handler._shift_bitmap & 0b00010000 == 0b00010000

    # Transition to galaxy map should trigger gui_focus changed_to rule.
    handler.handle_event(
        "Status",
        payload("status_dashboard", "galaxy_map"),
        source="dashboard",
        cmdr="TestCmdr",
        is_beta=False,
    )
    assert handler._subshift_bitmap & 0b00000100 == 0b00000100

    print("[OK] Status stream transition tests passed")


def test_edmc_like_capi_payloads():
    assert evaluate(
        "capi_commander_profile",
        source="capi",
        event_type="CmdrData",
        entry=payload("capi", "cmdr_data_good"),
    ) == RuleMatchResult.MATCH

    assert evaluate(
        "capi_commander_profile",
        source="capi",
        event_type="CmdrData",
        entry=payload("capi", "cmdr_data_bad_name"),
    ) == RuleMatchResult.NO_MATCH

    print("[OK] EDMC-like CAPI payload tests passed")


def test_else_and_indeterminate_action_paths():
    handler = create_handler_with_fixture_rules()

    # MATCH path sets Shift1.
    handler.handle_event(
        "Status",
        {"event": "Status", "Flags": 1 << 6, "Flags2": 0, "GuiFocus": 0},
        source="dashboard",
    )
    assert handler._shift_bitmap & 0b00000010 == 0b00000010

    # NO_MATCH path should run else and clear Shift1.
    handler.handle_event(
        "Status",
        {"event": "Status", "Flags": 0, "Flags2": 0, "GuiFocus": 0},
        source="dashboard",
    )
    assert handler._shift_bitmap & 0b00000010 == 0

    previous_shift = handler._shift_bitmap
    previous_subshift = handler._subshift_bitmap

    # INDETERMINATE path: no then/else execution.
    handler.handle_event(
        "Location",
        {"event": "Location", "StarSystem": "Achenar", "Body": "Achenar 1"},
        source="journal",
    )
    assert handler._shift_bitmap == previous_shift
    assert handler._subshift_bitmap == previous_subshift

    print("[OK] else-path and indeterminate no-op behavior passed")


def test_invalid_actions_and_tokens_do_not_break_valid_updates():
    handler = create_handler_with_fixture_rules()
    handler._shift_bitmap = 0
    handler._subshift_bitmap = 0

    # Invalid action shape should not raise.
    handler.handle_event(
        "Status",
        {"event": "Status", "Flags": 1 << 0, "Flags2": 0, "GuiFocus": 0},
        source="dashboard",
    )

    # Mixed token rule should still apply valid tokens Shift1/Subshift3.
    handler.handle_event(
        "Status",
        {"event": "Status", "Flags": 1 << 0, "Flags2": 0, "GuiFocus": 0},
        source="dashboard",
    )
    assert handler._shift_bitmap & 0b00000010 == 0b00000010
    assert handler._subshift_bitmap & 0b00001000 == 0b00001000

    print("[OK] Invalid actions/tokens handling passed")


def test_rules_file_loading_logic():
    handler = create_handler_with_fixture_rules()
    assert handler.rule_engine is not None
    assert len(handler.rule_engine.rules) > 0

    # Reload should keep a valid engine.
    handler.reload_rules()
    assert handler.rule_engine is not None

    print("[OK] Rule file loading/reloading passed")


if __name__ == "__main__":
    test_positive_rules()
    test_negative_rule_outcomes()
    test_edmc_like_journal_payloads()
    test_edmc_like_status_dashboard_payloads()
    test_state_transition_rules_for_status_stream()
    test_edmc_like_capi_payloads()
    test_else_and_indeterminate_action_paths()
    test_invalid_actions_and_tokens_do_not_break_valid_updates()
    test_rules_file_loading_logic()

    print("\n" + "=" * 70)
    print("[SUCCESS] Comprehensive file-backed rules tests passed")
    print("=" * 70)
