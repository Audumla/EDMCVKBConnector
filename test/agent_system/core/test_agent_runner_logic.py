"""
test_agent_runner_logic.py - Unit tests for dashboard data gathering and maintenance.
"""
import pytest
import json
import sys
from pathlib import Path

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

# Adjust sys.path for internal modular imports in dashboard
sys.path.insert(0, str(PROJECT_ROOT / "agent_system" / "core"))

from agent_system.dashboard.agent_dashboard import AgentDashboardApp
from agent_system.core.agent_maintenance import get_orphans

def test_dashboard_data_gathering(tmp_path, monkeypatch):
    # Ensure provider registry sees the test agent
    monkeypatch.setattr(
        "agent_system.core.provider_registry.load_delegation_config",
        lambda: {"executors": {"gemini": {"enabled": True}}},
    )
    # Mock artifact root where run data resolution actually happens
    artifacts_root = tmp_path / "agent_artifacts"
    monkeypatch.setattr("agent_system.core.agent_runner_utils.ARTIFACTS_ROOT", artifacts_root)
    monkeypatch.setattr("agent_system.core.agent_runner_utils.AGENT_TYPES", ["gemini"])
    try:
        import agent_runner_utils as aru  # type: ignore
        monkeypatch.setattr(aru, "ARTIFACTS_ROOT", artifacts_root)
        monkeypatch.setattr(aru, "AGENT_TYPES", ["gemini"])
    except Exception:
        pass
    monkeypatch.setattr("agent_system.dashboard.agent_dashboard.PROJECT_ROOT", tmp_path)
    
    # Create mock run data
    run_dir = artifacts_root / "gemini" / "reports" / "plan_runs" / "test_run_1"
    run_dir.mkdir(parents=True)
    status = {"state": "succeeded", "pid": 1234, "cost_estimate": {"model": "test", "total_usd": 0.05}}
    (run_dir / "status.json").write_text(json.dumps(status), encoding="utf-8-sig")
    meta = {"task_summary": "Test Summary", "isolation": {"branch_name": "test-branch"}}
    (run_dir / "metadata.json").write_text(json.dumps(meta), encoding="utf-8-sig")
    
    # We use the module-level data gathering function
    from agent_system.dashboard.agent_dashboard import get_all_runs
    runs = get_all_runs()
    
    assert len(runs) == 1
    assert runs[0]["id"] == "test_run_1"
    assert runs[0]["summary"] == "Test Summary"


def test_dashboard_error_falls_back_to_last_status_lines(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "agent_system.core.provider_registry.load_delegation_config",
        lambda: {"executors": {"gemini": {"enabled": True}}},
    )
    artifacts_root = tmp_path / "agent_artifacts"
    monkeypatch.setattr("agent_system.core.agent_runner_utils.ARTIFACTS_ROOT", artifacts_root)
    monkeypatch.setattr("agent_system.core.agent_runner_utils.AGENT_TYPES", ["gemini"])
    try:
        import agent_runner_utils as aru  # type: ignore
        monkeypatch.setattr(aru, "ARTIFACTS_ROOT", artifacts_root)
        monkeypatch.setattr(aru, "AGENT_TYPES", ["gemini"])
    except Exception:
        pass

    run_dir = artifacts_root / "gemini" / "reports" / "plan_runs" / "test_run_error"
    run_dir.mkdir(parents=True)
    status = {
        "state": "failed",
        "pid": 1234,
        "cost_estimate": {"model": "test", "total_usd": 0.0},
        "error": None,
        "last_stdout_line": "{\"type\":\"turn.failed\",\"error\":{\"message\":\"{\\\"detail\\\":\\\"quota exhausted\\\"}\"}}",
        "last_stderr_line": "",
    }
    (run_dir / "status.json").write_text(json.dumps(status), encoding="utf-8-sig")
    meta = {"task_summary": "Failing Summary", "isolation": {"branch_name": "test-branch"}}
    (run_dir / "metadata.json").write_text(json.dumps(meta), encoding="utf-8-sig")

    from agent_system.dashboard.agent_dashboard import get_all_runs

    runs = get_all_runs()
    assert len(runs) == 1
    assert runs[0]["state"] == "failed"
    assert "quota exhausted" in str(runs[0]["error"])

def test_maintenance_orphan_detection(tmp_path, monkeypatch):
    # Mock PROJECT_ROOT in the maintenance module
    monkeypatch.setattr("agent_system.core.agent_maintenance.PROJECT_ROOT", tmp_path)
    monkeypatch.setattr("agent_system.core.agent_maintenance.ARTIFACTS_ROOT", tmp_path / "agent_artifacts")
    
    # Mock git branch listing
    def mock_run_git(args):
        if "branch" in args:
            return ["  main", "  codex/plan-runs/dangling"]
        return []
    monkeypatch.setattr("agent_system.core.agent_maintenance.run_git", mock_run_git)
    
    # We should detect the "dangling" branch
    orphaned_branches, _ = get_orphans()
    assert "codex/plan-runs/dangling" in orphaned_branches
