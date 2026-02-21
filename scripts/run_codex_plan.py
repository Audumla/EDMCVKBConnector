"""
Run a Codex non-interactive session from a plan file and write progress artifacts.

This script is intended to be called by another automation agent/process.
All run outputs are written under:
    agent_artifacts/codex/reports/plan_runs/<run_id>/

By default, each non-dry run executes in an isolated Git worktree on a new branch
so file edits do not affect the caller's currently checked-out branch.
"""

from __future__ import annotations

import argparse
import json
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_ROOT = PROJECT_ROOT / "agent_artifacts" / "codex" / "reports" / "plan_runs"
DEFAULT_WORKTREE_ROOT = PROJECT_ROOT / "agent_artifacts" / "codex" / "temp" / "worktrees"
DEFAULT_CODEX_MODEL = "gpt-5.3-codex"
EFFORT_LEVEL_MAP: dict[int, str] = {
    1: "minimal",
    2: "low",
    3: "medium",
    4: "high",
}

# OpenAI API pricing used for best-effort run cost estimates
# (kept here, not imported; claude_run_plan.py reads cost_estimate from status.json instead of recalculating)
CODEX_PRICING: dict[str, dict[str, float]] = {
    "gpt-5": {"input": 1.25, "cached_input": 0.125, "output": 10.00},
    "gpt-5-codex": {"input": 1.25, "cached_input": 0.125, "output": 10.00},
    "gpt-5-mini": {"input": 0.25, "cached_input": 0.025, "output": 2.00},
    "gpt-5-nano": {"input": 0.05, "cached_input": 0.005, "output": 0.40},
    "codex": {"input": 1.25, "cached_input": 0.125, "output": 10.00},
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def slugify(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "-" for ch in value.strip())
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    return cleaned.strip("-") or "run"


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    temp_path.replace(path)


def normalize_windowsish_path(path_value: str) -> str:
    # Convert MSYS/Cygwin style paths like /c/Users/name/file.exe to C:\Users\name\file.exe.
    match = re.match(r"^/([a-zA-Z])/(.*)$", path_value)
    if not match:
        return path_value
    drive = match.group(1).upper()
    rest = match.group(2).replace("/", "\\")
    return f"{drive}:\\{rest}"


def discover_vscode_codex() -> Path | None:
    candidates: list[Path] = []
    roots = []
    userprofile = os.environ.get("USERPROFILE")
    home = os.environ.get("HOME")
    if userprofile:
        roots.append(Path(userprofile))
    if home:
        roots.append(Path(normalize_windowsish_path(home)))

    for root in roots:
        for vscode_dir in (".vscode", ".vscode-insiders"):
            ext_dir = root / vscode_dir / "extensions"
            if not ext_dir.exists():
                continue
            candidates.extend(
                ext_dir.glob("openai.chatgpt-*/bin/windows-x86_64/codex.exe")
            )

    if not candidates:
        return None
    # Prefer the most recently updated extension bundle.
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0]


def resolve_codex_bin(codex_bin: str) -> tuple[str, str | None]:
    codex_bin = normalize_windowsish_path(codex_bin)
    explicit_path = codex_bin not in {"codex", "codex.exe"}
    if explicit_path:
        return codex_bin, None

    resolved = shutil.which(codex_bin)
    if resolved:
        return resolved, None

    discovered = discover_vscode_codex()
    if discovered is not None:
        return str(discovered), "vscode_extension_fallback"

    return codex_bin, None


def resolve_cost_rates(model: str) -> dict[str, float] | None:
    rates = CODEX_PRICING.get(model)
    if rates is not None:
        return rates
    for key, value in CODEX_PRICING.items():
        if model.startswith(key) or key.startswith(model):
            return value
    return None


def estimate_cost_from_usage(model: str, usage: dict[str, Any]) -> dict[str, Any]:
    rates = resolve_cost_rates(model)
    if rates is None:
        return {
            "estimated": False,
            "model": model,
            "total_usd": None,
            "rates_per_million": None,
            "note": "No cost estimate: unknown model pricing.",
        }

    input_tokens = int(usage.get("input_tokens") or 0)
    cached_input_tokens = int(usage.get("cached_input_tokens") or 0)
    output_tokens = int(usage.get("output_tokens") or 0)
    billable_input_tokens = max(input_tokens - cached_input_tokens, 0)

    input_usd = (billable_input_tokens / 1_000_000) * rates["input"]
    cached_input_usd = (cached_input_tokens / 1_000_000) * rates["cached_input"]
    output_usd = (output_tokens / 1_000_000) * rates["output"]

    return {
        "estimated": True,
        "model": model,
        "input_usd": round(input_usd, 6),
        "cached_input_usd": round(cached_input_usd, 6),
        "output_usd": round(output_usd, 6),
        "total_usd": round(input_usd + cached_input_usd + output_usd, 6),
        "billable_input_tokens": billable_input_tokens,
        "rates_per_million": rates,
    }


