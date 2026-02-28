"""Tests for planner/executor thinking budget behavior in run_agent_plan."""

from __future__ import annotations

from argparse import Namespace
from pathlib import Path
import sys
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

from agent_system.core import run_agent_plan as rap


def test_main_uses_split_planner_and_executor_budgets(tmp_path):
    plan_file = tmp_path / "plan.md"
    plan_file.write_text("# Plan\n", encoding="utf-8")

    run_dir = tmp_path / "run"
    run_dir.mkdir(parents=True, exist_ok=True)

    args = Namespace(
        planner="codex",
        executor="codex",
        planner_model=None,
        executor_model=None,
        planner_input_tokens=None,
        planner_output_tokens=None,
        planner_thinking_budget="high",
        thinking_budget="low",
        task_summary="budget split",
        plan_file=plan_file,
        workspace=tmp_path,
    )

    captured: dict[str, str] = {}

    def fake_run_executor(executor, plan_file_arg, budget, task_summary, extra_args, executor_model, workspace):  # noqa: ANN001
        captured["executor_budget"] = budget
        captured["executor_model"] = executor_model
        return 0, str(run_dir), ""

    with patch("agent_system.core.run_agent_plan.parse_args", return_value=(args, [])):
        with patch("agent_system.core.run_agent_plan.run_executor", side_effect=fake_run_executor):
            with patch("agent_system.core.run_agent_plan._planners_config", {"codex": {"enabled": True, "model": "planner-m"}}):
                with patch("agent_system.core.run_agent_plan._executors_config", {"codex": {"enabled": True, "model": "exec-m"}}):
                    rc = rap.main()

    assert rc == 0
    assert captured["executor_budget"] == "low"
    assert captured["executor_model"] == "exec-m"
    report_path = run_dir / "agent_report.json"
    assert report_path.exists()
    report_text = report_path.read_text(encoding="utf-8")
    assert '"thinking_budget": "high"' in report_text


def test_main_uses_executor_stderr_in_failure_report(tmp_path):
    plan_file = tmp_path / "plan.md"
    plan_file.write_text("# Plan\n", encoding="utf-8")

    args = Namespace(
        planner="codex",
        executor="codex",
        planner_model=None,
        executor_model=None,
        planner_input_tokens=None,
        planner_output_tokens=None,
        planner_thinking_budget="medium",
        thinking_budget="medium",
        task_summary="budget split",
        plan_file=plan_file,
        workspace=tmp_path,
    )

    captured: dict[str, str] = {}

    with patch("agent_system.core.run_agent_plan.parse_args", return_value=(args, [])):
        with patch("agent_system.core.run_agent_plan.run_executor", return_value=(1, None, "model rejected")):
            with patch("agent_system.core.run_agent_plan.create_failure_report") as mock_failure:
                with patch("agent_system.core.run_agent_plan._planners_config", {"codex": {"enabled": True, "model": "planner-m"}}):
                    with patch("agent_system.core.run_agent_plan._executors_config", {"codex": {"enabled": True, "model": "exec-m"}}):
                        rc = rap.main()
                        captured["error_msg"] = mock_failure.call_args[0][2]

    assert rc == 1
    assert captured["error_msg"] == "model rejected"
