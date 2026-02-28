"""Provider-specific concise usage parsers for dashboard output."""
from __future__ import annotations

import json
import re
from typing import Any, Callable


def _with_defaults(payload: dict[str, Any]) -> dict[str, Any]:
    result = dict(payload)
    result.setdefault("status", "ACTIVE")
    result.setdefault("display", result["status"])
    result.setdefault("selector_key", None)
    result.setdefault("selector_options", [])
    result.setdefault("selector_selected", None)
    return result


def parse_opencode_stats(text: str) -> dict[str, Any]:
    stats: dict[str, str] = {}
    for line in text.splitlines():
        if "Total Cost" in line:
            stats["cost"] = line.split()[-1]
        if "Input" in line and "Tokens" not in line:
            stats["input"] = line.split()[-1]
        if "Output" in line and "Tokens" not in line:
            stats["output"] = line.split()[-1]
    if stats:
        return _with_defaults({
            "status": "ACTIVE",
            "display": f"Cost: {stats.get('cost', '-')} | In: {stats.get('input', '-')} | Out: {stats.get('output', '-')}",
            **stats,
        })
    return _with_defaults({"status": "ACTIVE", "display": "ACTIVE"})


def parse_ollama_ps(text: str) -> dict[str, Any]:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    model_lines = [ln for ln in lines if not ln.upper().startswith("NAME")]
    if not model_lines:
        return _with_defaults({"status": "ONLINE", "display": "No models running"})
    options: list[dict[str, Any]] = []
    for ln in model_lines:
        model = ln.split()[0]
        options.append({"key": model, "label": model, "status": "ONLINE", "display": ln})
    first_model = options[0]["key"]
    return _with_defaults({
        "status": "ONLINE",
        "display": f"{len(model_lines)} model(s) running | {first_model}",
        "selector_key": "model",
        "selector_options": options,
        "selector_selected": first_model,
    })


def parse_gemini_usage_json(text: str) -> dict[str, Any]:
    input_tokens = output_tokens = None
    selector_options: list[dict[str, Any]] = []
    try:
        payload = json.loads(text)
        usage = payload.get("usage") if isinstance(payload, dict) else None
        if isinstance(usage, dict):
            input_tokens = usage.get("input_tokens")
            output_tokens = usage.get("output_tokens")
        if isinstance(payload, dict):
            models = payload.get("models")
            if isinstance(models, list):
                for item in models:
                    if not isinstance(item, dict):
                        continue
                    key = str(item.get("model") or item.get("name") or "").strip()
                    if not key:
                        continue
                    in_tok = item.get("input_tokens", "-")
                    out_tok = item.get("output_tokens", "-")
                    selector_options.append(
                        {"key": key, "label": key, "status": "ACTIVE", "display": f"In: {in_tok} | Out: {out_tok}"}
                    )
            elif isinstance(models, dict):
                for key, item in models.items():
                    if not isinstance(item, dict):
                        continue
                    in_tok = item.get("input_tokens", "-")
                    out_tok = item.get("output_tokens", "-")
                    selector_options.append(
                        {"key": str(key), "label": str(key), "status": "ACTIVE", "display": f"In: {in_tok} | Out: {out_tok}"}
                    )
        if input_tokens is None and isinstance(payload, dict):
            input_tokens = payload.get("input_tokens")
        if output_tokens is None and isinstance(payload, dict):
            output_tokens = payload.get("output_tokens")
    except Exception:
        pass

    if input_tokens is None or output_tokens is None:
        in_match = re.search(r"input[_\s-]*tokens[^0-9]*([0-9,]+)", text, flags=re.IGNORECASE)
        out_match = re.search(r"output[_\s-]*tokens[^0-9]*([0-9,]+)", text, flags=re.IGNORECASE)
        input_tokens = input_tokens if input_tokens is not None else (in_match.group(1) if in_match else "-")
        output_tokens = output_tokens if output_tokens is not None else (out_match.group(1) if out_match else "-")

    # Fallback: parse text-table style model usage output from Gemini CLI /stats.
    if not selector_options:
        for raw in text.splitlines():
            line = raw.strip()
            if not line:
                continue
            # Handle boxed table output with leading/trailing box chars.
            if line.startswith("│") and line.endswith("│"):
                line = line.strip("│").strip()
            if not line.lower().startswith("gemini-"):
                continue
            # Pattern: <model> <reqs> <usage remaining...>
            match = re.match(r"^(gemini-[\w\.\-]+)\s+\S+\s+(.+)$", line)
            if not match:
                continue
            model = match.group(1).strip()
            remaining = match.group(2).strip()
            selector_options.append(
                {"key": model, "label": model, "status": "ACTIVE", "display": remaining}
            )
    quota_reset = re.search(r"quota will reset after\s+([0-9hms ]+)", text, flags=re.IGNORECASE)
    if quota_reset:
        return _with_defaults(
            {
                "status": "QUOTA_EXHAUSTED",
                "display": f"Quota exhausted | resets in {quota_reset.group(1).strip()}",
            }
        )
    if re.search(r"exhausted your capacity", text, flags=re.IGNORECASE):
        return _with_defaults({"status": "QUOTA_EXHAUSTED", "display": "Quota exhausted"})

    response = {"status": "ACTIVE", "display": f"In: {input_tokens} | Out: {output_tokens}"}
    if selector_options:
        response["selector_key"] = "model"
        response["selector_options"] = selector_options
        response["selector_selected"] = selector_options[0]["key"]
    return _with_defaults(response)


