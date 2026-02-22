"""
codex_results.py - Print a formatted summary for a Codex plan run.

Usage:
    python scripts/agent_runners/codex_results.py
    python scripts/agent_runners/codex_results.py --run-id 20260219T111945Z_code-review
    python scripts/agent_runners/codex_results.py --run-dir agent_artifacts/codex/reports/plan_runs/<run_id>
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from claude_run_plan import build_formatted_results, build_report, utc_now


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_OUTPUT_ROOT = PROJECT_ROOT / "agent_artifacts" / "codex" / "reports" / "plan_runs"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Print a clean /codex-results style summary from Codex run artifacts."
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=DEFAULT_OUTPUT_ROOT,
        help=f"Root folder for plan runs (default: {DEFAULT_OUTPUT_ROOT}).",
    )
    parser.add_argument(
        "--run-id",
        default=None,
        help="Run directory name under output root (for example: 20260219T111945Z_code-review).",
    )
    parser.add_argument(
        "--run-dir",
        type=Path,
        default=None,
        help="Explicit path to a run directory.",
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Ignore existing codex_results.md and regenerate from JSON artifacts.",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Write regenerated output to codex_results.md in the run directory.",
    )
    return parser.parse_args()


def find_latest_run_dir(output_root: Path) -> Path | None:
    if not output_root.exists():
        return None
    candidates = [p for p in output_root.iterdir() if p.is_dir()]
    if not candidates:
        return None
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0]


def resolve_run_dir(args: argparse.Namespace) -> Path | None:
    if args.run_dir is not None:
        return args.run_dir.resolve()
    if args.run_id:
        return (args.output_root.resolve() / args.run_id).resolve()
    return find_latest_run_dir(args.output_root.resolve())


def load_or_build_report(run_dir: Path) -> dict:
    report_file = run_dir / "claude_report.json"
    task_summary = "Codex run summary"
    claude_model = "claude-sonnet-4-6"
    thinking_budget = "none"
    claude_input_tokens = 0
    claude_output_tokens = 0
    codex_model_hint = "gpt-5"
    if report_file.exists():
        try:
            previous = json.loads(report_file.read_text(encoding="utf-8"))
            task_summary = previous.get("task_summary") or task_summary
            claude_section = previous.get("claude_planning", {})
            if isinstance(claude_section, dict):
                claude_model = claude_section.get("model") or claude_model
                thinking_budget = claude_section.get("thinking_budget") or thinking_budget
                claude_input_tokens = int(claude_section.get("input_tokens") or 0)
                claude_output_tokens = int(claude_section.get("output_tokens") or 0)
            codex_section = previous.get("codex_execution", {})
            if isinstance(codex_section, dict):
                codex_model_hint = codex_section.get("model") or codex_model_hint
        except Exception:
            pass

    # Fallback for legacy runs that may not have claude_report.json.
    status_file = run_dir / "status.json"
    status_return_code = 0
    if status_file.exists():
        try:
            status_data = json.loads(status_file.read_text(encoding="utf-8"))
            status_return_code = int(status_data.get("return_code") or 0)
        except Exception:
            status_return_code = 0

    return build_report(
        run_dir=run_dir,
        claude_model=claude_model,
        claude_input_tokens=claude_input_tokens,
        claude_output_tokens=claude_output_tokens,
        thinking_budget=thinking_budget,
        codex_model_hint=codex_model_hint,
        codex_input_rate=None,
        codex_cached_input_rate=None,
        codex_output_rate=None,
        task_summary=task_summary,
        codex_returncode=status_return_code,
        generated_at=utc_now(),
    )


def main() -> int:
    args = parse_args()
    run_dir = resolve_run_dir(args)
    if run_dir is None:
        print("ERROR: No run directory found.", file=sys.stderr)
        return 1
    if not run_dir.exists():
        print(f"ERROR: Run directory not found: {run_dir}", file=sys.stderr)
        return 1

    formatted_file = run_dir / "codex_results.md"
    if formatted_file.exists() and not args.refresh:
        print(formatted_file.read_text(encoding="utf-8"), end="")
        return 0

    report = load_or_build_report(run_dir)
    rendered = build_formatted_results(report)

    if args.refresh or args.write or not formatted_file.exists():
        formatted_file.write_text(rendered, encoding="utf-8")

    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
