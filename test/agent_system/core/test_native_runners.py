"""
test_native_runners.py - Unit tests for native agent runners.
"""
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add core to path
import sys
PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "agent_system" / "core"))

def test_runner_paths():
    """Verify that all runner scripts are in the expected locations."""
    runners_dir = PROJECT_ROOT / "agent_system" / "runners"
    expected = [
        "run_gemini_plan.py",
        "run_claude_plan.py",
        "run_codex_plan.py",
        "run_opencode_plan.py",
        "run_copilot_plan.py",
        "run_localllm_plan.py",
        "run_openai_api_plan.py",
    ]
    for runner in expected:
        assert (runners_dir / runner).exists(), f"Missing runner: {runner}"


@patch("subprocess.run")
def test_gemini_command_building(mock_run, tmp_path):
    """Test that Gemini runner builds the correct native CLI command."""
    from agent_system.runners.run_gemini_plan import main
    
    plan_file = tmp_path / "plan.md"
    plan_file.write_text("# Test Plan", encoding="utf-8")
    output_root = tmp_path / "outputs"
    worktree_root = tmp_path / "worktrees"
    
    # Mock shared runner utils to avoid git calls
    with patch("agent_runner_utils.create_isolated_worktree") as mock_wt:
        mock_wt.return_value = ("test-branch", tmp_path / "wt", tmp_path / "repo")
        with patch("agent_runner_utils.cleanup_worktree"):
            (tmp_path / "wt").mkdir(parents=True, exist_ok=True)

            # Setup sys.argv
            test_args = [
                "run_gemini_plan.py",
                "--plan-file", str(plan_file),
                "--output-root", str(output_root),
                "--worktree-root", str(worktree_root),
                "--model", "gemini-2.0-flash",
                "--no-cleanup"
            ]

            with patch.object(sys, 'argv', test_args):
                mock_run.return_value = MagicMock(returncode=0)
                main()

                # Verify the command passed to subprocess.run
                # Expected: gemini --yolo -p "# Test Plan" -m gemini-2.0-flash
                call_args = mock_run.call_args[0][0]
                assert any("gemini" in str(token).lower() for token in call_args)
                assert "--yolo" in call_args
                assert "-p" in call_args
                assert "# Test Plan" in call_args
                assert "-m" in call_args
                assert "gemini-2.0-flash" in call_args


@patch("subprocess.run")
def test_copilot_command_building(mock_run, tmp_path):
    """Test that Copilot runner builds the correct native CLI command."""
    from agent_system.runners.run_copilot_plan import main
    
    plan_file = tmp_path / "plan.md"
    plan_file.write_text("# Test Plan", encoding="utf-8")
    output_root = tmp_path / "outputs"
    worktree_root = tmp_path / "worktrees"
    
    with patch("agent_runner_utils.create_isolated_worktree") as mock_wt:
        mock_wt.return_value = ("test-branch", tmp_path / "wt", tmp_path / "repo")
        with patch("agent_runner_utils.cleanup_worktree"):
            (tmp_path / "wt").mkdir(parents=True, exist_ok=True)

            test_args = [
                "run_copilot_plan.py",
                "--plan-file", str(plan_file),
                "--output-root", str(output_root),
                "--worktree-root", str(worktree_root),
                "--model", "gpt-4o",
                "--no-cleanup"
            ]

            with patch.object(sys, 'argv', test_args):
                mock_run.return_value = MagicMock(returncode=0)
                main()

                # Expected: gh copilot explain "<plan>"
                call_args = mock_run.call_args[0][0]
                assert any("gh" in str(token).lower() for token in call_args)
                assert "copilot" in [str(token).lower() for token in call_args]
                assert "explain" in call_args
                assert "# Test Plan" in call_args


