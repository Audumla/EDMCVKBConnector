"""
Record a change in CHANGELOG.json and CHANGELOG.md.

Agents should call this script instead of manually editing both files.
It auto-increments the CHG-NNN ID, appends to CHANGELOG.json, and
prepends the summary row + detail section to CHANGELOG.md.

Usage
-----
python scripts/log_change.py \\
    --agent copilot \\
    --tags "New Feature" "Bug Fix" \\
    --summary "One-sentence description of what changed" \\
    --details "First bullet" "Second bullet" "Third bullet"

All flags are required except --date (defaults to today).

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
import sys
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CHANGELOG_JSON = PROJECT_ROOT / "CHANGELOG.json"
CHANGELOG_MD = PROJECT_ROOT / "CHANGELOG.md"

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

KNOWN_AGENTS = {"copilot", "claude", "codex"}


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


def next_id(entries: list[dict]) -> str:
    """Return the next CHG-NNN id, incrementing from the highest existing one."""
    max_n = 0
    for entry in entries:
        m = re.match(r"CHG-(\d+)", entry.get("id", ""))
        if m:
            max_n = max(max_n, int(m.group(1)))
    return f"CHG-{max_n + 1:03d}"


def build_md_row(chg_id: str, entry_date: str, tags: list[str], summary: str) -> str:
    tag_str = ", ".join(tags)
    return f"| {chg_id} | {entry_date} | {tag_str} | {summary} |"


def build_md_section(chg_id: str, entry_date: str, tags: list[str],
                     summary: str, details: list[str]) -> str:
    tag_str = ", ".join(tags)
    bullets = "\n".join(f"- {d}" for d in details)
    return (
        f"### {chg_id} \u2014 {entry_date} \u00b7 unreleased\n\n"
        f"**Tags:** {tag_str}\n\n"
        f"**Summary:** {summary}\n\n"
        f"**Changes:**\n{bullets}\n"
    )


def insert_into_md(chg_id: str, entry_date: str, tags: list[str],
                   summary: str, details: list[str]) -> None:
    if not CHANGELOG_MD.exists():
        print(f"WARNING: {CHANGELOG_MD} not found — skipping markdown update.", file=sys.stderr)
        return

    content = CHANGELOG_MD.read_text(encoding="utf-8")

    # Migrate legacy table headers that included an "Agent" column.
    content = content.replace(
        "| ID | Date | Agent | Tags | Summary |\n|----|------|-------|------|---------|",
        "| ID | Date | Tags | Summary |\n|----|------|------|---------|",
    )

    # Insert new row at the top of the summary table (after the header row and separator)
    table_header_pattern = re.compile(
        r"(\| ID \| Date \| Tags \| Summary \|\n\|[-| ]+\|\n)",
        re.MULTILINE,
    )
    new_row = build_md_row(chg_id, entry_date, tags, summary)
    if table_header_pattern.search(content):
        content = table_header_pattern.sub(
            r"\g<1>" + new_row + "\n",
            content,
            count=1,
        )
    else:
        print("WARNING: Could not locate summary table in CHANGELOG.md — row not inserted.", file=sys.stderr)

    # Insert new detail section above the first existing ### CHG- section
    new_section = build_md_section(chg_id, entry_date, tags, summary, details)
    detail_anchor = re.compile(r"(^### CHG-)", re.MULTILINE)
    if detail_anchor.search(content):
        content = detail_anchor.sub(new_section + "\n### CHG-", content, count=1)
    else:
        # No existing sections yet — append after "## Detail"
        content = re.sub(r"(## Detail\n)", r"\g<1>\n" + new_section, content, count=1)

    CHANGELOG_MD.write_text(content, encoding="utf-8")


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
        help="Which agent is recording this change (accepted for compatibility; not written to changelog output)",
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
    chg_id = next_id(entries)

    new_entry = {
        "id": chg_id,
        "plugin_version": "unreleased",
        "date": args.date,
        "summary_tags": args.tags,
        "summary": args.summary,
        "details": args.details,
    }

    if args.dry_run:
        print("=== DRY RUN — no files modified ===\n")
        print("CHANGELOG.json entry:")
        print(json.dumps(new_entry, indent=2))
        print("\nCHANGELOG.md row:")
        print(build_md_row(chg_id, args.date, args.tags, args.summary))
        print("\nCHANGELOG.md section:")
        print(build_md_section(chg_id, args.date, args.tags, args.summary, args.details))
        return

    entries.append(new_entry)
    save_json(entries)
    insert_into_md(chg_id, args.date, args.tags, args.summary, args.details)

    print(f"Recorded {chg_id}: {args.summary}")


if __name__ == "__main__":
    main()
