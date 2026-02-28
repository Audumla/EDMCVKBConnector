"""Config-driven provider usage services for dashboard and reporting."""
from __future__ import annotations

from typing import Any

try:
    from agent_system.core.provider_registry import get_provider_config, is_provider_test_blocked
    from agent_system.core.providers.command_runner import resolve_command, run_command, usage_timeout
    from agent_system.core.providers.usage_parsers import parse_usage
except ImportError:
    from provider_registry import get_provider_config, is_provider_test_blocked
    from providers.command_runner import resolve_command, run_command, usage_timeout
    from providers.usage_parsers import parse_usage


def _provider_usage_cfg(provider: str) -> tuple[dict[str, Any], dict[str, Any]]:
    cfg = get_provider_config(provider, role="executors")
    if not cfg:
        cfg = get_provider_config(provider)
    return cfg, cfg.get("usage", {}) if isinstance(cfg, dict) else {}


def _normalize_usage_payload(payload: dict[str, Any]) -> dict[str, Any]:
    result = dict(payload or {})
    result.setdefault("status", "ACTIVE")
    result.setdefault("display", result["status"])
    result.setdefault("selector_key", None)
    result.setdefault("selector_options", [])
    result.setdefault("selector_selected", None)
    return result


def get_provider_usage_summary(provider: str) -> dict[str, Any]:
    cfg, usage_cfg = _provider_usage_cfg(provider)
    if is_provider_test_blocked(cfg):
        return _normalize_usage_payload({"status": "TEST_DISABLED", "display": "Disabled in tests"})

    quick_static = usage_cfg.get("quick_static")
    if isinstance(quick_static, dict):
        return _normalize_usage_payload(quick_static)

    template = usage_cfg.get("quick_command")
    if not template:
        return _normalize_usage_payload({"status": "ACTIVE", "display": "ACTIVE"})

    cmd = resolve_command(template, provider=provider, provider_bin=str(cfg.get("bin", provider)))
    try:
        res = run_command(cmd, timeout_sec=usage_timeout(usage_cfg, "quick_timeout_sec", 10))
        parser_name = usage_cfg.get("quick_parser")
        raw = "\n".join(part for part in [(res.stdout or "").strip(), (res.stderr or "").strip()] if part).strip()
        if parser_name and raw:
            parsed = _normalize_usage_payload(parse_usage(parser_name, raw))
            if res.returncode == 0:
                return parsed
            if parsed.get("status") not in {"ACTIVE", "ERROR"} or parsed.get("display", "").strip() not in {"ACTIVE", "In: - | Out: -"}:
                return parsed
        if res.returncode != 0:
            err_line = (raw.splitlines() or ["ERROR"])[0]
            return _normalize_usage_payload({"status": "ERROR", "display": f"ERROR: {err_line}"})
        return _normalize_usage_payload(parse_usage(parser_name, raw))
    except Exception as e:
        return _normalize_usage_payload({"status": "ERROR", "display": f"ERROR: {e}"})


def get_provider_detailed_usage(provider: str) -> str:
    cfg, usage_cfg = _provider_usage_cfg(provider)
    if is_provider_test_blocked(cfg):
        return f"Detailed usage disabled in tests for '{provider}'."
    template = usage_cfg.get("detailed_command")
    if not template:
        return f"No detailed usage command configured for '{provider}'."

    cmd = resolve_command(template, provider=provider, provider_bin=str(cfg.get("bin", provider)))
    try:
        res = run_command(cmd, timeout_sec=usage_timeout(usage_cfg, "timeout_sec", 30))
        return (res.stdout or "") if res.returncode == 0 else (res.stderr or "")
    except Exception as e:
        return f"ERROR: Failed to run {provider}: {e}"
