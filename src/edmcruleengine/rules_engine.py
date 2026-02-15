"""
Rule engine for matching EDMC dashboard/status data.

Rules are loaded from JSON in the plugin directory and matched against
decoded Flags/Flags2/GuiFocus values.
"""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

# ---- Elite Dangerous Status Flags and GUI Focus States ----
# Complete flag definitions from Elite Dangerous Status.json
# Supports all dashboard flags, extended flags, and GUI focus states
# Reference: https://elite-journal.readthedocs.io/en/latest/Status%20File/

FLAGS: Dict[str, int] = {
    "FlagsDocked": (1 << 0),
    "FlagsLanded": (1 << 1),
    "FlagsLandingGearDown": (1 << 2),
    "FlagsShieldsUp": (1 << 3),
    "FlagsSupercruise": (1 << 4),
    "FlagsFlightAssistOff": (1 << 5),
    "FlagsHardpointsDeployed": (1 << 6),
    "FlagsInWing": (1 << 7),
    "FlagsLightsOn": (1 << 8),
    "FlagsCargoScoopDeployed": (1 << 9),
    "FlagsSilentRunning": (1 << 10),
    "FlagsScoopingFuel": (1 << 11),
    "FlagsSrvHandbrake": (1 << 12),
    "FlagsSrvTurret": (1 << 13),
    "FlagsSrvUnderShip": (1 << 14),
    "FlagsSrvDriveAssist": (1 << 15),
    "FlagsFsdMassLocked": (1 << 16),
    "FlagsFsdCharging": (1 << 17),
    "FlagsFsdCooldown": (1 << 18),
    "FlagsLowFuel": (1 << 19),
    "FlagsOverHeating": (1 << 20),
    "FlagsHasLatLong": (1 << 21),
    "FlagsIsInDanger": (1 << 22),
    "FlagsBeingInterdicted": (1 << 23),
    "FlagsInMainShip": (1 << 24),
    "FlagsInFighter": (1 << 25),
    "FlagsInSRV": (1 << 26),
    "FlagsAnalysisMode": (1 << 27),
    "FlagsNightVision": (1 << 28),
    "FlagsAverageAltitude": (1 << 29),
    "FlagsFsdJump": (1 << 30),
    "FlagsSrvHighBeam": (1 << 31),
}

FLAGS2: Dict[str, int] = {
    "Flags2OnFoot": (1 << 0),
    "Flags2InTaxi": (1 << 1),
    "Flags2InMulticrew": (1 << 2),
    "Flags2OnFootInStation": (1 << 3),
    "Flags2OnFootOnPlanet": (1 << 4),
    "Flags2AimDownSight": (1 << 5),
    "Flags2LowOxygen": (1 << 6),
    "Flags2LowHealth": (1 << 7),
    "Flags2Cold": (1 << 8),
    "Flags2Hot": (1 << 9),
    "Flags2VeryCold": (1 << 10),
    "Flags2VeryHot": (1 << 11),
    "Flags2GlideMode": (1 << 12),
    "Flags2OnFootInHangar": (1 << 13),
    "Flags2OnFootSocialSpace": (1 << 14),
    "Flags2OnFootExterior": (1 << 15),
    "Flags2BreathableAtmosphere": (1 << 16),
}

GUI_FOCUS: Dict[int, str] = {
    0: "GuiFocusNoFocus",
    1: "GuiFocusInternalPanel",
    2: "GuiFocusExternalPanel",
    3: "GuiFocusCommsPanel",
    4: "GuiFocusRolePanel",
    5: "GuiFocusStationServices",
    6: "GuiFocusGalaxyMap",
    7: "GuiFocusSystemMap",
    8: "GuiFocusOrrery",
    9: "GuiFocusFSS",
    10: "GuiFocusSAA",
    11: "GuiFocusCodex",
}

GUI_FOCUS_NAME_TO_VALUE: Dict[str, int] = {v: k for k, v in GUI_FOCUS.items()}


def _bit_is_set(value: int, bit: int) -> bool:
    return bool(value & bit)


