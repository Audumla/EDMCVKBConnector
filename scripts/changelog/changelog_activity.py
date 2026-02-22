"""
Run the changelog maintenance activity used before release preparation.

Activity steps:
1) Rebuild CHANGELOG.md from CHANGELOG JSON sources.
2) Build changelog preview with unreleased entries.
3) Generate compact unreleased release-note preview.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

# Ensure we can import from the same directory
sys.path.insert(0, str(Path(__file__).parent))

from build_changelog import rebuild_changelog_markdown

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_RELEASE_NOTES_PREVIEW = PROJECT_ROOT / "dist" / "RELEASE_NOTES.preview.md"
DEFAULT_CHANGELOG_PREVIEW = PROJECT_ROOT / "dist" / "CHANGELOG.preview.md"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run changelog rebuild + release-notes preview activity.")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail if duplicate active/non-legacy changelog IDs are detected.",
    )
    parser.add_argument(
        "--skip-preview",
        action="store_true",
        help="Only rebuild CHANGELOG.md; do not generate preview artifacts.",
    )
    parser.add_argument(
        "--skip-summarize",
        action="store_true",
        help="Skip LLM-based changelog summarization (use fallback format).",
    )
    parser.add_argument(
        "--summarize-backend",
        choices=("claude", "claude-cli", "codex", "copilot", "gemini", "lmstudio", "intelligent"),
        help="Override changelog summarizer backend for this run.",
    )
    parser.add_argument(
        "--preview-output",
        default=str(DEFAULT_RELEASE_NOTES_PREVIEW),
        help=f"Compact release-note preview output path (default: {DEFAULT_RELEASE_NOTES_PREVIEW})",
    )
    parser.add_argument(
        "--changelog-preview-output",
        default=str(DEFAULT_CHANGELOG_PREVIEW),
        help=f"Changelog preview output path (default: {DEFAULT_CHANGELOG_PREVIEW})",
    )
    args = parser.parse_args()

    # Step 1: Generate LLM summaries (optional)
    if not args.skip_summarize:
        print("Step 1: Generating LLM-based changelog summaries...")
        cmd = [
            sys.executable,
            str(PROJECT_ROOT / "scripts" / "changelog" / "summarize_changelog.py"),
            "--unreleased",
        ]
        if args.summarize_backend:
            backend = args.summarize_backend
            if backend == "claude":
                backend = "claude-cli"
            cmd.extend(["--backend", backend])
        proc = subprocess.run(cmd, cwd=PROJECT_ROOT)
        if proc.returncode != 0:
            print("ERROR: Summarization failed. Fix the error or run with --skip-summarize to bypass.", file=sys.stderr)
            return proc.returncode

    # Step 2: Rebuild CHANGELOG.md
    print("\nStep 2: Rebuilding CHANGELOG.md...")
    rebuild_rc = rebuild_changelog_markdown(strict_duplicates=args.strict, quiet=False)
    if rebuild_rc != 0:
        return rebuild_rc

    if args.skip_preview:
        print("\nChangelog activity complete.")
        return 0

    # Step 3: Generate changelog preview with unreleased entries
    print("\nStep 3: Generating changelog preview...")
    changelog_preview_path = Path(args.changelog_preview_output)
    preview_rc = rebuild_changelog_markdown(
        output_path=changelog_preview_path,
        strict_duplicates=args.strict,
        quiet=False,
        include_unreleased=True,
    )
    if preview_rc != 0:
        return preview_rc

    # Step 4: Generate release-notes preview
    print("\nStep 4: Generating release-notes preview...")
    cmd = [
        sys.executable,
        str(PROJECT_ROOT / "scripts" / "changelog" / "generate_release_notes.py"),
        "--output",
        str(Path(args.preview_output)),
    ]
    proc = subprocess.run(cmd, cwd=PROJECT_ROOT)
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
