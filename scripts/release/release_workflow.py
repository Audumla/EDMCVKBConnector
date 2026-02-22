"""
Run local release preparation and optionally trigger release-please.

This script is VS Code task friendly and supports:
- Configurable changelog summarizer backend (codex / claude-cli / copilot / intelligent)
- Preview-only mode (rebuild changelog + release preview, no GitHub workflow call)
- Optional forced bump intent (major/minor/patch) by dispatching release_as
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

# Ensure we can import from scripts/changelog
sys.path.insert(0, str(Path(__file__).parent.parent / "changelog"))

from changelog_utils import (
    PROJECT_ROOT,
    bump_version,
    find_open_release_pr_version,
    get_git_dirty_files,
    read_current_version,
)


def _run_step(cmd: list[str], cwd: Path) -> int:
    print(f"$ {' '.join(cmd)}")
    proc = subprocess.run(cmd, cwd=cwd)
    return int(proc.returncode)


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare release notes preview and optionally trigger release-please.")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail if duplicate active/non-legacy changelog IDs are detected.",
    )
    parser.add_argument(
        "--skip-summarize",
        action="store_true",
        help="Skip LLM-based changelog summarization.",
    )
    parser.add_argument(
        "--summarize-backend",
        choices=("claude-cli", "codex", "copilot", "gemini", "intelligent"),
        help="Override summarizer backend for this run.",
    )
    parser.add_argument(
        "--preview-output",
        default=str(PROJECT_ROOT / "dist" / "RELEASE_NOTES.preview.md"),
        help="Release preview markdown output path.",
    )
    parser.add_argument(
        "--preview-only",
        action="store_true",
        help="Only run local changelog activity; do not trigger release-please workflow.",
    )
    parser.add_argument(
        "--skip-prepare",
        action="store_true",
        help="Skip local changelog prep (assumes preview/changelog was already generated).",
    )
    parser.add_argument(
        "--bump",
        choices=("auto", "patch", "minor", "major"),
        default="auto",
        help="Requested release bump strategy. auto leaves release-please default behavior.",
    )
    parser.add_argument(
        "--workflow",
        default="release-please.yml",
        help="GitHub Actions workflow file to trigger (default: release-please.yml).",
    )
    parser.add_argument(
        "--gh-bin",
        default="gh",
        help="GitHub CLI executable (default: gh).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print commands without executing them.",
    )
    parser.add_argument(
        "--allow-dirty-dispatch",
        action="store_true",
        help=(
            "Allow workflow dispatch even when tracked files are modified after local prepare. "
            "Use only when you intentionally do not want to commit/push generated local changes first."
        ),
    )
    args = parser.parse_args()

    activity_cmd = [
        sys.executable,
        str(PROJECT_ROOT / "scripts" / "changelog" / "changelog_activity.py"),
        "--preview-output",
        str(Path(args.preview_output)),
    ]
    if args.strict:
        activity_cmd.append("--strict")
    if args.skip_summarize:
        activity_cmd.append("--skip-summarize")
    if args.summarize_backend:
        activity_cmd.extend(["--summarize-backend", args.summarize_backend])

    if args.skip_prepare:
        print("[1/2] Skipping local changelog activity (--skip-prepare).")
    else:
        if args.dry_run:
            print(f"$ {' '.join(activity_cmd)}")
        else:
            print("[1/2] Running changelog activity...")
            rc = _run_step(activity_cmd, PROJECT_ROOT)
            if rc != 0:
                return rc

    if args.preview_only:
        print("Preview generation complete.")
        return 0

    if not args.skip_prepare and not args.allow_dirty_dispatch:
        dirty_files = get_git_dirty_files()
        if dirty_files:
            print(
                "ERROR: Local tracked files changed during release preparation. "
                "Dispatch aborted to avoid releasing with stale local-only changelog state.",
                file=sys.stderr,
            )
            print(
                "Commit/push these files first (or run preview-only, commit, then dispatch with --skip-prepare).",
                file=sys.stderr,
            )
            print("Changed tracked files:", file=sys.stderr)
            for path in dirty_files:
                print(f"  - {path}", file=sys.stderr)
            print(
                "To bypass this safety check intentionally, rerun with --allow-dirty-dispatch.",
                file=sys.stderr,
            )
            return 2

    release_as = None
    if args.bump != "auto":
        current = read_current_version()
        release_as = bump_version(current, args.bump)
        print(f"Requested bump '{args.bump}': {current} -> {release_as}")

    open_release_version = find_open_release_pr_version(args.gh_bin)
    if open_release_version and release_as and open_release_version != release_as:
        print(
            "ERROR: Existing open release PR version conflicts with requested bump: "
            f"open PR={open_release_version}, requested={release_as}.",
            file=sys.stderr,
        )
        print(
            "Close/merge the current release-please PR first, then rerun with your desired --bump.",
            file=sys.stderr,
        )
        return 2
    if open_release_version:
        print(f"Detected open release-please PR for v{open_release_version}.")

    gh_cmd = [args.gh_bin, "workflow", "run", args.workflow]
    if release_as:
        gh_cmd.extend(["-f", f"release_as={release_as}"])

    if args.dry_run:
        print(f"$ {' '.join(gh_cmd)}")
        return 0

    print("[2/2] Triggering release-please workflow...")
    return _run_step(gh_cmd, PROJECT_ROOT)


if __name__ == "__main__":
    raise SystemExit(main())
