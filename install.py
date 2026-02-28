#!/usr/bin/env python3
"""
install.py - Portable installer and manager for the agent-system.

This script is the single entry point for installing, updating, starting, and
uninstalling the agent system. It is intentionally written in pure Python stdlib
so it can run before a virtual environment exists.

Usage
-----
  # Install into current workspace (auto-detects runtime dir)
  python install.py install

  # Install pointing at a specific workspace
  python install.py install --workspace /path/to/my/project

  # Install from a fresh clone into a custom location
  python install.py install --runtime-dir ~/.agent-system/runtime --workspace .

  # Pull the latest agent-system code and upgrade dependencies
  python install.py update

  # Launch the dashboard against a workspace
  python install.py start --workspace .

  # Remove agent-system integration from a workspace (leaves runtime intact)
  python install.py uninstall --workspace .

  # Remove integration AND the runtime directory
  python install.py uninstall --workspace . --remove-runtime
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DEFAULT_STATE_HOME = Path.home() / ".agent-system"
DEFAULT_RUNTIME_DIR = DEFAULT_STATE_HOME / "runtime"
AGENT_SYSTEM_JSON = ".vscode/agent-system.json"
AGENT_MD_PATH = "AGENT.md"   # workspace-level guide for AI agents

# Changelog seed files to create in a fresh workspace so the target project
# can start tracking them immediately.
CHANGELOG_SEED_DIRS = [
    "agent_system/reporting/data",
]
CHANGELOG_SEED_FILES = {
    "agent_system/CHANGELOG.md": "# Changelog\n\nNo entries yet.\n",
    "agent_system/reporting/data/CHANGELOG.json": "[]\n",
    "agent_system/reporting/data/CHANGELOG.archive.json": "[]\n",
    "agent_system/reporting/data/CHANGELOG.summaries.json": "[]\n",
}


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

def _this_file() -> Path:
    return Path(__file__).resolve()


def _runtime_root_from_script() -> Path:
    """The runtime dir is the directory containing this install.py."""
    return _this_file().parent


def _venv_python(runtime_dir: Path) -> Path:
    if os.name == "nt":
        return runtime_dir / ".venv" / "Scripts" / "python.exe"
    return runtime_dir / ".venv" / "bin" / "python"


def _inside_runtime_repo(runtime_dir: Path) -> bool:
    """True when this install.py is already inside the runtime git repo."""
    return _this_file().is_relative_to(runtime_dir)


# ---------------------------------------------------------------------------
# Core operations
# ---------------------------------------------------------------------------

def _git(args: list[str], cwd: Path, check: bool = True) -> subprocess.CompletedProcess:
    """Run a git command confined to *cwd* — never touches any other repo."""
    return subprocess.run(["git", "-C", str(cwd)] + args, check=check,
                          capture_output=True, text=True)


def cmd_install(args: argparse.Namespace) -> int:
    workspace = Path(args.workspace).expanduser().resolve()
    runtime_dir = Path(args.runtime_dir).expanduser().resolve()
    state_home = Path(args.state_home).expanduser().resolve()

    print(f"[agent-system] Runtime dir : {runtime_dir}")
    print(f"[agent-system] Workspace   : {workspace}")
    print(f"[agent-system] State home  : {state_home}")

    # 1. Clone if not already there
    if not _inside_runtime_repo(runtime_dir):
        if runtime_dir.exists() and any(runtime_dir.iterdir()):
            print(f"[agent-system] Runtime dir already exists, skipping clone.")
        else:
            repo_url = args.repo_url or _detect_origin()
            if not repo_url:
                print(
                    "[agent-system] ERROR: Cannot determine git origin URL.\n"
                    "  Pass --repo-url <url> or run from inside the cloned repo.",
                    file=sys.stderr,
                )
                return 1
            print(f"[agent-system] Cloning {repo_url} -> {runtime_dir} ...")
            runtime_dir.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(["git", "clone", repo_url, str(runtime_dir)], check=True)
    else:
        print("[agent-system] Running from inside the runtime repo — skipping clone.")

    # 2. Install dependencies into venv
    _install_deps(runtime_dir, force=args.force)

    # 3. Inject .vscode/tasks.json
    _inject_tasks(workspace, runtime_dir)

    # 4. Inject .gitignore block
    _inject_gitignore(workspace)

    # 5. Write machine-local .vscode/agent-system.json
    _write_local_config(workspace, runtime_dir, state_home)

    # 6. Seed changelog files in target workspace
    _seed_changelog(workspace)

    # 6b. Write/refresh AGENT.md — tells agents where artifacts go and how to log changes
    _seed_agent_md(workspace, runtime_dir, state_home)

    # 7. Provider detection + optional interactive selection
    if not args.skip_providers:
        enabled = _run_provider_setup(workspace, runtime_dir, interactive=not args.no_interactive)

        # 8. Auth check for enabled providers
        if enabled and not args.no_interactive:
            _run_auth_check(enabled, workspace, interactive=True)

    print("\n[agent-system] Installation complete.")
    print(f"  Dashboard : python \"{runtime_dir / 'install.py'}\" start --workspace \"{workspace}\"")
    print(f"  Update    : python \"{runtime_dir / 'install.py'}\" update")
    return 0


def cmd_update(args: argparse.Namespace) -> int:
    runtime_dir = Path(args.runtime_dir).expanduser().resolve()

    if not runtime_dir.exists():
        print(f"[agent-system] ERROR: Runtime dir not found: {runtime_dir}", file=sys.stderr)
        return 1

    # Get current commit hash for the diff summary
    before = _git(["rev-parse", "--short", "HEAD"], cwd=runtime_dir, check=False)
    before_hash = before.stdout.strip() if before.returncode == 0 else "unknown"

    print(f"[agent-system] Fetching updates (current: {before_hash}) ...")
    fetch = _git(["fetch", "origin"], cwd=runtime_dir, check=False)
    if fetch.returncode != 0:
        print(f"[agent-system] WARNING: fetch failed: {fetch.stderr.strip()}", file=sys.stderr)

    pull = _git(["pull", "--ff-only", "origin", "main"], cwd=runtime_dir, check=False)
    if pull.returncode != 0:
        # Try 'master' as a fallback branch name
        pull = _git(["pull", "--ff-only", "origin", "master"], cwd=runtime_dir, check=False)
    if pull.returncode != 0:
        print(
            "[agent-system] ERROR: Cannot fast-forward. There may be local modifications.\n"
            f"  {pull.stderr.strip()}",
            file=sys.stderr,
        )
        return 1

    after = _git(["rev-parse", "--short", "HEAD"], cwd=runtime_dir, check=False)
    after_hash = after.stdout.strip() if after.returncode == 0 else "unknown"

    if before_hash == after_hash:
        print("[agent-system] Already up to date.")
    else:
        print(f"[agent-system] Updated: {before_hash} -> {after_hash}")

    # Re-install dependencies in case requirements.txt changed
    print("[agent-system] Upgrading dependencies ...")
    _install_deps(runtime_dir, force=False, upgrade=True)

    print("[agent-system] Update complete.")
    return 0


def cmd_start(args: argparse.Namespace) -> int:
    workspace = Path(args.workspace).expanduser().resolve()
    runtime_dir = _resolve_runtime_dir(workspace, args)
    state_home = Path(args.state_home).expanduser().resolve()

    # Delegate to the existing manage_runtime.start_dashboard logic
    manage = runtime_dir / "scripts" / "agent_runners" / "manage_runtime.py"
    if not manage.exists():
        print(f"[agent-system] ERROR: manage_runtime.py not found at {manage}", file=sys.stderr)
        return 1

    cmd = [
        str(_venv_python(runtime_dir)),
        str(manage),
        "start",
        "--workspace", str(workspace),
        "--state-home", str(state_home),
    ]
    if args.web:
        cmd.append("--web")

    env = os.environ.copy()
    env["AGENT_WORKSPACE_ROOT"] = str(workspace)
    env["AGENT_STATE_HOME"] = str(state_home)

    return subprocess.run(cmd, env=env).returncode


def cmd_uninstall(args: argparse.Namespace) -> int:
    workspace = Path(args.workspace).expanduser().resolve()
    runtime_dir = _resolve_runtime_dir(workspace, args)

    print(f"[agent-system] Removing integration from: {workspace}")

    # Remove injected VS Code tasks
    _remove_tasks(workspace)

    # Remove .gitignore block
    _remove_gitignore(workspace)

    # Remove machine-local config
    local_cfg = workspace / AGENT_SYSTEM_JSON
    if local_cfg.exists():
        local_cfg.unlink()
        print(f"  Removed {AGENT_SYSTEM_JSON}")

    if args.remove_runtime:
        if runtime_dir.exists():
            shutil.rmtree(runtime_dir)
            print(f"  Removed runtime: {runtime_dir}")

    print("[agent-system] Uninstall complete.")
    return 0


def cmd_detect(args: argparse.Namespace) -> int:
    """Detect installed providers and optionally update delegation-config.json."""
    workspace = Path(args.workspace).expanduser().resolve()
    runtime_dir = _resolve_runtime_dir(workspace, args)

    _run_provider_setup(
        workspace, runtime_dir,
        interactive=not args.no_interactive,
        report_only=args.report_only,
    )
    return 0


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _run_provider_setup(
    workspace: Path,
    runtime_dir: Path,
    interactive: bool = True,
    report_only: bool = False,
) -> list:
    """Run provider detection, print a report, optionally select, and update config.

    Returns the list of enabled provider names, or [] on early exit.
    """
    try:
        sys.path.insert(0, str(_runtime_root_from_script() / "scripts" / "agent_runners"))
        from provider_detect import (
            detect_all,
            print_detection_report,
            interactive_select,
            apply_to_config,
        )
    except ImportError as exc:
        print(f"  WARNING: Could not load provider_detect module: {exc}", file=sys.stderr)
        return []

    print("[agent-system] Detecting installed AI providers ...")
    results = detect_all()
    print_detection_report(results)

    if report_only:
        return []

    # Determine which providers to enable
    if interactive:
        enabled = interactive_select(results)
    else:
        # Non-interactive: enable all detected providers
        enabled = [r.spec.name for r in results if r.available]
        found_names = ", ".join(enabled) if enabled else "none"
        print(f"  Auto-enabling detected providers: {found_names}")

    # Find delegation-config.json: prefer workspace copy, fall back to runtime
    workspace_config = workspace / "agent_system" / "config" / "delegation-config.json"
    runtime_config = runtime_dir / "agent_system" / "config" / "delegation-config.json"
    config_path = workspace_config if workspace_config.exists() else runtime_config

    if config_path.exists():
        changed = apply_to_config(config_path, enabled, results)
        if changed:
            print(f"  Updated provider config: {config_path}")
        else:
            print(f"  Provider config unchanged: {config_path}")
    else:
        print(f"  WARNING: delegation-config.json not found — skipping config update.",
              file=sys.stderr)

    return enabled


def _run_auth_check(enabled: list, workspace: Path, interactive: bool = True) -> None:
    """Check authentication for the given providers and optionally guide setup."""
    try:
        sys.path.insert(0, str(_runtime_root_from_script() / "scripts" / "agent_runners"))
        from auth_check import check_all, print_auth_report, guided_setup, ensure_secrets_gitignored
    except ImportError as exc:
        print(f"  WARNING: Could not load auth_check module: {exc}", file=sys.stderr)
        return

    print("\n[agent-system] Checking provider authentication ...")
    results = check_all(enabled, workspace=workspace)
    print_auth_report(results)

    if interactive:
        guided_setup(results, workspace=workspace)

    # Ensure .agent-secrets.env is gitignored in the workspace
    ensure_secrets_gitignored(workspace)


def cmd_auth(args: argparse.Namespace) -> int:
    """Check authentication state for all (or selected) providers."""
    workspace = Path(args.workspace).expanduser().resolve()

    try:
        sys.path.insert(0, str(_runtime_root_from_script() / "scripts" / "agent_runners"))
        from auth_check import (
            AUTH_SPECS,
            check_all,
            print_auth_report,
            guided_setup,
            ensure_secrets_gitignored,
        )
    except ImportError as exc:
        print(f"[agent-system] ERROR: Could not load auth_check module: {exc}", file=sys.stderr)
        return 1

    provider_names = args.providers if args.providers else [s.name for s in AUTH_SPECS]
    results = check_all(provider_names, workspace=workspace)
    print_auth_report(results)

    if args.fix and not args.report_only:
        guided_setup(results, workspace=workspace)
        ensure_secrets_gitignored(workspace)

    # Exit non-zero if any provider failed auth (useful for CI / pre-flight checks)
    if any(r.checked and not r.authenticated for r in results):
        return 2
    return 0


def _resolve_runtime_dir(workspace: Path, args: argparse.Namespace) -> Path:
    """Resolve the runtime directory: explicit arg > local config > this file's location."""
    if args.runtime_dir != str(DEFAULT_RUNTIME_DIR):
        return Path(args.runtime_dir).expanduser().resolve()
    local_cfg = workspace / AGENT_SYSTEM_JSON
    if local_cfg.exists():
        try:
            data = json.loads(local_cfg.read_text(encoding="utf-8"))
            rd = data.get("runtimeDir")
            if rd:
                return Path(rd).expanduser().resolve()
        except Exception:
            pass
    return _runtime_root_from_script()


