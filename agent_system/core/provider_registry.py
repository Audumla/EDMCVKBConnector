"""
provider_registry.py - Centralized provider configuration access for planners/executors.
"""
from __future__ import annotations

import json
import copy
import os
import shlex
import shutil
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG_FILE = PROJECT_ROOT / "agent_system" / "config" / "delegation-config.json"
PROVIDERS_DIR = PROJECT_ROOT / "agent_system" / "config" / "providers"

ProviderRole = Literal["planners", "executors"]


@lru_cache(maxsize=1)
def load_delegation_config() -> dict[str, Any]:
    config: dict[str, Any] = {}
    if CONFIG_FILE.exists():
        try:
            config = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            config = {}
    return _merge_provider_fragments(config)


def reload_delegation_config() -> None:
    load_delegation_config.cache_clear()


def _deep_merge_dicts(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Return a deep merge of two dictionaries where override wins."""
    result = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge_dicts(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def _merge_provider_fragments(config: dict[str, Any]) -> dict[str, Any]:
    """Merge optional per-provider fragment files into the loaded config."""
    merged = copy.deepcopy(config)
    if not PROVIDERS_DIR.exists():
        return merged

    merged.setdefault("providers", {})
    merged.setdefault("planners", {})
    merged.setdefault("executors", {})

    for path in sorted(PROVIDERS_DIR.glob("*.json")):
        try:
            fragment = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue

        name = str(fragment.get("name", "")).strip() or path.stem
        if not name:
            continue

        provider_cfg = fragment.get("provider", {})
        planner_cfg = fragment.get("planner", {})
        executor_cfg = fragment.get("executor", {})

        if isinstance(provider_cfg, dict):
            merged["providers"][name] = _deep_merge_dicts(merged["providers"].get(name, {}), provider_cfg)
        if isinstance(planner_cfg, dict):
            merged["planners"][name] = _deep_merge_dicts(merged["planners"].get(name, {}), planner_cfg)
        if isinstance(executor_cfg, dict):
            merged["executors"][name] = _deep_merge_dicts(merged["executors"].get(name, {}), executor_cfg)

    return merged


def _get_role_provider_config(config: dict[str, Any], name: str, role: ProviderRole) -> dict[str, Any]:
    return config.get(role, {}).get(name, {})


def get_shared_provider_config(name: str) -> dict[str, Any]:
    """Get shared provider defaults from top-level 'providers' section."""
    config = load_delegation_config()
    return config.get("providers", {}).get(name, {})


def get_provider_config(name: str, role: ProviderRole | None = None) -> dict[str, Any]:
    config = load_delegation_config()
    shared = config.get("providers", {}).get(name, {})
    if role:
        role_cfg = _get_role_provider_config(config, name, role)
        return _deep_merge_dicts(shared, role_cfg)

    exec_cfg = _get_role_provider_config(config, name, "executors")
    planner_cfg = _get_role_provider_config(config, name, "planners")
    merged = _deep_merge_dicts(shared, planner_cfg)
    merged = _deep_merge_dicts(merged, exec_cfg)
    return merged


def get_provider_names(role: ProviderRole) -> list[str]:
    config = load_delegation_config()
    return list(config.get(role, {}).keys())


def get_all_provider_names() -> list[str]:
    config = load_delegation_config()
    names = list(config.get("planners", {}).keys())
    for name in config.get("executors", {}).keys():
        if name not in names:
            names.append(name)
    return names


def get_enabled_provider_names(role: ProviderRole) -> list[str]:
    config = load_delegation_config()
    providers = config.get(role, {})
    return [name for name, cfg in providers.items() if cfg.get("enabled", True)]


def get_test_enabled_provider_names(role: ProviderRole) -> list[str]:
    config = load_delegation_config()
    providers = config.get(role, {})
    return [name for name, cfg in providers.items() if cfg.get("test_enabled", False)]


def is_pytest_context() -> bool:
    return "PYTEST_CURRENT_TEST" in os.environ


def is_provider_test_blocked(cfg: dict[str, Any]) -> bool:
    """
    Return True only when:
    - running under pytest, and
    - provider explicitly sets test_enabled, and
    - test_enabled is false.
    """
    return is_pytest_context() and ("test_enabled" in cfg) and (not bool(cfg.get("test_enabled")))


def get_default_planner() -> str | None:
    config = load_delegation_config()
    return config.get("default_planner")


def get_default_executor() -> str | None:
    config = load_delegation_config()
    return config.get("default_executor")


def get_provider_models(name: str, role: ProviderRole | None = None) -> list[str]:
    models: set[str] = set()
    roles = [role] if role else ["planners", "executors"]
    for role_name in roles:
        cfg = get_provider_config(name, role=role_name)
        if not cfg:
            continue
        if "available_models" in cfg:
            models.update(cfg["available_models"])
        elif cfg.get("model"):
            models.add(cfg["model"])
    return sorted(models) if models else ["default"]


def _bin_candidates(cfg: dict[str, Any]) -> list[str]:
    bins: list[str] = []
    configured = cfg.get("bin")
    if isinstance(configured, str) and configured.strip():
        try:
            parts = shlex.split(configured)
        except ValueError:
            parts = configured.strip().split()
        if parts:
            bins.append(parts[0])
    elif isinstance(configured, list) and configured:
        first = configured[0]
        if isinstance(first, str) and first.strip():
            bins.append(first.strip())
    return bins


def _discover_vscode_codex_bin() -> bool:
    """Windows fallback: detect codex.exe shipped in the VS Code extension bundle."""
    if os.name != "nt":
        return False
    roots: list[Path] = []
    userprofile = os.environ.get("USERPROFILE", "").strip()
    home = os.environ.get("HOME", "").strip()
    if userprofile:
        roots.append(Path(userprofile))
    if home:
        roots.append(Path(home))
    for root in roots:
        for vscode_dir in (".vscode", ".vscode-insiders"):
            ext_dir = root / vscode_dir / "extensions"
            if not ext_dir.exists():
                continue
            matches = list(ext_dir.glob("openai.chatgpt-*/bin/windows-x86_64/codex.exe"))
            if matches:
                return True
    return False


def _is_bin_installed(cfg: dict[str, Any]) -> bool:
    for candidate in _bin_candidates(cfg):
        if shutil.which(candidate):
            return True
        lower = candidate.lower()
        if lower in {"codex", "codex.exe"} and _discover_vscode_codex_bin():
            return True
    return False


def _command_is_ok(cmd: list[str], timeout_sec: int) -> bool:
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            encoding="utf-8",
            errors="replace",
        )
        return proc.returncode == 0
    except Exception:
        return False


def _replace_tokens(command: list[str], cfg: dict[str, Any]) -> list[str]:
    result: list[str] = []
    bin_name = _bin_candidates(cfg)
    for token in command:
        if token == "{bin}":
            result.extend(bin_name or [])
        else:
            result.append(token)
    return result


def _http_endpoint_ok(endpoint: str, path: str = "/models", timeout_sec: int = 5) -> bool:
    base = endpoint.strip().rstrip("/")
    if not base:
        return False
    target = urllib.parse.urljoin(base + "/", path.lstrip("/"))
    req = urllib.request.Request(target, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            return 200 <= int(getattr(resp, "status", 0) or 0) < 500
    except urllib.error.HTTPError as exc:
        # If endpoint exists but auth/config is wrong, treat as reachable for availability purposes.
        return 400 <= int(exc.code) < 500
    except Exception:
        return False


def _resolve_endpoint_from_local_settings() -> str | None:
    cfg_path = PROJECT_ROOT / "agent_system" / "config" / ".local-llm" / "settings.json"
    if not cfg_path.exists():
        return None
    try:
        data = json.loads(cfg_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    endpoint = str(data.get("endpoint", "")).strip()
    return endpoint or None


def get_provider_health(name: str, role: ProviderRole | None = None) -> dict[str, Any]:
    """
    Determine provider availability from config + local environment.

    Returned shape:
    {
      "provider": "<name>",
      "role": "planners|executors|all",
      "installed": bool,
      "working": bool,
      "status": "available|missing|degraded",
      "reason": "<short message>"
    }
    """
    cfg = get_provider_config(name, role=role)
    availability = cfg.get("availability", {}) if isinstance(cfg.get("availability"), dict) else {}
    installed_override = availability.get("installed")
    working_override = availability.get("working")
    required_env = availability.get("required_env", [])
    if isinstance(required_env, str):
        required_env = [required_env]
    required_env = [e for e in required_env if isinstance(e, str) and e.strip()]

    if isinstance(installed_override, bool):
        installed = installed_override
    else:
        availability_kind = str(availability.get("kind", "")).strip().lower()
        if availability_kind == "http_endpoint":
            installed = True
        else:
            provider_type = str(cfg.get("provider_type", "")).strip().lower()
            if provider_type in {"cli", "subscription"} or _bin_candidates(cfg):
                installed = _is_bin_installed(cfg)
            else:
                installed = True

    availability_kind = str(availability.get("kind", "")).strip().lower()
    timeout_sec = int(availability.get("timeout_sec", 8) or 8)
    endpoint_path = str(availability.get("path", "/models"))
    endpoint_value = str(availability.get("endpoint", "")).strip()
    endpoint_from = str(availability.get("endpoint_from", "")).strip().lower()
    if not endpoint_value and endpoint_from == "local_settings":
        endpoint_value = _resolve_endpoint_from_local_settings() or ""
    if not endpoint_value and name == "local-llm":
        endpoint_value = _resolve_endpoint_from_local_settings() or "http://localhost:11434/v1"

    env_ok = all(bool(os.environ.get(env_name, "").strip()) for env_name in required_env)

    if isinstance(working_override, bool):
        working = working_override and installed
        reason = "declared by config"
    else:
        health_cmd = availability.get("healthcheck_command")
        if not installed:
            working = False
            reason = "binary not found"
        elif required_env and not env_ok:
            working = False
            reason = f"missing env: {', '.join(required_env)}"
        elif availability_kind == "http_endpoint":
            working = _http_endpoint_ok(endpoint_value, path=endpoint_path, timeout_sec=timeout_sec)
            reason = "endpoint unreachable" if not working else "ready"
        elif isinstance(health_cmd, list) and health_cmd:
            resolved_cmd = _replace_tokens([str(x) for x in health_cmd], cfg)
            working = _command_is_ok(resolved_cmd, timeout_sec=timeout_sec)
            reason = "healthcheck failed" if not working else "ready"
        else:
            working = True
            reason = "ready"

    status = "available" if (installed and working) else ("missing" if not installed else "degraded")
    return {
        "provider": name,
        "role": role or "all",
        "installed": bool(installed),
        "working": bool(working),
        "status": status,
        "reason": reason,
    }


def get_provider_health_map(role: ProviderRole, enabled_only: bool = True) -> dict[str, dict[str, Any]]:
    names = get_enabled_provider_names(role) if enabled_only else get_provider_names(role)
    return {name: get_provider_health(name, role=role) for name in names}
