"""
test_provider_registry.py - Tests for merged shared + role-specific provider config.
"""
from pathlib import Path
import sys
from unittest.mock import patch, MagicMock

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

from agent_system.core.provider_registry import get_provider_config, get_provider_health


def test_provider_config_merges_shared_and_role_specific():
    cfg = {
        "providers": {
            "my-provider": {
                "provider_type": "cli",
                "bin": "mybin",
                "usage": {"timeout_sec": 10, "detailed_command": ["{bin}", "stats"]},
                "available_models": ["m1", "m2"],
            }
        },
        "executors": {
            "my-provider": {
                "enabled": True,
                "model": "m2",
                "usage": {"timeout_sec": 25},
            }
        },
    }

    with patch("agent_system.core.provider_registry.load_delegation_config", return_value=cfg):
        merged = get_provider_config("my-provider", role="executors")

    assert merged["provider_type"] == "cli"
    assert merged["bin"] == "mybin"
    assert merged["model"] == "m2"
    assert merged["available_models"] == ["m1", "m2"]
    assert merged["usage"]["detailed_command"] == ["{bin}", "stats"]
    assert merged["usage"]["timeout_sec"] == 25


def test_provider_health_reports_missing_binary():
    cfg = {
        "providers": {"x": {"provider_type": "cli", "bin": "missing-cli"}},
        "executors": {"x": {"enabled": True}},
    }
    with patch("agent_system.core.provider_registry.load_delegation_config", return_value=cfg):
        with patch("agent_system.core.provider_registry.shutil.which", return_value=None):
            health = get_provider_health("x", role="executors")
    assert health["installed"] is False
    assert health["working"] is False
    assert health["status"] == "missing"


def test_provider_health_runs_declared_healthcheck():
    cfg = {
        "providers": {
            "x": {
                "provider_type": "cli",
                "bin": "xcli",
                "availability": {"healthcheck_command": ["{bin}", "--version"], "timeout_sec": 3},
            }
        },
        "executors": {"x": {"enabled": True}},
    }
    proc = MagicMock()
    proc.returncode = 0
    with patch("agent_system.core.provider_registry.load_delegation_config", return_value=cfg):
        with patch("agent_system.core.provider_registry.shutil.which", return_value="/usr/bin/xcli"):
            with patch("agent_system.core.provider_registry.subprocess.run", return_value=proc) as mock_run:
                health = get_provider_health("x", role="executors")
    assert health["installed"] is True
    assert health["working"] is True
    assert health["status"] == "available"
    assert mock_run.call_args[0][0] == ["xcli", "--version"]


def test_provider_health_codex_uses_vscode_fallback():
    cfg = {
        "providers": {"codex": {"provider_type": "cli", "bin": "codex"}},
        "executors": {"codex": {"enabled": True}},
    }
    with patch("agent_system.core.provider_registry.load_delegation_config", return_value=cfg):
        with patch("agent_system.core.provider_registry.shutil.which", return_value=None):
            with patch("agent_system.core.provider_registry._discover_vscode_codex_bin", return_value=True):
                health = get_provider_health("codex", role="executors")
    assert health["installed"] is True
    assert health["working"] is True
    assert health["status"] == "available"


def test_provider_health_local_llm_uses_http_endpoint_mode():
    cfg = {
        "providers": {
            "local-llm": {
                "provider_type": "api_keyed",
                "availability": {
                    "kind": "http_endpoint",
                    "endpoint_from": "local_settings",
                    "path": "/models",
                    "timeout_sec": 3,
                },
            }
        },
        "executors": {"local-llm": {"enabled": True}},
    }
    with patch("agent_system.core.provider_registry.load_delegation_config", return_value=cfg):
        with patch("agent_system.core.provider_registry._resolve_endpoint_from_local_settings", return_value="http://localhost:50091/v1"):
            with patch("agent_system.core.provider_registry._http_endpoint_ok", return_value=True):
                health = get_provider_health("local-llm", role="executors")
    assert health["installed"] is True
    assert health["working"] is True
    assert health["status"] == "available"
    assert health["reason"] == "ready"

