"""Bootstrap local development for EDMCVKBConnector on a new machine.

This script ensures:
1) A sibling EDMC (DEV) repository exists and is up to date.
2) A local virtual environment exists at .venv.
3) Dependencies are installed for plugin development/testing.

Default EDMC (DEV) location:
    ../EDMarketConnector

Usage:
    python scripts/bootstrap_dev_env.py
    python scripts/bootstrap_dev_env.py --run-tests
    python scripts/bootstrap_dev_env.py --edmc-root /path/to/EDMarketConnector
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_EDMC_ROOT = (PROJECT_ROOT.parent / "EDMarketConnector").resolve()
EDMC_REPO_URL = "https://github.com/EDCD/EDMarketConnector.git"


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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bootstrap EDMCVKBConnector development environment")
    parser.add_argument(
        "--edmc-root",
        default=str(DEFAULT_EDMC_ROOT),
        help="Path to EDMC (DEV) repository",
    )
    parser.add_argument(
        "--venv-dir",
        default=str(PROJECT_ROOT / ".venv"),
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
    return parser.parse_args()


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
