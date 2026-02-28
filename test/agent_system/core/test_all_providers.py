"""
test_all_providers.py - Dynamic workflow tests for all test-enabled providers.
"""
import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add core to path
PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

from agent_system.core.agent_runner_utils import get_test_enabled_executors
from agent_system.core.run_agent_plan import run_executor
from agent_system.core.provider_registry import get_provider_config

@pytest.mark.parametrize("executor", get_test_enabled_executors())
def test_provider_workflow_dry_run(executor, tmp_path):
    """
    Dynamically test every executor that has 'test_enabled': true in delegation-config.json.
    This performs a simulated dry-run to verify the runner scripts are integrated correctly.
    """
    plan_file = tmp_path / "test_plan.md"
    plan_file.write_text("# Test Plan\nVerify sync logic.", encoding="utf-8")
    
    # Mock subprocess.run to avoid actual LLM calls but verify the command construction
    with patch("subprocess.run") as mock_run:
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "Run directory: /mock/path\n"
        mock_proc.stderr = ""
        mock_run.return_value = mock_proc
        
        rc, run_dir, err = run_executor(executor, plan_file, "low", "Test Summary", ["--dry-run"], workspace=tmp_path)
        
        assert rc == 0
        assert run_dir == "/mock/path"
        assert err == ""
        
        # Verify the command contained the binary defined in config
        args = mock_run.call_args[0][0]
        expected_bin = get_provider_config(executor, role="executors").get("bin", executor)
        
        assert any(expected_bin in str(arg) for arg in args)
