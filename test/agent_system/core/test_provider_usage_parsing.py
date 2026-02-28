"""
test_provider_usage_parsing.py - Validate concise provider-specific quota parsing.
"""
import os
from pathlib import Path
import sys
from unittest.mock import patch, MagicMock

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

from agent_system.core.providers.usage_service import get_provider_usage_summary, get_provider_detailed_usage


def _mock_proc(stdout: str, returncode: int = 0):
    proc = MagicMock()
    proc.returncode = returncode
    proc.stdout = stdout
    proc.stderr = ""
    return proc


def _mock_proc_with_stderr(stdout: str, stderr: str, returncode: int = 0):
    proc = MagicMock()
    proc.returncode = returncode
    proc.stdout = stdout
    proc.stderr = stderr
    return proc


@patch("agent_system.core.providers.usage_service.get_provider_config")
@patch("agent_system.core.providers.usage_service.run_command")
def test_opencode_usage_parsed(mock_run, mock_cfg):
    mock_cfg.return_value = {
        "bin": "opencode",
        "usage": {"quick_command": ["{bin}", "stats"], "quick_parser": "opencode_stats"},
    }
    mock_run.return_value = _mock_proc("Total Cost $1.23\nInput 10K\nOutput 5K\n")
    stats = get_provider_usage_summary("opencode")
    assert stats["status"] == "ACTIVE"
    assert "Cost: $1.23" in stats["display"]


@patch("agent_system.core.providers.usage_service.get_provider_config")
@patch("agent_system.core.providers.usage_service.run_command")
def test_gemini_usage_parsed(mock_run, mock_cfg):
    mock_cfg.return_value = {
        "bin": "gemini",
        "usage": {"quick_command": ["{bin}", "-p", "usage", "--output-format", "json"], "quick_parser": "gemini_usage_json"},
    }
    mock_run.return_value = _mock_proc('{"usage": {"input_tokens": 321, "output_tokens": 123}}')
    stats = get_provider_usage_summary("gemini")
    assert stats["status"] == "ACTIVE"
    assert stats["display"] == "In: 321 | Out: 123"


@patch("agent_system.core.providers.usage_service.get_provider_config")
@patch("agent_system.core.providers.usage_service.run_command")
def test_gemini_usage_with_model_selector(mock_run, mock_cfg):
    mock_cfg.return_value = {
        "bin": "gemini",
        "usage": {"quick_command": ["{bin}", "-p", "usage", "--output-format", "json"], "quick_parser": "gemini_usage_json"},
    }
    mock_run.return_value = _mock_proc(
        '{"usage":{"input_tokens":321,"output_tokens":123},"models":[{"model":"gemini-2.5-pro","input_tokens":100,"output_tokens":40},{"model":"gemini-2.5-flash","input_tokens":221,"output_tokens":83}]}'
    )
    stats = get_provider_usage_summary("gemini")
    assert stats["selector_key"] == "model"
    assert len(stats["selector_options"]) == 2
    assert stats["selector_options"][0]["key"] == "gemini-2.5-pro"


@patch("agent_system.core.providers.usage_service.get_provider_config")
@patch("agent_system.core.providers.usage_service.run_command")
def test_gemini_stats_text_table_builds_selector(mock_run, mock_cfg):
    mock_cfg.return_value = {
        "bin": "gemini",
        "usage": {"quick_command": ["{bin}", "/stats"], "quick_parser": "gemini_usage_json"},
    }
    mock_run.return_value = _mock_proc(
        """
│  Auto (Gemini 3) Usage                                                                                                                                           │
│  Model                       Reqs             Usage remaining                                                                                                     │
│  gemini-2.5-flash               -     40.7% resets in 10h 57m                                                                                                    │
│  gemini-2.5-pro                 -          0.0% resets in 57m                                                                                                    │
"""
    )
    stats = get_provider_usage_summary("gemini")
    assert stats["selector_key"] == "model"
    assert len(stats["selector_options"]) == 2
    assert stats["selector_options"][0]["key"] == "gemini-2.5-flash"
    assert "resets" in stats["selector_options"][0]["display"]


@patch("agent_system.core.providers.usage_service.get_provider_config")
@patch("agent_system.core.providers.usage_service.run_command")
def test_claude_usage_parsed(mock_run, mock_cfg):
    mock_cfg.return_value = {
        "bin": "claude",
        "usage": {"quick_command": ["{bin}", "-p", "usage"], "quick_parser": "claude_usage"},
    }
    mock_run.return_value = _mock_proc("Used 42% of plan. Resets in 3 hours.")
    stats = get_provider_usage_summary("claude")
    assert stats["status"] == "ACTIVE"
    assert "Used: 42%" in stats["display"]


