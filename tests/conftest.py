"""
Pytest configuration and shared fixtures for edmcruleengine tests.

Path setup is handled by pyproject.toml [tool.pytest.ini_options] pythonpath.
"""

import json
import time
import threading
from pathlib import Path

import pytest

from tests.mock_vkb_server import MockVKBServer
from edmcruleengine.config import Config
from edmcruleengine.event_handler import EventHandler


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

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
    time.sleep(0.2)


@pytest.fixture
def journal_events():
    """Parse the sample journal fixture and return the event list."""
    journal_path = Path(__file__).parent / "fixtures" / "Journal.2026-02-13T120000.01.log"
    assert journal_path.exists(), f"Journal fixture not found: {journal_path}"
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
def config():
    """Return a default Config instance (test-mode, no EDMC)."""
    return Config()

