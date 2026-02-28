#!/usr/bin/env python3
"""Cross-platform runtime installer/launcher for the agent dashboard."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


def runtime_root() -> Path:
    return Path(__file__).resolve().parents[2]


def venv_python(root: Path) -> Path:
    if os.name == "nt":
        return root / ".venv" / "Scripts" / "python.exe"
    return root / ".venv" / "bin" / "python"


def venv_textual(root: Path) -> Path:
    if os.name == "nt":
        return root / ".venv" / "Scripts" / "textual.exe"
    return root / ".venv" / "bin" / "textual"


def install_runtime(force_reinstall: bool = False, with_web: bool = False) -> None:
    root = runtime_root()
    venv_dir = root / ".venv"
    venv_py = venv_python(root)
    requirements = root / "requirements.txt"

    if force_reinstall and venv_dir.exists():
        shutil.rmtree(venv_dir)

    if not venv_py.exists():
        print("[agent-system] Creating virtual environment...")
        subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], check=True)

    print("[agent-system] Installing dependencies...")
    subprocess.run([str(venv_py), "-m", "pip", "install", "--upgrade", "pip"], check=True)
    subprocess.run([str(venv_py), "-m", "pip", "install", "-r", str(requirements)], check=True)
    if with_web:
        print("[agent-system] Installing Textual browser tooling...")
        subprocess.run([str(venv_py), "-m", "pip", "install", "textual-dev"], check=True)
    print("[agent-system] Runtime install complete.")


def start_dashboard(workspace: str, state_home: str, web: bool = False) -> int:
    root = runtime_root()
    venv_py = venv_python(root)
    textual_cli = venv_textual(root)
    dashboard_script = root / "agent_system" / "dashboard" / "agent_dashboard.py"

    if not venv_py.exists():
        raise FileNotFoundError(f"Runtime venv not found at {venv_py}. Run install first.")
    if not dashboard_script.exists():
        raise FileNotFoundError(f"Dashboard script not found: {dashboard_script}")

    resolved_workspace = Path(workspace).expanduser().resolve()
    resolved_state_home = Path(state_home).expanduser().resolve()
    resolved_state_home.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env["AGENT_WORKSPACE_ROOT"] = str(resolved_workspace)
    env["AGENT_STATE_HOME"] = str(resolved_state_home)

    print(f"[agent-system] Workspace: {resolved_workspace}")
    print(f"[agent-system] State home: {resolved_state_home}")
    if web:
        if not textual_cli.exists():
            raise FileNotFoundError(
                f"Textual CLI not found at {textual_cli}. "
                "Install browser mode support with: "
                "python scripts/agent_runners/manage_runtime.py install --with-web"
            )
        print("[agent-system] Launching dashboard in browser mode...")
        command = [str(textual_cli), "serve", str(dashboard_script)]
    else:
        print("[agent-system] Launching dashboard...")
        command = [str(venv_py), str(dashboard_script)]

    return subprocess.run(command, cwd=str(root), env=env).returncode


def bootstrap(workspace: str, state_home: str, no_launch: bool, force_reinstall: bool, web: bool) -> int:
    install_runtime(force_reinstall=force_reinstall, with_web=web)
    if no_launch:
        return 0
    return start_dashboard(workspace=workspace, state_home=state_home, web=web)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage agent runtime install/start across OSes.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_install = sub.add_parser("install", help="Install runtime dependencies into .venv")
    p_install.add_argument("--force-reinstall", action="store_true", help="Recreate .venv before install")
    p_install.add_argument("--with-web", action="store_true", help="Install textual-dev for browser mode")

    p_start = sub.add_parser("start", help="Launch dashboard")
    p_start.add_argument("--workspace", default=str(Path.cwd()), help="Target workspace path")
    p_start.add_argument("--state-home", default=str(Path.home() / ".agent-system"), help="Agent state root")
    p_start.add_argument("--web", action="store_true", help="Launch dashboard in browser mode")

    p_bootstrap = sub.add_parser("bootstrap", help="Install runtime and optionally launch dashboard")
    p_bootstrap.add_argument("--workspace", default=str(Path.cwd()), help="Target workspace path")
    p_bootstrap.add_argument("--state-home", default=str(Path.home() / ".agent-system"), help="Agent state root")
    p_bootstrap.add_argument("--no-launch", action="store_true", help="Install only")
    p_bootstrap.add_argument("--force-reinstall", action="store_true", help="Recreate .venv before install")
    p_bootstrap.add_argument("--web", action="store_true", help="Install browser tooling and launch in browser")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.command == "install":
            install_runtime(force_reinstall=args.force_reinstall, with_web=args.with_web)
            return 0
        if args.command == "start":
            return start_dashboard(workspace=args.workspace, state_home=args.state_home, web=args.web)
        if args.command == "bootstrap":
            return bootstrap(
                workspace=args.workspace,
                state_home=args.state_home,
                no_launch=args.no_launch,
                force_reinstall=args.force_reinstall,
                web=args.web,
            )
    except FileNotFoundError as exc:
        print(f"[agent-system] ERROR: {exc}", file=sys.stderr)
        return 1
    raise ValueError(f"Unknown command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