@patch("agent_system.core.providers.usage_service.get_provider_config")
@patch("agent_system.core.providers.usage_service.run_command")
def test_codex_version_parsed(mock_run, mock_cfg):
    mock_cfg.return_value = {
        "bin": "codex",
        "usage": {"quick_command": ["{bin}", "login", "status"], "quick_parser": "codex_login_status"},
    }
    mock_run.return_value = _mock_proc_with_stderr("", "Logged in using ChatGPT", returncode=0)
    stats = get_provider_usage_summary("codex")
    assert stats["status"] == "ACTIVE"
    assert "Logged in" in stats["display"]


@patch("agent_system.core.providers.usage_service.get_provider_config")
@patch("agent_system.core.providers.usage_service.run_command")
def test_copilot_help_parsed(mock_run, mock_cfg):
    mock_cfg.return_value = {
        "bin": "gh copilot",
        "usage": {"quick_command": ["gh", "copilot", "--help"], "quick_parser": "copilot_help"},
    }
    mock_run.return_value = _mock_proc("GitHub Copilot CLI help")
    stats = get_provider_usage_summary("copilot")
    assert stats["status"] == "ACTIVE"
    assert "subscription" in stats["display"].lower()


@patch("agent_system.core.providers.usage_service.get_provider_config")
@patch("agent_system.core.providers.usage_service.run_command")
def test_local_llm_ps_parsed(mock_run, mock_cfg):
    mock_cfg.return_value = {
        "bin": "local-llm",
        "usage": {"quick_command": ["ollama", "ps"], "quick_parser": "ollama_ps"},
    }
    mock_run.return_value = _mock_proc("NAME ID SIZE\nllama3 latest 4GB\n")
    stats = get_provider_usage_summary("local-llm")
    assert stats["status"] == "ONLINE"
    assert "1 model(s) running" in stats["display"]
    assert stats["selector_key"] == "model"
    assert len(stats["selector_options"]) == 1


@patch("agent_system.core.providers.usage_service.get_provider_config")
@patch("agent_system.core.providers.usage_service.run_command")
def test_usage_error_status(mock_run, mock_cfg):
    mock_cfg.return_value = {
        "bin": "codex",
        "usage": {"quick_command": ["{bin}", "login", "status"], "quick_parser": "codex_login_status"},
    }
    mock_run.return_value = _mock_proc("", returncode=1)
    stats = get_provider_usage_summary("codex")
    assert stats["status"] == "ERROR"
    assert stats["display"].startswith("ERROR")


@patch("agent_system.core.providers.usage_service.get_provider_config")
@patch("agent_system.core.providers.usage_service.run_command")
def test_gemini_quota_exhausted_parsed_from_error_text(mock_run, mock_cfg):
    mock_cfg.return_value = {
        "bin": "gemini",
        "usage": {"quick_command": ["{bin}", "-r", "latest", "/stats"], "quick_parser": "gemini_usage_json"},
    }
    mock_run.return_value = _mock_proc_with_stderr(
        "",
        "TerminalQuotaError: You have exhausted your capacity on this model. Your quota will reset after 10h12m34s.",
        returncode=1,
    )
    stats = get_provider_usage_summary("gemini")
    assert stats["status"] == "QUOTA_EXHAUSTED"
    assert "resets in 10h12m34s" in stats["display"]


@patch.dict(os.environ, {"PYTEST_CURRENT_TEST": "unit::test"}, clear=False)
@patch("agent_system.core.providers.usage_service.get_provider_config")
@patch("agent_system.core.providers.usage_service.run_command")
def test_usage_blocked_when_test_disabled(mock_run, mock_cfg):
    mock_cfg.return_value = {
        "bin": "gemini",
        "test_enabled": False,
        "usage": {"quick_command": ["{bin}", "-p", "usage"], "quick_parser": "version"},
    }
    stats = get_provider_usage_summary("gemini")
    assert stats["status"] == "TEST_DISABLED"
    assert stats["display"] == "Disabled in tests"
    mock_run.assert_not_called()


@patch.dict(os.environ, {"PYTEST_CURRENT_TEST": "unit::test"}, clear=False)
@patch("agent_system.core.providers.usage_service.get_provider_config")
@patch("agent_system.core.providers.usage_service.run_command")
def test_detailed_usage_blocked_when_test_disabled(mock_run, mock_cfg):
    mock_cfg.return_value = {
        "bin": "claude",
        "test_enabled": False,
        "usage": {"detailed_command": ["{bin}", "-p", "usage"]},
    }
    out = get_provider_detailed_usage("claude")
    assert out == "Detailed usage disabled in tests for 'claude'."
    mock_run.assert_not_called()
