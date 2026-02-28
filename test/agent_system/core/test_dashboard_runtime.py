"""
test_dashboard_runtime.py - Runtime smoke tests for Textual dashboard startup.
"""
import asyncio
from types import SimpleNamespace
from pathlib import Path
import sys
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

from agent_system.dashboard.agent_dashboard import AgentDashboardApp


def test_dashboard_provider_select_shows_health_status():
    assert AgentDashboardApp._provider_label("codex", {"status": "available"}) == "CODEX [ready]"
    assert AgentDashboardApp._provider_label("codex", {"status": "missing"}) == "CODEX [missing]"
    assert AgentDashboardApp._provider_label("codex", {"status": "degraded"}) == "CODEX [degraded]"
    assert AgentDashboardApp._provider_label("codex", {"status": "checking"}) == "CODEX [checking]"


def test_dashboard_provider_health_table_lists_each_provider():
    async def _run() -> None:
        app = AgentDashboardApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            app.planner_health = {
                "codex": {"status": "available", "reason": "ok"},
                "gemini": {"status": "missing", "reason": "binary not found"},
            }
            app.executor_health = {
                "codex": {"status": "degraded", "reason": "healthcheck failed"},
                "claude": {"status": "available", "reason": "ok"},
            }
            app._render_provider_health()
            table = app.query_one("#provider-health-table")
            providers = [table.get_row_at(i)[2] for i in range(len(table.rows))]
            assert "codex" in providers
            assert "gemini" in providers
            assert "claude" in providers

    asyncio.run(_run())


def test_dashboard_provider_health_table_empty_state_message():
    async def _run() -> None:
        app = AgentDashboardApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            app.planner_health = {}
            app.executor_health = {}
            app._render_provider_health()
            table = app.query_one("#provider-health-table")
            assert len(table.rows) == 1
            assert table.get_row_at(0)[2] == "No providers"

    asyncio.run(_run())


def test_dashboard_starts_with_checking_state_before_background_health_load():
    async def _run() -> None:
        with patch.object(AgentDashboardApp, "start_provider_health_refresh", return_value=None):
            with patch("agent_system.dashboard.agent_dashboard.get_provider_health", side_effect=AssertionError("should not be called synchronously")):
                app = AgentDashboardApp()
                async with app.run_test() as pilot:
                    await pilot.pause()
                    table = app.query_one("#provider-health-table")
                    statuses = [str(table.get_row_at(i)[3]) for i in range(len(table.rows))]
                    assert "checking" in statuses

    asyncio.run(_run())


def test_dashboard_starts_and_mounts_widgets():
    """Dashboard should start in Textual test harness and mount core widgets."""

    async def _run() -> None:
        app = AgentDashboardApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            assert app.query_one("#dispatcher-panel") is not None
            assert app.query_one("#run-list") is not None
            assert app.query_one("#stats-panel") is not None
            assert app.query_one("#provider-health-panel") is not None
            table = app.query_one("#provider-health-table")
            assert table is not None
            assert len(table.rows) > 0

    asyncio.run(_run())


def test_dashboard_handles_duplicate_run_ids_across_agents():
    """Run table should support identical run ids across different providers."""

    async def _run() -> None:
        app = AgentDashboardApp()
        duplicate_runs = [
            {"id": "same-id", "agent": "gemini", "state": "succeeded", "dir": PROJECT_ROOT, "pid": None, "model": "m1", "cost": 0.0, "tokens": 0, "branch": None, "summary": "A", "error": None, "mtime": 1},
            {"id": "same-id", "agent": "opencode", "state": "failed", "dir": PROJECT_ROOT, "pid": None, "model": "m2", "cost": 0.0, "tokens": 0, "branch": None, "summary": "B", "error": "err", "mtime": 2},
        ]
        with patch("agent_system.dashboard.agent_dashboard.get_all_runs", return_value=duplicate_runs):
            async with app.run_test() as pilot:
                await pilot.pause()
                table = app.query_one("#run-list")
                assert len(table.rows) == 2

    asyncio.run(_run())


def test_dashboard_handles_duplicate_run_ids_same_agent():
    """Run table should not crash if same agent emits duplicate run ids."""

    async def _run() -> None:
        app = AgentDashboardApp()
        duplicate_runs = [
            {"id": "same-id", "agent": "gemini", "state": "succeeded", "dir": PROJECT_ROOT / "a", "pid": None, "model": "m1", "cost": 0.0, "tokens": 0, "branch": None, "summary": "A", "error": None, "mtime": 1},
            {"id": "same-id", "agent": "gemini", "state": "failed", "dir": PROJECT_ROOT / "b", "pid": None, "model": "m2", "cost": 0.0, "tokens": 0, "branch": None, "summary": "B", "error": "err", "mtime": 2},
        ]
        with patch("agent_system.dashboard.agent_dashboard.get_all_runs", return_value=duplicate_runs):
            async with app.run_test() as pilot:
                await pilot.pause()
                table = app.query_one("#run-list")
                assert len(table.rows) == 2

    asyncio.run(_run())


