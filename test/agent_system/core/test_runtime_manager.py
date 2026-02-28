"""Tests for cross-platform runtime management script."""

from __future__ import annotations

import importlib.util
from types import SimpleNamespace
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = PROJECT_ROOT / "scripts" / "agent_runners" / "manage_runtime.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("manage_runtime", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_venv_python_returns_os_specific_path(monkeypatch):
    module = _load_module()
    root = PROJECT_ROOT

    monkeypatch.setattr(module.os, "name", "nt", raising=False)
    win_path = str(module.venv_python(root)).replace("\\", "/").lower()
    assert win_path.endswith(".venv/scripts/python.exe")

    monkeypatch.setattr(module.os, "name", "posix", raising=False)
    posix_path = str(module.venv_python(root)).replace("\\", "/").lower()
    assert posix_path.endswith(".venv/bin/python")


def test_bootstrap_no_launch_installs_only(monkeypatch):
    module = _load_module()
    calls = {"install": 0, "start": 0}

    def fake_install(force_reinstall: bool = False, with_web: bool = False) -> None:
        assert with_web is False
        calls["install"] += 1

    def fake_start(workspace: str, state_home: str, web: bool = False) -> int:
        assert web is False
        calls["start"] += 1
        return 0

    monkeypatch.setattr(module, "install_runtime", fake_install)
    monkeypatch.setattr(module, "start_dashboard", fake_start)

    rc = module.bootstrap(workspace=".", state_home=".state", no_launch=True, force_reinstall=False, web=False)
    assert rc == 0
    assert calls == {"install": 1, "start": 0}


def test_bootstrap_web_installs_and_starts_in_web_mode(monkeypatch):
    module = _load_module()
    seen: dict[str, tuple] = {}

    def fake_install(force_reinstall: bool = False, with_web: bool = False) -> None:
        seen["install"] = (force_reinstall, with_web)

    def fake_start(workspace: str, state_home: str, web: bool = False) -> int:
        seen["start"] = (workspace, state_home, web)
        return 7

    monkeypatch.setattr(module, "install_runtime", fake_install)
    monkeypatch.setattr(module, "start_dashboard", fake_start)

    rc = module.bootstrap(workspace="w", state_home="s", no_launch=False, force_reinstall=True, web=True)
    assert rc == 7
    assert seen["install"] == (True, True)
    assert seen["start"] == ("w", "s", True)


def test_install_runtime_with_web_installs_textual_dev(monkeypatch, tmp_path):
    module = _load_module()
    root = tmp_path / "runtime"
    requirements = root / "requirements.txt"
    venv_py = root / "venv-python"
    requirements.parent.mkdir(parents=True, exist_ok=True)
    requirements.write_text("textual>=0.80.0\n", encoding="utf-8")
    venv_py.parent.mkdir(parents=True, exist_ok=True)
    venv_py.write_text("", encoding="utf-8")

    monkeypatch.setattr(module, "runtime_root", lambda: root)
    monkeypatch.setattr(module, "venv_python", lambda _root: venv_py)

    calls: list[list[str]] = []

    def fake_run(command, check=False):  # noqa: ANN001
        calls.append(command)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(module.subprocess, "run", fake_run)

    module.install_runtime(force_reinstall=False, with_web=True)

    assert calls[0] == [str(venv_py), "-m", "pip", "install", "--upgrade", "pip"]
    assert calls[1] == [str(venv_py), "-m", "pip", "install", "-r", str(requirements)]
    assert calls[2] == [str(venv_py), "-m", "pip", "install", "textual-dev"]


def test_build_parser_accepts_web_flags():
    module = _load_module()
    parser = module.build_parser()

    install_args = parser.parse_args(["install", "--with-web"])
    assert install_args.command == "install"
    assert install_args.with_web is True

    start_args = parser.parse_args(["start", "--web"])
    assert start_args.command == "start"
    assert start_args.web is True

    bootstrap_args = parser.parse_args(["bootstrap", "--web"])
    assert bootstrap_args.command == "bootstrap"
    assert bootstrap_args.web is True


