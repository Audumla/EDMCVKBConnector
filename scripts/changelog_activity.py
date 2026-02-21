"""
Run the changelog maintenance activity used before release preparation.

Activity steps:
1) Rebuild CHANGELOG.md from CHANGELOG JSON sources.
2) Generate compact unreleased release-note preview.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from build_changelog import rebuild_changelog_markdown

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PREVIEW = PROJECT_ROOT / "dist" / "RELEASE_NOTES.preview.md"


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
        help="Only rebuild CHANGELOG.md; do not generate release-note preview.",
    )
    parser.add_argument(
        "--skip-summarize",
        action="store_true",
        help="Skip LLM-based changelog summarization (use fallback format).",
    )
    parser.add_argument(
        "--preview-output",
        default=str(DEFAULT_PREVIEW),
        help=f"Compact release-note preview output path (default: {DEFAULT_PREVIEW})",
    )
    args = parser.parse_args()

    # Step 1: Generate LLM summaries (optional)
    if not args.skip_summarize:
        print("Step 1: Generating LLM-based changelog summaries...")
        cmd = [
            sys.executable,
            str(PROJECT_ROOT / "scripts" / "summarize_changelog.py"),
            "--unreleased",
        ]
        proc = subprocess.run(cmd, cwd=PROJECT_ROOT)
        if proc.returncode != 0:
            print("WARNING: Summarization failed; continuing with fallback format.", file=sys.stderr)

    # Step 2: Rebuild CHANGELOG.md
    print("\nStep 2: Rebuilding CHANGELOG.md...")
    rebuild_rc = rebuild_changelog_markdown(strict_duplicates=args.strict, quiet=False)
    if rebuild_rc != 0:
        return rebuild_rc

    if args.skip_preview:
        print("\nChangelog activity complete.")
        return 0

    # Step 3: Generate release-notes preview
    print("\nStep 3: Generating release-notes preview...")
    cmd = [
        sys.executable,
        str(PROJECT_ROOT / "scripts" / "generate_release_notes.py"),
        "--output",
        str(Path(args.preview_output)),
    ]
    proc = subprocess.run(cmd, cwd=PROJECT_ROOT)
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
