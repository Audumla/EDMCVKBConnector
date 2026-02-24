"""
test_provider_control.py - Tests for enabling/disabling providers and workflow branches.
"""
import pytest
import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add core to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from agent_system.core.run_agent_plan import get_planner_defaults, run_executor

def test_planner_enabled_respects_config():
    """Verify that get_planner_defaults raises SystemExit if the planner is disabled."""
    mock_config = {
        "opencode": {"enabled": False, "model": "opencode-latest"},
        "gemini": {"enabled": True, "model": "gemini-2.0"}
    }
    
    with patch("agent_system.core.run_agent_plan._planners_config", mock_config):
        # Enabled planner should work
        defaults = get_planner_defaults("gemini")
        assert defaults["model"] == "gemini-2.0"
        
        # Disabled planner should exit
        with pytest.raises(SystemExit) as excinfo:
            get_planner_defaults("opencode")
        assert excinfo.value.code == 1

def test_executor_enabled_respects_config(tmp_path):
    """Verify that run_executor raises SystemExit if the executor is disabled."""
    mock_config = {
        "codex": {"enabled": False, "runner": "runners/run_codex_plan.py"},
        "opencode": {"enabled": True, "runner": "runners/run_opencode_plan.py"}
    }
    
    plan_file = tmp_path / "test.md"
    plan_file.write_text("test", encoding="utf-8")
    
    with patch("agent_system.core.run_agent_plan._executors_config", mock_config):
        # Disabled executor should exit
        with pytest.raises(SystemExit) as excinfo:
            run_executor("codex", plan_file, "low", [])
        assert excinfo.value.code == 1

def test_workflow_branch_thinking_budget(tmp_path):
    """Verify that thinking budget is passed correctly to the executor."""
    mock_config = {
        "gemini": {"enabled": True, "runner": "runners/run_gemini_plan.py", "model": "gemini-flash"}
    }
    
    plan_file = tmp_path / "test.md"
    plan_file.write_text("test", encoding="utf-8")
    
    with patch("agent_system.core.run_agent_plan._executors_config", mock_config):
        with patch("subprocess.run") as mock_run:
            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_proc.stdout = "Run directory: /mock/path\n"
            mock_run.return_value = mock_proc
            
            # Test with 'high' budget
            run_executor("gemini", plan_file, "high", [])
            
            # Check subprocess call
            args = mock_run.call_args[0][0]
            assert "--thinking-budget" in args
            idx = args.index("--thinking-budget")
            assert args[idx+1] == "high"
            
            # Test with 'none' budget (should NOT pass --thinking-budget)
            run_executor("gemini", plan_file, "none", [])
            args = mock_run.call_args[0][0]
            assert "--thinking-budget" not in args

def test_extra_args_forwarding(tmp_path):
    """Verify that extra args are forwarded to the executor."""
    mock_config = {
        "codex": {"enabled": True, "runner": "runners/run_codex_plan.py"}
    }
    
    plan_file = tmp_path / "test.md"
    plan_file.write_text("test", encoding="utf-8")
    
    with patch("agent_system.core.run_agent_plan._executors_config", mock_config):
        with patch("subprocess.run") as mock_run:
            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_proc.stdout = "Run directory: /mock/path\n"
            mock_run.return_value = mock_proc
            
            run_executor("codex", plan_file, "low", ["--dry-run", "--custom-flag", "value"])
            
            args = mock_run.call_args[0][0]
            assert "--dry-run" in args
            assert "--custom-flag" in args
            assert "value" in args

def test_executor_failure_handling(tmp_path):
    """Verify that run_executor handles failures correctly."""
    mock_config = {
        "opencode": {"enabled": True, "runner": "runners/run_opencode_plan.py"}
    }
    
    plan_file = tmp_path / "test.md"
    plan_file.write_text("test", encoding="utf-8")
    
    with patch("agent_system.core.run_agent_plan._executors_config", mock_config):
        with patch("subprocess.run") as mock_run:
            mock_proc = MagicMock()
            mock_proc.returncode = 1
            mock_proc.stdout = "ERROR: Failed to run\nRun directory: /mock/fail/path\n"
            mock_run.return_value = mock_proc
            
            rc, run_dir = run_executor("opencode", plan_file, "low", [])
            
            assert rc == 1
            assert run_dir == "/mock/fail/path"