def test_start_dashboard_terminal_mode_uses_python_entrypoint(monkeypatch, tmp_path):
    module = _load_module()
    root = tmp_path / "runtime"
    workspace = tmp_path / "workspace"
    state_home = tmp_path / "state-home"
    workspace.mkdir(parents=True, exist_ok=True)

    venv_py = root / "venv-python"
    dashboard_script = root / "agent_system" / "dashboard" / "agent_dashboard.py"
    venv_py.parent.mkdir(parents=True, exist_ok=True)
    venv_py.write_text("", encoding="utf-8")
    dashboard_script.parent.mkdir(parents=True, exist_ok=True)
    dashboard_script.write_text("print('ok')\n", encoding="utf-8")

    monkeypatch.setattr(module, "runtime_root", lambda: root)
    monkeypatch.setattr(module, "venv_python", lambda _root: venv_py)
    monkeypatch.setattr(module, "venv_textual", lambda _root: root / "missing-textual")

    calls: list[dict] = []

    def fake_run(command, cwd=None, env=None, check=False):  # noqa: ANN001
        calls.append({"command": command, "cwd": cwd, "env": env, "check": check})
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(module.subprocess, "run", fake_run)

    rc = module.start_dashboard(workspace=str(workspace), state_home=str(state_home), web=False)
    assert rc == 0
    assert calls, "subprocess.run should be called"
    assert calls[0]["command"] == [str(venv_py), str(dashboard_script)]
    assert calls[0]["cwd"] == str(root)
    assert calls[0]["env"]["AGENT_WORKSPACE_ROOT"] == str(workspace.resolve())
    assert calls[0]["env"]["AGENT_STATE_HOME"] == str(state_home.resolve())


def test_start_dashboard_web_mode_requires_textual_cli(monkeypatch, tmp_path):
    module = _load_module()
    root = tmp_path / "runtime"
    workspace = tmp_path / "workspace"
    state_home = tmp_path / "state-home"
    workspace.mkdir(parents=True, exist_ok=True)

    venv_py = root / "venv-python"
    dashboard_script = root / "agent_system" / "dashboard" / "agent_dashboard.py"
    venv_py.parent.mkdir(parents=True, exist_ok=True)
    venv_py.write_text("", encoding="utf-8")
    dashboard_script.parent.mkdir(parents=True, exist_ok=True)
    dashboard_script.write_text("print('ok')\n", encoding="utf-8")

    monkeypatch.setattr(module, "runtime_root", lambda: root)
    monkeypatch.setattr(module, "venv_python", lambda _root: venv_py)
    monkeypatch.setattr(module, "venv_textual", lambda _root: root / "missing-textual")

    with pytest.raises(FileNotFoundError, match="install --with-web"):
        module.start_dashboard(workspace=str(workspace), state_home=str(state_home), web=True)


def test_start_dashboard_web_mode_uses_textual_serve(monkeypatch, tmp_path):
    module = _load_module()
    root = tmp_path / "runtime"
    workspace = tmp_path / "workspace"
    state_home = tmp_path / "state-home"
    workspace.mkdir(parents=True, exist_ok=True)

    venv_py = root / "venv-python"
    textual_cli = root / "textual-cli"
    dashboard_script = root / "agent_system" / "dashboard" / "agent_dashboard.py"
    venv_py.parent.mkdir(parents=True, exist_ok=True)
    venv_py.write_text("", encoding="utf-8")
    textual_cli.parent.mkdir(parents=True, exist_ok=True)
    textual_cli.write_text("", encoding="utf-8")
    dashboard_script.parent.mkdir(parents=True, exist_ok=True)
    dashboard_script.write_text("print('ok')\n", encoding="utf-8")

    monkeypatch.setattr(module, "runtime_root", lambda: root)
    monkeypatch.setattr(module, "venv_python", lambda _root: venv_py)
    monkeypatch.setattr(module, "venv_textual", lambda _root: textual_cli)

    calls: list[dict] = []

    def fake_run(command, cwd=None, env=None, check=False):  # noqa: ANN001
        calls.append({"command": command, "cwd": cwd, "env": env, "check": check})
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(module.subprocess, "run", fake_run)

    rc = module.start_dashboard(workspace=str(workspace), state_home=str(state_home), web=True)
    assert rc == 0
    assert calls, "subprocess.run should be called"
    assert calls[0]["command"] == [str(textual_cli), "serve", str(dashboard_script)]


def test_main_returns_error_code_for_missing_runtime(monkeypatch):
    module = _load_module()
    fake_args = SimpleNamespace(command="start", workspace=".", state_home=".state", web=True)
    fake_parser = SimpleNamespace(parse_args=lambda: fake_args)

    monkeypatch.setattr(module, "build_parser", lambda: fake_parser)

    def fake_start(**_kwargs):  # noqa: ANN003
        raise FileNotFoundError("missing runtime")

    monkeypatch.setattr(module, "start_dashboard", fake_start)

    assert module.main() == 1