def _detect_origin() -> str | None:
    """Try to find the git remote URL of the repo containing this file."""
    result = subprocess.run(
        ["git", "-C", str(_this_file().parent), "remote", "get-url", "origin"],
        capture_output=True, text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def _install_deps(runtime_dir: Path, force: bool = False, upgrade: bool = False) -> None:
    venv_dir = runtime_dir / ".venv"
    venv_py = _venv_python(runtime_dir)
    requirements = runtime_dir / "requirements.txt"

    if force and venv_dir.exists():
        shutil.rmtree(venv_dir)

    if not venv_py.exists():
        print("[agent-system] Creating virtual environment ...")
        subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], check=True)

    pip_cmd = [str(venv_py), "-m", "pip", "install", "--upgrade", "pip"]
    subprocess.run(pip_cmd, check=True, capture_output=True)

    install_cmd = [str(venv_py), "-m", "pip", "install", "-r", str(requirements)]
    if upgrade:
        install_cmd.append("--upgrade")
    subprocess.run(install_cmd, check=True)
    print("[agent-system] Dependencies installed.")


def _inject_tasks(workspace: Path, runtime_dir: Path) -> None:
    try:
        sys.path.insert(0, str(_runtime_root_from_script() / "scripts" / "agent_runners"))
        from vscode_tasks import inject_tasks
        labels = inject_tasks(workspace, runtime_dir)
        print(f"  VS Code tasks injected/updated: {len(labels)}")
    except Exception as exc:
        print(f"  WARNING: Could not inject VS Code tasks: {exc}", file=sys.stderr)


