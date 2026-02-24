"""
build_changelog.py - Rebuild CHANGELOG.md from JSON sources.
"""
from pathlib import Path
from datetime import datetime
from changelog_utils import (
    get_changes_grouped_by_version,
    format_version_header,
    get_summaries,
    CHANGELOG_MD
)

def main():
    versions = get_changes_grouped_by_version()
    summaries = get_summaries()
    
    lines = ["# Changelog", ""]
    
    # Sort versions descending
    sorted_v = sorted(versions.keys(), reverse=True)
    if "unreleased" in sorted_v:
        sorted_v.remove("unreleased")
        sorted_v.insert(0, "unreleased")
        
    for v in sorted_v:
        changes = versions[v]
        date = changes[0].get("date", "unknown")
        lines.append(format_version_header(v, date))
        lines.append("")
        
        # Add summary if it exists
        summary_key = f"{v}" # Simplified for this modular proof
        for key in summaries:
            if key.startswith(v):
                lines.append(summaries[key])
                lines.append("")
                break
        
        # Group by change type
        for c in changes:
            tags = ", ".join(c.get("summary_tags", []))
            lines.append(f"### {c['summary']} ({tags})")
            for d in c.get("details", []):
                lines.append(f"- {d}")
            lines.append("")
        lines.append("---")
        lines.append("")

    CHANGELOG_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"Rebuilt {CHANGELOG_MD} (versions: {len(sorted_v)})")

def rebuild_changelog_markdown(quiet=False):
    """Wrapper for log_change.py compatibility."""
    main()
    return 0

if __name__ == "__main__":
    main()
