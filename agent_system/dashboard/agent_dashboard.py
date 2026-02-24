"""
agent_dashboard.py - Modern Textual TUI for Agent Lifecycle Management.
"""
import json
import os
import shutil
import subprocess
import time
import sys
from pathlib import Path
from datetime import datetime

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Footer, DataTable, RichLog, Input, Select, Button, Static, Label
from textual.reactive import reactive

# Add core to path for shared utils
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "core"))
from agent_runner_utils import (
    AGENT_TYPES, get_enabled_planners, get_enabled_executors, get_agent_models,
    get_all_runs, PROJECT_ROOT
)

# --- Data Gathering ---
BUDGETS = ["low", "medium", "high"]

# --- Main Textual App ---
class AgentDashboardApp(App):
    CSS = """
    Screen {
        background: #1a1b26;
    }

    #dispatcher-panel {
        dock: top;
        height: 10;
        background: #24283b;
        border: tall #7aa2f7;
        padding: 0 2;
        margin: 1;
        overflow: hidden;
    }

    #dispatcher-panel Horizontal {
        height: 3;
        align: center middle;
    }

    #dispatcher-panel Label {
        width: 100%;
        text-align: center;
        color: #7aa2f7;
        text-style: bold;
        margin-top: 1;
    }

    #prompt-input {
        width: 1fr;
        border: inner #414868;
    }

    Select {
        width: 24;
        margin-left: 1;
    }

    #launch-btn {
        margin-left: 1;
        min-width: 12;
    }

    #main-container {
        layout: horizontal;
        height: 1fr;
    }

    #run-list {
        width: 40%;
        height: 1fr;
        border: tall #7aa2f7;
        background: #24283b;
        margin: 0 1;
    }

    #detail-container {
        width: 60%;
        margin-right: 1;
    }

    #stats-panel {
        height: auto;
        background: #24283b;
        border: tall #7aa2f7;
        padding: 1 2;
        margin-bottom: 1;
    }

    .stat-row {
        height: 1;
    }

    .stat-label {
        width: 10;
        color: #bb9af7;
        text-style: bold;
    }

    .stat-value {
        color: #c0caf5;
    }

    #run-log {
        height: 1fr;
        border: tall #7aa2f7;
        background: #1a1b26;
    }
    """

    BINDINGS = [
        ("m", "merge_run", "Merge"),
        ("k", "kill_run", "Kill"),
        ("d", "delete_run", "Delete"),
        ("c", "maintenance", "Cleanup"),
        ("q", "quit", "Quit"),
        ("ctrl+s", "submit_task", "Dispatch"),
    ]

    runs = reactive(list)
    selected_run = reactive(dict)
    log_positions = {} # Track read position per run_id

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        
        enabled_planners = get_enabled_planners()
        enabled_executors = get_enabled_executors()

        with Container(id="dispatcher-panel"):
            yield Label("🚀 TASK DISPATCHER")
            with Vertical():
                yield Input(placeholder="Describe the task...", id="prompt-input")
                with Horizontal():
                    yield Select([(a.upper(), a) for a in enabled_planners], value=enabled_planners[0] if enabled_planners else None, id="planner-select", prompt="Planner")
                    yield Select([(a.upper(), a) for a in enabled_executors], value=enabled_executors[0] if enabled_executors else None, id="executor-select", prompt="Executor")
                    yield Select([], id="model-select", prompt="Model")
                    yield Select([(b.title(), b) for b in BUDGETS], value="medium", id="budget-select", prompt="Depth")
                    yield Button("Launch", variant="success", id="launch-btn")

        with Container(id="main-container"):
            yield DataTable(id="run-list")
            with Vertical(id="detail-container"):
                with Vertical(id="stats-panel"):
                    with Horizontal(classes="stat-row"):
                        yield Label("ID: ", classes="stat-label")
                        yield Label("-", id="stat-id", classes="stat-value")
                    with Horizontal(classes="stat-row"):
                        yield Label("Model: ", classes="stat-label")
                        yield Label("-", id="stat-model", classes="stat-value")
                    with Horizontal(classes="stat-row"):
                        yield Label("Branch: ", classes="stat-label")
                        yield Label("-", id="stat-branch", classes="stat-value")
                    with Horizontal(classes="stat-row"):
                        yield Label("Stats: ", classes="stat-label")
                        yield Label("-", id="stat-summary", classes="stat-value")
                yield RichLog(id="run-log", highlight=True, markup=True)
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#dispatcher-panel").border_title = "Task Dispatcher (CTRL+S to launch)"
        table = self.query_one(DataTable)
        table.border_title = "RUN NAVIGATOR"
        table.cursor_type = "row"
        table.add_columns("Status", "Agent", "Task Summary")
        
        self.query_one("#stats-panel").border_title = "DETAILS & STATS"
        self.query_one("#run-log").border_title = "LIVE EXECUTION LOG"

        # Initialize model select for default executor
        self.update_model_options("codex")

        self.update_runs()
        self.set_interval(2, self.update_runs)

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "executor-select":
            self.update_model_options(event.value)

    def update_model_options(self, agent: str) -> None:
        model_select = self.query_one("#model-select")
        models = get_agent_models(agent)
        model_select.set_options([(m, m) for m in models])
        if models:
            model_select.value = models[0]

    def update_runs(self) -> None:
        new_runs = get_all_runs()
        table = self.query_one(DataTable)
        
        selected_id = None
        try:
            cursor_row = table.cursor_coordinate.row
            if cursor_row >= 0 and cursor_row < len(table.rows):
                selected_id = list(table.rows.keys())[cursor_row].value
        except: pass

        if self.runs != new_runs:
            self.runs = new_runs
            table.clear()
            status_styles = {"running": "yellow", "succeeded": "green", "failed": "red", "cancelled": "red"}
            for run in self.runs:
                state = run['state'].lower()
                status = f"[{status_styles.get(state, 'white')}]{state.upper()}"
                table.add_row(status, run['agent'].upper(), run['summary'], key=run['id'])
            
            if selected_id:
                try:
                    for i, key in enumerate(table.rows.keys()):
                        if key.value == selected_id:
                            table.move_cursor(row=i)
                            break
                except:
                    if self.runs: table.move_cursor(row=0)
            elif self.runs:
                 table.move_cursor(row=0)
        
        self.update_details()

    def update_details(self) -> None:
        table = self.query_one(DataTable)
        run_log_widget = self.query_one("#run-log")

        # Handle empty state or no selection
        if not self.runs or table.cursor_row < 0:
            self.query_one("#stat-id").update("-")
            self.query_one("#stat-model").update("-")
            self.query_one("#stat-branch").update("-")
            self.query_one("#stat-summary").update("-")
            run_log_widget.clear()
            self.selected_run = {}
            return

        idx = table.cursor_row
        if idx < len(self.runs):
            prev_run_id = self.selected_run.get('id')
            self.selected_run = self.runs[idx]
            curr_run_id = self.selected_run['id']
            
            self.query_one("#stat-id").update(curr_run_id)
            self.query_one("#stat-model").update(self.selected_run['model'])
            self.query_one("#stat-branch").update(self.selected_run['branch'] or "n/a")
            self.query_one("#stat-summary").update(f"Cost: ${self.selected_run['cost']:.4f} | Tokens: {self.selected_run['tokens']}")

            # If we switched runs, clear the log and reset position
            if prev_run_id != curr_run_id:
                run_log_widget.clear()
                self.log_positions[curr_run_id] = 0

            log_file = self.selected_run["dir"] / "stdout.log"
            if log_file.exists():
                pos = self.log_positions.get(curr_run_id, 0)
                try:
                    with open(log_file, "r", encoding="utf-8", errors="replace") as f:
                        f.seek(pos)
                        new_content = f.read()
                        if new_content:
                            # Use RichLog functionality if available, or stay with Log
                            run_log_widget.write(new_content)
                            self.log_positions[curr_run_id] = f.tell()
                except: pass

    def on_data_table_row_selected(self) -> None:
        self.update_details()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "launch-btn":
            self.action_submit_task()

    def action_submit_task(self) -> None:
        prompt = self.query_one("#prompt-input").value
        if not prompt:
            self.notify("Please enter a prompt", severity="error")
            return

        planner = self.query_one("#planner-select").value
        executor = self.query_one("#executor-select").value
        model = self.query_one("#model-select").value
        budget = self.query_one("#budget-select").value

        plan_dir = PROJECT_ROOT / "agent_artifacts" / planner / "temp"
        plan_dir.mkdir(parents=True, exist_ok=True)
        plan_file = plan_dir / f"dispatch_{int(time.time())}.md"
        plan_file.write_text(f"# Task\n{prompt}\n", encoding="utf-8")

        cmd = [
            f'"{sys.executable}"',
            f'"{PROJECT_ROOT / "agent_system" / "core" / "run_agent_plan.py"}"',
            "--planner", planner,
            "--executor", executor,
            "--planner-model", model, # Use the selected model
            "--thinking-budget", budget,
            "--plan-file", f'"{plan_file}"',
            "--task-summary", f'"{prompt[:50]}"',
            "--cleanup-worktree"
        ]
        
        cmd_str = " ".join(cmd)
        subprocess.Popen(
            cmd_str, 
            cwd=str(PROJECT_ROOT), 
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=0x00000008 if os.name == 'nt' else 0
        )
        
        self.query_one("#prompt-input").value = ""
        self.notify(f"Task dispatched: {model}")
        self.update_runs()

    def action_merge_run(self) -> None:
        if self.selected_run and self.selected_run.get("branch"):
            subprocess.run(["git", "merge", self.selected_run["branch"]], cwd=PROJECT_ROOT)
            self.notify("Merged successfully")
            self.update_runs()
            
    def action_kill_run(self) -> None:
        if self.selected_run and self.selected_run.get("pid"):
            if os.name == 'nt':
                os.system(f"taskkill /F /T /PID {self.selected_run['pid']} > nul 2>&1")
            self.notify("Process killed")
            self.update_runs()
            
    def action_delete_run(self) -> None:
        if self.selected_run:
            run_id = self.selected_run['id']
            agent = self.selected_run['agent']
            
            # 1. Remove the report directory
            shutil.rmtree(self.selected_run["dir"], ignore_errors=True)
            
            # 2. Attempt to remove the associated worktree directory
            worktree_dir = PROJECT_ROOT / "agent_artifacts" / agent / "temp" / "worktrees" / run_id.replace(":", "_")
            if worktree_dir.exists():
                # Force remove worktree from git first
                subprocess.run(["git", "worktree", "remove", "--force", str(worktree_dir)], cwd=PROJECT_ROOT, capture_output=True)
                shutil.rmtree(worktree_dir, ignore_errors=True)

            # 3. Delete the git branch
            if self.selected_run.get("branch"):
                subprocess.run(["git", "branch", "-D", self.selected_run["branch"]], cwd=PROJECT_ROOT, capture_output=True)
            
            # 4. Prune any stale worktree metadata
            subprocess.run(["git", "worktree", "prune"], cwd=PROJECT_ROOT, capture_output=True)

            self.notify("Artifacts & Worktree purged")
            self.update_runs()
            
    def action_maintenance(self) -> None:
        with self.suspend():
            os.system(f".venv/Scripts/python.exe agent_system/core/agent_maintenance.py")
            input("Press Enter to return...")

if __name__ == "__main__":
    app = AgentDashboardApp()
    app.run()