def _remove_tasks(workspace: Path) -> None:
    try:
        sys.path.insert(0, str(_runtime_root_from_script() / "scripts" / "agent_runners"))
        from vscode_tasks import remove_tasks
        labels = remove_tasks(workspace)
        if labels:
            print(f"  Removed {len(labels)} VS Code tasks.")
    except Exception as exc:
        print(f"  WARNING: Could not remove VS Code tasks: {exc}", file=sys.stderr)


def _inject_gitignore(workspace: Path) -> None:
    try:
        sys.path.insert(0, str(_runtime_root_from_script() / "scripts" / "agent_runners"))
        from gitignore_inject import inject_gitignore
        changed = inject_gitignore(workspace)
        print(f"  .gitignore: {'block injected' if changed else 'block already up to date'}.")
    except Exception as exc:
        print(f"  WARNING: Could not update .gitignore: {exc}", file=sys.stderr)


def _remove_gitignore(workspace: Path) -> None:
    try:
        sys.path.insert(0, str(_runtime_root_from_script() / "scripts" / "agent_runners"))
        from gitignore_inject import remove_gitignore
        changed = remove_gitignore(workspace)
        print(f"  .gitignore: {'block removed' if changed else 'no block found'}.")
    except Exception as exc:
        print(f"  WARNING: Could not update .gitignore: {exc}", file=sys.stderr)


