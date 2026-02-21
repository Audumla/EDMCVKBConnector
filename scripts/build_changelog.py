"""
Rebuild CHANGELOG.md from CHANGELOG.json and CHANGELOG.archive.json.

This keeps the markdown changelog readable while JSON files remain the
source-of-truth for agent writes and release automation.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CHANGELOG_JSON = PROJECT_ROOT / "docs" / "changelog" / "CHANGELOG.json"
CHANGELOG_ARCHIVE_JSON = PROJECT_ROOT / "docs" / "changelog" / "CHANGELOG.archive.json"
CHANGELOG_MD = PROJECT_ROOT / "CHANGELOG.md"
CHANGELOG_SUMMARIES_JSON = PROJECT_ROOT / "docs" / "changelog" / "CHANGELOG.summaries.json"

LEGACY_NUMERIC_ID = re.compile(r"^CHG-\d+$")


def load_entries(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(f"{path} must contain a JSON array.")
    return [e for e in data if isinstance(e, dict)]


def load_summaries() -> dict:
    """Load cached LLM summaries if available."""
    if not CHANGELOG_SUMMARIES_JSON.exists():
        return {}
    try:
        with open(CHANGELOG_SUMMARIES_JSON, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _safe_text(value: object) -> str:
    text = str(value or "")
    return text.replace("|", r"\|").replace("\n", " ").strip()


def _format_tags(entry: dict) -> str:
    tags = entry.get("summary_tags")
    if isinstance(tags, list):
        return ", ".join(str(t) for t in tags if str(t).strip())
    return ""


def _format_group(entry: dict) -> str:
    return _safe_text(entry.get("change_group", ""))


def _entry_date(entry: dict) -> str:
    return str(entry.get("date", "") or "")


def _entry_id(entry: dict) -> str:
    return str(entry.get("id", "") or "")


def _entry_sort_key(entry: dict) -> tuple[str, str]:
    return (_entry_date(entry), _entry_id(entry))


def _primary_tag(entry: dict) -> str:
    tags = entry.get("summary_tags")
    if isinstance(tags, list) and tags:
        value = str(tags[0]).strip()
        if value:
            return value
    return "Other"


def _group_key(entry: dict) -> str:
    value = str(entry.get("change_group", "")).strip()
    return value if value else "_ungrouped_"


def _entry_count_by_tag(entries: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for entry in entries:
        counts[_primary_tag(entry)] += 1
    return dict(sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])))


def _group_stats(entries: list[dict]) -> list[dict]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for entry in entries:
        grouped[_group_key(entry)].append(entry)

    stats: list[dict] = []
    for group, group_entries in grouped.items():
        group_entries = sorted(group_entries, key=_entry_sort_key)
        latest = group_entries[-1]
        tag_counts = _entry_count_by_tag(group_entries)
        top_tags = ", ".join(list(tag_counts.keys())[:2]) if tag_counts else "Other"
        stats.append(
            {
                "group": group,
                "entries": len(group_entries),
                "latest_date": _entry_date(latest),
                "top_tags": top_tags,
            }
        )
    return sorted(stats, key=lambda x: (x["entries"], x["latest_date"], x["group"]), reverse=True)


def _version_tuple(version: str) -> tuple[int, ...]:
    parts: list[int] = []
    for token in str(version).split("."):
        try:
            parts.append(int(token))
        except ValueError:
            parts.append(0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts)


def _date_range(entries: list[dict]) -> str:
    dates = sorted(d for d in (_entry_date(e) for e in entries) if d)
    if not dates:
        return "-"
    if dates[0] == dates[-1]:
        return dates[0]
    return f"{dates[0]} to {dates[-1]}"


def _is_legacy_numeric_id(change_id: str) -> bool:
    return bool(LEGACY_NUMERIC_ID.match(change_id))


def find_problem_duplicate_ids(current_entries: list[dict], archive_entries: list[dict]) -> dict[str, list[str]]:
    """
    Return duplicate IDs that are likely to cause merge/release issues.

    Rules:
    - Always report duplicate IDs that occur more than once in current entries.
    - Report duplicates for non-legacy IDs anywhere.
    - Ignore legacy numeric IDs duplicated only across current-vs-archive/history.
    """
    locations: dict[str, list[str]] = defaultdict(list)
    for entry in current_entries:
        cid = _entry_id(entry)
        if cid:
            locations[cid].append("current")
    for entry in archive_entries:
        cid = _entry_id(entry)
        if cid:
            locations[cid].append("archive")

    problems: dict[str, list[str]] = {}
    for cid, locs in locations.items():
        if len(locs) < 2:
            continue
        current_count = sum(1 for src in locs if src == "current")
        if current_count > 1:
            problems[cid] = locs
            continue
        if not _is_legacy_numeric_id(cid):
            problems[cid] = locs
    return problems


def build_markdown(
    current_entries: list[dict],
    archive_entries: list[dict],
    use_summaries: bool = True,
    summaries: dict | None = None,
) -> str:
    """Build markdown changelog, optionally using LLM-generated summaries."""
    if summaries is None:
        summaries = {}

    unreleased = [e for e in current_entries if e.get("plugin_version") == "unreleased"]
    released = [e for e in (archive_entries + current_entries) if e.get("plugin_version") not in ("", None, "unreleased")]

    unreleased.sort(key=_entry_sort_key, reverse=True)

    released_by_version: dict[str, list[dict]] = defaultdict(list)
    for entry in released:
        released_by_version[str(entry.get("plugin_version"))].append(entry)
    for version_entries in released_by_version.values():
        version_entries.sort(key=_entry_sort_key)

    versions = sorted(released_by_version.keys(), key=_version_tuple, reverse=True)

    lines: list[str] = []
    lines.append("# Changelog")
    lines.append("")
    lines.append(
        "> Source of truth: `CHANGELOG.json` (unreleased) and `CHANGELOG.archive.json` (released history)."
    )
    lines.append("")

    # Unreleased section
    lines.append("## [Unreleased]")
    lines.append("")
    if unreleased:
        # Try to use LLM summary
        unreleased_summary = None
        if use_summaries and summaries:
            for key, value in summaries.items():
                if key.startswith("unreleased:"):
                    unreleased_summary = value
                    break

        if unreleased_summary:
            lines.append(unreleased_summary)
            lines.append("")
        else:
            # Fallback to stats view
            group_stats = _group_stats(unreleased)
            tag_counts = _entry_count_by_tag(unreleased)
            lines.append(
                f"Pending {len(unreleased)} entries across {len(group_stats)} workstreams."
            )
            lines.append("")
            lines.append("| Area | Entries |")
            lines.append("|------|---------|")
            for tag, count in tag_counts.items():
                lines.append(f"| {_safe_text(tag)} | {count} |")
            lines.append("")
    else:
        lines.append("_No unreleased entries._")
        lines.append("")

    # Released versions section
    for version in versions:
        entries = released_by_version[version]
        date_range = _date_range(entries)

        lines.append("---")
        lines.append("")
        version_header = f"## v{version}"
        if date_range:
            version_header += f" — {date_range}"
        lines.append(version_header)
        lines.append("")

        # Try to use LLM summary
        version_summary = None
        if use_summaries and summaries:
            for key, value in summaries.items():
                if key.startswith(f"{version}:"):
                    version_summary = value
                    break

        if version_summary:
            lines.append(version_summary)
            lines.append("")
        else:
            # Fallback to stats view
            tag_counts = _entry_count_by_tag(entries)
            groups = _group_stats(entries)
            top_areas = ", ".join(list(tag_counts.keys())[:3]) if tag_counts else "Other"
            lines.append(
                f"_Condensed {len(entries)} entries across {len(groups)} workstreams._"
            )
            lines.append(f"_Primary areas: {top_areas}_")
            lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def rebuild_changelog_markdown(
    output_path: Path | None = None,
    strict_duplicates: bool = False,
    quiet: bool = False,
    use_summaries: bool = True,
) -> int:
    current_entries = load_entries(CHANGELOG_JSON)
    archive_entries = load_entries(CHANGELOG_ARCHIVE_JSON)

    duplicate_ids = find_problem_duplicate_ids(current_entries, archive_entries)
    if duplicate_ids:
        ids = sorted(duplicate_ids.keys())
        if strict_duplicates:
            print(
                "ERROR: Duplicate changelog IDs detected in active/non-legacy entries:\n"
                + "\n".join(f"  - {cid} ({', '.join(duplicate_ids[cid])})" for cid in ids),
                file=sys.stderr,
            )
            return 1
        if not quiet:
            print(
                "WARNING: Duplicate changelog IDs detected (legacy archive duplicates are ignored). "
                "Run with --strict to fail.\n"
                + "\n".join(f"  - {cid} ({', '.join(duplicate_ids[cid])})" for cid in ids),
                file=sys.stderr,
            )

    summaries = load_summaries() if use_summaries else {}
    rendered = build_markdown(current_entries, archive_entries, use_summaries=use_summaries, summaries=summaries)
    path = output_path or CHANGELOG_MD
    path.write_text(rendered, encoding="utf-8")

    if not quiet:
        unreleased = sum(1 for e in current_entries if e.get("plugin_version") == "unreleased")
        released = sum(1 for e in archive_entries if e.get("plugin_version") != "unreleased")
        print(
            f"Rebuilt {path} "
            f"(unreleased: {unreleased}, archived: {released}, duplicate_ids: {len(duplicate_ids)})"
        )

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Rebuild CHANGELOG.md from changelog JSON sources.")
    parser.add_argument(
        "--output",
        default=str(CHANGELOG_MD),
        help=f"Markdown output path (default: {CHANGELOG_MD})",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail if duplicate changelog IDs are detected in active/non-legacy entries.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress non-error output.",
    )
    parser.add_argument(
        "--no-summaries",
        action="store_true",
        help="Don't use LLM-generated summaries (use fallback format instead).",
    )
    args = parser.parse_args()

    return rebuild_changelog_markdown(
        output_path=Path(args.output),
        strict_duplicates=args.strict,
        quiet=args.quiet,
        use_summaries=not args.no_summaries,
    )


if __name__ == "__main__":
    raise SystemExit(main())
