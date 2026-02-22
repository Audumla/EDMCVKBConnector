"""
claude_run_plan.py - Claude orchestration wrapper for run_codex_plan.py

Calls run_codex_plan.py with a plan file, then writes claude_report.json into the
run directory with Claude planning metadata, Codex execution summary, cost estimates,
and a preformatted codex_results.md summary.

Usage (called by Claude after writing a plan file):
    python scripts/agent_runners/claude_run_plan.py \\
        --plan-file agent_artifacts/claude/temp/my_plan.md \\
        --claude-model claude-sonnet-4-6 \\
        --task-summary "One-line description of what Claude is orchestrating" \\
        [--claude-input-tokens 5000] [--claude-output-tokens 2000] \\
        [--run-name label] [--dry-run] [--sandbox MODE] [--approval POLICY] ...

Note: Token estimates default to 5000 input / 2000 output for typical plan files. Adjust if your
plan is unusually large or requires extensive reasoning.

All remaining args after known claude_run_plan.py flags are forwarded to run_codex_plan.py.
The claude_report.json is written into the same run directory that run_codex_plan.py creates.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Load default configuration
CONFIG_FILE = PROJECT_ROOT / "scripts" / "delegation-config.json"
_config_defaults = {}
if CONFIG_FILE.exists():
    try:
        _config_data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        _config_defaults = _config_data.get("codex_delegation", {})
    except json.JSONDecodeError:
        pass

# ---------------------------------------------------------------------------
# Pricing tables (USD per million tokens)
# ---------------------------------------------------------------------------
CLAUDE_PRICING: dict[str, dict[str, float]] = {
    "claude-opus-4-6":     {"input": 15.00, "output": 75.00},
    "claude-sonnet-4-6":   {"input":  3.00, "output": 15.00},
    "claude-haiku-4-5":    {"input":  0.80, "output":  4.00},
    # aliases / shorthands
    "opus":                {"input": 15.00, "output": 75.00},
    "sonnet":              {"input":  3.00, "output": 15.00},
    "haiku":               {"input":  0.80, "output":  4.00},
}

# OpenAI API pricing table used for best-effort Codex execution cost estimates.
# Rates are configurable via CLI overrides in case your account/pricing differs.
CODEX_PRICING: dict[str, dict[str, float]] = {
    "gpt-5": {"input": 1.25, "cached_input": 0.125, "output": 10.00},
    "gpt-5-codex": {"input": 1.25, "cached_input": 0.125, "output": 10.00},
    "gpt-5-mini": {"input": 0.25, "cached_input": 0.025, "output": 2.00},
    "gpt-5-nano": {"input": 0.05, "cached_input": 0.005, "output": 0.40},
    # common aliases
    "codex": {"input": 1.25, "cached_input": 0.125, "output": 10.00},
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_args() -> tuple[argparse.Namespace, list[str]]:
    parser = argparse.ArgumentParser(
        description="Claude orchestration wrapper: calls run_codex_plan.py and appends claude_report.json.",
        add_help=True,
    )
    # Claude-specific args
    parser.add_argument("--claude-model", default=_config_defaults.get("claude_model", "claude-sonnet-4-6"),
                        help="Claude model ID used for the planning phase (default: from scripts/delegation-config.json or claude-sonnet-4-6).")
    parser.add_argument("--claude-input-tokens", type=int, default=_config_defaults.get("claude_input_tokens", 5000),
                        help="Input tokens used by Claude during planning (default: from scripts/delegation-config.json or 5000).")
    parser.add_argument("--claude-output-tokens", type=int, default=_config_defaults.get("claude_output_tokens", 2000),
                        help="Output tokens used by Claude during planning (default: from scripts/delegation-config.json or 2000).")
    parser.add_argument("--thinking-budget", default=_config_defaults.get("thinking_budget", "none"),
                        choices=["none", "low", "medium", "high"],
                        help="Extended thinking budget for Claude (default: from scripts/delegation-config.json or 'none'). Pass to run_codex_plan.py.")
    parser.add_argument("--task-summary", default="",
                        help="One-line description of the task Claude is orchestrating.")
    parser.add_argument(
        "--codex-model",
        default=_config_defaults.get("codex_model", "gpt-5"),
        help="Codex model used for execution-cost estimation (default: from scripts/delegation-config.json or gpt-5).",
    )
    parser.add_argument(
        "--codex-input-rate",
        type=float,
        default=None,
        help="Override Codex input token rate (USD per million).",
    )
    parser.add_argument(
        "--codex-cached-input-rate",
        type=float,
        default=None,
        help="Override Codex cached input token rate (USD per million).",
    )
    parser.add_argument(
        "--codex-output-rate",
        type=float,
        default=None,
        help="Override Codex output token rate (USD per million).",
    )
    # Required: plan file (also passed to run_codex_plan.py)
    parser.add_argument("--plan-file", required=True, type=Path,
                        help="Path to the plan file to hand to Codex.")
    return parser.parse_known_args()


def estimate_claude_cost(model: str, input_tokens: int, output_tokens: int) -> dict[str, Any]:
    pricing = CLAUDE_PRICING.get(model)
    if pricing is None:
        # Try prefix match (e.g. "claude-sonnet-4" matches "claude-sonnet-4-6")
        for key, val in CLAUDE_PRICING.items():
            if model.startswith(key) or key.startswith(model):
                pricing = val
                break
    if pricing is None:
        return {"input_usd": None, "output_usd": None, "total_usd": None, "note": "unknown model"}

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

    for idx, token in enumerate(command):
        if token == "--model" and idx + 1 < len(command):
            candidate = command[idx + 1]
            if isinstance(candidate, str) and candidate.strip():
                return candidate.strip()
    return fallback_model


def parse_codex_events(events_file: Path) -> dict[str, Any]:
    """Extract summary metrics from the Codex events.jsonl file in a single pass."""
    if not events_file.exists():
        return {}

    usage: dict = {}
    thread_id: str | None = None
    command_count = 0
    reasoning_count = 0
    agent_message_count = 0
    event_count = 0

    # Single pass: parse events and count types simultaneously
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


def run_codex_plan(plan_file: Path, thinking_budget: str, extra_args: list[str]) -> tuple[int, str | None]:
    """
    Invoke run_codex_plan.py and return (returncode, run_dir_path).
    run_dir is parsed from the stdout line 'Run directory: <path>'.
    """
    cmd = [
        sys.executable,
        str(PROJECT_ROOT / "scripts" / "agent_runners" / "run_codex_plan.py"),
        "--plan-file", str(plan_file),
    ]

    # Pass thinking budget if not 'none'
    if thinking_budget and thinking_budget != "none":
        cmd.extend(["--thinking-budget", thinking_budget])

    cmd.extend(extra_args)
    print(f"[claude_run_plan] Launching: {' '.join(cmd)}", flush=True)

    proc = subprocess.run(cmd, capture_output=False, text=True,
                          stdout=subprocess.PIPE, stderr=None)
    stdout = proc.stdout or ""

    # Print so the caller can see progress
    print(stdout, end="", flush=True)

    run_dir: str | None = None
    for line in stdout.splitlines():
        if line.startswith("Run directory:") or line.startswith("Dry run created:"):
            run_dir = line.split(":", 1)[1].strip()
            break

    return proc.returncode, run_dir


def build_report(
    *,
    run_dir: Path,
    claude_model: str,
    claude_input_tokens: int,
    claude_output_tokens: int,
    thinking_budget: str,
    codex_model_hint: str,
    codex_input_rate: float | None,
    codex_cached_input_rate: float | None,
    codex_output_rate: float | None,
    task_summary: str,
    codex_returncode: int,
    generated_at: str,
) -> dict[str, Any]:
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

    # Read cost estimate from status.json if available (run_codex_plan.py calculates this)
    # Only recalculate if rate overrides are provided or if status doesn't have the estimate
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
    claude_cost = estimate_claude_cost(claude_model, claude_input_tokens, claude_output_tokens)
    total_estimated_cost: float | None = None
    if claude_cost.get("total_usd") is not None and codex_cost.get("total_usd") is not None:
        total_estimated_cost = round(
            float(claude_cost["total_usd"]) + float(codex_cost["total_usd"]), 6
        )

    return {
        "generated_at": generated_at,
        "run_id": run_dir.name,
        "task_summary": task_summary,

        "claude_planning": {
            "model": claude_model,
            "thinking_budget": thinking_budget,
            "input_tokens":  claude_input_tokens,
            "output_tokens": claude_output_tokens,
            "cost": claude_cost,
        },

        "codex_execution": {
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
            "claude_total_tokens": claude_input_tokens + claude_output_tokens,
            "codex_total_tokens":  (total_input + (codex_usage.get("output_tokens") or 0)),
            "claude_cost_usd": claude_cost.get("total_usd"),
            "codex_cost_usd": codex_cost.get("total_usd"),
            "total_estimated_cost_usd": total_estimated_cost,
            "note": "Codex cost is an estimate from token usage and configured rate table/overrides.",
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
    codex_exec = report.get("codex_execution", {})
    codex_tokens = codex_exec.get("token_usage", {})
    codex_cost = codex_exec.get("cost_estimate", {})
    combined = report.get("combined", {})
    final_message = codex_exec.get("final_message") or "(No final message captured.)"
    events = codex_exec.get("events", {})

    lines = [
        "# Codex Results",
        "",
        f"- Run ID: `{report.get('run_id', 'n/a')}`",
        f"- Task: {report.get('task_summary') or 'n/a'}",
        f"- State: `{codex_exec.get('state', 'n/a')}` (return code `{codex_exec.get('return_code', 'n/a')}`)",
        f"- Duration: {_fmt_duration_seconds(codex_exec.get('duration_seconds'))}",
        "",
        "## Execution",
        "",
        f"- Model: `{codex_exec.get('model', 'n/a')}`",
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
        f"- Input: {_fmt_int(codex_tokens.get('input_tokens'))}",
        f"- Cached Input: {_fmt_int(codex_tokens.get('cached_input_tokens'))}",
        f"- Output: {_fmt_int(codex_tokens.get('output_tokens'))}",
        f"- Cache Hit: {_fmt_pct(codex_tokens.get('cache_hit_pct'))}",
        f"- Total (input + output): {_fmt_int(combined.get('codex_total_tokens'))}",
        "",
        "## Cost Estimate",
        "",
        f"- Codex Input: {_fmt_money(codex_cost.get('input_usd'))}",
        f"- Codex Cached Input: {_fmt_money(codex_cost.get('cached_input_usd'))}",
        f"- Codex Output: {_fmt_money(codex_cost.get('output_usd'))}",
        f"- Codex Total: {_fmt_money(codex_cost.get('total_usd'))}",
        f"- Claude Planning Total: {_fmt_money(combined.get('claude_cost_usd'))}",
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


def main() -> int:
    args, extra_args = parse_args()
    generated_at = utc_now()

    returncode, run_dir_str = run_codex_plan(args.plan_file, args.thinking_budget, extra_args)

    if run_dir_str is None:
        print(
            "[claude_run_plan] ERROR: Could not parse run directory from run_codex_plan.py output.",
            file=sys.stderr,
        )
        return returncode or 1

    run_dir = Path(run_dir_str)
    if not run_dir.exists():
        print(f"[claude_run_plan] ERROR: Run directory not found: {run_dir}", file=sys.stderr)
        return returncode or 1

    report = build_report(
        run_dir=run_dir,
        claude_model=args.claude_model,
        claude_input_tokens=args.claude_input_tokens,
        claude_output_tokens=args.claude_output_tokens,
        thinking_budget=args.thinking_budget,
        codex_model_hint=args.codex_model,
        codex_input_rate=args.codex_input_rate,
        codex_cached_input_rate=args.codex_cached_input_rate,
        codex_output_rate=args.codex_output_rate,
        task_summary=args.task_summary,
        codex_returncode=returncode,
        generated_at=generated_at,
    )

    report_file = run_dir / "claude_report.json"
    report_file.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    formatted_results_file = run_dir / "codex_results.md"
    formatted_results_file.write_text(build_formatted_results(report), encoding="utf-8")
    print(f"[claude_run_plan] Report written: {report_file}", flush=True)
    print(f"[claude_run_plan] Formatted results written: {formatted_results_file}", flush=True)
    return returncode


if __name__ == "__main__":
    raise SystemExit(main())