class _LazyFlagDict(dict):
    """
    Lazy-loading dictionary for flag boolean values.
    
    Decodes flags only when accessed, not all at once during initialization.
    This optimization reduces memory usage and CPU time for large flag sets.
    """
    def __init__(self, flags_bits: int, flag_map: Dict[str, int]):
        super().__init__()
        self._flags_bits = flags_bits
        self._flag_map = flag_map
        self._cached: Dict[str, bool] = {}

    def __getitem__(self, key: str) -> bool:
        if key not in self._cached:
            if key not in self._flag_map:
                raise KeyError(key)
            self._cached[key] = _bit_is_set(self._flags_bits, self._flag_map[key])
        return self._cached[key]

    def __contains__(self, key: object) -> bool:
        return key in self._flag_map

    def get(self, key: str, default: Any = None) -> Any:
        try:
            return self[key]
        except KeyError:
            return default

    def items(self):
        """Force full evaluation for iteration."""
        for key in self._flag_map:
            if key not in self._cached:
                self._cached[key] = _bit_is_set(self._flags_bits, self._flag_map[key])
        return self._cached.items()

    def keys(self):
        return self._flag_map.keys()

    def values(self):
        """Force full evaluation for iteration."""
        for key in self._flag_map:
            if key not in self._cached:
                self._cached[key] = _bit_is_set(self._flags_bits, self._flag_map[key])
        return self._cached.values()


def decode_dashboard(entry: Dict[str, Any]) -> Dict[str, Any]:
    """
    Returns a normalized view with lazy-loaded flags:
      - flags_bits, flags2_bits (raw integer values)
      - flags_bool, flags2_bool (lazy-loading dicts)
      - gui_focus_value (int), gui_focus_name (str)
      
    Optimization #14: Flags are only decoded when accessed, not all at once.
    """
    flags_bits = int(entry.get("Flags") or 0)
    flags2_bits = int(entry.get("Flags2") or 0)
    gui_val = int(entry.get("GuiFocus") or 0)

    return {
        "flags_bits": flags_bits,
        "flags2_bits": flags2_bits,
        "flags_bool": _LazyFlagDict(flags_bits, FLAGS),
        "flags2_bool": _LazyFlagDict(flags2_bits, FLAGS2),
        "gui_focus_value": gui_val,
        "gui_focus_name": GUI_FOCUS.get(gui_val, f"UnknownGuiFocus({gui_val})"),
        "raw": entry,
    }


import re


class RuleMatchError(Exception):
    pass


class MissingDataError(RuleMatchError):
    pass


class RuleMatchResult(str, Enum):
    MATCH = "match"
    NO_MATCH = "no_match"
    INDETERMINATE = "indeterminate"
    SKIPPED = "skipped"  # Rule does not apply (source/event filter mismatch)


def _require_fields(entry: Dict[str, Any], fields: Iterable[str]) -> bool:
    return all(field in entry for field in fields)


def _get_field(entry: Dict[str, Any], path: str) -> Tuple[bool, Any]:
    current: Any = entry
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return False, None
        current = current[part]
    return True, current


def _match_flags_block(
    decoded: Dict[str, Any],
    *,
    which: str,
    block: Dict[str, Any],
    prev_decoded: Optional[Dict[str, Any]] = None,
) -> bool:
    current = decoded[which]

    def require_known(names: Iterable[str], valid: Dict[str, int]) -> None:
        unknown = [n for n in names if n not in valid]
        if unknown:
            raise RuleMatchError(f"Unknown flag(s) in {which}: {unknown}")

    all_of = block.get("all_of")
    if all_of is not None:
        require_known(all_of, FLAGS if which == "flags_bool" else FLAGS2)
        if not all(current[n] for n in all_of):
            return False

    any_of = block.get("any_of")
    if any_of is not None:
        require_known(any_of, FLAGS if which == "flags_bool" else FLAGS2)
        if not any(current[n] for n in any_of):
            return False

    none_of = block.get("none_of")
    if none_of is not None:
        require_known(none_of, FLAGS if which == "flags_bool" else FLAGS2)
        if any(current[n] for n in none_of):
            return False

    equals = block.get("equals")
    if equals is not None:
        require_known(equals.keys(), FLAGS if which == "flags_bool" else FLAGS2)
        for name, val in equals.items():
            if bool(current[name]) != bool(val):
                return False

    if "changed_to_true" in block or "changed_to_false" in block:
        if prev_decoded is None:
            return False

        prev = prev_decoded[which]
        changed_to_true = block.get("changed_to_true") or []
        changed_to_false = block.get("changed_to_false") or []
        require_known(changed_to_true, FLAGS if which == "flags_bool" else FLAGS2)
        require_known(changed_to_false, FLAGS if which == "flags_bool" else FLAGS2)

        for n in changed_to_true:
            if not (prev.get(n) is False and current.get(n) is True):
                return False
        for n in changed_to_false:
            if not (prev.get(n) is True and current.get(n) is False):
                return False

    return True


