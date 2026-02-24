"""
test_get_usage_stats.py - Tests for the provider usage statistics script.
"""
import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add reporting to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "agent_system" / "reporting"))

from get_usage_stats import (
    get_gemini_stats, get_opencode_stats, get_claude_stats, get_local_llm_stats
)

@patch("get_usage_stats.shutil.which")
def test_binary_not_found(mock_which):
    """Test that an error is returned if the binary is not found in PATH."""
    mock_which.return_value = None
    assert "ERROR: 'gemini' command not found" in get_gemini_stats()
    assert "ERROR: 'opencode' command not found" in get_opencode_stats()
    assert "ERROR: 'claude' command not found" in get_claude_stats()
    assert "INFO: 'ollama' command not found" in get_local_llm_stats()

@patch("get_usage_stats.shutil.which")
@patch("get_usage_stats.subprocess.run")
def test_get_opencode_stats_success(mock_run, mock_which):
    """Test successful parsing of opencode stats."""
    mock_which.return_value = "/fake/path/opencode"
    mock_proc = MagicMock()
    mock_proc.returncode = 0
    mock_proc.stdout = "┌───────────────────┐\\n│ COST & TOKENS     │\\n├───────────────────┤\\n│Total Cost    $0.123 │\\n│Input         12.3K │\\n│Output        45.6K │\\n└───────────────────┘"
    mock_run.return_value = mock_proc
    
    # The script currently returns the raw string, let's just check it's returned
    stats = get_opencode_stats()
    assert "Total Cost" in stats
    assert "$0.123" in stats

@patch("get_usage_stats.shutil.which")
@patch("get_usage_stats.subprocess.run")
def test_get_gemini_stats_success(mock_run, mock_which):
    """Test successful command execution for gemini."""
    mock_which.return_value = "/fake/path/gemini"
    mock_proc = MagicMock()
    mock_proc.returncode = 0
    mock_proc.stdout = '{"session_id": "xyz", "summary": "..."}'
    mock_run.return_value = mock_proc
    
    stats = get_gemini_stats()
    assert '"session_id": "xyz"' in stats

@patch("get_usage_stats.shutil.which")
@patch("get_usage_stats.subprocess.run")
def test_command_failure(mock_run, mock_which):
    """Test that stderr is returned on command failure."""
    mock_which.return_value = "/fake/path/claude"
    mock_proc = MagicMock()
    mock_proc.returncode = 1
    mock_proc.stdout = ""
    mock_proc.stderr = "Something went wrong"
    mock_run.return_value = mock_proc
    
    stats = get_claude_stats()
    assert "Something went wrong" in stats

@patch("get_usage_stats.shutil.which")
@patch("get_usage_stats.subprocess.run")
def test_command_exception(mock_run, mock_which):
    """Test that a generic exception is caught and reported."""
    mock_which.return_value = "/fake/path/opencode"
    mock_run.side_effect = TimeoutError("Process took too long")
    
    stats = get_opencode_stats()
    assert "ERROR: Failed to run OpenCode: Process took too long" in stats
