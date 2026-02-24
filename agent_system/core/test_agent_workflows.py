"""
test_agent_workflows.py - Workflow branch tests for the Agent System.
"""
import pytest
import sys
import json
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add core to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

def test_full_delegation_flow(tmp_path):
    """Verify the orchestration logic for a successful delegation."""
    plan_file = tmp_path / "test_plan.md"
    plan_file.write_text("# Test Plan Content", encoding="utf-8")
    
    # Mock subprocess.run to simulate a successful runner execution
    with patch("subprocess.run") as mock_run:
        # Mocking the output of the runner script
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "Run directory: /mock/run/path\n"
        mock_run.return_value = mock_proc
        
        # We'll use the orchestrator's run_executor directly for this test
        from agent_system.core.run_agent_plan import run_executor
        
        # Patch the internal config for executors
        with patch("agent_system.core.run_agent_plan._executors_config", {
            "codex": {"enabled": True, "runner": "runners/run_codex_plan.py", "bin": "codex"}
        }):
            # Mock PROJECT_ROOT inside the module
            with patch("agent_system.core.run_agent_plan.PROJECT_ROOT", tmp_path):
                rc, run_dir = run_executor("codex", plan_file, "low", "Summary", [])
                
                assert rc == 0
                assert run_dir == "/mock/run/path"
                
                # Verify runner was called with correct relative paths
                args = mock_run.call_args[0][0]
                # Normalize path for comparison
                normalized_script_path = str(Path(args[1])).replace("\\", "/")
                assert "runners/run_codex_plan.py" in normalized_script_path
                assert "--plan-file" in args
                assert str(plan_file) in args

def test_report_generation(tmp_path):
    """Verify the report generation logic in agent_runner_utils."""
    from agent_system.core.agent_runner_utils import build_report, utc_now
    
    run_dir = tmp_path / "TEST_RUN_001"
    run_dir.mkdir()
    
    report = build_report(
        run_dir=run_dir,
        planner_model="gemini-test",
        planner_input_tokens=100,
        planner_output_tokens=50,
        thinking_budget="low",
        codex_model_hint="gpt-5-test",
        task_summary="Test Task",
        codex_returncode=0,
        generated_at=utc_now()
    )
    
    assert report["run_id"] == "TEST_RUN_001"
    assert report["planner"]["model"] == "gemini-test"
    assert report["executor"]["state"] == "succeeded"
    assert report["task_summary"] == "Test Task"
