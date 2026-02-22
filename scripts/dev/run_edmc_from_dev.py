"""Run EDMarketConnector GUI from local EDMC (DEV) repository with isolated dev config.

Default EDMC (DEV) path:
    ../EDMarketConnector

This script:
1) Launches EDMarketConnector.py from the EDMC (DEV) root
2) Creates an isolated dev config directory for testing
3) Passes --config argument to EDMC to use the isolated config
4) Verifies the plugin is linked into EDMC plugins directory

Usage:
    python scripts/run_edmc_from_dev.py
    python scripts/run_edmc_from_dev.py --use-system-config  # Use real EDMC config instead
"""

from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path

from dev_paths import (
    PROJECT_ROOT,
    DATA_DIR,
    default_python,
    load_dev_config,
    resolve_path,
)

DEFAULT_CONFIG_FILE = DATA_DIR / "dev_paths.json"
PLUGIN_NAME = "EDMCVKBConnector"


def ensure_dev_config_dir() -> Path:
    """Create and return the dev config directory path."""
    dev_config = PROJECT_ROOT / ".edmc_dev_config"
    dev_config.mkdir(exist_ok=True)
    return dev_config


def sanitize_config_for_dev(config_content: str, edmc_root: Path) -> str:
    """Sanitize EDMC config: update plugin dir and remove sensitive information.
    
    Args:
        config_content: The raw config file content
        edmc_root: Path to EDMC dev repository
        
    Returns:
        Sanitized config content
    """
    import re
    
    # Calculate the dev plugins directory
    dev_plugins_dir = edmc_root / "plugins"
    
    # Update plugin_dir to point to dev EDMC plugins
    # Use forward slashes for TOML compatibility (works fine on Windows)
    plugin_path = str(dev_plugins_dir).replace("\\", "/")
    config_content = re.sub(
        r'plugin_dir\s*=\s*"[^"]*"',
        f'plugin_dir = "{plugin_path}"',
        config_content
    )
    
    # Remove ALL sensitive information: API keys, usernames, CMDRs, etc.
    # This is a comprehensive list of keys that shouldn't be in dev config
    sensitive_keys = [
        'edsm_usernames',
        'edsm_cmdrs',
        'edsm_apikeys',
        'fdev_apikeys',
        'cmdrs',
        'inara_cmdrs',
        'inara_apikeys',
    ]
    
    for key in sensitive_keys:
        # Remove lines with sensitive keys (handles arrays spanning multiple lines)
        # This regex handles both simple values and multi-line arrays
        config_content = re.sub(
            rf'^{key}\s*=.*?(?=\n[a-z_]|\n\[|\Z)',
            '',
            config_content,
            flags=re.MULTILINE | re.DOTALL
        )
    
    # Clean up any resulting blank lines (more than 2 consecutive newlines)
    config_content = re.sub(r'\n\n\n+', '\n\n', config_content)
    
    return config_content


def create_dev_config_file(dev_config_dir: Path, edmc_root: Path) -> Path:
    """Create a dev EDMC config.toml with sensible defaults.
    
    Args:
        dev_config_dir: Directory to store the config
        edmc_root: Path to EDMC dev repository
    """
    config_file = dev_config_dir / "config.toml"
    
    if not config_file.exists():
        # Try to read the real EDMC config to seed the dev config
        real_config_dir = Path.home() / "AppData" / "Local" / "EDMarketConnector" if os.name == "nt" else Path.home() / ".local" / "share" / "EDMarketConnector"
        real_config_file = real_config_dir / "config.toml"
        
        if real_config_file.exists():
            # Copy the real config as a starting point, then sanitize
            try:
                config_content = real_config_file.read_text(encoding="utf-8")
                # Sanitize: update plugin dir + remove sensitive info
                config_content = sanitize_config_for_dev(config_content, edmc_root)
                config_file.write_text(config_content, encoding="utf-8")
                print(f"[INFO] Seeded and sanitized dev config from {real_config_file}")
                print(f"[INFO] Plugin directory set to: {edmc_root / 'plugins'}")
                return config_file
            except Exception as e:
                print(f"[WARN] Could not seed real config: {e}")
        
        # Fallback: create minimal config with settings that prevent setup prompts
        config_content = """# Development config for EDMCVKBConnector testing
# This is automatically generated and can be safely deleted

generated = "2026-02-15T00:00:00+00:00"
source = "dev_edmc"

[settings]
# Minimal settings - EDMC will populate this as it runs
"""
        config_file.write_text(config_content, encoding="utf-8")
        print(f"[INFO] Created dev config: {config_file}")
    
    return config_file


def check_plugin_linked(edmc_root: Path) -> bool:
    """Check if plugin is linked into EDMC plugins directory."""
    plugins_dir = edmc_root / "plugins"
    link_path = plugins_dir / PLUGIN_NAME
    
    if not link_path.exists() and not link_path.is_symlink():
        return False
    
    target_path = PROJECT_ROOT.resolve()
    if link_path.is_symlink():
        return link_path.resolve() == target_path
    
    # Could be a regular directory copy - that's ok too
    return True


def setup_dev_environment(edmc_root: Path, use_isolated_config: bool) -> str | None:
    """Set up isolated config and return config file path if using dev config.
    
    Args:
        edmc_root: Path to EDMC repository
        use_isolated_config: Whether to use isolated config
        
    Returns:
        Config file path to pass to EDMC via --config, or None to use system config
    """
    if use_isolated_config:
        dev_config = ensure_dev_config_dir()
        config_file = create_dev_config_file(dev_config, edmc_root)
        print(f"[INFO] Using isolated dev config: {config_file}")
        return str(config_file)
    else:
        print("[INFO] Using system EDMC configuration")
        return None


