#!/usr/bin/env python
"""
Migrate CHANGELOG.json entries from old timestamp-based IDs to new commit-hash-based IDs.

Old format: CHG-20260221T085528186611Z-main-codex-7267
New format: CHG-55c6ba67

This script finds the commit that introduced each entry and uses its hash.
"""

import json
import re
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CHANGELOG_JSON = PROJECT_ROOT / "docs" / "changelog" / "CHANGELOG.json"
CHANGELOG_ARCHIVE_JSON = PROJECT_ROOT / "docs" / "changelog" / "CHANGELOG.archive.json"


def git_log_short_hashes_by_date(date_str: str, file_path: Path) -> list[str]:
    """Get commits that modified a file on a specific date (with ±1 day tolerance)."""
    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d")
        start_date = (target_date - timedelta(days=1)).isoformat()
        end_date = (target_date + timedelta(days=1)).isoformat()

        result = subprocess.run(
            [
                "git",
                "log",
                "--since", start_date,
                "--until", end_date,
                "--pretty=format:%h",
                "--",
                str(file_path),
            ],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        hashes = result.stdout.strip().split("\n")
        return [h for h in hashes if h]
    except Exception:
        return []


def extract_timestamp_from_old_id(old_id: str) -> Optional[str]:
    """Extract timestamp from old format ID: CHG-20260221T085528186611Z-..."""
    match = re.match(r"^CHG-(\d{8}T\d{6})\d+Z", old_id)
    if match:
        return match.group(1)
    return None


def date_from_timestamp(timestamp_str: str) -> str:
    """Convert YYYYMMDDTHHmmss to YYYY-MM-DD."""
    try:
        dt = datetime.strptime(timestamp_str, "%Y%m%dT%H%M%S")
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        return ""


def find_best_commit_hash(entry: dict, file_path: Path) -> Optional[str]:
    """Find the best matching commit hash for an entry."""
    entry_date = entry.get("date", "")
    if not entry_date:
        return None

    hashes = git_log_short_hashes_by_date(entry_date, file_path)
    if hashes:
        # Return the most recent commit from that date
        return hashes[0]

    # Fallback: try extracting from old ID timestamp
    old_id = entry.get("id", "")
    timestamp = extract_timestamp_from_old_id(old_id)
    if timestamp:
        date = date_from_timestamp(timestamp)
        if date:
            hashes = git_log_short_hashes_by_date(date, file_path)
            if hashes:
                return hashes[0]

    return None


def generate_new_id(commit_hash: Optional[str], existing_ids: set[str], fallback_prefix: str = "LEGACY") -> str:
    """Generate a new ID based on commit hash or fallback."""
    if commit_hash:
        new_id = f"CHG-{commit_hash}"
        if new_id not in existing_ids:
            return new_id

        # If conflict, add counter
        for counter in range(1, 100):
            candidate = f"CHG-{commit_hash}-{counter}"
            if candidate not in existing_ids:
                return candidate

    # Fallback for entries where we can't find a commit
    return fallback_prefix


def migrate_file(file_path: Path, is_archive: bool = False, global_existing_ids: set[str] | None = None) -> dict[str, str]:
    """Migrate IDs in a changelog file. Returns mapping of old_id -> new_id.

    For archive files, prepends 'a' to commit hash to avoid collisions with current entries.
    """
    if not file_path.exists():
        return {}

    with open(file_path, encoding="utf-8") as f:
        entries = json.load(f)

    if not isinstance(entries, list):
        print(f"ERROR: {file_path} must be a JSON list")
        return {}

    if global_existing_ids is None:
        global_existing_ids = set()

    id_mapping = {}

    for entry in entries:
        old_id = entry.get("id", "")
        if not old_id:
            continue

        # Skip if already in new format
        if re.match(r"^CHG-[0-9a-f]{7,8}(\-\d+)?$", old_id):
            global_existing_ids.add(old_id)
            id_mapping[old_id] = old_id
            continue

        # For archive entries, use archive-specific prefix to avoid collisions
        if is_archive:
            # Use simple incremental format for archived entries: CHG-arc-NNN
            # Extract the number from old ID if it's numeric
            match = re.match(r"CHG-(\d+)", old_id)
            if match:
                number = match.group(1)
                new_id = f"CHG-arc-{number.zfill(3)}"
            else:
                new_id = f"CHG-arc-{old_id.replace('CHG-', '')}"
        else:
            # For current entries, use commit hash
            commit_hash = find_best_commit_hash(entry, file_path)
            new_id = generate_new_id(commit_hash, global_existing_ids, fallback_prefix=old_id)

        if new_id not in global_existing_ids:
            entry["id"] = new_id
            global_existing_ids.add(new_id)
            id_mapping[old_id] = new_id
            print(f"  {old_id:55s} -> {new_id}")
        else:
            # Handle collision by adding counter
            for counter in range(1, 1000):
                candidate = f"{new_id}-{counter}"
                if candidate not in global_existing_ids:
                    entry["id"] = candidate
                    global_existing_ids.add(candidate)
                    id_mapping[old_id] = candidate
                    print(f"  {old_id:55s} -> {candidate}")
                    break

    # Save updated entries
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)
        f.write("\n")

    return id_mapping


def main() -> None:
    print("=" * 80)
    print("CHANGELOG.json ID Migration: timestamp-based -> commit-hash-based")
    print("=" * 80)
    print()

    # Use a shared set to track IDs across both files
    global_existing_ids: set[str] = set()

    # Migrate main changelog
    print("Migrating CHANGELOG.json...")
    main_mapping = migrate_file(CHANGELOG_JSON, is_archive=False, global_existing_ids=global_existing_ids)

    print()
    print("Migrating CHANGELOG.archive.json...")
    archive_mapping = migrate_file(CHANGELOG_ARCHIVE_JSON, is_archive=True, global_existing_ids=global_existing_ids)

    # Summary
    all_migrations = len(main_mapping) + len(archive_mapping)
    unchanged = sum(
        1 for mapping in [main_mapping, archive_mapping]
        for old_id, new_id in mapping.items()
        if old_id == new_id
    )

    print()
    print("=" * 80)
    print(f"Migration complete!")
    print(f"  Total entries processed: {all_migrations}")
    print(f"  Already in new format: {unchanged}")
    print(f"  Converted: {all_migrations - unchanged}")
    print()
    print("Rebuilt CHANGELOG.md from JSON sources (next step)...")

    # Rebuild CHANGELOG.md
    from build_changelog import rebuild_changelog_markdown
    rc = rebuild_changelog_markdown(quiet=False)
    if rc == 0:
        print("[OK] Migration and rebuild successful!")
    else:
        print(f"[ERROR] Rebuild failed with return code {rc}")


if __name__ == "__main__":
    main()