def _build_agent_md(workspace: Path, runtime_dir: Path, state_home: Path) -> str:
    """Generate the AGENT.md content for a given workspace installation."""
    import hashlib
    ws_key_raw = str(workspace).lower().encode("utf-8")
    ws_key = workspace.name + "-" + hashlib.sha1(ws_key_raw).hexdigest()[:10]
    artifacts_root = state_home / "workspaces" / ws_key / "agent_artifacts"
    changelog_json = workspace / "agent_system" / "reporting" / "data" / "CHANGELOG.json"
    changelog_md   = workspace / "agent_system" / "CHANGELOG.md"
    log_change_cmd = str(runtime_dir / "agent_system" / "reporting" / "log_change.py")
    run_agent_cmd  = str(runtime_dir / "agent_system" / "core" / "run_agent_plan.py")
    venv_py        = str(runtime_dir / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python"))

    return f"""\
# Agent Guide

This file is auto-generated by the agent-system installer.
It tells every AI agent working in this workspace where to put files and how to
record changes. **Do not delete this file.** Re-run `install.py install` to refresh it.

---

## Workspace and Runtime Paths

| Variable | Value |
|---|---|
| Workspace root | `{workspace}` |
| Runtime root | `{runtime_dir}` |
| Venv Python | `{venv_py}` |
| Artifact storage | `{artifacts_root}` |
| Changelog JSON | `{changelog_json}` |
| Changelog Markdown | `{changelog_md}` |

The path resolver (`runtime_paths.py`) picks up the workspace automatically from the
`AGENT_WORKSPACE_ROOT` environment variable.  The dashboard and VS Code tasks set this
variable before launching any agent, so agents should not hard-code it.

---

## Artifact Storage

Agents **must not** write run outputs into the workspace git tree.
All artifacts go under:

```
{artifacts_root}/<agent-type>/reports/plan_runs/<run-id>/
```

Where:
- `<agent-type>` is the executor name: `claude`, `gemini`, `codex`, `opencode`,
  `copilot`, `cline`, `ollama`, `lmstudio`
- `<run-id>` is `YYYYMMDDTHHMMSSZ_<slug>` (generated by the runner)

Each run directory contains:
| File | Purpose |
|---|---|
| `plan_input.md` | The plan as received |
| `stdout.log` | Raw agent output |
| `status.json` | Live state (`state`, `phase`, `started_at`, `ended_at`) |
| `metadata.json` | Model, cost, branch, task summary |

Temporary planning files belong in `{artifacts_root}/claude/temp/` (or the
equivalent for your agent type) and should be cleaned up after delegation.

---

## Changelog Policy

**Every meaningful change must be recorded.** Use the log_change script — do not
edit `CHANGELOG.json` or `CHANGELOG.md` by hand.

### Quick command

```bash
AGENT_WORKSPACE_ROOT="{workspace}" \\
  "{venv_py}" "{log_change_cmd}" \\
  --agent <agent-name> \\
  --group <WorkstreamSlug> \\
  --tags "New Feature" \\
  --summary "One-sentence description" \\
  --details "First bullet" "Second bullet"
```

### Approved `--tags` values

```
Bug Fix          New Feature        Code Refactoring     Configuration Cleanup
Dependency Update   Documentation Update   Test Update
Performance Improvement   UI Improvement   Build / Packaging
```

### Approved `--agent` values

```
claude   gemini   codex   opencode   copilot   cline   ollama   lmstudio
```

### Changelog file locations

- JSON source of truth: `{changelog_json}`
- Rendered Markdown:    `{changelog_md}`

Both files live inside the **workspace** git tree so they are tracked by the project.
The runtime directory does not own changelog data.

---

## Delegation Protocol

To hand off work to another agent, write a plan file and call `run_agent_plan.py`:

```bash
# Write your plan to:
{artifacts_root}/claude/temp/plan.md

# Then execute:
"{venv_py}" "{run_agent_cmd}" \\
  --planner <planner> \\
  --executor <executor> \\
  --thinking-budget <none|low|medium|high> \\
  --plan-file "{artifacts_root}/claude/temp/plan.md" \\
  --cleanup-worktree \\
  --task-summary "Agent: <short description>"
```

### Inline dispatch tags (CLAUDE.md shorthand)

| Tag | Example | Effect |
|---|---|---|
| `#plan <provider>` | `#plan gemini` | Sets the planning agent |
| `#exec <provider>` | `#exec codex` | Sets the executor |
| `#budget <level>` | `#budget high` | Sets thinking budget |

Valid providers: `claude`, `gemini`, `codex`, `opencode`, `copilot`, `cline`,
`ollama`, `lmstudio` (subject to `delegation-config.json` enabled flags).

---

## Environment Variables

| Variable | Purpose | Default |
|---|---|---|
| `AGENT_WORKSPACE_ROOT` | Workspace being operated on | cwd |
| `AGENT_STATE_HOME` | Root of all agent state | `~/.agent-system` |

The dashboard and `install.py start` set these automatically.
When running scripts directly, set `AGENT_WORKSPACE_ROOT` explicitly.
"""


def _seed_agent_md(workspace: Path, runtime_dir: Path, state_home: Path) -> None:
    """Write AGENT.md to the workspace (always regenerated — it's machine-local content)."""
    dest = workspace / AGENT_MD_PATH
    content = _build_agent_md(workspace, runtime_dir, state_home)
    dest.write_text(content, encoding="utf-8")
    print(f"  Wrote {AGENT_MD_PATH}")


def _write_local_config(workspace: Path, runtime_dir: Path, state_home: Path) -> None:
    import hashlib
    ws_key_raw = str(workspace).lower().encode("utf-8")
    ws_key = workspace.name + "-" + hashlib.sha1(ws_key_raw).hexdigest()[:10]
    artifacts_root = state_home / "workspaces" / ws_key / "agent_artifacts"

    cfg_path = workspace / AGENT_SYSTEM_JSON
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "runtimeDir": str(runtime_dir),
        "stateHome": str(state_home),
        "artifactsRoot": str(artifacts_root),
        "changelogJson": str(workspace / "agent_system" / "reporting" / "data" / "CHANGELOG.json"),
        "changelogMd": str(workspace / "agent_system" / "CHANGELOG.md"),
        "logChangeScript": str(runtime_dir / "agent_system" / "reporting" / "log_change.py"),
        "venvPython": str(runtime_dir / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")),
        "_note": "Machine-local config — do not commit. Regenerated by install.py.",
    }
    cfg_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"  Wrote {AGENT_SYSTEM_JSON}")


