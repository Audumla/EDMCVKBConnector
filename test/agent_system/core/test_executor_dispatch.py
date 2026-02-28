"""
test_executor_dispatch.py - Unit tests for execution dispatch module.
"""
from pathlib import Path
import sys
from unittest.mock import patch, MagicMock

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

from agent_system.core.execution.executor_dispatch import (
    build_executor_command,
    extract_run_directory,
    run_executor_process,
)
from agent_system.core.runtime_paths import RUNTIME_ROOT


def test_build_executor_command_includes_core_args(tmp_path):
    cfg = {
        "runner": "runners/run_openai_api_plan.py",
        "model": "m-default",
        "bin": "mybin",
        "runner_args": ["--base-url", "https://example.invalid/v1"],
    }
    plan_file = tmp_path / "plan.md"
    plan_file.write_text("# Plan", encoding="utf-8")

    cmd, runner = build_executor_command(
        project_root=tmp_path,
        executor="gemini-api",
        executor_cfg=cfg,
        plan_file=plan_file,
        task_summary="summary",
        thinking_budget="low",
        extra_args=["--dry-run"],
        executor_model=None,
    )

    assert runner == "runners/run_openai_api_plan.py"
    assert str(RUNTIME_ROOT / "agent_system" / "runners" / "run_openai_api_plan.py") in cmd
    assert "--task-summary" in cmd
    assert "summary" in cmd
    assert "--thinking-budget" in cmd
    assert "low" in cmd
    assert "--bin" in cmd
    assert "mybin" in cmd
    assert "--base-url" in cmd
    assert "https://example.invalid/v1" in cmd
    assert "--dry-run" in cmd


def test_build_executor_command_uses_codex_bin_flag_for_codex_runner(tmp_path):
    cfg = {
        "runner": "runners/run_codex_plan.py",
        "model": "gpt-5.3-codex",
        "bin": "codex",
    }
    plan_file = tmp_path / "plan.md"
    plan_file.write_text("# Plan", encoding="utf-8")

    cmd, _ = build_executor_command(
        project_root=tmp_path,
        executor="codex",
        executor_cfg=cfg,
        plan_file=plan_file,
        task_summary="summary",
        thinking_budget="low",
        extra_args=["--dry-run"],
        executor_model=None,
    )

    assert "--codex-bin" in cmd
    assert "--bin" not in cmd


def test_extract_run_directory_handles_both_markers():
    assert extract_run_directory("Run directory: /a/b") == "/a/b"
    assert extract_run_directory("Dry run created: /x/y") == "/x/y"
    assert extract_run_directory("No marker") is None


@patch("agent_system.core.execution.executor_dispatch.subprocess.run")
def test_run_executor_process(mock_run):
    proc = MagicMock()
    proc.returncode = 3
    proc.stdout = "out"
    proc.stderr = "err"
    mock_run.return_value = proc

    rc, out, err = run_executor_process(["python", "runner.py"])
    assert rc == 3
    assert out == "out"
    assert err == "err"