def test_dashboard_merge_hotkey_ignored_when_run_list_not_focused():
    """Merge action should be ignored unless run table has focus."""

    async def _run() -> None:
        app = AgentDashboardApp()
        with patch("agent_system.dashboard.agent_dashboard.subprocess.run") as mock_run:
            async with app.run_test() as pilot:
                await pilot.pause()
                app.selected_run = {"id": "x", "branch": "branch/test", "dir": PROJECT_ROOT}
                before = mock_run.call_count
                with patch.object(app, "_run_list_is_focused", return_value=False):
                    app.action_merge_run()
                    assert mock_run.call_count == before

    asyncio.run(_run())


def test_dashboard_prompt_sanitizes_terminal_escape_sequences():
    async def _run() -> None:
        app = AgentDashboardApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            dirty = "Do work\x1b[<64;120;19M now"
            clean = app._sanitize_prompt(dirty)
            assert clean == "Do work now"

    asyncio.run(_run())


def test_dashboard_prompt_sanitizes_orphan_mouse_fragment():
    async def _run() -> None:
        app = AgentDashboardApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            dirty = "task [<35;102;22M now"
            clean = app._sanitize_prompt(dirty)
            assert clean == "task  now"

    asyncio.run(_run())


def test_dashboard_submit_task_uses_non_shell_popen():
    async def _run() -> None:
        with patch.object(AgentDashboardApp, "start_provider_health_refresh", return_value=None):
            app = AgentDashboardApp()
            with patch("agent_system.dashboard.agent_dashboard.subprocess.Popen") as mock_popen:
                async with app.run_test() as pilot:
                    await pilot.pause()
                    app.planner_health = {"codex": {"status": "available", "working": True, "reason": "ready"}}
                    app.executor_health = {"codex": {"status": "available", "working": True, "reason": "ready"}}
                    app.query_one("#planner-select").value = "codex"
                    app.query_one("#executor-select").value = "codex"
                    app.query_one("#prompt-input").text = "Cross platform run"
                    app.action_submit_task()
                    assert mock_popen.called
                    cmd = mock_popen.call_args[0][0]
                    kwargs = mock_popen.call_args.kwargs
                    assert isinstance(cmd, list)
                    assert "--workspace" in cmd
                    assert "--planner-model" in cmd
                    assert "--executor-model" in cmd
                    assert "--planner-thinking-budget" in cmd
                    assert "--thinking-budget" in cmd
                    assert kwargs.get("shell", False) is False

    asyncio.run(_run())


def test_dashboard_submit_task_blocks_unavailable_executor():
    async def _run() -> None:
        with patch.object(AgentDashboardApp, "start_provider_health_refresh", return_value=None):
            app = AgentDashboardApp()
            with patch("agent_system.dashboard.agent_dashboard.subprocess.Popen") as mock_popen:
                async with app.run_test() as pilot:
                    await pilot.pause()
                    app.planner_health = {"codex": {"status": "available", "working": True, "reason": "ready"}}
                    app.executor_health = {"codex": {"status": "missing", "working": False, "reason": "binary not found"}}
                    app.query_one("#planner-select").value = "codex"
                    app.query_one("#executor-select").value = "codex"
                    app.query_one("#prompt-input").text = "Do thing"
                    app.action_submit_task()
                    mock_popen.assert_not_called()

    asyncio.run(_run())


def test_dashboard_submit_task_blocks_while_health_checking():
    async def _run() -> None:
        with patch.object(AgentDashboardApp, "start_provider_health_refresh", return_value=None):
            app = AgentDashboardApp()
            with patch("agent_system.dashboard.agent_dashboard.subprocess.Popen") as mock_popen:
                async with app.run_test() as pilot:
                    await pilot.pause()
                    app.planner_health = {"codex": {"status": "checking", "working": None, "reason": "checking"}}
                    app.executor_health = {"codex": {"status": "available", "working": True, "reason": "ready"}}
                    app.query_one("#planner-select").value = "codex"
                    app.query_one("#executor-select").value = "codex"
                    app.query_one("#prompt-input").text = "Do thing"
                    app.action_submit_task()
                    mock_popen.assert_not_called()

    asyncio.run(_run())


def test_dashboard_row_selected_ignores_provider_health_table():
    app = AgentDashboardApp()
    with patch.object(app, "update_details") as mock_update:
        app.on_data_table_row_selected(SimpleNamespace(data_table=SimpleNamespace(id="provider-health-table")))
        mock_update.assert_not_called()
        app.on_data_table_row_selected(SimpleNamespace(data_table=SimpleNamespace(id="run-list")))
        mock_update.assert_called_once()
