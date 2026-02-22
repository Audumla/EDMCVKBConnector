"""
Bump project version across version sources.

Usage:
    python scripts/bump_version.py --part patch
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
PYPROJECT_PATH = PROJECT_ROOT / "pyproject.toml"
VERSION_MODULE_PATH = PROJECT_ROOT / "src" / "edmcruleengine" / "version.py"

SEMVER_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")
PYPROJECT_VERSION_RE = re.compile(
    r'^(version\s*=\s*")(?P<version>\d+\.\d+\.\d+)(")$', re.MULTILINE
)
MODULE_VERSION_RE = re.compile(
    r'^(__version__\s*=\s*")(?P<version>\d+\.\d+\.\d+)(")$', re.MULTILINE
)


def parse_semver(text: str) -> tuple[int, int, int]:
    match = SEMVER_RE.fullmatch(text.strip())
    if not match:
        raise ValueError(f"Invalid semantic version: {text!r}")
    return tuple(int(part) for part in match.groups())


def bump(version: str, part: str) -> str:
    major, minor, patch = parse_semver(version)
    if part == "major":
        major += 1
        minor = 0
        patch = 0
    elif part == "minor":
        minor += 1
        patch = 0
    elif part == "patch":
        patch += 1
    else:
        raise ValueError(f"Unsupported part: {part}")
    return f"{major}.{minor}.{patch}"


def read_versions() -> tuple[str, str]:
    pyproject_text = PYPROJECT_PATH.read_text(encoding="utf-8")
    module_text = VERSION_MODULE_PATH.read_text(encoding="utf-8")

    pyproject_match = PYPROJECT_VERSION_RE.search(pyproject_text)
    module_match = MODULE_VERSION_RE.search(module_text)

    if not pyproject_match:
        raise RuntimeError(f"Could not find project version in {PYPROJECT_PATH}")
    if not module_match:
        raise RuntimeError(f"Could not find __version__ in {VERSION_MODULE_PATH}")

    return pyproject_match.group("version"), module_match.group("version")


def write_versions(new_version: str) -> None:
    pyproject_text = PYPROJECT_PATH.read_text(encoding="utf-8")
    module_text = VERSION_MODULE_PATH.read_text(encoding="utf-8")

    pyproject_text, pyproject_count = PYPROJECT_VERSION_RE.subn(
        rf'\g<1>{new_version}\g<3>', pyproject_text, count=1
    )
    module_text, module_count = MODULE_VERSION_RE.subn(
        rf'\g<1>{new_version}\g<3>', module_text, count=1
    )

    if pyproject_count != 1:
        raise RuntimeError(f"Failed updating version in {PYPROJECT_PATH}")
    if module_count != 1:
        raise RuntimeError(f"Failed updating version in {VERSION_MODULE_PATH}")

    PYPROJECT_PATH.write_text(pyproject_text, encoding="utf-8")
    VERSION_MODULE_PATH.write_text(module_text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Bump semantic version")
    parser.add_argument(
        "--part",
        choices=("major", "minor", "patch"),
        default="patch",
        help="Which version part to bump (default: patch)",
    )
    args = parser.parse_args()

    pyproject_version, module_version = read_versions()
    if pyproject_version != module_version:
        raise RuntimeError(
            "Version mismatch detected: "
            f"pyproject.toml={pyproject_version}, version.py={module_version}. "
            "Sync them before bumping."
        )

    new_version = bump(pyproject_version, args.part)
    write_versions(new_version)
    print(new_version)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
