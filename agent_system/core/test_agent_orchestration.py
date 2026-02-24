"""
test_agent_orchestration.py - Integration tests for agent orchestration and provider control.
"""
import pytest
import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from agent_system.core.run_agent_plan import main

@pytest.fixture
def mock_config(tmp_path):
    config = {
        "system_settings": {"test_mode": True},
        "planners": {
            "gemini": {"enabled": True, "model": "gemini-test"},
            "claude": {"enabled": False, "model": "claude-test"}
        },
        "executors": {
            "codex": {"enabled": True, "runner": "runners/run_codex_plan.py"},
            "opencode": {"enabled": False, "runner": "runners/run_opencode_plan.py"}
        }
    }
    config_file = tmp_path / "delegation-config.json"
    config_file.write_text(json.dumps(config))
    return config_file

def test_disabled_planner(mock_config, capsys):
    """Verify that using a disabled planner results in an error exit."""
    with patch("agent_system.core.run_agent_plan._planners_config", {
        "claude": {"enabled": False}
    }):
        test_args = [
            "run_agent_plan.py",
            "--planner", "claude",
            "--executor", "codex",
            "--plan-file", "dummy.md"
        ]
        with patch.object(sys, 'argv', test_args):
            with pytest.raises(SystemExit) as excinfo:
                main()
            assert excinfo.value.code == 1
            captured = capsys.readouterr()
            assert "ERROR: Planner 'claude' is currently disabled" in captured.err

def test_disabled_executor(mock_config, capsys):
    """Verify that using a disabled executor results in an error."""
    with patch("agent_system.core.run_agent_plan._planners_config", {"gemini": {"enabled": True}}), \
         patch("agent_system.core.run_agent_plan._executors_config", {"opencode": {"enabled": False}}):
        
        test_args = [
            "run_agent_plan.py",
            "--planner", "gemini",
            "--executor", "opencode",
            "--plan-file", "dummy.md"
        ]
        with patch.object(sys, 'argv', test_args):
            with pytest.raises(SystemExit) as excinfo:
                main()
            # If run_executor fails it should return rc 1
            captured = capsys.readouterr()
            assert "ERROR: Executor 'opencode' is currently disabled" in captured.err