def _seed_changelog(workspace: Path) -> None:
    """Create empty changelog stubs in the workspace if they don't exist."""
    for d in CHANGELOG_SEED_DIRS:
        (workspace / d).mkdir(parents=True, exist_ok=True)
    for rel, content in CHANGELOG_SEED_FILES.items():
        dest = workspace / rel
        if not dest.exists():
            dest.write_text(content, encoding="utf-8")
            print(f"  Created {rel}")


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="install.py",
        description="Portable installer and manager for the agent-system.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # ---- install ----
    p_install = sub.add_parser("install", help="Install agent-system into a workspace")
    p_install.add_argument("--workspace", default=str(Path.cwd()),
                           help="Target workspace path (default: cwd)")
    p_install.add_argument("--runtime-dir", default=str(DEFAULT_RUNTIME_DIR),
                           help=f"Where to install the runtime (default: {DEFAULT_RUNTIME_DIR})")
    p_install.add_argument("--state-home", default=str(DEFAULT_STATE_HOME),
                           help=f"Agent state root (default: {DEFAULT_STATE_HOME})")
    p_install.add_argument("--repo-url", default=None,
                           help="Git URL to clone from (auto-detected if running from inside the repo)")
    p_install.add_argument("--force", action="store_true",
                           help="Recreate the virtual environment from scratch")
    p_install.add_argument("--no-interactive", action="store_true",
                           help="Skip interactive prompts; auto-enable all detected providers")
    p_install.add_argument("--skip-providers", action="store_true",
                           help="Skip provider detection entirely")

    # ---- detect ----
    p_detect = sub.add_parser("detect", help="Detect installed AI providers and update config")
    p_detect.add_argument("--workspace", default=str(Path.cwd()),
                          help="Target workspace path (default: cwd)")
    p_detect.add_argument("--runtime-dir", default=str(DEFAULT_RUNTIME_DIR),
                          help="Runtime directory")
    p_detect.add_argument("--no-interactive", action="store_true",
                          help="Print report only; auto-enable all detected providers without prompting")
    p_detect.add_argument("--report-only", action="store_true",
                          help="Print the detection report but do not modify any config")

    # ---- update ----
    p_update = sub.add_parser("update", help="Pull latest agent-system code and upgrade deps")
    p_update.add_argument("--runtime-dir", default=str(DEFAULT_RUNTIME_DIR),
                          help=f"Runtime directory to update (default: {DEFAULT_RUNTIME_DIR})")

    # ---- start ----
    p_start = sub.add_parser("start", help="Launch the agent dashboard")
    p_start.add_argument("--workspace", default=str(Path.cwd()),
                         help="Target workspace path (default: cwd)")
    p_start.add_argument("--runtime-dir", default=str(DEFAULT_RUNTIME_DIR),
                         help="Runtime directory (auto-detected from .vscode/agent-system.json if present)")
    p_start.add_argument("--state-home", default=str(DEFAULT_STATE_HOME),
                         help="Agent state root")
    p_start.add_argument("--web", action="store_true",
                         help="Launch in browser mode (requires textual-dev)")

    # ---- auth ----
    p_auth = sub.add_parser("auth", help="Check (and optionally fix) provider authentication")
    p_auth.add_argument("--workspace", default=str(Path.cwd()),
                        help="Target workspace path (used for .agent-secrets.env location)")
    p_auth.add_argument("providers", nargs="*",
                        help="Provider names to check (default: all configured providers)")
    p_auth.add_argument("--fix", action="store_true",
                        help="Interactively prompt to resolve missing credentials")
    p_auth.add_argument("--report-only", action="store_true",
                        help="Print report and exit without attempting fixes")

    # ---- uninstall ----
    p_uninstall = sub.add_parser("uninstall", help="Remove agent-system integration from a workspace")
    p_uninstall.add_argument("--workspace", default=str(Path.cwd()),
                             help="Target workspace to clean up")
    p_uninstall.add_argument("--runtime-dir", default=str(DEFAULT_RUNTIME_DIR),
                             help="Runtime directory")
    p_uninstall.add_argument("--remove-runtime", action="store_true",
                             help="Also delete the runtime directory entirely")

    return parser


def main() -> int:
    args = _build_parser().parse_args()
    dispatch = {
        "install": cmd_install,
        "update": cmd_update,
        "start": cmd_start,
        "uninstall": cmd_uninstall,
        "detect": cmd_detect,
        "auth": cmd_auth,
    }
    return dispatch[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
