"""
test_runner_args_forwarding.py - Ensure executor runner_args config is forwarded.
"""
from pathlib import Path
import sys
from unittest.mock import patch, MagicMock

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

from agent_system.core.run_agent_plan import run_executor


def test_runner_args_are_forwarded(tmp_path):
    plan_file = tmp_path / "plan.md"
    plan_file.write_text("# Plan", encoding="utf-8")

    mock_cfg = {
        "gemini-api": {
            "enabled": True,
            "runner": "runners/run_openai_api_plan.py",
            "model": "gemini-2.5-flash",
            "runner_args": ["--base-url", "https://example.invalid/v1", "--api-key-env", "GEMINI_API_KEY"],
        }
    }

    with patch("agent_system.core.run_agent_plan._executors_config", mock_cfg):
        with patch("subprocess.run") as mock_run:
            proc = MagicMock()
            proc.returncode = 0
            proc.stdout = "Run directory: /mock/path\n"
            proc.stderr = ""
            mock_run.return_value = proc

            rc, run_dir, err = run_executor("gemini-api", plan_file, "low", "summary", ["--dry-run"], workspace=tmp_path)
            assert rc == 0
            assert run_dir == "/mock/path"
            assert err == ""

            cmd = mock_run.call_args[0][0]
            assert "--base-url" in cmd
            assert "https://example.invalid/v1" in cmd
            assert "--api-key-env" in cmd
            assert "GEMINI_API_KEY" in cmd