def parse_claude_usage(text: str) -> dict[str, Any]:
    percent_match = re.search(r"([0-9]{1,3})\s*%", text)
    reset_match = re.search(r"(reset[^\\n\\.]*|renews?[^\\n\\.]*)", text, flags=re.IGNORECASE)
    pct = f"{percent_match.group(1)}%" if percent_match else "n/a"
    reset = reset_match.group(1).strip() if reset_match else "reset: n/a"
    return _with_defaults({"status": "ACTIVE", "display": f"Used: {pct} | {reset}"})


def parse_version(text: str) -> dict[str, Any]:
    line = (text.splitlines()[0] if text else "").strip()
    return _with_defaults({"status": "ACTIVE", "display": line or "Version: unknown"})


def parse_codex_login_status(text: str) -> dict[str, Any]:
    normalized = (text or "").strip()
    if not normalized:
        return _with_defaults({"status": "ERROR", "display": "Unable to determine login status"})
    first = normalized.splitlines()[0].strip()
    if "Logged in" in first:
        return _with_defaults({"status": "ACTIVE", "display": first})
    return _with_defaults({"status": "ERROR", "display": first})


def parse_copilot_help(text: str) -> dict[str, Any]:
    if text and ("copilot" in text.lower() or "github" in text.lower()):
        return _with_defaults({"status": "ACTIVE", "display": "CLI available | usage via subscription"})
    return _with_defaults({"status": "ACTIVE", "display": "Subscription provider"})


def parse_help_available(_: str) -> dict[str, Any]:
    return _with_defaults({"status": "ACTIVE", "display": "CLI available"})


PARSERS: dict[str, Callable[[str], dict[str, Any]]] = {
    "opencode_stats": parse_opencode_stats,
    "ollama_ps": parse_ollama_ps,
    "gemini_usage_json": parse_gemini_usage_json,
    "claude_usage": parse_claude_usage,
    "version": parse_version,
    "codex_login_status": parse_codex_login_status,
    "copilot_help": parse_copilot_help,
    "help_available": parse_help_available,
}


def parse_usage(parser_name: str | None, text: str) -> dict[str, Any]:
    if parser_name and parser_name in PARSERS:
        return PARSERS[parser_name](text)
    first_line = text.splitlines()[0] if text else "ACTIVE"
    return _with_defaults({"status": "ACTIVE", "display": first_line})
