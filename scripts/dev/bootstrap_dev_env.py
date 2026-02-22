"""Bootstrap local development for EDMCVKBConnector on a new machine.

This script ensures:
1) A sibling EDMC (DEV) repository exists and is up to date.
2) A local virtual environment exists at .venv.
3) Dependencies are installed for plugin development/testing.
4) Plugin is linked into EDMC (DEV) plugins directory.

Default EDMC (DEV) location:
    ../EDMarketConnector

Usage:
    python scripts/dev/bootstrap_dev_env.py
    python scripts/dev/bootstrap_dev_env.py --run-tests
    python scripts/dev/bootstrap_dev_env.py --edmc-root /path/to/EDMarketConnector
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

from dev_paths import PROJECT_ROOT, DATA_DIR, load_dev_config, resolve_path

DEFAULT_CONFIG_FILE = DATA_DIR / "dev_paths.json"
EDMC_REPO_URL = "https://github.com/EDCD/EDMarketConnector.git"
PLUGIN_NAME = "EDMCVKBConnector"


def run(cmd: list[str], *, cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    location = str(cwd) if cwd else str(PROJECT_ROOT)
    print(f"[RUN] ({location}) {' '.join(cmd)}")
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else str(PROJECT_ROOT),
        text=True,
        check=check,
        capture_output=False,
    )


def current_branch(repo: Path) -> str | None:
    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=str(repo),
        text=True,
        capture_output=True,
        check=False,
    )
    branch = result.stdout.strip()
    if result.returncode != 0 or not branch or branch == "HEAD":
        return None
    return branch


def origin_default_branch(repo: Path) -> str | None:
    result = subprocess.run(
        ["git", "symbolic-ref", "refs/remotes/origin/HEAD"],
        cwd=str(repo),
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    ref = result.stdout.strip()
    if "/" not in ref:
        return None
    return ref.split("/")[-1]


def ensure_edmc_repo(edmc_root: Path, *, update: bool) -> None:
    if not edmc_root.exists():
        print(f"[INFO] Cloning EDMC into {edmc_root}")
        run(["git", "clone", EDMC_REPO_URL, str(edmc_root)], cwd=PROJECT_ROOT.parent)
        return

    if not (edmc_root / ".git").exists():
        raise RuntimeError(f"{edmc_root} exists but is not a git repository")

    if not update:
        print("[INFO] Skipping EDMC update (--no-edmc-update)")
        return

    print(f"[INFO] Updating EDMC repo at {edmc_root}")
    run(["git", "fetch", "--prune", "origin"], cwd=edmc_root)

    branch = current_branch(edmc_root) or origin_default_branch(edmc_root)
    if branch:
        checkout = subprocess.run(
            ["git", "checkout", branch],
            cwd=str(edmc_root),
            text=True,
            capture_output=True,
            check=False,
        )
        if checkout.returncode != 0:
            print(f"[WARN] Could not checkout branch '{branch}': {checkout.stderr.strip()}")
        pull = subprocess.run(
            ["git", "pull", "--ff-only", "origin", branch],
            cwd=str(edmc_root),
            text=True,
            capture_output=True,
            check=False,
        )
        if pull.returncode != 0:
            print(f"[WARN] Could not fast-forward EDMC ({branch}): {pull.stderr.strip()}")
        else:
            print(f"[OK] EDMC is up to date on branch '{branch}'")
    else:
        print("[WARN] Could not determine EDMC branch; skipping pull")


def venv_python(venv_dir: Path) -> Path:
    if os.name == "nt":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def ensure_venv_and_deps(venv_dir: Path) -> Path:
    py = venv_python(venv_dir)
    if not py.exists():
        print(f"[INFO] Creating virtual environment at {venv_dir}")
        run([sys.executable, "-m", "venv", str(venv_dir)], cwd=PROJECT_ROOT)
    else:
        print(f"[OK] Virtual environment already exists at {venv_dir}")

    print("[INFO] Installing development dependencies")
    run([str(py), "-m", "pip", "install", "--upgrade", "pip"], cwd=PROJECT_ROOT)
    run([str(py), "-m", "pip", "install", "-r", "requirements.txt", "-e", ".[dev]"], cwd=PROJECT_ROOT)
    return py


def install_edmc_deps(py: Path, edmc_root: Path) -> None:
    requirements = edmc_root / "requirements.txt"
    if not requirements.exists():
        print(f"[WARN] EDMC requirements not found at {requirements}; skipping EDMC dependency install")
        return
    print(f"[INFO] Installing EDMC dependencies from {requirements}")
    run([str(py), "-m", "pip", "install", "-r", str(requirements)], cwd=edmc_root)


def run_dev_tests(py: Path) -> int:
    print("[INFO] Running development test suite")
    result = subprocess.run([str(py), "test/dev_test.py"], cwd=str(PROJECT_ROOT), check=False)
    return result.returncode


def remove_existing(path: Path) -> None:
    """Remove existing directory, symlink, or junction."""
    if not path.exists() and not path.is_symlink():
        return

    # On Windows, directory symlinks/junctions are best removed with `rmdir`.
    if os.name == "nt":
        result = subprocess.run(
            ["cmd", "/c", "rmdir", str(path)],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            return

    try:
        path.unlink()
        return
    except IsADirectoryError:
        pass
    except OSError:
        pass

    if path.is_dir():
        import shutil
        shutil.rmtree(path)
        return

    path.unlink()


def create_windows_junction(link_path: Path, target_path: Path) -> None:
    """Create a Windows directory junction."""
    result = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(link_path), str(target_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        details = result.stderr.strip() or result.stdout.strip() or "unknown error"
        raise RuntimeError(f"Failed to create junction: {details}")


def create_link(link_path: Path, target_path: Path) -> str:
    """Create a symlink or junction linking plugin into EDMC."""
    try:
        os.symlink(str(target_path), str(link_path), target_is_directory=True)
        return "symlink"
    except OSError as exc:
        if os.name != "nt":
            raise RuntimeError(f"Failed to create symlink: {exc}") from exc
        create_windows_junction(link_path, target_path)
        return "junction"


def link_plugin_into_edmc(edmc_root: Path) -> bool:
    """Link the plugin directory into EDMC plugins folder."""
    plugins_dir = edmc_root / "plugins"
    plugins_dir.mkdir(parents=True, exist_ok=True)

    target_path = PROJECT_ROOT.resolve()
    link_path = plugins_dir / PLUGIN_NAME

    if link_path.exists() or link_path.is_symlink():
        if link_path.is_symlink() and link_path.resolve() == target_path:
            print(f"[OK] Plugin already linked: {link_path} -> {target_path}")
            return True
        print(f"[INFO] Replacing existing path: {link_path}")
        remove_existing(link_path)

    try:
        link_type = create_link(link_path, target_path)
        print(f"[SUCCESS] Linked plugin into EDMC as {link_type}:")
        print(f"  {link_path} -> {target_path}")
        return True
    except Exception as exc:
        print(f"[WARN] Could not link plugin: {exc}")
        return False


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
    default_venv_dir = resolve_path("venv_dir", config_data, PROJECT_ROOT / ".venv")

    parser = argparse.ArgumentParser(description="Bootstrap EDMCVKBConnector development environment")
    parser.add_argument(
        "--config-file",
        default=str(config_file),
        help="Path to development path config JSON (default: ./dev_paths.json)",
    )
    parser.add_argument(
        "--edmc-root",
        default=str(default_edmc_root),
        help="Path to EDMC (DEV) repository",
    )
    parser.add_argument(
        "--venv-dir",
        default=str(default_venv_dir),
        help="Path for the local virtual environment",
    )
    parser.add_argument(
        "--no-edmc-update",
        action="store_true",
        help="Do not pull latest changes if EDMC repo already exists",
    )
    parser.add_argument(
        "--run-tests",
        action="store_true",
        help="Run test/dev_test.py after bootstrap",
    )
    parser.add_argument(
        "--no-edmc-python-deps",
        action="store_true",
        help="Skip installing EDMC (DEV) requirements into the virtual environment",
    )
    return parser.parse_args(remaining)


def main() -> int:
    args = parse_args()
    edmc_root = Path(args.edmc_root).resolve()
    venv_dir = Path(args.venv_dir).resolve()

    try:
        ensure_edmc_repo(edmc_root, update=not args.no_edmc_update)
        py = ensure_venv_and_deps(venv_dir)
        if not args.no_edmc_python_deps:
            install_edmc_deps(py, edmc_root)
        else:
            print("[INFO] Skipping EDMC Python dependencies (--no-edmc-python-deps)")
        
        # Link plugin into EDMC plugins directory
        link_plugin_into_edmc(edmc_root)
    except FileNotFoundError as exc:
        print(f"[FAIL] Required command not found: {exc}")
        return 1
    except Exception as exc:
        print(f"[FAIL] {exc}")
        return 1

    print("\n[SUCCESS] Bootstrap complete")
    print(f"  - EDMC repo: {edmc_root}")
    print(f"  - Python: {py}")

    if args.run_tests:
        code = run_dev_tests(py)
        if code != 0:
            print(f"[FAIL] Development tests failed with code {code}")
            return code
        print("[OK] Development tests passed")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