@dataclass
class StreamLine:
    stream_name: str
    text: str


def _stream_reader(stream, stream_name: str, out_queue: queue.Queue[StreamLine]) -> None:
    try:
        for line in iter(stream.readline, ""):
            out_queue.put(StreamLine(stream_name=stream_name, text=line))
    finally:
        stream.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run codex exec from a plan file and persist progress/status artifacts."
    )
    parser.add_argument(
        "--plan-file",
        required=True,
        type=Path,
        help="Path to a text/markdown file containing the plan/prompt for Codex.",
    )
    parser.add_argument(
        "--run-name",
        default=None,
        help="Optional short label used in the run folder name.",
    )
    parser.add_argument(
        "--workspace",
        type=Path,
        default=PROJECT_ROOT,
        help=f"Workspace root for Codex (default: {PROJECT_ROOT}).",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=DEFAULT_OUTPUT_ROOT,
        help=f"Root folder for run artifacts (default: {DEFAULT_OUTPUT_ROOT}).",
    )
    parser.add_argument(
        "--no-isolated-branch",
        action="store_true",
        help="Run directly in --workspace instead of creating a per-run worktree branch.",
    )
    parser.add_argument(
        "--branch-prefix",
        default="codex/plan-runs",
        help="Git branch prefix for isolated runs (default: codex/plan-runs).",
    )
    parser.add_argument(
        "--worktree-root",
        type=Path,
        default=DEFAULT_WORKTREE_ROOT,
        help=f"Root folder for isolated run worktrees (default: {DEFAULT_WORKTREE_ROOT}).",
    )
    parser.add_argument(
        "--codex-bin",
        default="codex",
        help="Codex CLI executable name/path (default: codex).",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_CODEX_MODEL,
        help=f"Model value passed to Codex (default: {DEFAULT_CODEX_MODEL}).",
    )
    parser.add_argument(
        "--effort",
        type=int,
        choices=sorted(EFFORT_LEVEL_MAP.keys()),
        default=None,
        help="Reasoning effort level shorthand: 1=minimal, 2=low, 3=medium, 4=high.",
    )
    parser.add_argument(
        "--thinking-budget",
        choices=["none", "low", "medium", "high"],
        default=None,
        help="Extended thinking budget level (maps to effort: low→2, medium→3, high→4). Overrides --effort if provided.",
    )
    parser.add_argument(
        "--cost-model",
        default=DEFAULT_CODEX_MODEL,
        help="Model profile used for best-effort token cost estimate in status.json.",
    )
    parser.add_argument(
        "--profile",
        default=None,
        help="Optional Codex config profile.",
    )
    parser.add_argument(
        "--sandbox",
        default="workspace-write",
        choices=["read-only", "workspace-write", "danger-full-access"],
        help="Codex sandbox mode.",
    )
    parser.add_argument(
        "--approval",
        default="never",
        choices=["untrusted", "on-failure", "on-request", "never"],
        help="Codex approval policy (default: never for unattended runs).",
    )
    parser.add_argument(
        "--add-dir",
        action="append",
        default=[],
        help="Additional writable directory (repeatable).",
    )
    parser.add_argument(
        "--config",
        action="append",
        default=[],
        help="Codex config override key=value (repeatable).",
    )
    parser.add_argument(
        "--codex-arg",
        action="append",
        default=[],
        help="Extra argument forwarded to codex exec (repeatable, one token each).",
    )
    parser.add_argument(
        "--no-json",
        action="store_true",
        help="Disable --json mode on codex exec.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Create metadata files but do not launch codex.",
    )
    return parser.parse_args()


def unique_run_dir(output_root: Path, run_label: str) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    base = output_root / f"{timestamp}_{slugify(run_label)}"
    if not base.exists():
        return base
    idx = 1
    while True:
        candidate = output_root / f"{timestamp}_{slugify(run_label)}_{idx:02d}"
        if not candidate.exists():
            return candidate
        idx += 1