def parse_args() -> argparse.Namespace:
    bootstrap = argparse.ArgumentParser(add_help=False)
    bootstrap.add_argument(
        "--config-file",
        default=str(DEFAULT_CONFIG_FILE),
        help=argparse.SUPPRESS,
    )
    bootstrap_args, remaining = bootstrap.parse_known_args()
    config_file = Path(bootstrap_args.config_file).expanduser().resolve()
    config_data = load_dev_config(config_file)

    default_edmc_root = resolve_path("edmc_root", config_data, PROJECT_ROOT.parent / "EDMarketConnector")
    default_py = resolve_path("python_exec", config_data, default_python())

    parser = argparse.ArgumentParser(description="Run EDMC GUI from local EDMC (DEV) repository")
    parser.add_argument(
        "--config-file",
        default=str(config_file),
        help="Path to development path config JSON (default: ./dev_paths.json)",
    )
    parser.add_argument(
        "--edmc-root",
        default=str(default_edmc_root),
        help="Path to EDMC (DEV) repository root",
    )
    parser.add_argument(
        "--python",
        dest="python_exec",
        default=str(default_py),
        help="Python executable to use for launch",
    )
    parser.add_argument(
        "--no-ensure-deps",
        action="store_true",
        help="Skip automatic EDMC dependency install check",
    )
    parser.add_argument(
        "--use-system-config",
        action="store_true",
        help="Use system EDMC configuration instead of isolated dev config",
    )
    parser.add_argument(
        "--no-plugin",
        action="store_true",
        help="Temporarily disable plugin loading (for debugging UI issues)",
    )
    parser.add_argument(
        "edmc_args",
        nargs=argparse.REMAINDER,
        help="Arguments forwarded to EDMarketConnector.py (prefix with --)",
    )
    return parser.parse_args(remaining)


def has_module(python_exec: Path, module_name: str) -> bool:
    result = subprocess.run(
        [str(python_exec), "-c", f"import {module_name}"],
        check=False,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def ensure_edmc_deps(python_exec: Path, edmc_root: Path) -> bool:
    requirements = edmc_root / "requirements.txt"
    if not requirements.exists():
        print(f"[WARN] EDMC requirements.txt not found at {requirements}; skipping dependency install")
        return True

    # `semantic_version` is an EDMC import that fails early when deps are missing.
    if has_module(python_exec, "semantic_version"):
        return True

    print(f"[INFO] Installing EDMC dependencies from {requirements}")
    result = subprocess.run(
        [str(python_exec), "-m", "pip", "install", "-r", str(requirements)],
        cwd=str(edmc_root),
        check=False,
    )
    if result.returncode != 0:
        print("[FAIL] Could not install EDMC dependencies")
        return False

    if not has_module(python_exec, "semantic_version"):
        print("[FAIL] EDMC dependency check still failing after install")
        return False

    return True


def main() -> int:
    args = parse_args()
    edmc_root = Path(args.edmc_root).resolve()
    python_exec = Path(args.python_exec).resolve()
    entrypoint = edmc_root / "EDMarketConnector.py"

    if not edmc_root.exists() or not (edmc_root / ".git").exists():
        print(f"[FAIL] EDMC (DEV) repo not found at: {edmc_root}")
        print("       Run bootstrap first: python scripts/bootstrap_dev_env.py")
        return 1
    if not entrypoint.exists():
        print(f"[FAIL] EDMC entrypoint not found: {entrypoint}")
        return 1
    if not python_exec.exists():
        print(f"[FAIL] Python executable not found: {python_exec}")
        return 1
    if not args.no_ensure_deps and not ensure_edmc_deps(python_exec, edmc_root):
        return 1

    # Check if plugin is linked
    plugin_link = edmc_root / "plugins" / PLUGIN_NAME
    if not check_plugin_linked(edmc_root):
        print(f"[WARN] Plugin not linked in EDMC plugins directory")
        print(f"       Run bootstrap to link it: python scripts/bootstrap_dev_env.py")

    # Temporarily disable plugin if requested
    plugin_disabled = False
    if args.no_plugin and plugin_link.exists():
        plugin_disabled_path = plugin_link.with_stem(plugin_link.stem + ".disabled")
        try:
            plugin_link.rename(plugin_disabled_path)
            plugin_disabled = True
            print(f"[INFO] Plugin temporarily disabled: {plugin_link} -> {plugin_disabled_path}")
        except Exception as e:
            print(f"[WARN] Could not disable plugin: {e}")

    try:
        # Set up isolated dev config
        config_file = setup_dev_environment(edmc_root, use_isolated_config=not args.use_system_config)

        # Build EDMC command
        cmd = [str(python_exec), str(entrypoint)]
        
        # Add --config if using isolated config
        if config_file:
            cmd.extend(["--config", config_file])
        
        # Add any forwarded arguments
        forwarded = args.edmc_args
        if forwarded and forwarded[0] == "--":
            forwarded = forwarded[1:]
        
        cmd.extend(forwarded)
        
        print(f"[RUN] ({edmc_root}) {' '.join(cmd)}")
        print()
        
        # Run EDMC
        result = subprocess.run(cmd, cwd=str(edmc_root), check=False)
        return result.returncode
    finally:
        # Re-enable plugin if it was disabled
        if plugin_disabled:
            try:
                plugin_disabled_path = plugin_link.with_stem(plugin_link.stem + ".disabled")
                plugin_disabled_path.rename(plugin_link)
                print(f"[INFO] Plugin re-enabled")
            except Exception as e:
                print(f"[WARN] Could not re-enable plugin: {e}")


if __name__ == "__main__":
    raise SystemExit(main())
