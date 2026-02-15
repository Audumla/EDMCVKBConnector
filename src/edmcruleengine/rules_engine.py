"""Rule engine for catalog-backed signal rules."""

from __future__ import annotations

import re
from collections import OrderedDict
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

from . import plugin_logger
from .signals_catalog import derive_signal_values, validate_condition

logger = plugin_logger(__name__)


# Backward-compatible constants still used by the legacy visual editor.
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


_SHIFT_TOKEN_PATTERN = re.compile(r"^(Shift[1-2]|Subshift[1-7])$")


class RuleMatchError(Exception):
    """Raised for invalid rules that cannot be evaluated."""


class RuleMatchResult(str, Enum):
    MATCH = "match"
    NO_MATCH = "no_match"
    STABLE = "stable"


@dataclass
class MatchResult:
    rule_id: str
    rule_title: str
    source: str
    event_type: str
    actions: List[Dict[str, Any]]
    signal_values: Dict[str, Any]
    outcome: RuleMatchResult


def decode_dashboard(entry: Dict[str, Any]) -> Dict[str, Any]:
    """Backward-compatible helper used by older tests."""
    flags_bits = int(entry.get("Flags") or 0)
    flags2_bits = int(entry.get("Flags2") or 0)
    gui_val = int(entry.get("GuiFocus") or 0)
    return {
        "flags_bits": flags_bits,
        "flags2_bits": flags2_bits,
        "gui_focus_value": gui_val,
        "gui_focus_name": GUI_FOCUS.get(gui_val, f"UnknownGuiFocus({gui_val})"),
        "raw": entry,
    }


def rule_evaluate(
    rule: Dict[str, Any],
    *,
    source: str,
    event_type: str,
    entry: Dict[str, Any],
    decoded: Optional[Dict[str, Any]] = None,
    prev_decoded: Optional[Dict[str, Any]] = None,
) -> RuleMatchResult:
    """
    Backward-compatible function signature.
    Returns MATCH only when the normalized v3 rule conditions are true.
    """
    del source, event_type, decoded, prev_decoded  # v3 rules are source/event agnostic.
    when = rule.get("when") or {"all": []}
    all_conditions = when.get("all") if isinstance(when, dict) else []
    any_conditions = when.get("any") if isinstance(when, dict) else []
    if not all_conditions and not any_conditions:
        return RuleMatchResult.MATCH

    signal_values = entry.get("signals")
    if not isinstance(signal_values, dict):
        return RuleMatchResult.NO_MATCH

    all_match = all(_eval_condition(c, signal_values) for c in all_conditions or [])
    any_match = True if not any_conditions else any(_eval_condition(c, signal_values) for c in any_conditions)
    return RuleMatchResult.MATCH if (all_match and any_match) else RuleMatchResult.NO_MATCH


def parse_rules_payload(payload: Any) -> List[Dict[str, Any]]:
    """Support both top-level list and wrapped object forms."""
    if isinstance(payload, list):
        rules = payload
    elif isinstance(payload, dict) and isinstance(payload.get("rules"), list):
        rules = payload["rules"]
    else:
        raise ValueError("Rules file must be a list or an object with a 'rules' list")

    if not all(isinstance(r, dict) for r in rules):
        raise ValueError("Rules list must contain only objects")
    return [dict(r) for r in rules]


def normalize_and_validate_rules(rules: List[Dict[str, Any]], catalog: Dict[str, Any]) -> List[Dict[str, Any]]:
    used_ids: set[str] = set()
    normalized: List[Dict[str, Any]] = []

    for idx, rule in enumerate(rules):
        nrule = _normalize_rule(rule, idx, used_ids)
        _validate_rule(nrule, catalog)
        normalized.append(nrule)
    return normalized


