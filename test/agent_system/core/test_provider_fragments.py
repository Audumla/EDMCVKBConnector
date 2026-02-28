"""
test_provider_fragments.py - Tests optional provider fragment merge behavior.
"""
from pathlib import Path
import json
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

from agent_system.core import provider_registry


def test_provider_fragment_merge(tmp_path, monkeypatch):
    cfg_file = tmp_path / "delegation-config.json"
    providers_dir = tmp_path / "providers"
    providers_dir.mkdir(parents=True)

    cfg_file.write_text(
        json.dumps(
            {
                "providers": {"alpha": {"bin": "alpha", "usage": {"timeout_sec": 10}}},
                "planners": {"alpha": {"enabled": True, "model": "a1"}},
                "executors": {"alpha": {"enabled": True, "runner": "runners/run_alpha.py"}},
            }
        ),
        encoding="utf-8",
    )

    (providers_dir / "alpha.json").write_text(
        json.dumps(
            {
                "name": "alpha",
                "provider": {"usage": {"timeout_sec": 25, "detailed_command": ["{bin}", "stats"]}},
                "executor": {"runner_args": ["--x", "1"]},
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(provider_registry, "CONFIG_FILE", cfg_file)
    monkeypatch.setattr(provider_registry, "PROVIDERS_DIR", providers_dir)
    provider_registry.reload_delegation_config()

    merged = provider_registry.get_provider_config("alpha", role="executors")
    assert merged["usage"]["timeout_sec"] == 25
    assert merged["usage"]["detailed_command"] == ["{bin}", "stats"]
    assert merged["runner_args"] == ["--x", "1"]