def git_run(repo: Path, git_args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *git_args],
        capture_output=True,
        text=True,
    )


def resolve_git_root(workspace: Path) -> Path:
    result = git_run(workspace, ["rev-parse", "--show-toplevel"])
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(f"Workspace is not a Git repository: {detail or workspace}")
    return Path(result.stdout.strip())


def sanitize_branch_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._/\-]+", "-", value)
    cleaned = cleaned.strip("/.-")
    while "//" in cleaned:
        cleaned = cleaned.replace("//", "/")
    while ".." in cleaned:
        cleaned = cleaned.replace("..", ".")
    cleaned = cleaned.replace("@{", "-")
    return cleaned or "codex/plan-run"


def branch_exists(repo: Path, branch_name: str) -> bool:
    result = git_run(repo, ["show-ref", "--verify", "--quiet", f"refs/heads/{branch_name}"])
    return result.returncode == 0


def unique_branch_name(repo: Path, base_name: str) -> str:
    base = sanitize_branch_name(base_name)
    if not branch_exists(repo, base):
        return base
    suffix = 1
    while True:
        candidate = f"{base}-{suffix:02d}"
        if not branch_exists(repo, candidate):
            return candidate
        suffix += 1


def unique_worktree_dir(worktree_root: Path, branch_name: str) -> Path:
    safe_name = re.sub(r"[^A-Za-z0-9._-]+", "-", branch_name.replace("/", "__")).strip("-") or "run"
    candidate = worktree_root / safe_name
    if not candidate.exists():
        return candidate
    suffix = 1
    while True:
        next_candidate = worktree_root / f"{safe_name}-{suffix:02d}"
        if not next_candidate.exists():
            return next_candidate
        suffix += 1


