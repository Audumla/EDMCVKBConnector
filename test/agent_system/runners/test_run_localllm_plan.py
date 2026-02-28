"""Regression tests for local LLM runner argument/runtime behavior."""

from __future__ import annotations

import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

from agent_system.runners import run_localllm_plan


def test_localllm_dry_run_accepts_workspace_and_skips_worktree(tmp_path, monkeypatch):
    plan_file = tmp_path / "plan.md"
    plan_file.write_text("# Test plan\n", encoding="utf-8")
    output_root = tmp_path / "out"
    worktree_root = tmp_path / "worktrees"
    workspace = tmp_path / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)

    calls = {"worktree": 0}

    def fail_if_called(*args, **kwargs):
        calls["worktree"] += 1
        raise AssertionError("create_isolated_worktree should not be called in --dry-run")

    monkeypatch.setattr(run_localllm_plan, "create_isolated_worktree", fail_if_called)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_localllm_plan.py",
            "--plan-file",
            str(plan_file),
            "--output-root",
            str(output_root),
            "--worktree-root",
            str(worktree_root),
            "--workspace",
            str(workspace),
            "--dry-run",
        ],
    )

    rc = run_localllm_plan.main()
    assert rc == 0
    assert calls["worktree"] == 0

    run_dirs = sorted(output_root.iterdir())
    assert len(run_dirs) == 1
    status = json.loads((run_dirs[0] / "status.json").read_text(encoding="utf-8"))
    assert status["state"] == "dry_run"
