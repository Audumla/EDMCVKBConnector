"""
Generate release notes from CHANGELOG.json.

Reads the shared agent changelog and outputs a human-readable RELEASE_NOTES.md
grouped by summary tag.

------------------------------------------------------------------------------
How versioning works
------------------------------------------------------------------------------
Agents always write  "plugin_version": "unreleased"  in new CHANGELOG.json
entries.  version.py holds the LAST RELEASED version, so agents must never
read it for changelog purposes.

At release time, this script:
  1. Collects all "unreleased" entries.
  2. Writes RELEASE_NOTES.md for the release body.
  3. With --stamp, updates CHANGELOG.json in-place: replaces every
     "unreleased" with the real version string so the history is permanent.

------------------------------------------------------------------------------
Usage
------------------------------------------------------------------------------

Preview unreleased changes (no file writes to CHANGELOG.json):
    python scripts/generate_release_notes.py --stdout

Write release notes for the current unreleased batch:
    python scripts/generate_release_notes.py
    # -> dist/RELEASE_NOTES.md

Stamp and release (used by the CI workflow):
    python scripts/generate_release_notes.py --stamp 0.3.0
    # writes dist/RELEASE_NOTES.md AND updates CHANGELOG.json in-place

Show all historical entries:
    python scripts/generate_release_notes.py --all --stdout

Show entries for a specific already-released version:
    python scripts/generate_release_notes.py --version 0.2.0 --stdout

Show entries between two released versions:
    python scripts/generate_release_notes.py --since 0.1.0 --version 0.2.0 --stdout

Custom output path:
    python scripts/generate_release_notes.py --output path/to/file.md
"""

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CHANGELOG_PATH = PROJECT_ROOT / "CHANGELOG.json"
CHANGELOG_ARCHIVE_PATH = PROJECT_ROOT / "CHANGELOG.archive.json"
DEFAULT_OUTPUT = PROJECT_ROOT / "dist" / "RELEASE_NOTES.md"

# Display order for approved summary tags
TAG_ORDER = [
    "New Feature",
    "Bug Fix",
    "UI Improvement",
    "Performance Improvement",
    "Code Refactoring",
    "Configuration Cleanup",
    "Build / Packaging",
    "Dependency Update",
    "Test Update",
    "Documentation Update",
]


def get_current_version() -> str:
    ns: dict = {}
    exec((PROJECT_ROOT / "src" / "edmcruleengine" / "version.py").read_text(), ns)
    return str(ns.get("__version__", "0.0.0"))


def load_changelog() -> list[dict]:
    if not CHANGELOG_PATH.exists():
        print(f"ERROR: {CHANGELOG_PATH} not found.", file=sys.stderr)
        sys.exit(1)
    with open(CHANGELOG_PATH, encoding="utf-8") as f:
        return json.load(f)


def save_changelog(entries: list[dict]) -> None:
    with open(CHANGELOG_PATH, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)
        f.write("\n")


def _version_tuple(v: str) -> tuple[int, ...]:
    parts = []
    for p in v.split("."):
        try:
            parts.append(int(p))
        except ValueError:
            parts.append(0)
    return tuple(parts)


def filter_entries(
    entries: list[dict],
    version: str | None,
    since: str | None,
    all_entries: bool,
    unreleased_only: bool,
) -> list[dict]:
    if all_entries:
        return list(entries)

    if unreleased_only:
        return [e for e in entries if e.get("plugin_version") == "unreleased"]

    # Historical version filter — never includes "unreleased" entries
    target = _version_tuple(version) if version else None
    since_t = _version_tuple(since) if since else None

    result = []
    for entry in entries:
        ev_raw = entry.get("plugin_version", "0.0.0")
        if ev_raw == "unreleased":
            continue
        ev = _version_tuple(ev_raw)
        if target and since_t:
            if since_t < ev <= target:
                result.append(entry)
        elif target:
            if ev == target:
                result.append(entry)
    return result


def group_by_tag(entries: list[dict]) -> dict[str, list[str]]:
    """File each entry's detail bullets under its primary summary tag only."""
    buckets: dict[str, list[str]] = {}
    for entry in entries:
        tags = entry.get("summary_tags", ["Other"])
        primary_tag = tags[0] if tags else "Other"
        details = entry.get("details", [entry.get("summary", "")])
        buckets.setdefault(primary_tag, []).extend(details)
    return buckets