def _match_gui_focus_block(
    decoded: Dict[str, Any],
    block: Dict[str, Any],
    prev_decoded: Optional[Dict[str, Any]] = None,
) -> bool:
    cur_val = decoded["gui_focus_value"]

    def to_val(v: Any) -> int:
        if isinstance(v, int):
            return v
        if isinstance(v, str):
            if v.startswith("UnknownGuiFocus("):
                raise RuleMatchError("Cannot match UnknownGuiFocus string directly; use int.")
            if v not in GUI_FOCUS_NAME_TO_VALUE:
                raise RuleMatchError(f"Unknown GuiFocus name: {v}")
            return GUI_FOCUS_NAME_TO_VALUE[v]
        raise RuleMatchError(f"Invalid GuiFocus value type: {type(v)}")

    if "equals" in block:
        if cur_val != to_val(block["equals"]):
            return False

    if "in" in block:
        wanted = [to_val(x) for x in block["in"]]
        if cur_val not in wanted:
            return False

    if "changed_to" in block:
        if prev_decoded is None:
            return False
        prev_val = prev_decoded["gui_focus_value"]
        target = to_val(block["changed_to"])
        if not (prev_val != target and cur_val == target):
            return False

    return True


def _match_field_block(
    entry: Dict[str, Any],
    block: Dict[str, Any],
    prev_entry: Optional[Dict[str, Any]] = None,
) -> bool:
    name = block.get("name")
    if not isinstance(name, str) or not name:
        raise RuleMatchError("field block requires non-empty string 'name'")

    exists, value = _get_field(entry, name)
    expected_exists = block.get("exists")
    if expected_exists is not None and bool(exists) != bool(expected_exists):
        return False

    # If field does not exist and no explicit exists=false handling matched above,
    # this rule is indeterminate for operators that need a concrete value.
    if not exists:
        if expected_exists is False:
            return True
        raise MissingDataError(f"Missing field '{name}'")

    if "equals" in block and value != block["equals"]:
        return False
    if "in" in block and value not in block["in"]:
        return False
    if "not_in" in block and value in block["not_in"]:
        return False
    if "contains" in block:
        target = block["contains"]
        if isinstance(value, (str, list, tuple, set)):
            if target not in value:
                return False
        elif isinstance(value, dict):
            if target not in value.keys():
                return False
        else:
            return False
    if "gt" in block and not (value > block["gt"]):
        return False
    if "gte" in block and not (value >= block["gte"]):
        return False
    if "lt" in block and not (value < block["lt"]):
        return False
    if "lte" in block and not (value <= block["lte"]):
        return False

    if "changed" in block:
        if prev_entry is None:
            return False
        prev_exists, prev_value = _get_field(prev_entry, name)
        changed = prev_exists != exists or prev_value != value
        if bool(changed) != bool(block["changed"]):
            return False

    if "changed_to" in block:
        if prev_entry is None:
            return False
        _, prev_value = _get_field(prev_entry, name)
        if prev_value == block["changed_to"] or value != block["changed_to"]:
            return False

    return True


