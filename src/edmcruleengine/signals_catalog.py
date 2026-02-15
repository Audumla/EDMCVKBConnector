"""Signals catalog loading, validation, and derivation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


EXPECTED_CATALOG_VERSION = 3
VALUE_REQUIRED_OPS = {"eq", "ne", "in", "nin", "lt", "lte", "gt", "gte", "contains"}
VALUE_OPTIONAL_OPS = {"exists"}


class CatalogError(ValueError):
    """Raised when the signals catalog is missing/invalid/incompatible."""


def _get_path(payload: Dict[str, Any], path: str) -> Tuple[bool, Any]:
    current: Any = payload
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return False, None
        current = current[part]
    return True, current


def _get_path_with_dashboard_fallback(payload: Dict[str, Any], path: str) -> Tuple[bool, Any]:
    """
    Support both nested dashboard payloads and EDMC flat Status entries.
    Catalog paths use "dashboard.*", while EDMC often emits top-level fields.
    """
    exists, value = _get_path(payload, path)
    if exists:
        return exists, value
    if path.startswith("dashboard."):
        return _get_path(payload, path.split(".", 1)[1])
    return False, None


def load_signals_catalog(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise CatalogError(f"Signals catalog not found: {path}")

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise CatalogError(f"Signals catalog JSON parse failed ({path}): {exc}") from exc

    validate_signals_catalog(data)
    return data


def validate_signals_catalog(catalog: Dict[str, Any]) -> None:
    if not isinstance(catalog, dict):
        raise CatalogError("Signals catalog root must be an object")

    for key in ("version", "ui_tiers", "operators", "bitfields", "signals"):
        if key not in catalog:
            raise CatalogError(f"Signals catalog missing required key: {key}")

    version = catalog.get("version")
    if version != EXPECTED_CATALOG_VERSION:
        raise CatalogError(
            f"Unsupported signals catalog version {version}; expected {EXPECTED_CATALOG_VERSION}"
        )

    ui_tiers = catalog.get("ui_tiers")
    if not isinstance(ui_tiers, dict):
        raise CatalogError("ui_tiers must be an object")
    if set(ui_tiers.keys()) != {"core", "detail"}:
        raise CatalogError("ui_tiers must contain exactly 'core' and 'detail'")

    operators = catalog.get("operators")
    if not isinstance(operators, dict) or not operators:
        raise CatalogError("operators must be a non-empty object")

    bitfields = catalog.get("bitfields")
    if not isinstance(bitfields, dict) or not bitfields:
        raise CatalogError("bitfields must be a non-empty object")
    for ref, field_path in bitfields.items():
        if not isinstance(ref, str) or not ref:
            raise CatalogError("bitfields keys must be non-empty strings")
        if not isinstance(field_path, str) or not field_path:
            raise CatalogError(f"bitfields['{ref}'] must be a non-empty path string")

    signals = catalog.get("signals")
    if not isinstance(signals, dict) or not signals:
        raise CatalogError("signals must be a non-empty object")

    for signal_name, spec in signals.items():
        _validate_signal(signal_name, spec, bitfields)


def _validate_signal(signal_name: str, spec: Dict[str, Any], bitfields: Dict[str, str]) -> None:
    if not isinstance(spec, dict):
        raise CatalogError(f"signals['{signal_name}'] must be an object")

    signal_type = spec.get("type")
    if signal_type not in {"bool", "enum"}:
        raise CatalogError(f"signals['{signal_name}'].type must be bool|enum")

    if signal_type == "enum":
        values = spec.get("values")
        if not isinstance(values, list) or not values:
            raise CatalogError(f"signals['{signal_name}'].values must be a non-empty list")
        enum_values = set()
        for item in values:
            if not isinstance(item, dict) or "value" not in item:
                raise CatalogError(f"signals['{signal_name}'].values entries need 'value'")
            enum_values.add(item["value"])
        derive = spec.get("derive", {})
        default = derive.get("default")
        if default is None:
            raise CatalogError(
                f"signals['{signal_name}'] enum derive requires explicit default for total mapping"
            )
        if default not in enum_values:
            raise CatalogError(
                f"signals['{signal_name}'] derive.default '{default}' not in enum values"
            )

    derive = spec.get("derive")
    if not isinstance(derive, dict):
        raise CatalogError(f"signals['{signal_name}'].derive must be an object")
    _validate_derive_expr(signal_name, derive, bitfields)


def _validate_derive_expr(signal_name: str, expr: Dict[str, Any], bitfields: Dict[str, str]) -> None:
    op = expr.get("op")
    if op not in {"path", "flag", "map", "first_match"}:
        raise CatalogError(f"signals['{signal_name}'].derive has unsupported op '{op}'")

    if op == "path":
        if not isinstance(expr.get("path"), str) or not expr["path"]:
            raise CatalogError(f"signals['{signal_name}'].derive.path requires non-empty 'path'")
        return

    if op == "flag":
        field_ref = expr.get("field_ref")
        if field_ref not in bitfields:
            raise CatalogError(f"signals['{signal_name}'].derive.flag unknown field_ref '{field_ref}'")
        bit = expr.get("bit")
        if not isinstance(bit, int) or bit < 0:
            raise CatalogError(f"signals['{signal_name}'].derive.flag bit must be >= 0 integer")
        return

    if op == "map":
        from_expr = expr.get("from")
        if not isinstance(from_expr, dict):
            raise CatalogError(f"signals['{signal_name}'].derive.map requires object 'from'")
        _validate_derive_expr(signal_name, from_expr, bitfields)
        if not isinstance(expr.get("map"), dict):
            raise CatalogError(f"signals['{signal_name}'].derive.map requires object 'map'")
        return

    if op == "first_match":
        cases = expr.get("cases")
        if not isinstance(cases, list):
            raise CatalogError(f"signals['{signal_name}'].derive.first_match requires list 'cases'")
        for case in cases:
            if not isinstance(case, dict) or "when" not in case or "value" not in case:
                raise CatalogError(
                    f"signals['{signal_name}'].derive.first_match cases need 'when' and 'value'"
                )
            when_expr = case.get("when")
            if not isinstance(when_expr, dict):
                raise CatalogError(
                    f"signals['{signal_name}'].derive.first_match case 'when' must be object"
                )
            _validate_derive_expr(signal_name, when_expr, bitfields)


def derive_signal_values(catalog: Dict[str, Any], entry: Dict[str, Any]) -> Dict[str, Any]:
    values: Dict[str, Any] = {}
    bitfields = catalog["bitfields"]
    for signal_name, spec in catalog["signals"].items():
        derived = _eval_derive(spec["derive"], entry, bitfields)
        values[signal_name] = _normalize_derived_value(spec, derived)
    return values


def _eval_derive(expr: Dict[str, Any], entry: Dict[str, Any], bitfields: Dict[str, str]) -> Any:
    op = expr["op"]
    if op == "path":
        exists, value = _get_path_with_dashboard_fallback(entry, expr["path"])
        if exists:
            return value
        return expr.get("default")

    if op == "flag":
        field_path = bitfields[expr["field_ref"]]
        exists, value = _get_path_with_dashboard_fallback(entry, field_path)
        bits = int(value) if exists and value is not None else 0
        mask = 1 << int(expr["bit"])
        return bool(bits & mask)

    if op == "map":
        raw = _eval_derive(expr["from"], entry, bitfields)
        map_table = expr.get("map", {})
        key = str(raw).lower() if isinstance(raw, bool) else str(raw)
        if key in map_table:
            return map_table[key]
        return expr.get("default")

    if op == "first_match":
        for case in expr.get("cases", []):
            if bool(_eval_derive(case["when"], entry, bitfields)):
                return case["value"]
        return expr.get("default")

    return None


def _normalize_derived_value(spec: Dict[str, Any], value: Any) -> Any:
    signal_type = spec["type"]
    if signal_type == "bool":
        return bool(value)

    if signal_type == "enum":
        allowed = {item["value"] for item in spec.get("values", []) if isinstance(item, dict)}
        if value in allowed:
            return value
        default = spec.get("derive", {}).get("default")
        if default in allowed:
            return default
        # Catalog validator should prevent this; keep deterministic fallback.
        return next(iter(allowed)) if allowed else None

    return value


def validate_condition(
    condition: Dict[str, Any],
    catalog: Dict[str, Any],
    *,
    rule_id: str,
) -> None:
    if not isinstance(condition, dict):
        raise ValueError(f"Rule '{rule_id}': condition must be an object")

    signal = condition.get("signal")
    if signal not in catalog["signals"]:
        raise ValueError(f"Rule '{rule_id}': unknown signal '{signal}'")

    op = condition.get("op")
    if op not in catalog["operators"]:
        raise ValueError(f"Rule '{rule_id}': unknown operator '{op}'")

    has_value = "value" in condition
    if op in VALUE_REQUIRED_OPS and not has_value:
        raise ValueError(f"Rule '{rule_id}': operator '{op}' requires 'value'")
    if op in VALUE_OPTIONAL_OPS and not has_value:
        return

    signal_spec = catalog["signals"][signal]
    signal_type = signal_spec["type"]
    value = condition.get("value")

    if signal_type == "bool":
        if op in {"eq", "ne"}:
            if not isinstance(value, bool):
                raise ValueError(f"Rule '{rule_id}': signal '{signal}' requires boolean value")
        elif op in {"in", "nin"}:
            if not isinstance(value, list) or not all(isinstance(v, bool) for v in value):
                raise ValueError(
                    f"Rule '{rule_id}': signal '{signal}' requires list[bool] for '{op}'"
                )
        return

    if signal_type == "enum":
        allowed = {item["value"] for item in signal_spec.get("values", []) if isinstance(item, dict)}
        if op in {"eq", "ne"}:
            if not isinstance(value, str) or value not in allowed:
                raise ValueError(
                    f"Rule '{rule_id}': signal '{signal}' value must be one of {sorted(allowed)}"
                )
        elif op in {"in", "nin"}:
            if (
                not isinstance(value, list)
                or not value
                or not all(isinstance(v, str) and v in allowed for v in value)
            ):
                raise ValueError(
                    f"Rule '{rule_id}': signal '{signal}' requires list of valid enum values"
                )


def evaluate_condition(condition: Dict[str, Any], signal_values: Dict[str, Any]) -> bool:
    signal = condition.get("signal")
    op = condition.get("op")
    value = signal_values.get(signal)
    if op == "exists":
        expected = condition.get("value", True)
        return bool(value is not None) is bool(expected)

    target = condition.get("value")
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


def list_catalog_options(catalog: Dict[str, Any]) -> Dict[str, Any]:
    """Return UI-ready options without hardcoded names."""
    return {
        "version": catalog["version"],
        "ui_tiers": catalog["ui_tiers"],
        "operators": catalog["operators"],
        "signals": catalog["signals"],
    }
