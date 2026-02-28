"""
agent_dashboard.py - Modern Textual TUI for Agent Lifecycle Management.
"""
import os
import re
import shutil
import signal
import subprocess
import threading
import time
import sys
from pathlib import Path

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Footer, DataTable, RichLog, Select, Button, Label, TextArea
from textual.reactive import reactive

# Add core to path for shared utils
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "core"))

from agent_runner_utils import (
    get_enabled_planners, get_enabled_executors, get_agent_models,
    get_all_runs, PROJECT_ROOT, write_json_safe, get_provider_health
)
from runtime_paths import RUNTIME_ROOT, ARTIFACTS_ROOT

# --- Data Gathering ---
EFFORT_LEVELS = ["none", "low", "medium", "high"]

# --- Main Textual App ---
class AgentDashboardApp(App):
    CSS = """
    Screen {
        background: #1a1b26;
    }

    #dispatcher-panel {
        dock: top;
        height: 16;
        background: #24283b;
        border: tall #7aa2f7;
        padding: 0 2;
        margin: 1;
        overflow: hidden;
    }
    
    #dispatcher-controls { height: 5; align: left top; }
    .control-block { height: 5; margin-right: 1; }
    .control-label { height: 1; color: #7aa2f7; text-style: bold; padding-left: 1; }
    #planner-block, #planner-effort-block, #executor-block, #executor-effort-block { width: 16; }
    #planner-model-block, #executor-model-block { width: 44; }
    #launch-block { width: 12; margin-right: 0; }
    #prompt-input { width: 1fr; height: 5; border: inner #414868; }
    #dispatcher-controls Select { width: 1fr; margin-right: 0; }
    #launch-btn { width: 1fr; margin-left: 0; min-width: 12; }
    #main-container { layout: horizontal; height: 1fr; }
    #run-list { width: 40%; height: 1fr; border: tall #7aa2f7; background: #24283b; margin: 0 1; }
    #detail-container { width: 60%; margin-right: 1; }
    #top-details { height: 18; margin-bottom: 1; layout: horizontal; }
    #stats-panel { width: 60%; height: 1fr; background: #24283b; border: tall #7aa2f7; padding: 1 2; margin-right: 1; }
    #provider-health-panel { width: 40%; height: 1fr; background: #24283b; border: tall #7aa2f7; padding: 1 2; }
    #provider-health-table { height: 1fr; color: #c0caf5; background: #1a1b26; }
    .stat-row { height: 1; }
    .stat-label { width: 10; color: #bb9af7; text-style: bold; }
    .stat-value { color: #c0caf5; }
    #stat-error { color: #f7768e; text-style: bold; }
    #run-log { height: 1fr; border: tall #7aa2f7; background: #1a1b26; }
    """

    BINDINGS = [
        ("m", "merge_run", "Merge"), ("k", "kill_run", "Kill"), ("d", "delete_run", "Delete"),
        ("c", "maintenance", "Cleanup"), ("q", "quit", "Quit"), ("ctrl+s", "submit_task", "Dispatch"),
    ]

    runs = reactive(list)
    selected_run = reactive(dict)
    log_positions = {}
    status_markers = {}
    _is_shutting_down: bool = False
    _health_refresh_inflight: bool = False
    _enabled_planners: list[str] = []
    _enabled_executors: list[str] = []
    planner_health: dict[str, dict] = {}
    executor_health: dict[str, dict] = {}
    _follow_latest_run_once: bool = False

    @staticmethod
    def _provider_label(provider: str, health: dict) -> str:
        status = str((health or {}).get("status", "unknown")).lower()
        suffix = {
            "available": "ready",
            "missing": "missing",
            "degraded": "degraded",
            "checking": "checking",
        }.get(status, "unknown")
        return f"{provider.upper()} [{suffix}]"

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        enabled_planners = get_enabled_planners()
        enabled_executors = get_enabled_executors()
        initial_planner = enabled_planners[0] if enabled_planners else None
        initial_executor = enabled_executors[0] if enabled_executors else None
        self._enabled_planners = list(enabled_planners)
        self._enabled_executors = list(enabled_executors)
        self._seed_provider_health_checking(enabled_planners, enabled_executors)
        planner_options = [
            (self._provider_label(name, self.planner_health.get(name, {})), name)
            for name in enabled_planners
        ]
        executor_options = [
            (self._provider_label(name, self.executor_health.get(name, {})), name)
            for name in enabled_executors
        ]
        planner_model_values: list[str] = []
        executor_model_values: list[str] = []
        if initial_planner:
            try:
                planner_model_values = get_agent_models(initial_planner, role="planners")
            except TypeError:
                planner_model_values = get_agent_models(initial_planner)
        if initial_executor:
            try:
                executor_model_values = get_agent_models(initial_executor, role="executors")
            except TypeError:
                executor_model_values = get_agent_models(initial_executor)
        planner_model_options = [(m, m) for m in planner_model_values]
        executor_model_options = [(m, m) for m in executor_model_values]
        planner_model_default = planner_model_values[0] if planner_model_values else Select.NULL
        executor_model_default = executor_model_values[0] if executor_model_values else Select.NULL

        with Container(id="dispatcher-panel"):
            with Vertical():
                yield TextArea("", id="prompt-input")
                with Horizontal(id="dispatcher-controls"):
                    with Vertical(id="planner-block", classes="control-block"):
                        yield Label("Planner", classes="control-label")
                        yield Select(
                            planner_options,
                            value=initial_planner if initial_planner is not None else Select.NULL,
                            id="planner-select",
                            prompt="",
                            allow_blank=not bool(planner_options),
                        )
                    with Vertical(id="planner-model-block", classes="control-block"):
                        yield Label("Planner Model", classes="control-label")
                        yield Select(
                            planner_model_options,
                            value=planner_model_default,
                            id="planner-model-select",
                            prompt="",
                            allow_blank=not bool(planner_model_options),
                        )
                    with Vertical(id="planner-effort-block", classes="control-block"):
                        yield Label("Plan Effort", classes="control-label")
                        yield Select(
                            [(level.title(), level) for level in EFFORT_LEVELS],
                            value="medium",
                            id="planner-effort-select",
                            prompt="",
                            allow_blank=False,
                        )
                    with Vertical(id="executor-block", classes="control-block"):
                        yield Label("Executor", classes="control-label")
                        yield Select(
                            executor_options,
                            value=initial_executor if initial_executor is not None else Select.NULL,
                            id="executor-select",
                            prompt="",
                            allow_blank=not bool(executor_options),
                        )
                    with Vertical(id="executor-model-block", classes="control-block"):
                        yield Label("Executor Model", classes="control-label")
                        yield Select(
                            executor_model_options,
                            value=executor_model_default,
                            id="executor-model-select",
                            prompt="",
                            allow_blank=not bool(executor_model_options),
                        )
                    with Vertical(id="executor-effort-block", classes="control-block"):
                        yield Label("Exec Effort", classes="control-label")
                        yield Select(
                            [(level.title(), level) for level in EFFORT_LEVELS],
                            value="medium",
                            id="executor-effort-select",
                            prompt="",
                            allow_blank=False,
                        )
                    with Vertical(id="launch-block", classes="control-block"):
                        yield Label("Action", classes="control-label")
                        yield Button("Launch", variant="success", id="launch-btn")

        with Container(id="main-container"):
            yield DataTable(id="run-list")
            with Vertical(id="detail-container"):
                with Container(id="top-details"):
                    with Vertical(id="stats-panel"):
                        with Horizontal(classes="stat-row"):
                            yield Label("ID: ", classes="stat-label"); yield Label("-", id="stat-id", classes="stat-value")
                        with Horizontal(classes="stat-row"):
                            yield Label("Model: ", classes="stat-label"); yield Label("-", id="stat-model", classes="stat-value")
                        with Horizontal(classes="stat-row"):
                            yield Label("Branch: ", classes="stat-label"); yield Label("-", id="stat-branch", classes="stat-value")
                        with Horizontal(classes="stat-row"):
                            yield Label("Stats: ", classes="stat-label"); yield Label("-", id="stat-summary", classes="stat-value")
                        with Horizontal(classes="stat-row", id="error-row"):
                            yield Label("Error: ", classes="stat-label"); yield Label("-", id="stat-error", classes="stat-value")
                    with Vertical(id="provider-health-panel"):
                        yield DataTable(id="provider-health-table")
                yield RichLog(id="run-log", highlight=True, markup=True)
        yield Footer()

    def on_mount(self) -> None:
        self._is_shutting_down = False
        self._health_refresh_inflight = False
        self.query_one("#dispatcher-panel").border_title = "Task Dispatcher (CTRL+S to launch)"
        table = self.query_one("#run-list", DataTable)
        table.border_title = "RUN NAVIGATOR"; table.cursor_type = "row"
        table.add_columns("Status", "Phase", "Agent", "Task Summary")
        self.query_one("#stats-panel").border_title = "DETAILS & STATS"
        self.query_one("#provider-health-panel").border_title = "PROVIDER HEALTH"
        health_table = self.query_one("#provider-health-table", DataTable)
        health_table.cursor_type = "row"
        health_table.add_columns("Sel", "R", "Provider", "Status")
        self.query_one("#run-log").border_title = "LIVE EXECUTION LOG"

        prompt = self.query_one("#prompt-input", TextArea)
        prompt.border_title = "Prompt"
        prompt.tooltip = "Enter task prompt (multiline supported)"
        prompt.text = ""
        planner_select = self.query_one("#planner-select", Select)
        planner_select.tooltip = "Provider status is shown as [checking], [ready], [missing], or [degraded]"
        executor_select = self.query_one("#executor-select", Select)
        executor_select.tooltip = "Provider status is shown as [checking], [ready], [missing], or [degraded]"

        if planner_select.value:
            self.update_planner_model_options(str(planner_select.value))
        if executor_select.value:
            self.update_executor_model_options(str(executor_select.value))
        self._render_provider_health()
        self.start_provider_health_refresh()
        self.update_runs()
        # Keep focus off prompt initially to avoid terminal control bytes becoming prompt text.
        self.query_one("#run-list", DataTable).focus()
        self.set_interval(2, self.update_runs)
        self.set_interval(10, self.start_provider_health_refresh)

    def on_unmount(self) -> None:
        self._is_shutting_down = True

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "planner-select":
            self.update_planner_model_options(event.value)
        if event.select.id == "executor-select":
            self.update_executor_model_options(event.value)
        if event.select.id in {"planner-select", "executor-select"}:
            self._render_provider_health()

    def _seed_provider_health_checking(self, planners: list[str], executors: list[str]) -> None:
        self.planner_health = {
            name: {
                "provider": name,
                "role": "planners",
                "installed": None,
                "working": None,
                "status": "checking",
                "reason": "checking",
            }
            for name in planners
        }
        self.executor_health = {
            name: {
                "provider": name,
                "role": "executors",
                "installed": None,
                "working": None,
                "status": "checking",
                "reason": "checking",
            }
            for name in executors
        }

    def _refresh_provider_select_labels(self) -> None:
        planner_select = self.query_one("#planner-select", Select)
        executor_select = self.query_one("#executor-select", Select)

        current_planner = planner_select.value
        planner_options = [
            (self._provider_label(name, self.planner_health.get(name, {})), name)
            for name in self._enabled_planners
        ]
        planner_select.set_options(planner_options)
        if current_planner in self._enabled_planners:
            planner_select.value = current_planner
        elif self._enabled_planners:
            planner_select.value = self._enabled_planners[0]

        current_executor = executor_select.value
        executor_options = [
            (self._provider_label(name, self.executor_health.get(name, {})), name)
            for name in self._enabled_executors
        ]
        executor_select.set_options(executor_options)
        if current_executor in self._enabled_executors:
            executor_select.value = current_executor
        elif self._enabled_executors:
            executor_select.value = self._enabled_executors[0]

    def _apply_provider_health(self, planner_health: dict[str, dict], executor_health: dict[str, dict]) -> None:
        if self._is_shutting_down:
            return
        if planner_health:
            self.planner_health = planner_health
        if executor_health:
            self.executor_health = executor_health
        self._refresh_provider_select_labels()
        self._render_provider_health()

    def start_provider_health_refresh(self) -> None:
        if self._is_shutting_down or self._health_refresh_inflight:
            return
        self._health_refresh_inflight = True

        def worker() -> None:
            planner_health: dict[str, dict] = {}
            executor_health: dict[str, dict] = {}
            try:
                planner_health = get_provider_health("planners")
                executor_health = get_provider_health("executors")
            finally:
                def apply_updates() -> None:
                    try:
                        self._apply_provider_health(planner_health, executor_health)
                    finally:
                        self._health_refresh_inflight = False

                try:
                    self.call_from_thread(apply_updates)
                except Exception:
                    self._health_refresh_inflight = False

        thread = threading.Thread(target=worker, name="provider-health-refresh", daemon=True)
        thread.start()

    def _render_provider_health(self) -> None:
        planner_selected = str(self.query_one("#planner-select", Select).value or "")
        executor_selected = str(self.query_one("#executor-select", Select).value or "")
        table = self.query_one("#provider-health-table", DataTable)
        try:
            # Guard startup race where selection events can fire before columns are initialized.
            if len(table.columns) == 0:
                return
            table.clear()
            all_names = sorted(set(self.planner_health.keys()) | set(self.executor_health.keys()))
            if not all_names:
                table.add_row("-", "-", "No providers", "unknown")
                return
            for name in all_names:
                planner_state = self.planner_health.get(name, {})
                executor_state = self.executor_health.get(name, {})
                planner = bool(planner_state)
                executor = bool(executor_state)
                role_mark = f"{'P' if planner else '-'}{'E' if executor else '-'}"
                selected = "*" if name in {planner_selected, executor_selected} else "-"

                statuses: list[str] = []
                if planner:
                    statuses.append(str(planner_state.get("status", "unknown")))
                if executor:
                    statuses.append(str(executor_state.get("status", "unknown")))

                if "missing" in statuses:
                    status = "missing"
                elif "degraded" in statuses:
                    status = "degraded"
                elif "checking" in statuses:
                    status = "checking"
                elif statuses:
                    status = "available"
                else:
                    status = "unknown"

                table.add_row(selected, role_mark, name, status)
        except Exception:
            table.clear()
            table.add_row("-", "--", "Provider health", "error")

    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        if event.text_area.id != "prompt-input":
            return
        clean = self._sanitize_prompt(event.text_area.text)
        if clean != event.text_area.text:
            event.text_area.text = clean

    def _sanitize_prompt(self, text: str) -> str:
        # Strip terminal mouse-tracking/control escape sequences if they leak into input.
        text = re.sub(r"\x1b\[[0-9;?<]*[ -/]*[@-~]", "", text)
        # Also strip common orphaned fragments when ESC is eaten but payload remains.
        text = re.sub(r"\[<\d+;\d+;\d+[mM]", "", text)
        return "".join(ch for ch in text if ch in ("\n", "\t") or ord(ch) >= 32)

    def _update_model_select(self, select_id: str, provider: str, role: str) -> None:
        try:
            model_select = self.query_one(f"#{select_id}", Select)
        except Exception:
            # Startup race: selection events may fire before model selects are mounted.
            return
        try:
            models = get_agent_models(str(provider), role=role)
        except TypeError:
            models = get_agent_models(str(provider))
        current = model_select.value
        model_select.set_options([(m, m) for m in models])
        if current in models:
            model_select.value = current
        elif models:
            model_select.value = models[0]

    def update_planner_model_options(self, provider: str) -> None:
        self._update_model_select("planner-model-select", provider, role="planners")

    def update_executor_model_options(self, provider: str) -> None:
        self._update_model_select("executor-model-select", provider, role="executors")

    def update_runs(self) -> None:
        new_runs = get_all_runs(); table = self.query_one("#run-list", DataTable); selected_key = None
        try:
            if 0 <= table.cursor_coordinate.row < len(table.rows):
                selected_key = list(table.rows.keys())[table.cursor_coordinate.row].value
        except Exception:
            pass
        if self.runs != new_runs:
            self.runs = new_runs; table.clear()
            styles = {"running":"yellow","succeeded":"green","failed":"red","cancelled":"red","merged":"cyan","crashed":"bold red"}
            phase_styles = {"planning":"[yellow italic]PLANNING","executing":"[cyan]EXECUTING","done":"[white]DONE"}
            for idx, run in enumerate(self.runs):
                state = run['state'].lower(); status = f"[{styles.get(state, 'white')}]{state.upper()}"
                phase_raw = run.get('phase', 'done')
                phase_cell = phase_styles.get(phase_raw, f"[white]{phase_raw.upper()}")
                row_key = f"{run['agent']}:{run['id']}:{run.get('mtime')}:{idx}"
                table.add_row(status, phase_cell, run['agent'].upper(), run['summary'], key=row_key)
            if self._follow_latest_run_once and self.runs:
                table.move_cursor(row=0)
                self._follow_latest_run_once = False
            elif selected_key:
                try:
                    for i, key in enumerate(table.rows.keys()):
                        if key.value == selected_key: table.move_cursor(row=i); break
                except Exception:
                    if self.runs: table.move_cursor(row=0)
            elif self.runs: table.move_cursor(row=0)
        self.update_details()

    def _read_status(self, run_dir: Path) -> dict:
        status_path = run_dir / "status.json"
        if not status_path.exists():
            return {}
        try:
            import json
            return json.loads(status_path.read_text(encoding="utf-8-sig"))
        except Exception:
            return {}

    def update_details(self) -> None:
        table = self.query_one("#run-list", DataTable); log = self.query_one("#run-log")
        if not self.runs or table.cursor_row < 0:
            self.query_one("#stat-id").update("-"); self.query_one("#stat-model").update("-")
            self.query_one("#stat-branch").update("-"); self.query_one("#stat-summary").update("-")
            self.query_one("#stat-error").update("-"); self.query_one("#error-row").display = False
            log.clear(); self.selected_run = {}
            return
        idx = table.cursor_row
        if idx < len(self.runs):
            prev_key = str(self.selected_run.get("dir")) if self.selected_run else None
            self.selected_run = self.runs[idx]
            curr_key = str(self.selected_run["dir"])
            self.query_one("#stat-id").update(self.selected_run['id'])
            self.query_one("#stat-model").update(self.selected_run['model'])
            self.query_one("#stat-branch").update(self.selected_run['branch'] or "n/a")
            self.query_one("#stat-summary").update(f"Cost: ${self.selected_run['cost']:.4f} | Tokens: {self.selected_run['tokens']}")
            err_row = self.query_one("#error-row")
            if self.selected_run.get("error"):
                self.query_one("#stat-error").update(self.selected_run["error"]); err_row.display = True
            else: err_row.display = False
            if prev_key != curr_key:
                log.clear()
                self.log_positions[curr_key] = {"stdout": 0, "stderr": 0}
                self.status_markers[curr_key] = None

            positions = self.log_positions.setdefault(curr_key, {"stdout": 0, "stderr": 0})
            got_output = False
            for stream_name, label in (("stdout", ""), ("stderr", "[stderr] ")):
                log_file = self.selected_run["dir"] / f"{stream_name}.log"
                if not log_file.exists():
                    continue
                try:
                    with open(log_file, "r", encoding="utf-8", errors="replace") as f:
                        f.seek(int(positions.get(stream_name, 0)))
                        new = f.read()
                        if new:
                            got_output = True
                            if label:
                                for line in new.splitlines():
                                    log.write(f"{label}{line}")
                            else:
                                log.write(new)
                        positions[stream_name] = f.tell()
                except Exception:
                    pass

            status = self._read_status(self.selected_run["dir"])
            marker = (
                status.get("state"),
                status.get("heartbeat_at"),
                status.get("last_event_type"),
                status.get("error"),
            )
            if not got_output and self.selected_run.get("state") == "running":
                if self.status_markers.get(curr_key) != marker:
                    heartbeat = status.get("heartbeat_at", "n/a")
                    event = status.get("last_event_type", "n/a")
                    log.write(f"[status] RUNNING | heartbeat={heartbeat} | event={event}")
                    if status.get("error"):
                        log.write(f"[status] ERROR: {status.get('error')}")
                    self.status_markers[curr_key] = marker

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        if getattr(event.data_table, "id", "") != "run-list":
            return
        self.update_details()
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "launch-btn": self.action_submit_task()

    def _run_list_is_focused(self) -> bool:
        focused = self.focused
        return focused is not None and getattr(focused, "id", None) == "run-list"

    def action_submit_task(self) -> None:
        prompt = self.query_one("#prompt-input", TextArea).text.strip()
        if not prompt: self.notify("Please enter a prompt", severity="error"); return
        planner = self.query_one("#planner-select").value; executor = self.query_one("#executor-select").value
        planner_state = self.planner_health.get(str(planner), {})
        executor_state = self.executor_health.get(str(executor), {})
        if planner_state.get("status") == "checking":
            self.notify("Planner status still checking", severity="warning")
            return
        if executor_state.get("status") == "checking":
            self.notify("Executor status still checking", severity="warning")
            return
        if not planner_state.get("working", True):
            reason = planner_state.get("reason", "planner unavailable")
            self.notify(f"Planner unavailable: {reason}", severity="error")
            return
        if not executor_state.get("working", True):
            reason = executor_state.get("reason", "executor unavailable")
            self.notify(f"Executor unavailable: {reason}", severity="error")
            return
        planner_model = self.query_one("#planner-model-select", Select).value
        executor_model = self.query_one("#executor-model-select", Select).value
        planner_effort = self.query_one("#planner-effort-select").value
        executor_effort = self.query_one("#executor-effort-select").value
        plan_dir = ARTIFACTS_ROOT / planner / "temp"
        plan_dir.mkdir(parents=True, exist_ok=True); plan_file = plan_dir / f"dispatch_{int(time.time())}.md"
        plan_content = f"""# BOUNDARY ENFORCEMENT & SAFETY MANDATE
- **Workspace**: You MUST only work within the current directory.
- **Isolation**: You are running in an isolated Git worktree on a dedicated branch.
- **No Escaping**: Do not attempt to access paths outside of the current directory tree.
- **Goal**: {prompt}
"""
        plan_file.write_text(plan_content, encoding="utf-8")
        cmd = [
            sys.executable,
            str(RUNTIME_ROOT / "agent_system" / "core" / "run_agent_plan.py"),
            "--planner",
            str(planner),
            "--executor",
            str(executor),
            "--planner-model",
            str(planner_model),
            "--executor-model",
            str(executor_model),
            "--planner-thinking-budget",
            str(planner_effort),
            "--thinking-budget",
            str(executor_effort),
            "--plan-file",
            str(plan_file),
            "--task-summary",
            prompt[:50],
            "--workspace",
            str(PROJECT_ROOT),
            "--cleanup-worktree",
        ]
        popen_kwargs = {
            "cwd": str(PROJECT_ROOT),
            "stdout": subprocess.DEVNULL,
            "stderr": subprocess.DEVNULL,
        }
        if os.name == "nt":
            # Detached + no window prevents pop-up terminals when launching from web dashboard.
            popen_kwargs["creationflags"] = 0x00000008 | 0x08000000
        else:
            popen_kwargs["start_new_session"] = True
        subprocess.Popen(cmd, **popen_kwargs)
        self._follow_latest_run_once = True
        self.query_one("#prompt-input", TextArea).text = ""
        self.notify(f"Task dispatched: plan={planner_model} exec={executor_model}"); self.update_runs()

    def action_merge_run(self) -> None:
        if not self._run_list_is_focused():
            return
        if self.selected_run.get("branch"):
            shutil.rmtree(self.selected_run["dir"] / "worktree", ignore_errors=True)
            subprocess.run(["git", "merge", self.selected_run["branch"]], cwd=PROJECT_ROOT)
            if "lifecycle" not in self.selected_run: self.selected_run["lifecycle"] = {}
            self.selected_run["lifecycle"]["state"] = "merged"
            write_json_safe(self.selected_run["dir"] / "metadata.json", self.selected_run)
            self.notify("Merged successfully"); self.update_runs()

    def action_kill_run(self) -> None:
        if not self._run_list_is_focused():
            return
        if self.selected_run.get("pid"):
            pid = int(self.selected_run["pid"])
            try:
                if os.name == "nt":
                    subprocess.run(
                        ["taskkill", "/F", "/T", "/PID", str(pid)],
                        capture_output=True,
                    )
                else:
                    # Attempt process-group kill first for runs started in their own session.
                    try:
                        os.killpg(pid, signal.SIGTERM)
                    except Exception:
                        os.kill(pid, signal.SIGTERM)
                self.notify("Process killed")
            except Exception as exc:
                self.notify(f"Failed to kill process: {exc}", severity="error")
            self.update_runs()

    def action_delete_run(self) -> None:
        if not self._run_list_is_focused():
            return
        if self.selected_run:
            run_id = self.selected_run['id']; agent = self.selected_run['agent']
            shutil.rmtree(self.selected_run["dir"], ignore_errors=True)
            worktree_dir = ARTIFACTS_ROOT / agent / "temp" / "worktrees" / run_id.replace(":", "_")
            if worktree_dir.exists():
                subprocess.run(["git", "worktree", "remove", "--force", str(worktree_dir)], cwd=PROJECT_ROOT, capture_output=True)
                shutil.rmtree(worktree_dir, ignore_errors=True)
            if self.selected_run.get("branch"):
                subprocess.run(["git", "branch", "-D", self.selected_run["branch"]], cwd=PROJECT_ROOT, capture_output=True)
            subprocess.run(["git", "worktree", "prune"], cwd=PROJECT_ROOT, capture_output=True)
            self.notify("Artifacts & Worktree purged"); self.update_runs()

    def action_maintenance(self) -> None:
        cmd = [
            sys.executable,
            str(RUNTIME_ROOT / "agent_system" / "core" / "agent_maintenance.py"),
            "--yes",
        ]
        res = subprocess.run(cmd, cwd=str(PROJECT_ROOT), capture_output=True, text=True)
        if res.returncode == 0:
            self.notify("Cleanup completed")
        else:
            msg = ((res.stderr or res.stdout or "cleanup failed").strip().splitlines() or ["cleanup failed"])[0]
            self.notify(f"Cleanup failed: {msg}", severity="error")

if __name__ == "__main__":
    app = AgentDashboardApp()
    app.run()
