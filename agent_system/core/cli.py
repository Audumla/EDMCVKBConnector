"""
cli.py - Entry point for the `agent` CLI command (registered in pyproject.toml).

After `pip install -e .` or `pip install .`, the `agent` command delegates
directly to install.py which lives at the root of the runtime directory.
"""
from __future__ import annotations

import sys
from pathlib import Path


def main() -> None:
    install_py = Path(__file__).resolve().parent.parent.parent / "install.py"
    if not install_py.exists():
        print(f"[agent-system] ERROR: install.py not found at {install_py}", file=sys.stderr)
        sys.exit(1)

    # Re-exec install.py with the same arguments, replacing this process.
    # We import and call main() directly to avoid a subprocess round-trip.
    import importlib.util
    spec = importlib.util.spec_from_file_location("install", install_py)
    module = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    sys.exit(module.main())


if __name__ == "__main__":
    main()