def build_markdown(version: str, entries: list[dict]) -> str:
    if not entries:
        return f"# Release Notes — v{version}\n\nNo changelog entries found.\n"

    buckets = group_by_tag(entries)

    dates = [e.get("date", "") for e in entries if e.get("date")]
    date_range = ""
    if dates:
        lo, hi = min(dates), max(dates)
        date_range = lo if lo == hi else f"{lo} - {hi}"

    lines = [f"# Release Notes - v{version}"]
    if date_range:
        lines.append(f"\n_{date_range}_")
    lines.append("")

    ordered_tags = [t for t in TAG_ORDER if t in buckets]
    remaining = [t for t in sorted(buckets) if t not in TAG_ORDER]

    for tag in ordered_tags + remaining:
        lines.append(f"## {tag}")
        for bullet in buckets[tag]:
            lines.append(f"- {bullet}")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("| ID | Date | Agent | Summary |")
    lines.append("|----|------|-------|---------|")
    for e in sorted(entries, key=lambda x: x.get("id", "")):
        lines.append(
            f"| {e.get('id','')} | {e.get('date','')} "
            f"| {e.get('agent','')} | {e.get('summary','')} |"
        )
    lines.append("")

    return "\n".join(lines)


def stamp_changelog(entries: list[dict], version: str) -> int:
    """Replace 'unreleased' with *version* in-place. Returns count stamped."""
    count = 0
    for entry in entries:
        if entry.get("plugin_version") == "unreleased":
            entry["plugin_version"] = version
            count += 1
    return count


def archive_stamped(entries: list[dict]) -> tuple[list[dict], list[dict]]:
    """Split entries into (unreleased, stamped). Append stamped to archive file."""
    unreleased = [e for e in entries if e.get("plugin_version") == "unreleased"]
    stamped = [e for e in entries if e.get("plugin_version") != "unreleased"]

    if stamped:
        existing: list[dict] = []
        if CHANGELOG_ARCHIVE_PATH.exists():
            with open(CHANGELOG_ARCHIVE_PATH, encoding="utf-8") as f:
                existing = json.load(f)
        with open(CHANGELOG_ARCHIVE_PATH, "w", encoding="utf-8") as f:
            json.dump(existing + stamped, f, indent=2, ensure_ascii=False)
            f.write("\n")

    return unreleased, stamped


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate release notes from CHANGELOG.json")

    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--stamp", metavar="VERSION",
        help=(
            "Stamp all 'unreleased' entries with VERSION, write notes, "
            "and update CHANGELOG.json in-place. Used by CI."
        ),
    )
    mode.add_argument(
        "--version", metavar="VERSION",
        help="Show notes for a specific already-released version",
    )
    mode.add_argument(
        "--all", dest="all_entries", action="store_true",
        help="Include all changelog entries regardless of version",
    )

    parser.add_argument(
        "--archive", action="store_true",
        help="With --stamp: move stamped entries to CHANGELOG.archive.json, leaving only 'unreleased' in CHANGELOG.json",
    )
    parser.add_argument(
        "--since", metavar="VERSION",
        help="With --version: include entries > SINCE up to --version",
    )
    parser.add_argument(
        "--output", default=str(DEFAULT_OUTPUT),
        help=f"Output path (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--stdout", action="store_true",
        help="Print to stdout instead of writing a file",
    )
    args = parser.parse_args()

    entries = load_changelog()

    if args.stamp:
        display_version = args.stamp
        filtered = filter_entries(entries, None, None, False, unreleased_only=True)
        if not filtered:
            print("WARNING: No 'unreleased' entries found in CHANGELOG.json.", file=sys.stderr)
    elif args.all_entries:
        display_version = get_current_version()
        filtered = filter_entries(entries, None, None, True, False)
    elif args.version:
        display_version = args.version
        filtered = filter_entries(entries, args.version, args.since, False, False)
    else:
        # Default: preview unreleased entries
        display_version = get_current_version()
        filtered = filter_entries(entries, None, None, False, unreleased_only=True)
        if not filtered:
            print(
                "WARNING: No 'unreleased' entries found. "
                "Use --version <ver> for historical notes or --all for everything.",
                file=sys.stderr,
            )

    md = build_markdown(display_version, filtered)

    if args.stdout:
        print(md)
    else:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(md, encoding="utf-8")
        print(f"Release notes written to {output}")

    # Stamp CHANGELOG.json only when explicitly requested
    if args.stamp and filtered:
        n = stamp_changelog(entries, args.stamp)
        if args.archive:
            remaining, archived = archive_stamped(entries)
            save_changelog(remaining)
            print(f"Stamped {n} entries as v{args.stamp}, archived {len(archived)} to CHANGELOG.archive.json")
        else:
            save_changelog(entries)
            print(f"Stamped {n} entries in CHANGELOG.json as v{args.stamp}")


if __name__ == "__main__":
    main()
