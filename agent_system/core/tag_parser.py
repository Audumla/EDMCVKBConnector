"""
tag_parser.py - Parse inline dispatch tags from user prompts.

Supported tag syntax (case-insensitive, order-independent):

  #plan <provider>      Sets the planning agent  (e.g. #plan gemini)
  #exec <provider>      Sets the executor agent  (e.g. #exec codex)
  #budget <level>       Sets thinking budget     (e.g. #budget high)

  Legacy / backward-compat:
  #agent:<budget>:<planner>  Maps to planner + budget (executor from config)
  /agent:<budget>:<planner>  Same, with forward-slash prefix

Providers are validated against delegation-config.json.  Unknown providers
emit a warning string in the returned ``warnings`` list; the tag is ignored
and the caller's default is kept.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Config loading (lazy, no circular imports)
# ---------------------------------------------------------------------------

_VALID_BUDGETS = {"none", "low", "medium", "high"}
# Budget aliases used in the legacy #agent:<budget>:<planner> syntax
_BUDGET_ALIASES: dict[str, str] = {
    "deep": "high",
    "fast": "low",
    "verbose": "high",
}

_config_cache: dict[str, Any] | None = None


def _load_config() -> dict[str, Any]:
    global _config_cache
    if _config_cache is not None:
        return _config_cache
    # Locate delegation-config.json relative to this file
    cfg_path = Path(__file__).resolve().parent.parent / "config" / "delegation-config.json"
    if cfg_path.exists():
        try:
            _config_cache = json.loads(cfg_path.read_text(encoding="utf-8"))
            return _config_cache
        except json.JSONDecodeError:
            pass
    _config_cache = {}
    return _config_cache


def _enabled_providers(role: str) -> set[str]:
    cfg = _load_config()
    section = cfg.get(role, {})
    return {name for name, v in section.items() if v.get("enabled", True)}


def _all_known_providers() -> set[str]:
    cfg = _load_config()
    names: set[str] = set()
    for role in ("planners", "executors"):
        names.update(cfg.get(role, {}).keys())
    return names


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_inline_tags(prompt: str) -> dict[str, Any]:
    """Parse dispatch tags from *prompt* and return a result dict.

    Returns::

        {
            "planner": str | None,   # provider name or None if not specified
            "executor": str | None,  # provider name or None if not specified
            "budget":   str | None,  # budget level or None if not specified
            "clean_prompt": str,     # prompt with all recognised tags stripped
            "warnings": list[str],   # validation messages (unknown providers etc.)
        }
    """
    planner: str | None = None
    executor: str | None = None
    budget: str | None = None
    warnings: list[str] = []

    # Work on a mutable copy; we'll strip recognised tags from it
    text = prompt

    # ------------------------------------------------------------------
    # 1. Legacy #agent:<budget>:<planner> / /agent:<budget>:<planner>
    # ------------------------------------------------------------------
    legacy_pattern = re.compile(
        r"(?:#|/)agent:([a-zA-Z0-9_-]+):([a-zA-Z0-9_-]+)",
        re.IGNORECASE,
    )
    for m in legacy_pattern.finditer(text):
        raw_budget, raw_planner = m.group(1), m.group(2)
        resolved_budget = _BUDGET_ALIASES.get(raw_budget.lower(), raw_budget.lower())
        if resolved_budget in _VALID_BUDGETS:
            budget = resolved_budget
        else:
            warnings.append(
                f"Unknown budget '{raw_budget}' in {m.group(0)!r}; "
                f"valid values: {', '.join(sorted(_VALID_BUDGETS))}"
            )
        resolved_planner = raw_planner.lower()
        enabled = _enabled_providers("planners")
        if resolved_planner in enabled:
            planner = resolved_planner
        elif resolved_planner in _all_known_providers():
            warnings.append(
                f"Planner '{resolved_planner}' is disabled in config; tag ignored."
            )
        else:
            warnings.append(
                f"Unknown planner '{resolved_planner}' in {m.group(0)!r}; tag ignored."
            )
    text = legacy_pattern.sub("", text)

    # ------------------------------------------------------------------
    # 2. #plan <provider>
    # ------------------------------------------------------------------
    plan_pattern = re.compile(r"#plan\s+([a-zA-Z0-9_-]+)", re.IGNORECASE)
    for m in plan_pattern.finditer(text):
        raw = m.group(1).lower()
        enabled = _enabled_providers("planners")
        if raw in enabled:
            planner = raw
        elif raw in _all_known_providers():
            warnings.append(f"Planner '{raw}' is disabled in config; #plan tag ignored.")
        else:
            warnings.append(f"Unknown planner '{raw}'; #plan tag ignored.")
    text = plan_pattern.sub("", text)

    # ------------------------------------------------------------------
    # 3. #exec <provider>
    # ------------------------------------------------------------------
    exec_pattern = re.compile(r"#exec\s+([a-zA-Z0-9_-]+)", re.IGNORECASE)
    for m in exec_pattern.finditer(text):
        raw = m.group(1).lower()
        enabled = _enabled_providers("executors")
        if raw in enabled:
            executor = raw
        elif raw in _all_known_providers():
            warnings.append(f"Executor '{raw}' is disabled in config; #exec tag ignored.")
        else:
            warnings.append(f"Unknown executor '{raw}'; #exec tag ignored.")
    text = exec_pattern.sub("", text)

    # ------------------------------------------------------------------
    # 4. #budget <level>
    # ------------------------------------------------------------------
    budget_pattern = re.compile(r"#budget\s+([a-zA-Z0-9_-]+)", re.IGNORECASE)
    for m in budget_pattern.finditer(text):
        raw = m.group(1).lower()
        resolved = _BUDGET_ALIASES.get(raw, raw)
        if resolved in _VALID_BUDGETS:
            budget = resolved
        else:
            warnings.append(
                f"Unknown budget level '{raw}'; #budget tag ignored. "
                f"Valid: {', '.join(sorted(_VALID_BUDGETS))}"
            )
    text = budget_pattern.sub("", text)

    # ------------------------------------------------------------------
    # Tidy up the cleaned prompt (collapse extra whitespace / blank lines)
    # ------------------------------------------------------------------
    clean_lines = [line.rstrip() for line in text.splitlines()]
    # Drop leading/trailing blank lines
    while clean_lines and not clean_lines[0].strip():
        clean_lines.pop(0)
    while clean_lines and not clean_lines[-1].strip():
        clean_lines.pop()
    clean_prompt = "\n".join(clean_lines).strip()

    return {
        "planner": planner,
        "executor": executor,
        "budget": budget,
        "clean_prompt": clean_prompt,
        "warnings": warnings,
    }


# ---------------------------------------------------------------------------
# CLI helper — useful for quick testing from a terminal
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    sample = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "#plan gemini #exec codex #budget high Fix the broken unit tests"
    result = parse_inline_tags(sample)
    print(f"Planner : {result['planner']}")
    print(f"Executor: {result['executor']}")
    print(f"Budget  : {result['budget']}")
    print(f"Prompt  : {result['clean_prompt']!r}")
    if result["warnings"]:
        print("Warnings:")
        for w in result["warnings"]:
            print(f"  ! {w}")