def rule_evaluate(
    rule: Dict[str, Any],
    *,
    source: str,
    event_type: str,
    entry: Dict[str, Any],
    decoded: Dict[str, Any],
    prev_decoded: Optional[Dict[str, Any]] = None,
) -> RuleMatchResult:
    if not rule.get("enabled", True):
        return RuleMatchResult.NO_MATCH

    when = rule.get("when") or {}
    source_filter = when.get("source")
    if source_filter and source_filter != "any":
        if isinstance(source_filter, str):
            if source_filter != source:
                return RuleMatchResult.SKIPPED
        elif isinstance(source_filter, list):
            if source not in source_filter:
                return RuleMatchResult.SKIPPED
        else:
            return RuleMatchResult.SKIPPED

    event_filter = when.get("event")
    if event_filter:
        if isinstance(event_filter, str):
            if event_filter != event_type:
                return RuleMatchResult.SKIPPED
        elif isinstance(event_filter, list):
            if event_type not in event_filter:
                return RuleMatchResult.SKIPPED
        else:
            return RuleMatchResult.SKIPPED

    all_blocks: List[Dict[str, Any]] = when.get("all") or []
    any_blocks: List[Dict[str, Any]] = when.get("any") or []

    def match_block(b: Dict[str, Any]) -> bool:
        if "flags" in b:
            return _match_flags_block(decoded, which="flags_bool", block=b["flags"], prev_decoded=prev_decoded)
        if "flags2" in b:
            return _match_flags_block(decoded, which="flags2_bool", block=b["flags2"], prev_decoded=prev_decoded)
        if "gui_focus" in b:
            return _match_gui_focus_block(decoded, block=b["gui_focus"], prev_decoded=prev_decoded)
        if "field" in b:
            prev_entry = prev_decoded["raw"] if prev_decoded else None
            return _match_field_block(entry, block=b["field"], prev_entry=prev_entry)
        raise RuleMatchError(f"Unknown match block: {b}")

    for b in all_blocks:
        try:
            if not match_block(b):
                return RuleMatchResult.NO_MATCH
        except MissingDataError:
            return RuleMatchResult.INDETERMINATE

    if any_blocks:
        any_true = False
        any_indeterminate = False
        for b in any_blocks:
            try:
                if match_block(b):
                    any_true = True
                    break
            except MissingDataError:
                any_indeterminate = True

        if not any_true and any_indeterminate:
            return RuleMatchResult.INDETERMINATE
        if not any_true:
            return RuleMatchResult.NO_MATCH

    return RuleMatchResult.MATCH


@dataclass
class MatchResult:
    rule_id: str
    source: str
    event_type: str
    then: Dict[str, Any]
    otherwise: Dict[str, Any]
    decoded: Dict[str, Any]
    outcome: RuleMatchResult


class DashboardRuleEngine:
    # Maximum number of commander/beta combinations to track to prevent memory leaks
    MAX_CACHE_SIZE = 64

    def __init__(
        self,
        rules: List[Dict[str, Any]],
        *,
        action_handler: Callable[[MatchResult], None],
    ) -> None:
        # Validate and sanitize rule IDs
        for i, rule in enumerate(rules):
            if "id" not in rule:
                rule["id"] = f"<rule-{i}>"
            else:
                rule_id = rule["id"]
                # Ensure rule ID is string-like and sanitize it
                if not isinstance(rule_id, str):
                    rule["id"] = str(rule_id)
                # Sanitize: remove control characters
                rule["id"] = rule["id"].replace("\n", "\\n").replace("\r", "\\r")
        
        self.rules = rules
        self.action_handler = action_handler
        # Use OrderedDict with bounded size to prevent memory leaks from inactive commanders
        self._prev_by_cmdr_beta: OrderedDict[Tuple[str, bool], Dict[str, Any]] = OrderedDict()

    def on_notification(
        self,
        cmdr: str,
        is_beta: bool,
        source: str,
        event_type: str,
        entry: Dict[str, Any],
    ) -> None:
        decoded = decode_dashboard(entry)
        key = (cmdr, is_beta)
        prev = self._prev_by_cmdr_beta.get(key)

        for r in self.rules:
            try:
                outcome = rule_evaluate(
                    r,
                    source=source,
                    event_type=event_type,
                    entry=entry,
                    decoded=decoded,
                    prev_decoded=prev,
                )
                self.action_handler(
                    MatchResult(
                        rule_id=r.get("id", "<no-id>"),
                        source=source,
                        event_type=event_type,
                        then=r.get("then", {}),
                        otherwise=r.get("else", {}),
                        decoded=decoded,
                        outcome=outcome,
                    )
                )
            except RuleMatchError:
                pass

        # Update the decoded state for this commander/beta combo
        # Move to end to mark as recently used (for LRU eviction)
        self._prev_by_cmdr_beta[key] = decoded
        self._prev_by_cmdr_beta.move_to_end(key)

        # Evict oldest entry if cache exceeds maximum size
        if len(self._prev_by_cmdr_beta) > self.MAX_CACHE_SIZE:
            evicted = next(iter(self._prev_by_cmdr_beta))
            del self._prev_by_cmdr_beta[evicted]

    def on_dashboard_entry(self, cmdr: str, is_beta: bool, entry: Dict[str, Any]) -> None:
        """
        Backward-compatible alias for existing callers.
        """
        event_type = str(entry.get("event", "Unknown"))
        self.on_notification(cmdr, is_beta, "dashboard", event_type, entry)