def create_isolated_worktree(
    *,
    workspace: Path,
    run_id: str,
    branch_prefix: str,
    worktree_root: Path,
) -> tuple[str, Path, Path]:
    repo_root = resolve_git_root(workspace)
    branch_name = unique_branch_name(repo_root, f"{branch_prefix}/{run_id}")
    worktree_root.mkdir(parents=True, exist_ok=True)
    worktree_dir = unique_worktree_dir(worktree_root, branch_name)
    result = git_run(
        repo_root,
        ["worktree", "add", "-b", branch_name, str(worktree_dir), "HEAD"],
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(f"Failed to create isolated worktree branch: {detail or branch_name}")
    return branch_name, worktree_dir, repo_root


def build_command(
    args: argparse.Namespace,
    final_message_file: Path,
    execution_workspace: Path,
) -> list[str]:
    cmd = [
        args.codex_bin,
        "--sandbox",
        args.sandbox,
        "--ask-for-approval",
        args.approval,
        "exec",
        "--cd",
        str(execution_workspace.resolve()),
        "--output-last-message",
        str(final_message_file),
    ]
    if not args.no_json:
        cmd.append("--json")
    if args.model:
        cmd.extend(["--model", args.model])
    if args.profile:
        cmd.extend(["--profile", args.profile])
    for add_dir in args.add_dir:
        cmd.extend(["--add-dir", add_dir])
    config_overrides = list(args.config)
    has_explicit_effort = any(
        re.match(r"^\s*model_reasoning_effort\s*=", item or "") for item in config_overrides
    )

    # If thinking-budget is provided, map it to effort level (overrides --effort if both given)
    effort_to_use = args.effort
    if args.thinking_budget and args.thinking_budget != "none":
        thinking_budget_map = {"low": 2, "medium": 3, "high": 4, "none": 1}
        effort_to_use = thinking_budget_map.get(args.thinking_budget, args.effort)

    if effort_to_use is not None and not has_explicit_effort:
        effort_name = EFFORT_LEVEL_MAP[effort_to_use]
        config_overrides.append(f'model_reasoning_effort="{effort_name}"')
    for config_override in config_overrides:
        cmd.extend(["--config", config_override])
    if args.codex_arg:
        cmd.extend(args.codex_arg)
    # Read prompt from stdin so plan files of any size/format are supported.
    cmd.append("-")
    return cmd


def main() -> int:
    args = parse_args()
    plan_file = args.plan_file.resolve()
    workspace = args.workspace.resolve()
    output_root = args.output_root.resolve()
    worktree_root = args.worktree_root.resolve()
    isolation_requested = not args.no_isolated_branch

    if not plan_file.exists():
        print(f"ERROR: Plan file not found: {plan_file}", file=sys.stderr)
        return 1
    if not workspace.exists():
        print(f"ERROR: Workspace not found: {workspace}", file=sys.stderr)
        return 1

    resolved_codex_bin, resolve_method = resolve_codex_bin(args.codex_bin)
    if shutil.which(resolved_codex_bin) is None and not Path(resolved_codex_bin).exists():
        print(
            "ERROR: Could not locate Codex CLI. "
            "Install it or pass --codex-bin with an absolute path.",
            file=sys.stderr,
        )
        return 1
    args.codex_bin = resolved_codex_bin

    run_label = args.run_name or plan_file.stem
    run_dir = unique_run_dir(output_root, run_label)
    run_dir.mkdir(parents=True, exist_ok=False)

    execution_workspace = workspace
    isolated_branch_name: str | None = None
    isolated_worktree_path: Path | None = None
    git_repo_root: Path | None = None
    if isolation_requested and not args.dry_run:
        try:
            (
                isolated_branch_name,
                isolated_worktree_path,
                git_repo_root,
            ) = create_isolated_worktree(
                workspace=workspace,
                run_id=run_dir.name,
                branch_prefix=args.branch_prefix,
                worktree_root=worktree_root,
            )
            execution_workspace = isolated_worktree_path
        except RuntimeError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1

    plan_copy = run_dir / "plan_input.txt"
    metadata_file = run_dir / "metadata.json"
    status_file = run_dir / "status.json"
    stdout_file = run_dir / "stdout.log"
    stderr_file = run_dir / "stderr.log"
    events_file = run_dir / "events.jsonl"
    final_message_file = run_dir / "final_message.txt"
    command_file = run_dir / "command.txt"

    shutil.copy2(plan_file, plan_copy)
    command = build_command(args, final_message_file, execution_workspace)
    command_file.write_text(" ".join(command) + "\n", encoding="utf-8")

    metadata: dict[str, Any] = {
        "run_id": run_dir.name,
        "created_at": utc_now(),
        "plan_file": str(plan_file),
        "plan_copy": str(plan_copy),
        "workspace": str(execution_workspace),
        "workspace_requested": str(workspace),
        "workspace_execution": str(execution_workspace),
        "isolation": {
            "requested": isolation_requested,
            "active": isolated_branch_name is not None,
            "branch_prefix": args.branch_prefix,
            "branch_name": isolated_branch_name,
            "worktree_root": str(worktree_root),
            "worktree_path": str(isolated_worktree_path) if isolated_worktree_path else None,
            "git_repo_root": str(git_repo_root) if git_repo_root else None,
        },
        "resolved_codex_bin": resolved_codex_bin,
        "codex_bin_resolution": resolve_method or "as_provided_or_path",
        "command": command,
        "files": {
            "status": str(status_file),
            "stdout": str(stdout_file),
            "stderr": str(stderr_file),
            "events": str(events_file),
            "final_message": str(final_message_file),
            "command": str(command_file),
        },
    }
    write_json(metadata_file, metadata)

    status: dict[str, Any] = {
        "run_id": run_dir.name,
        "state": "created",
        "created_at": utc_now(),
        "started_at": None,
        "ended_at": None,
        "heartbeat_at": utc_now(),
        "return_code": None,
        "pid": None,
        "event_count": 0,
        "last_event_type": None,
        "last_event_at": None,
        "last_stdout_line": None,
        "last_stderr_line": None,
        "token_usage": {
            "input_tokens": None,
            "cached_input_tokens": None,
            "output_tokens": None,
        },
        "cost_estimate": {
            "estimated": False,
            "model": args.cost_model,
            "total_usd": None,
            "rates_per_million": None,
        },
        "error": None,
    }
    write_json(status_file, status)

    if args.dry_run:
        status["state"] = "dry_run"
        status["ended_at"] = utc_now()
        status["heartbeat_at"] = utc_now()
        write_json(status_file, status)
        print(f"Dry run created: {run_dir}")
        return 0

    plan_text = plan_file.read_text(encoding="utf-8")
    status["state"] = "running"
    status["started_at"] = utc_now()
    status["heartbeat_at"] = utc_now()
    write_json(status_file, status)

    out_queue: queue.Queue[StreamLine] = queue.Queue()
    heartbeat_interval = 2.0
    last_heartbeat = time.time()

    proc: subprocess.Popen[str] | None = None
    stdout_thread: threading.Thread | None = None
    stderr_thread: threading.Thread | None = None

    try:
        proc = subprocess.Popen(
            command,
            cwd=str(execution_workspace),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
        status["pid"] = proc.pid
        status["heartbeat_at"] = utc_now()
        write_json(status_file, status)

        assert proc.stdout is not None
        assert proc.stderr is not None
        stdout_thread = threading.Thread(
            target=_stream_reader,
            args=(proc.stdout, "stdout", out_queue),
            daemon=True,
        )
        stderr_thread = threading.Thread(
            target=_stream_reader,
            args=(proc.stderr, "stderr", out_queue),
            daemon=True,
        )
        stdout_thread.start()
        stderr_thread.start()

        assert proc.stdin is not None
        proc.stdin.write(plan_text)
        proc.stdin.close()

        with (
            stdout_file.open("a", encoding="utf-8") as stdout_handle,
            stderr_file.open("a", encoding="utf-8") as stderr_handle,
            events_file.open("a", encoding="utf-8") as events_handle,
        ):
            while True:
                drained = False
                try:
                    line = out_queue.get(timeout=0.5)
                    drained = True
                    target = stdout_handle if line.stream_name == "stdout" else stderr_handle
                    target.write(line.text)
                    target.flush()

                    text = line.text.rstrip("\n")
                    if line.stream_name == "stdout":
                        status["last_stdout_line"] = text
                    else:
                        status["last_stderr_line"] = text

                    if line.stream_name == "stdout" and not args.no_json:
                        try:
                            event_obj = json.loads(text)
                        except json.JSONDecodeError:
                            event_obj = None
                        if isinstance(event_obj, dict):
                            events_handle.write(json.dumps(event_obj, ensure_ascii=False) + "\n")
                            events_handle.flush()
                            status["event_count"] = int(status["event_count"]) + 1
                            event_type = event_obj.get("type") or event_obj.get("event") or "unknown"
                            status["last_event_type"] = event_type
                            status["last_event_at"] = utc_now()
                            if event_type == "turn.completed":
                                usage = event_obj.get("usage", {})
                                if isinstance(usage, dict):
                                    status["token_usage"] = {
                                        "input_tokens": usage.get("input_tokens"),
                                        "cached_input_tokens": usage.get("cached_input_tokens"),
                                        "output_tokens": usage.get("output_tokens"),
                                    }
                                    status["cost_estimate"] = estimate_cost_from_usage(
                                        args.cost_model,
                                        usage,
                                    )
                except queue.Empty:
                    pass

                now = time.time()
                if drained or (now - last_heartbeat >= heartbeat_interval):
                    status["heartbeat_at"] = utc_now()
                    write_json(status_file, status)
                    last_heartbeat = now

                stdout_alive = stdout_thread.is_alive() if stdout_thread is not None else False
                stderr_alive = stderr_thread.is_alive() if stderr_thread is not None else False
                if proc.poll() is not None and out_queue.empty() and not stdout_alive and not stderr_alive:
                    break

        if stdout_thread:
            stdout_thread.join(timeout=2.0)
        if stderr_thread:
            stderr_thread.join(timeout=2.0)

        status["return_code"] = proc.returncode
        status["state"] = "succeeded" if proc.returncode == 0 else "failed"
        status["ended_at"] = utc_now()
        status["heartbeat_at"] = utc_now()
        write_json(status_file, status)
    except KeyboardInterrupt:
        if proc is not None and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5)
        status["return_code"] = proc.returncode if proc is not None else -1
        status["state"] = "cancelled"
        status["ended_at"] = utc_now()
        status["heartbeat_at"] = utc_now()
        status["error"] = "Interrupted by user."
        write_json(status_file, status)
        return 130
    except Exception as exc:  # pragma: no cover - defensive runtime path
        status["return_code"] = proc.returncode if proc is not None else -1
        status["state"] = "failed"
        status["ended_at"] = utc_now()
        status["heartbeat_at"] = utc_now()
        status["error"] = str(exc)
        write_json(status_file, status)
        raise

    print(f"Run directory: {run_dir}")
    if isolated_branch_name:
        print(f"Execution branch: {isolated_branch_name}")
        print(f"Execution workspace: {execution_workspace}")
    print(f"Status file: {status_file}")
    return int(status["return_code"] or 0)


if __name__ == "__main__":
    raise SystemExit(main())
