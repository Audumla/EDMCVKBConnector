"""
agent_runner_utils.py - Shared utilities for agent runner scripts.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Pricing tables (USD per million tokens)
# ---------------------------------------------------------------------------
AGENT_PRICING: dict[str, dict[str, float]] = {
    # Claude
    "claude-opus-4-6":     {"input": 15.00, "output": 75.00},
    "claude-sonnet-4-6":   {"input":  3.00, "output": 15.00},
    "claude-haiku-4-5":    {"input":  0.80, "output":  4.00},
    "claude-3-5-sonnet":   {"input":  3.00, "output": 15.00},
    # Gemini
    "gemini-2.0-flash":    {"input":  0.10, "output":  0.40},
    "gemini-2.0-pro":      {"input":  1.25, "output":  5.00},
    "gemini-1.5-pro":      {"input":  1.25, "output":  5.00},
    "gemini-1.5-flash":    {"input":  0.075, "output": 0.30},
    # Codex / GPT
    "gpt-5":               {"input":  1.25, "output": 10.00},
    "gpt-5-mini":          {"input":  0.15, "output":  0.60},
    "gpt-4o":              {"input":  5.00, "output": 15.00},
    "gpt-4o-mini":         {"input":  0.15, "output":  0.60},
    # Others
    "opencode-latest":     {"input":  1.00, "output":  5.00},
    "copilot-gpt-4":       {"input":  0.00, "output":  0.00},
    "local-llm":           {"input":  0.00, "output":  0.00},
}

# Aliases
AGENT_PRICING["sonnet"] = AGENT_PRICING["claude-3-5-sonnet"]
AGENT_PRICING["opus"] = AGENT_PRICING["claude-opus-4-6"]
AGENT_PRICING["haiku"] = AGENT_PRICING["claude-haiku-4-5"]
AGENT_PRICING["gemini"] = AGENT_PRICING["gemini-2.0-flash"]
AGENT_PRICING["codex"] = AGENT_PRICING["gpt-5"]


# OpenAI API pricing table used for best-effort Codex execution cost estimates.
CODEX_PRICING: dict[str, dict[str, float]] = {
    "gpt-5": {"input": 1.25, "cached_input": 0.125, "output": 10.00},
    "gpt-5-codex": {"input": 1.25, "cached_input": 0.125, "output": 10.00},
    "gpt-5-mini": {"input": 0.25, "cached_input": 0.025, "output": 2.00},
    "gpt-5-nano": {"input": 0.05, "cached_input": 0.025, "output": 0.40},
    "codex": {"input": 1.25, "cached_input": 0.125, "output": 10.00},
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def estimate_planner_cost(model: str | None, input_tokens: int, output_tokens: int) -> dict[str, Any]:
    if not model:
        return {"input_usd": None, "output_usd": None, "total_usd": None, "note": "unknown model"}
    
    pricing = AGENT_PRICING.get(model)
    if pricing is None:
        for key, val in AGENT_PRICING.items():
            if model.startswith(key) or key.startswith(model):
                pricing = val
                break
    
    if pricing is None:
        return {"input_usd": None, "output_usd": None, "total_usd": None, "note": f"unknown pricing for {model}"}

    input_usd  = (input_tokens  / 1_000_000) * pricing["input"]
    output_usd = (output_tokens / 1_000_000) * pricing["output"]
    return {
        "input_usd":  round(input_usd,  6),
        "output_usd": round(output_usd, 6),
        "total_usd":  round(input_usd + output_usd, 6),
        "rates_per_million": pricing,
    }


def _resolve_codex_pricing(
    *,
    model: str,
    input_rate: float | None,
    cached_input_rate: float | None,
    output_rate: float | None,
) -> tuple[dict[str, float] | None, str]:
    if (
        input_rate is not None
        and cached_input_rate is not None
        and output_rate is not None
    ):
        return {
            "input": float(input_rate),
            "cached_input": float(cached_input_rate),
            "output": float(output_rate),
        }, "manual_override"

    pricing = CODEX_PRICING.get(model)
    if pricing is None:
        for key, value in CODEX_PRICING.items():
            if model.startswith(key) or key.startswith(model):
                pricing = value
                break

    if pricing is None:
        return None, "unknown_model"
    return pricing, "pricing_table"


def estimate_codex_cost(
    *,
    model: str,
    input_tokens: int | None,
    cached_input_tokens: int | None,
    output_tokens: int | None,
    input_rate: float | None,
    cached_input_rate: float | None,
    output_rate: float | None,
) -> dict[str, Any]:
    rates, rate_source = _resolve_codex_pricing(
        model=model,
        input_rate=input_rate,
        cached_input_rate=cached_input_rate,
        output_rate=output_rate,
    )

    if rates is None:
        return {
            "estimated": False,
            "model": model,
            "input_usd": None,
            "cached_input_usd": None,
            "output_usd": None,
            "total_usd": None,
            "rate_source": rate_source,
            "rates_per_million": None,
            "note": "No Codex cost estimate: unknown model and no explicit rate override.",
        }

    input_count = int(input_tokens or 0)
    cached_count = int(cached_input_tokens or 0)
    output_count = int(output_tokens or 0)
    non_cached_input_count = max(input_count - cached_count, 0)

    input_usd = (non_cached_input_count / 1_000_000) * rates["input"]
    cached_input_usd = (cached_count / 1_000_000) * rates["cached_input"]
    output_usd = (output_count / 1_000_000) * rates["output"]
    total_usd = input_usd + cached_input_usd + output_usd

    return {
        "estimated": True,
        "model": model,
        "input_usd": round(input_usd, 6),
        "cached_input_usd": round(cached_input_usd, 6),
        "output_usd": round(output_usd, 6),
        "total_usd": round(total_usd, 6),
        "rate_source": rate_source,
        "rates_per_million": rates,
        "billable_input_tokens": non_cached_input_count,
    }


def detect_codex_model(run_dir: Path, fallback_model: str) -> str:
    metadata_file = run_dir / "metadata.json"
    if not metadata_file.exists():
        return fallback_model

    try:
        metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return fallback_model

    command = metadata.get("command")
    if not isinstance(command, list):
        return fallback_model

    detected = None
    for idx, token in enumerate(command):
        if token == "--model" and idx + 1 < len(command):
            candidate = command[idx + 1]
            if isinstance(candidate, str) and candidate.strip():
                detected = candidate.strip()
    
    return detected if detected else fallback_model


def parse_codex_events(events_file: Path) -> dict[str, Any]:
    if not events_file.exists():
        return {}

    usage: dict = {}
    thread_id: str | None = None
    command_count = 0
    reasoning_count = 0
    agent_message_count = 0
    event_count = 0

    with events_file.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
                event_count += 1

                ev_type = ev.get("type", "")
                if ev_type == "thread.started":
                    thread_id = ev.get("thread_id")
                elif ev_type == "turn.completed":
                    usage = ev.get("usage", {})
                elif ev_type == "item.completed":
                    item = ev.get("item", {})
                    item_type = item.get("type", "")
                    if item_type == "command_execution":
                        command_count += 1
                    elif item_type == "reasoning":
                        reasoning_count += 1
                    elif item_type == "agent_message":
                        agent_message_count += 1
            except json.JSONDecodeError:
                pass

    return {
        "thread_id": thread_id,
        "event_count": event_count,
        "command_executions": command_count,
        "reasoning_steps": reasoning_count,
        "agent_messages": agent_message_count,
        "token_usage": {
            "input_tokens":        usage.get("input_tokens"),
            "cached_input_tokens": usage.get("cached_input_tokens"),
            "output_tokens":       usage.get("output_tokens"),
        },
    }


def build_report(
    *,
    run_dir: Path,
    planner_model: str | None,
    planner_input_tokens: int,
    planner_output_tokens: int,
    thinking_budget: str,
    codex_model_hint: str,
    codex_input_rate: float | None = None,
    codex_cached_input_rate: float | None = None,
    codex_output_rate: float | None = None,
    task_summary: str = "",
    codex_returncode: int = 0,
    generated_at: str | None = None,
) -> dict[str, Any]:
    if generated_at is None:
        generated_at = utc_now()
        
    status_file  = run_dir / "status.json"
    events_file  = run_dir / "events.jsonl"
    final_msg    = run_dir / "final_message.txt"

    status: dict = {}
    if status_file.exists():
        try:
            status = json.loads(status_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass

    codex_events = parse_codex_events(events_file)
    final_message_text = final_msg.read_text(encoding="utf-8").strip() if final_msg.exists() else None
    codex_model = detect_codex_model(run_dir, codex_model_hint)

    # Duration
    duration_seconds: float | None = None
    started  = status.get("started_at")
    ended    = status.get("ended_at")
    if started and ended:
        try:
            fmt = "%Y-%m-%dT%H:%M:%SZ"
            duration_seconds = (
                datetime.strptime(ended, fmt) - datetime.strptime(started, fmt)
            ).total_seconds()
        except ValueError:
            pass

    # Codex cache savings
    codex_usage = codex_events.get("token_usage", {})
    cached = codex_usage.get("cached_input_tokens") or 0
    total_input = codex_usage.get("input_tokens") or 0
    cache_hit_pct = round(100 * cached / total_input, 1) if total_input else None

    if status.get("cost_estimate") and not (codex_input_rate or codex_cached_input_rate or codex_output_rate):
        codex_cost = status.get("cost_estimate")
    else:
        codex_cost = estimate_codex_cost(
            model=codex_model,
            input_tokens=codex_usage.get("input_tokens"),
            cached_input_tokens=codex_usage.get("cached_input_tokens"),
            output_tokens=codex_usage.get("output_tokens"),
            input_rate=codex_input_rate,
            cached_input_rate=codex_cached_input_rate,
            output_rate=codex_output_rate,
        )
    planner_cost = estimate_planner_cost(planner_model, planner_input_tokens, planner_output_tokens)
    total_estimated_cost: float | None = None
    if planner_cost.get("total_usd") is not None and codex_cost.get("total_usd") is not None:
        total_estimated_cost = round(
            float(planner_cost["total_usd"]) + float(codex_cost["total_usd"]), 6
        )

    return {
        "generated_at": generated_at,
        "run_id": run_dir.name,
        "task_summary": task_summary,

        "planner_results": {
            "model": planner_model,
            "thinking_budget": thinking_budget,
            "input_tokens":  planner_input_tokens,
            "output_tokens": planner_output_tokens,
            "cost": planner_cost,
        },

        "executor_results": {
            "state":           status.get("state"),
            "return_code":     codex_returncode,
            "model":           codex_model,
            "started_at":      started,
            "ended_at":        ended,
            "duration_seconds": duration_seconds,
            "thread_id":       codex_events.get("thread_id"),
            "events": {
                "total":               codex_events.get("event_count"),
                "command_executions":  codex_events.get("command_executions"),
                "reasoning_steps":     codex_events.get("reasoning_steps"),
                "agent_messages":      codex_events.get("agent_messages"),
            },
            "token_usage": {
                **codex_usage,
                "cache_hit_pct": cache_hit_pct,
            },
            "cost_estimate": codex_cost,
            "final_message": final_message_text,
        },

        "combined": {
            "planner_total_tokens": planner_input_tokens + planner_output_tokens,
            "executor_total_tokens":  (total_input + (codex_usage.get("output_tokens") or 0)),
            "planner_cost_usd": planner_cost.get("total_usd"),
            "executor_cost_usd": codex_cost.get("total_usd"),
            "total_estimated_cost_usd": total_estimated_cost,
            "note": "Executor cost is an estimate from token usage and configured rate table/overrides.",
        },
    }


def _fmt_int(value: Any) -> str:
    if value is None:
        return "n/a"
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return "n/a"


def _fmt_money(value: Any) -> str:
    if value is None:
        return "n/a"
    try:
        return f"${float(value):,.4f}"
    except (TypeError, ValueError):
        return "n/a"


def _fmt_pct(value: Any) -> str:
    if value is None:
        return "n/a"
    try:
        return f"{float(value):.1f}%"
    except (TypeError, ValueError):
        return "n/a"


def _fmt_duration_seconds(value: Any) -> str:
    if value is None:
        return "n/a"
    try:
        seconds = int(round(float(value)))
    except (TypeError, ValueError):
        return "n/a"
    mins, secs = divmod(seconds, 60)
    hours, mins = divmod(mins, 60)
    if hours:
        return f"{hours}h {mins}m {secs}s"
    if mins:
        return f"{mins}m {secs}s"
    return f"{secs}s"


def build_formatted_results(report: dict[str, Any]) -> str:
    executor_exec = report.get("executor_results", {})
    executor_tokens = executor_exec.get("token_usage", {})
    executor_cost = executor_exec.get("cost_estimate", {})
    combined = report.get("combined", {})
    final_message = executor_exec.get("final_message") or "(No final message captured.)"
    events = executor_exec.get("events", {})

    lines = [
        "# Agent Results",
        "",
        f"- Run ID: `{report.get('run_id', 'n/a')}`",
        f"- Task: {report.get('task_summary') or 'n/a'}",
        f"- State: `{executor_exec.get('state', 'n/a')}` (return code `{executor_exec.get('return_code', 'n/a')}`)",
        f"- Duration: {_fmt_duration_seconds(executor_exec.get('duration_seconds'))}",
        "",
        "## Execution",
        "",
        f"- Model: `{executor_exec.get('model', 'n/a')}`",
        (
            "- Events: "
            f"{_fmt_int(events.get('total'))} total, "
            f"{_fmt_int(events.get('command_executions'))} commands, "
            f"{_fmt_int(events.get('reasoning_steps'))} reasoning, "
            f"{_fmt_int(events.get('agent_messages'))} messages"
        ),
        "",
        "## Tokens",
        "",
        f"- Input: {_fmt_int(executor_tokens.get('input_tokens'))}",
        f"- Cached Input: {_fmt_int(executor_tokens.get('cached_input_tokens'))}",
        f"- Output: {_fmt_int(executor_tokens.get('output_tokens'))}",
        f"- Cache Hit: {_fmt_pct(executor_tokens.get('cache_hit_pct'))}",
        f"- Total (input + output): {_fmt_int(combined.get('executor_total_tokens'))}",
        "",
        "## Cost Estimate",
        "",
        f"- Execution Input: {_fmt_money(executor_cost.get('input_usd'))}",
        f"- Execution Cached Input: {_fmt_money(executor_cost.get('cached_input_usd'))}",
        f"- Execution Output: {_fmt_money(executor_cost.get('output_usd'))}",
        f"- Execution Total: {_fmt_money(executor_cost.get('total_usd'))}",
        f"- Agent Planning Total: {_fmt_money(combined.get('planner_cost_usd'))}",
        f"- Combined Estimated Total: {_fmt_money(combined.get('total_estimated_cost_usd'))}",
        f"- Estimation Basis: {combined.get('note') or 'n/a'}",
        "",
        "## Final Message",
        "",
        "```text",
        final_message,
        "```",
    ]
    return "\n".join(lines) + "\n"
