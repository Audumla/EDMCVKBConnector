"""
agent_dashboard.py - Rich TUI with Coordinate-Locked Formatting.
"""
import curses
import json
import os
import signal
import time
import subprocess
import shutil
import locale
from pathlib import Path

# Force locale for Unicode
try:
    locale.setlocale(locale.LC_ALL, '')
except:
    pass

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
AGENT_TYPES = ["gemini", "claude", "codex", "opencode", "copilot"]

ICONS = {
    "running": "🚀",
    "succeeded": "✅",
    "failed": "❌",
    "cancelled": "⏹",
    "gemini": "♊",
    "claude": "🎭",
    "codex": "🤖",
    "opencode": "🔓",
    "copilot": "👨‍✈️",
}

class EnhancedDashboard:
    def __init__(self):
        self.runs = []
        self.selected_index = 0
        self.log_scroll_offset = 0
        self.running = True
        self.message = " System Ready "
        self.confirm_delete = False

    def get_all_runs(self):
        all_runs = []
        for agent in AGENT_TYPES:
            output_root = PROJECT_ROOT / "agent_artifacts" / agent / "reports" / "plan_runs"
            if output_root.exists():
                for p in output_root.iterdir():
                    status_file = p / "status.json"
                    meta_file = p / "metadata.json"
                    if status_file.exists():
                        try:
                            status = json.loads(status_file.read_text(encoding="utf-8-sig"))
                            meta = json.loads(meta_file.read_text(encoding="utf-8-sig")) if meta_file.exists() else {}
                            mtime = max(p.stat().st_mtime, status_file.stat().st_mtime)
                            all_runs.append({
                                "id": p.name,
                                "agent": agent,
                                "dir": p,
                                "state": status.get("state", "unknown"),
                                "pid": status.get("pid"),
                                "model": status.get("cost_estimate", {}).get("model", "n/a"),
                                "cost": float(status.get("cost_estimate", {}).get("total_usd") or 0.0),
                                "tokens": int(status.get("token_usage", {}).get("output_tokens") or 0),
                                "branch": meta.get("isolation", {}).get("branch_name"),
                                "summary": meta.get("task_summary", "No summary"),
                                "mtime": mtime
                            })
                        except: pass
        all_runs.sort(key=lambda x: x["mtime"], reverse=True)
        return all_runs[:25]

    def run(self, stdscr):
        try:
            curses.start_color()
            curses.use_default_colors()
            curses.init_pair(1, curses.COLOR_GREEN, -1)
            curses.init_pair(2, curses.COLOR_CYAN, -1)
            curses.init_pair(3, curses.COLOR_RED, -1)
            curses.init_pair(4, curses.COLOR_YELLOW, -1)
        except: pass

        curses.curs_set(0)
        stdscr.nodelay(True)
        stdscr.timeout(500)

        while self.running:
            try:
                self.runs = self.get_all_runs()
                h, w = stdscr.getmaxyx()
                stdscr.clear()
                
                if w < 110 or h < 15:
                    stdscr.addstr(h//2, max(0, (w-35)//2), "Terminal too small (min 110x15)")
                    stdscr.refresh()
                    ch = stdscr.getch()
                    if ch == ord('q'): self.running = False
                    continue

                sidebar_w = 60
                content_x = sidebar_w + 4
                
                # --- Drawing the Frame ---
                stdscr.attron(curses.color_pair(2))
                # Horizontal lines
                stdscr.addstr(1, 1, "┌" + ("─" * (sidebar_w-2)) + "┐ ┌" + ("─" * (w - sidebar_w - 7)) + "┐")
                stdscr.addstr(h-2, 1, "└" + ("─" * (sidebar_w-2)) + "┘ └" + ("─" * (w - sidebar_w - 7)) + "┘")
                # Vertical bars
                for y in range(2, h-2):
                    stdscr.addstr(y, 1, "│")
                    stdscr.addstr(y, sidebar_w, "│")
                    stdscr.addstr(y, sidebar_w + 2, "│")
                    stdscr.addstr(y, w-2, "│")
                stdscr.attroff(curses.color_pair(2))

                # --- Header ---
                sync_time = time.strftime("%H:%M:%S")
                stdscr.addstr(0, (w-30)//2, f" 🤖 AGENT COMMAND CENTER ({sync_time}) ", curses.A_BOLD | curses.color_pair(2))
                stdscr.addstr(1, 3, " RUN NAVIGATOR ", curses.color_pair(2))
                stdscr.addstr(1, sidebar_w + 4, " EXECUTION LOGS ", curses.color_pair(2))

                # --- Sidebar Content ---
                for i, run in enumerate(self.runs):
                    y = i + 2
                    if y >= h - 2: break
                    attr = curses.A_REVERSE if i == self.selected_index else curses.A_NORMAL
                    
                    st_color = curses.color_pair(1) if run["state"] in ("running", "succeeded") else curses.color_pair(5)
                    if run["state"] in ("failed", "cancelled"): st_color = curses.color_pair(3)
                    
                    icon = ICONS.get(run["state"], "?")
                    agent = ICONS.get(run["agent"], "🤖")
                    
                    # Manual summary truncation to ensure no bar-drift
                    sum_w = sidebar_w - 15
                    summary = run['summary'][:sum_w]
                    label = f" {icon} | {agent} | {summary}"
                    
                    # Fill row background completely
                    stdscr.addstr(y, 2, " " * (sidebar_w-2), attr)
                    stdscr.addstr(y, 2, label[:sidebar_w-2], attr | st_color)

                # --- Details Content ---
                if self.runs:
                    sel = self.runs[self.selected_index]
                    dw = w - content_x - 3
                    
                    stdscr.addnstr(2, content_x, f"ID: {sel['id']}", dw, curses.A_BOLD)
                    stdscr.addnstr(3, content_x, f"Model:  {sel['model']}", dw, curses.A_DIM)
                    stdscr.addnstr(4, content_x, f"Branch: {sel['branch'] or 'n/a'}", dw, curses.color_pair(4))
                    stats = f"Cost: ${sel['cost']:.4f} | Tokens: {sel['tokens']}"
                    stdscr.addnstr(5, content_x, stats, dw, curses.color_pair(1))
                    stdscr.addstr(6, content_x, "-" * dw, curses.color_pair(2))

                    log_file = sel["dir"] / "stdout.log"
                    if log_file.exists():
                        lines = log_file.read_text(encoding="utf-8", errors="replace").splitlines()
                        visible_h = h - 10
                        start = max(0, len(lines) - visible_h - self.log_scroll_offset)
                        end = max(0, len(lines) - self.log_scroll_offset)
                        if end == 0 and lines: end = len(lines)
                        
                        for k, line in enumerate(lines[start:end]):
                            if k + 7 < h - 2:
                                stdscr.addnstr(k + 7, content_x, line, dw)

                # --- Footer ---
                f_color = curses.color_pair(3) if self.confirm_delete else curses.A_REVERSE
                help_line = "[M] Merge | [K] Kill | [DEL] Purge | [C] Maint | [Q] Quit"
                footer = f" 💬 {self.message} ".ljust(w-len(help_line)-2) + help_line
                stdscr.addnstr(h-1, 0, footer, w-1, f_color)

                stdscr.refresh()

                # --- Input ---
                ch = stdscr.getch()
                if ch == ord('q'): self.running = False
                elif ch == ord('c'):
                    curses.endwin()
                    os.system(f".venv\\Scripts\\python.exe scripts/agent_runners/agent_maintenance.py")
                    input("\nPress Enter to return...")
                    stdscr.refresh()
                elif ch == curses.KEY_UP: self.selected_index = max(0, self.selected_index - 1)
                elif ch == curses.KEY_DOWN: self.selected_index = min(len(self.runs) - 1, self.selected_index + 1)
                elif ch == ord('k'):
                    sel = self.runs[self.selected_index]
                    if sel["state"] == "running" and sel["pid"]:
                        os.system(f"taskkill /F /T /PID {sel['pid']} > nul 2>&1")
                        self.message = f" Killed {sel['id']} "
                elif ch == ord('m'):
                    sel = self.runs[self.selected_index]
                    if sel["branch"]:
                        self.message = " Merging... "
                        subprocess.run(["git", "merge", sel["branch"]], capture_output=True, cwd=str(PROJECT_ROOT))
                        self.message = " Merged "
                elif ch in (curses.KEY_DC, ord('\x7f')):
                    if not self.confirm_delete:
                        self.confirm_delete = True
                        self.message = " CONFIRM PURGE (DEL) "
                    else:
                        sel = self.runs[self.selected_index]
                        if sel["state"] == "running" and sel["pid"]: os.system(f"taskkill /F /T /PID {sel['pid']} > nul 2>&1")
                        if sel["branch"]: subprocess.run(["git", "branch", "-D", sel["branch"]], capture_output=True, cwd=str(PROJECT_ROOT))
                        shutil.rmtree(sel["dir"], ignore_errors=True)
                        self.message = f" Purged {sel['id']} "
                        self.confirm_delete = False
                else:
                    if self.confirm_delete and ch != -1:
                        self.confirm_delete = False
                        self.message = " Ready "
            except Exception as e:
                self.message = f" Error: {str(e)[:20]} "
                time.sleep(0.1)

if __name__ == "__main__":
    dash = EnhancedDashboard()
    curses.wrapper(dash.run)
