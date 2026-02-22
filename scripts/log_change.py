"""
Record a change in CHANGELOG.json and CHANGELOG.md.

Agents should call this script instead of manually editing both files.
It generates a globally unique CHG ID, appends to CHANGELOG.json, and
rebuilds CHANGELOG.md from JSON sources.

Usage
-----
python scripts/log_change.py \
    --agent copilot \
    --group "vkb-link-lifecycle" \
    --tags "New Feature" "Bug Fix" \
    --summary "One-sentence description of what changed" \
    --details "First bullet" "Second bullet" "Third bullet"

All flags are required except --date and --group.

Approved --tags values (use exact strings):
    "Bug Fix"
    "New Feature"
    "Code Refactoring"
    "Configuration Cleanup"
    "Documentation Update"
    "Test Update"
    "Dependency Update"
    "Performance Improvement"
    "UI Improvement"
    "Build / Packaging"
"""

import argparse
import json
import re
import subprocess
import sys
from datetime import date, datetime, timezone
from pathlib import Path

from build_changelog import rebuild_changelog_markdown

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CHANGELOG_JSON = PROJECT_ROOT / "docs" / "changelog" / "CHANGELOG.json"

APPROVED_TAGS = {
    "Bug Fix",
    "New Feature",
    "Code Refactoring",
    "Configuration Cleanup",
    "Documentation Update",
    "Test Update",
    "Dependency Update",
    "Performance Improvement",
    "UI Improvement",
    "Build / Packaging",
}

KNOWN_AGENTS = {"copilot", "claude", "codex", "gemini"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def load_json() -> list[dict]:
    if not CHANGELOG_JSON.exists():
        return []
    with open(CHANGELOG_JSON, encoding="utf-8") as f:
        return json.load(f)


def save_json(entries: list[dict]) -> None:
    with open(CHANGELOG_JSON, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)
        f.write("\n")


def _slugify(value: str, fallback: str = "misc") -> str:
    """Convert text to kebab-case slug."""
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug if slug else fallback


def _extract_group_topic(text: str) -> str:
    """Extract a concise group name from summary/group text.

    Takes first 2-4 key words, resulting in short, focused group names:
    - "Refactor changelog tooling" → "refactor-changelog-tooling"
    - "Migrate all existing IDs" → "migrate-existing-ids"
    - "Fix VKB link recovery" → "fix-vkb-link-recovery"
    """
    # Common filler words to skip when identifying key terms
    stopwords = {
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
        "of", "with", "by", "from", "that", "this", "is", "are", "be", "been",
        "all", "each", "every", "both", "some", "any", "other", "such", "as",
    }

    # Extract words and filter out stopwords
    words = text.lower().split()
    key_words = [w.replace("-", "").replace(",", "").replace(".", "")
                 for w in words if w.replace("-", "").replace(",", "").replace(".", "")
                 and w.replace("-", "").replace(",", "").replace(".", "") not in stopwords]

    # Take up to 4 key words for a concise but meaningful group
    key_words = key_words[:4]

    # Convert to kebab-case
    slug = "-".join(key_words).lower()
    slug = re.sub(r"[^a-z0-9\-]+", "-", slug).strip("-")

    return slug if slug else "misc"


def _git_commit_hash() -> str:
    """Get the current git HEAD commit hash (8 chars)."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short=8", "HEAD"],
            cwd=PROJECT_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()
    except Exception:
        # Fallback: use current timestamp if git fails
        return datetime.now(timezone.utc).strftime("%Y%m%d%H")[:8]


def _default_group(summary: str) -> str:
    """Generate a concise group name from a summary (2-4 key words)."""
    return _extract_group_topic(summary)


def _normalise_group(value: str) -> str:
    """Normalize user-provided group name to kebab-case."""
    slug = _slugify(value, fallback="ungrouped")
    # User-provided groups can be longer if they're being explicit
    return slug if len(slug) <= 40 else slug[:40]


def generate_unique_id(agent: str, existing_ids: set[str]) -> str:
    """Generate a short, globally-unique changelog ID based on git commit hash.

    Format: CHG-<commit-hash>[-counter if needed]

    This approach ensures:
    - Short format (8-12 chars vs 50+)
    - No merge conflicts across branches (commit hash is globally unique)
    - Reproducible (same commit always generates same base ID)
    - Counter suffix only used if multiple changes in same commit
    """
    commit = _git_commit_hash()
    change_id = f"CHG-{commit}"

    # If this ID already exists, add a counter suffix
    if change_id not in existing_ids:
        return change_id

    for counter in range(1, 100):
        candidate = f"CHG-{commit}-{counter}"
        if candidate not in existing_ids:
            return candidate

    raise RuntimeError(f"Could not generate unique changelog ID for commit {commit}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Append a change entry to CHANGELOG.json and CHANGELOG.md.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--agent", required=True, choices=sorted(KNOWN_AGENTS),
        help="Which agent is recording this change",
    )
    parser.add_argument(
        "--tags", required=True, nargs="+", metavar="TAG",
        help="One or more approved summary tags (quoted if they contain spaces)",
    )
    parser.add_argument(
        "--summary", required=True,
        help="One-sentence summary of what changed",
    )
    parser.add_argument(
        "--group",
        help=(
            "Optional workstream/commit grouping key (recommended). "
            "Entries that share a group are condensed together in release notes."
        ),
    )
    parser.add_argument(
        "--details", required=True, nargs="+", metavar="BULLET",
        help="Detail bullets (one string per bullet)",
    )
    parser.add_argument(
        "--date", default=str(date.today()),
        help="Entry date in YYYY-MM-DD format (default: today)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print what would be written without modifying any files",
    )
    args = parser.parse_args()

    # Validate tags
    bad_tags = [t for t in args.tags if t not in APPROVED_TAGS]
    if bad_tags:
        print(
            f"ERROR: Unrecognised tag(s): {bad_tags}\n"
            f"Approved values: {sorted(APPROVED_TAGS)}",
            file=sys.stderr,
        )
        sys.exit(1)

    entries = load_json()
    existing_ids = {str(e.get("id", "")) for e in entries if str(e.get("id", ""))}
    chg_id = generate_unique_id(args.agent, existing_ids)
    change_group = _normalise_group(args.group) if args.group else _default_group(args.summary)

    new_entry = {
        "id": chg_id,
        "change_group": change_group,
        "plugin_version": "unreleased",
        "date": args.date,
        "summary_tags": args.tags,
        "summary": args.summary,
        "details": args.details,
    }

    if args.dry_run:
        print("=== DRY RUN - no files modified ===\n")
        print("CHANGELOG.json entry:")
        print(json.dumps(new_entry, indent=2))
        print("\nCHANGELOG.md will be regenerated from CHANGELOG.json + CHANGELOG.archive.json.")
        return

    entries.append(new_entry)
    save_json(entries)

    rebuild_rc = rebuild_changelog_markdown(quiet=True)
    if rebuild_rc != 0:
        print("ERROR: CHANGELOG.md rebuild failed after writing CHANGELOG.json.", file=sys.stderr)
        sys.exit(rebuild_rc)

    print(f"Recorded {chg_id} [{change_group}]: {args.summary}")


if __name__ == "__main__":
    main()