def _slugify(text: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", text.strip().lower()).strip("-")
    return value or "rule"


def _allocate_rule_id(base: str, used_ids: set[str]) -> str:
    candidate = base
    suffix = 2
    while candidate in used_ids:
        candidate = f"{base}-{suffix}"
        suffix += 1
    used_ids.add(candidate)
    return candidate


def _normalize_rule(rule: Dict[str, Any], idx: int, used_ids: set[str]) -> Dict[str, Any]:
    title = rule.get("title")
    if not isinstance(title, str) or not title.strip():
        raise ValueError(f"Rule[{idx}]: 'title' is required and must be a non-empty string")

    rule_id = rule.get("id")
    if rule_id is None:
        rule_id = _allocate_rule_id(_slugify(title), used_ids)
    else:
        rule_id = str(rule_id).strip()
        if not rule_id:
            raise ValueError(f"Rule[{idx}] '{title}': 'id' must not be empty when provided")
        if rule_id in used_ids:
            raise ValueError(f"Rule[{idx}] '{title}': duplicate rule id '{rule_id}'")
        used_ids.add(rule_id)

    enabled = bool(rule.get("enabled", True))

    when = rule.get("when")
    if when is None:
        when = {"all": []}
    if not isinstance(when, dict):
        raise ValueError(f"Rule '{rule_id}': 'when' must be an object")
    all_conditions = when.get("all", [])
    any_conditions = when.get("any", [])
    if not isinstance(all_conditions, list) or not isinstance(any_conditions, list):
        raise ValueError(f"Rule '{rule_id}': 'when.all' and 'when.any' must be arrays")

    then_actions = _normalize_actions(rule.get("then", []), rule_id=rule_id, branch="then")
    else_actions = _normalize_actions(rule.get("else", []), rule_id=rule_id, branch="else")

    return {
        "id": rule_id,
        "title": title.strip(),
        "enabled": enabled,
        "when": {"all": all_conditions, "any": any_conditions},
        "then": then_actions,
        "else": else_actions,
    }


def _normalize_actions(raw: Any, *, rule_id: str, branch: str) -> List[Dict[str, Any]]:
    if raw is None:
        return []
    if isinstance(raw, list):
        actions = raw
    elif isinstance(raw, dict):
        # Legacy dict actions are converted to deterministic ordered action objects.
        actions = [{k: v} for k, v in raw.items()]
    else:
        raise ValueError(f"Rule '{rule_id}': '{branch}' must be an array of action objects")

    normalized: List[Dict[str, Any]] = []
    for i, action in enumerate(actions):
        if not isinstance(action, dict):
            raise ValueError(f"Rule '{rule_id}': {branch}[{i}] must be an object")
        normalized.append(_normalize_action(action, rule_id=rule_id, branch=branch, idx=i))
    return normalized


def _normalize_action(action: Dict[str, Any], *, rule_id: str, branch: str, idx: int) -> Dict[str, Any]:
    if "type" in action:
        action_type = str(action["type"])
        if action_type == "log":
            message = action.get("message", "")
            return {"type": "log", "message": str(message)}
        if action_type in {"vkb_set_shift", "vkb_clear_shift"}:
            tokens = action.get("tokens", [])
            if not isinstance(tokens, list) or not all(isinstance(t, str) for t in tokens):
                raise ValueError(f"Rule '{rule_id}': {branch}[{idx}] {action_type} requires string array tokens")
            _validate_shift_tokens(tokens, rule_id=rule_id, branch=branch, idx=idx)
            return {"type": action_type, "tokens": list(tokens)}
        raise ValueError(f"Rule '{rule_id}': {branch}[{idx}] unknown action type '{action_type}'")

    if "log" in action:
        return {"type": "log", "message": str(action.get("log", ""))}
    if "vkb_set_shift" in action:
        tokens = action.get("vkb_set_shift")
        if not isinstance(tokens, list) or not all(isinstance(t, str) for t in tokens):
            raise ValueError(f"Rule '{rule_id}': {branch}[{idx}] vkb_set_shift must be string array")
        _validate_shift_tokens(tokens, rule_id=rule_id, branch=branch, idx=idx)
        return {"type": "vkb_set_shift", "tokens": list(tokens)}
    if "vkb_clear_shift" in action:
        tokens = action.get("vkb_clear_shift")
        if not isinstance(tokens, list) or not all(isinstance(t, str) for t in tokens):
            raise ValueError(f"Rule '{rule_id}': {branch}[{idx}] vkb_clear_shift must be string array")
        _validate_shift_tokens(tokens, rule_id=rule_id, branch=branch, idx=idx)
        return {"type": "vkb_clear_shift", "tokens": list(tokens)}

    raise ValueError(f"Rule '{rule_id}': {branch}[{idx}] has no supported action fields")


def _validate_shift_tokens(tokens: List[str], *, rule_id: str, branch: str, idx: int) -> None:
    for token in tokens:
        if not _SHIFT_TOKEN_PATTERN.fullmatch(token):
            raise ValueError(
                f"Rule '{rule_id}': {branch}[{idx}] invalid shift token '{token}' "
                "(expected Shift1/Shift2/Subshift1..Subshift7)"
            )


def _validate_rule(rule: Dict[str, Any], catalog: Dict[str, Any]) -> None:
    rule_id = rule["id"]
    when = rule["when"]
    for i, condition in enumerate(when.get("all", [])):
        try:
            validate_condition(condition, catalog, rule_id=rule_id)
        except ValueError as exc:
            raise ValueError(f"Rule '{rule_id}' when.all[{i}]: {exc}") from exc
    for i, condition in enumerate(when.get("any", [])):
        try:
            validate_condition(condition, catalog, rule_id=rule_id)
        except ValueError as exc:
            raise ValueError(f"Rule '{rule_id}' when.any[{i}]: {exc}") from exc


def _eval_condition(condition: Dict[str, Any], signal_values: Dict[str, Any]) -> bool:
    signal = condition.get("signal")
    op = condition.get("op")
    value = signal_values.get(signal)
    target = condition.get("value")

    if op == "exists":
        expected = condition.get("value", True)
        return bool(value is not None) is bool(expected)
    if op == "eq":
        return value == target
    if op == "ne":
        return value != target
    if op == "in":
        return value in (target or [])
    if op == "nin":
        return value not in (target or [])
    if op == "lt":
        return value < target
    if op == "lte":
        return value <= target
    if op == "gt":
        return value > target
    if op == "gte":
        return value >= target
    if op == "contains":
        if isinstance(value, (str, list, tuple, set)):
            return target in value
        if isinstance(value, dict):
            return target in value.keys()
        return False
    return False


class DashboardRuleEngine:
    """Evaluates rules against catalog-derived signal values with edge triggering."""

    MAX_CACHE_SIZE = 64

    def __init__(
        self,
        rules: List[Dict[str, Any]],
        *,
        catalog: Dict[str, Any],
        action_handler: Callable[[MatchResult], None],
    ) -> None:
        self.catalog = catalog
        self.rules = normalize_and_validate_rules(rules, catalog)
        self.action_handler = action_handler
        self._prev_match_by_cmdr_beta: OrderedDict[Tuple[str, bool], Dict[str, bool]] = OrderedDict()
        self.catalog_version = int(catalog.get("version", -1))

    def on_notification(
        self,
        cmdr: str,
        is_beta: bool,
        source: str,
        event_type: str,
        entry: Dict[str, Any],
    ) -> None:
        signal_values = derive_signal_values(self.catalog, entry)

        key = (cmdr or "", bool(is_beta))
        prev = self._prev_match_by_cmdr_beta.get(key, {})
        next_state: Dict[str, bool] = dict(prev)

        for rule in self.rules:
            rule_id = rule["id"]
            was_matched = bool(prev.get(rule_id, False))
            is_matched = bool(rule.get("enabled", True) and self._rule_matches(rule, signal_values))
            next_state[rule_id] = is_matched

            if not was_matched and is_matched:
                self.action_handler(
                    MatchResult(
                        rule_id=rule_id,
                        rule_title=rule["title"],
                        source=source,
                        event_type=event_type,
                        actions=list(rule["then"]),
                        signal_values=signal_values,
                        outcome=RuleMatchResult.MATCH,
                    )
                )
            elif was_matched and not is_matched:
                self.action_handler(
                    MatchResult(
                        rule_id=rule_id,
                        rule_title=rule["title"],
                        source=source,
                        event_type=event_type,
                        actions=list(rule["else"]),
                        signal_values=signal_values,
                        outcome=RuleMatchResult.NO_MATCH,
                    )
                )

        self._prev_match_by_cmdr_beta[key] = next_state
        self._prev_match_by_cmdr_beta.move_to_end(key)
        if len(self._prev_match_by_cmdr_beta) > self.MAX_CACHE_SIZE:
            oldest = next(iter(self._prev_match_by_cmdr_beta))
            del self._prev_match_by_cmdr_beta[oldest]

    def _rule_matches(self, rule: Dict[str, Any], signal_values: Dict[str, Any]) -> bool:
        when = rule.get("when", {"all": []})
        all_conditions = when.get("all", [])
        any_conditions = when.get("any", [])

        all_match = all(_eval_condition(c, signal_values) for c in all_conditions)
        any_match = True if not any_conditions else any(_eval_condition(c, signal_values) for c in any_conditions)
        return all_match and any_match

    def on_dashboard_entry(self, cmdr: str, is_beta: bool, entry: Dict[str, Any]) -> None:
        event_type = str(entry.get("event", "Status"))
        self.on_notification(cmdr=cmdr, is_beta=is_beta, source="dashboard", event_type=event_type, entry=entry)
