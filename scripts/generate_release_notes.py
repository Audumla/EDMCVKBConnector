"""
Generate release notes from CHANGELOG.json.

Reads the shared agent changelog, filters entries for a specific plugin
version (or all entries since a previous version), groups them by
summary tag, and writes a human-readable RELEASE_NOTES.md.

The generated file is:
  - Included in the distributable ZIP by package_plugin.py
  - Used as the GitHub release body by the release-please workflow

Usage (local):
    python scripts/generate_release_notes.py
        Uses the current version from src/edmcruleengine/version.py.

    python scripts/generate_release_notes.py --version 0.3.0
        Generates notes for a specific version.

    python scripts/generate_release_notes.py --since 0.2.0 --version 0.3.0
        Generates notes for all changelog entries between two versions.

    python scripts/generate_release_notes.py --all
        Generates notes for every entry in CHANGELOG.json.

    python scripts/generate_release_notes.py --output path/to/file.md
        Write to a custom path (default: dist/RELEASE_NOTES.md).

    python scripts/generate_release_notes.py --stdout
        Print to stdout instead of writing a file (useful for CI piping).
"""

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CHANGELOG_PATH = PROJECT_ROOT / "CHANGELOG.json"
DEFAULT_OUTPUT = PROJECT_ROOT / "dist" / "RELEASE_NOTES.md"

# Display order and human labels for approved summary tags
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


def _version_tuple(v: str) -> tuple[int, ...]:
    """Convert '1.2.3' to (1, 2, 3) for comparison. Non-numeric parts sort last."""
    parts = []
    for p in v.split("."):
        try:
            parts.append(int(p))
        except ValueError:
            parts.append(0)
    return tuple(parts)


def filter_entries(
    entries: list[dict],
    version: str,
    since: str | None,
    all_entries: bool,
) -> list[dict]:
    if all_entries:
        return list(entries)

    target = _version_tuple(version)
    since_t = _version_tuple(since) if since else None

    result = []
    for entry in entries:
        ev = _version_tuple(entry.get("plugin_version", "0.0.0"))
        if since_t:
            # entries strictly between since (exclusive) and version (inclusive)
            if since_t < ev <= target:
                result.append(entry)
        else:
            # entries for exactly this version
            if ev == target:
                result.append(entry)

    return result


def group_by_tag(entries: list[dict]) -> dict[str, list[str]]:
    """Collect all detail bullets, each filed under the entry's primary tag.

    Secondary tags on an entry are shown in the section header only (via the
    summary table at the bottom); they do not duplicate bullets across sections.
    """
    buckets: dict[str, list[str]] = {}
    for entry in entries:
        tags = entry.get("summary_tags", ["Other"])
        primary_tag = tags[0] if tags else "Other"
        details = entry.get("details", [entry.get("summary", "")])
        buckets.setdefault(primary_tag, []).extend(details)
    return buckets


def build_markdown(version: str, entries: list[dict], all_entries: bool) -> str:
    if not entries:
        return f"# Release Notes — v{version}\n\nNo changelog entries found for this version.\n"

    buckets = group_by_tag(entries)

    # Determine date range
    dates = [e.get("date", "") for e in entries if e.get("date")]
    date_range = ""
    if dates:
        lo, hi = min(dates), max(dates)
        date_range = lo if lo == hi else f"{lo} – {hi}"

    lines = [f"# Release Notes — v{version}"]
    if date_range:
        lines.append(f"\n_{date_range}_")
    lines.append("")

    # Ordered sections
    ordered_tags = [t for t in TAG_ORDER if t in buckets]
    remaining = [t for t in sorted(buckets) if t not in TAG_ORDER]

    for tag in ordered_tags + remaining:
        lines.append(f"## {tag}")
        for bullet in buckets[tag]:
            lines.append(f"- {bullet}")
        lines.append("")

    # Summary table of included CHG entries
    lines.append("---")
    lines.append("")
    lines.append("| ID | Date | Agent | Summary |")
    lines.append("|----|------|-------|---------|")
    for e in sorted(entries, key=lambda x: x.get("id", "")):
        lines.append(
            f"| {e.get('id','')} | {e.get('date','')} | {e.get('agent','')} | {e.get('summary','')} |"
        )
    lines.append("")

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate release notes from CHANGELOG.json")
    parser.add_argument("--version", default=None, help="Plugin version to generate notes for (default: current)")
    parser.add_argument("--since", default=None, help="Include entries for versions > SINCE up to --version")
    parser.add_argument("--all", dest="all_entries", action="store_true", help="Include all changelog entries regardless of version")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help=f"Output path (default: {DEFAULT_OUTPUT})")
    parser.add_argument("--stdout", action="store_true", help="Print to stdout instead of writing a file")
    args = parser.parse_args()

    version = args.version or get_current_version()
    entries = load_changelog()
    filtered = filter_entries(entries, version, args.since, args.all_entries)

    if not filtered and not args.all_entries:
        print(
            f"WARNING: No changelog entries found for version {version}. "
            "Use --since <prev_version> to widen the range, or --all for everything.",
            file=sys.stderr,
        )

    md = build_markdown(version, filtered, args.all_entries)

    if args.stdout:
        print(md)
    else:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(md, encoding="utf-8")
        print(f"Release notes written to {output}")


if __name__ == "__main__":
    main()
