"""
Pytest configuration and shared fixtures for edmcruleengine tests.

Path setup is handled by pyproject.toml [tool.pytest.ini_options] pythonpath.
"""

import sys
import io
import json
import os
import subprocess
import time
import threading
from pathlib import Path

import pytest


def _list_vkb_link_pids() -> set[int]:
    """Return the set of currently running VKB-Link process IDs."""
    if sys.platform == "win32":
        cmd = [
            "powershell",
            "-NoProfile",
            "-Command",
            (
                "$procs = Get-Process -Name 'VKB-Link' -ErrorAction SilentlyContinue | "
                "Select-Object Id; "
                "if ($null -eq $procs) { '[]' } else { $procs | ConvertTo-Json -Compress }"
            ),
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=10)
            if result.returncode != 0 or not result.stdout.strip():
                return set()
            payload = json.loads(result.stdout.strip())
            if isinstance(payload, dict):
                payload = [payload]
            return {
                int(item["Id"])
                for item in payload
                if isinstance(item, dict) and str(item.get("Id", "")).isdigit()
            }
        except Exception:
            return set()

    try:
        result = subprocess.run(
            ["pgrep", "-f", "VKB-Link"],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
        if result.returncode not in (0, 1):
            return set()
        return {int(pid) for pid in result.stdout.split() if pid.isdigit()}
    except Exception:
        return set()


def _kill_vkb_link_pids(pids: set[int]) -> None:
    """Force-stop VKB-Link processes by PID."""
    for pid in sorted(pids):
        try:
            if sys.platform == "win32":
                subprocess.run(
                    ["taskkill", "/PID", str(pid), "/T", "/F"],
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=15,
                )
            else:
                os.kill(pid, 15)
        except Exception:
            pass


@pytest.fixture(scope="session", autouse=True)
def ensure_vkb_link_shutdown_after_tests():
    """Kill any VKB-Link processes started during this pytest session."""
    starting_pids = _list_vkb_link_pids()
    yield
    leaked_pids = _list_vkb_link_pids() - starting_pids
    if leaked_pids:
        _kill_vkb_link_pids(leaked_pids)
        time.sleep(1.0)
        remaining = _list_vkb_link_pids() - starting_pids
        if remaining:
            _kill_vkb_link_pids(remaining)


def pytest_addoption(parser):
    parser.addoption(
        "--run-live-agents", action="store_true", default=False, help="run live LLM agent tests"
    )
    parser.addoption(
        "--run-changelog", action="store", default="1", choices=("0", "1"), help="Run changelog tests (1=Yes, 0=No)"
    )


def pytest_configure(config):
    """Ensure stdout/stderr use UTF-8 on Windows so Unicode test output works."""
    config.addinivalue_line("markers", "live_agent: mark test as requiring a live LLM agent call")
    config.addinivalue_line("markers", "changelog: mark test as part of the changelog utility suite")
    config.addinivalue_line("markers", "skip_all_by_default: mark test to be skipped unless explicitly requested")
    if sys.stdout and hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    if sys.stderr and hasattr(sys.stderr, "buffer"):
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


def as_bool(value) -> bool:
    """Convert truthy/falsy values including 1/0 and '1'/'0' to bool."""
    if isinstance(value, bool):
        return value
    if str(value).lower() in ("1", "true", "yes", "on"):
        return True
    return False


def pytest_collection_modifyitems(config, items):
    # Load test settings manually here since we are in collection phase (before fixtures)
    test_settings = {}
    config_path = Path(__file__).parent / "test_config.json"
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                test_settings = json.load(f)
        except Exception:
            pass

    # Priority: CLI flag > test_config.json > Default
    
    # run_changelog defaults to '1' in addoption
    cli_changelog = config.getoption("--run-changelog")
    config_changelog = test_settings.get("run_changelog")
    
    # If explicitly set in test_config and NOT default '1' on CLI, use config
    if config_changelog is not None and cli_changelog == "1":
        run_changelog = as_bool(config_changelog)
    else:
        run_changelog = as_bool(cli_changelog)

    # run_live_agents defaults to False
    cli_live = config.getoption("--run-live-agents")
    config_live = test_settings.get("run_live_agents")
    run_live = cli_live or as_bool(config_live)
    
    skip_live = pytest.mark.skip(reason="need --run-live-agents option or test_config.json enable to run")
    skip_changelog = pytest.mark.skip(reason="changelog tests disabled via --run-changelog=0 or test_config.json")

    for item in items:
        if "live_agent" in item.keywords and not run_live:
            item.add_marker(skip_live)
        if "changelog" in item.keywords and not run_changelog:
            item.add_marker(skip_changelog)

from test.mock_vkb_server import MockVKBServer


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def test_settings():
    """Load test-specific configuration from test/test_config.json."""
    config_path = Path(__file__).parent / "test_config.json"
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Failed to load {config_path}: {e}")
    return {}


@pytest.fixture
def mock_server():
    """Start and stop a mock VKB server on a dynamic port.

    Yields a (server, port) tuple.  Each test gets a unique port so
    they can run in parallel without collisions.
    """
    # Use a free port picked by the OS
    server = MockVKBServer(host="127.0.0.1", port=0)
    thread = threading.Thread(target=server.start, daemon=True)
    thread.start()
    time.sleep(0.5)  # Let the server bind
    port = server.port  # Actual port after bind
    yield server, port
    server.stop()
    thread.join(timeout=2.0) # Ensure thread exits
    time.sleep(0.2)


@pytest.fixture
def journal_events():
    """Parse the sample journal fixture and return the event list."""
    journal_path = Path(__file__).parent / "fixtures" / "Journal.2026-02-13T120000.01.log"
    if not journal_path.exists():
        pytest.skip(f"Journal fixture not found: {journal_path}")
    events = []
    with open(journal_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return events


@pytest.fixture
def vkb_manager(config):
    """Return a VKBLinkManager instance for testing."""
    from edmcruleengine.vkb.vkb_link_manager import VKBLinkManager
    from edmcruleengine.vkb.vkb_client import VKBClient
    from pathlib import Path
    
    vkb_client = VKBClient(
        host=config.get("vkb_host", "127.0.0.1"),
        port=config.get("vkb_port", 50995)
    )
    return VKBLinkManager(config, Path.cwd(), client=vkb_client)

@pytest.fixture
def event_handler(config, vkb_manager):
    """Return an EventHandler instance for testing, with VKB endpoint registered."""
    from edmcruleengine import EventHandler
    handler = EventHandler(config)
    handler.add_endpoint(vkb_manager)
    return handler

