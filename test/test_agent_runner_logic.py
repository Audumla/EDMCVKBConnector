
import pytest
import json
from pathlib import Path
from scripts.agent_runners.agent_dashboard import StableRichDashboard
from scripts.agent_runners.agent_maintenance import get_orphans

def test_dashboard_data_gathering(tmp_path, monkeypatch):
    monkeypatch.setattr("scripts.agent_runners.agent_dashboard.PROJECT_ROOT", tmp_path)
    run_dir = tmp_path / "agent_artifacts" / "gemini" / "reports" / "plan_runs" / "test_run_1"
    run_dir.mkdir(parents=True)
    status = {"state": "succeeded", "pid": 1234, "cost_estimate": {"model": "test", "total_usd": 0.05}}
    (run_dir / "status.json").write_text(json.dumps(status), encoding="utf-8-sig")
    meta = {"task_summary": "Test Summary", "isolation": {"branch_name": "test-branch"}}
    (run_dir / "metadata.json").write_text(json.dumps(meta), encoding="utf-8-sig")
    
    dash = StableRichDashboard()
    runs = dash.get_all_runs()
    assert len(runs) == 1
    assert runs[0]["id"] == "test_run_1"

def test_maintenance_orphan_detection(tmp_path, monkeypatch):
    monkeypatch.setattr("scripts.agent_runners.agent_maintenance.PROJECT_ROOT", tmp_path)
    def mock_run_git(args):
        if "branch" in args: return ["  main", "  codex/plan-runs/dangling"]
        return []
    monkeypatch.setattr("scripts.agent_runners.agent_maintenance.run_git", mock_run_git)
    orphaned_branches, _ = get_orphans()
    assert "codex/plan-runs/dangling" in orphaned_branches
