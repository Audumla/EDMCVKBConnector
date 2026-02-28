"""
test_provider_gating.py - Ensures providers can be enabled for prod while restricted in tests.
"""
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

from agent_system.core.provider_registry import (
    load_delegation_config,
    get_enabled_provider_names,
    get_test_enabled_provider_names,
)


def test_test_enabled_is_subset_of_enabled_executors():
    enabled = set(get_enabled_provider_names("executors"))
    test_enabled = set(get_test_enabled_provider_names("executors"))
    assert test_enabled.issubset(enabled)


def test_test_enabled_is_subset_of_enabled_planners():
    enabled = set(get_enabled_provider_names("planners"))
    test_enabled = set(get_test_enabled_provider_names("planners"))
    assert test_enabled.issubset(enabled)


def test_config_has_prod_only_providers():
    cfg = load_delegation_config()
    execs = cfg.get("executors", {})
    planners = cfg.get("planners", {})

    prod_only_execs = [
        name for name, p in execs.items()
        if p.get("enabled", True) and not p.get("test_enabled", False)
    ]
    prod_only_planners = [
        name for name, p in planners.items()
        if p.get("enabled", True) and not p.get("test_enabled", False)
    ]

    # Guardrail: ensure we keep at least one provider available in prod but excluded from tests.
    assert len(prod_only_execs) > 0
    assert len(prod_only_planners) > 0
