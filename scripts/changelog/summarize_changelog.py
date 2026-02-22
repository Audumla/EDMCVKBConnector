"""
Generate intelligent LLM-based changelog summaries.

This script reads CHANGELOG.json + CHANGELOG.archive.json, groups entries by
version, and uses Claude CLI or Codex CLI to generate readable, human-friendly
summaries for each release. Summaries are cached in CHANGELOG.summaries.json.
"""

import argparse
import hashlib
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from collections import defaultdict
from pathlib import Path

from changelog_utils import (
    CHANGELOG_ARCHIVE_JSON,
    CHANGELOG_JSON,
    TAG_ORDER,
    _intelligent_tag_summary,
    build_change_groups,
    group_by_tag,
    load_config,
    load_json_list,
    load_summaries,
    run_llm_with_fallback,
    save_summaries,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def _common_cfg(config: dict) -> dict:
    common = config.get("common")
    if isinstance(common, dict):
        return common
    return config


def load_entries(path: Path) -> list[dict]:
    return load_json_list(path)


def group_entries_by_version(entries: list[dict]) -> dict[str, list[dict]]:
    """Group entries by plugin_version."""
    grouped: dict[str, list[dict]] = defaultdict(list)
    for entry in entries:
        version = str(entry.get("plugin_version", "unreleased"))
        grouped[version].append(entry)
    return dict(grouped)


def compute_version_hash(entries: list[dict]) -> str:
    """Compute a hash of entry IDs to detect changes."""
    ids = sorted(str(e.get("id", "")) for e in entries if str(e.get("id", "")))
    content = "\n".join(ids)
    return hashlib.sha256(content.encode()).hexdigest()[:12]


def format_entries_for_prompt(entries: list[dict], version: str, config: dict | None = None) -> str:
    """Format changelog entries concisely for LLM context."""
    if config is None:
        config = {}
    
    # Use version context only in the header
    lines = [f"# Changes for v{version}", ""]

    if not entries:
        return "No changes found."

    # Format entries as a compact list
    for entry in entries:
        tags = entry.get("summary_tags")
        tag_str = ", ".join(str(t) for t in tags) if tags else "Misc"
        summary = str(entry.get("summary", "")).strip()
        
        # Output: [Tags] Summary
        lines.append(f"[{tag_str}] {summary}")
        
        # Details as sub-bullets (strip internal IDs if they somehow leaked into details)
        details = entry.get("details", [])
        if isinstance(details, list):
            for detail in details:
                # Basic cleaning of detail strings
                clean_detail = str(detail).strip()
                if clean_detail:
                    lines.append(f"  - {clean_detail}")
    
    lines.append("\n---\n")
    
    # Minimal instructions
    requirements = _common_cfg(config).get("changelog_prompt_requirements", [])
    lines.append("Generate a human-readable summary following these rules:")
    for requirement in requirements:
        lines.append(f"- {requirement}")

    return "\n".join(lines).strip()


def _build_intelligent_summary(entries: list[dict], version: str) -> str | None:
    """Build deterministic grouped summary without external LLM/API calls."""
    if not entries:
        return None

    groups = build_change_groups(entries)
    buckets = group_by_tag(groups)
    if not buckets:
        return None

    tag_order = [t for t in TAG_ORDER if t in buckets] + [t for t in sorted(buckets) if t not in TAG_ORDER]
    top_focus = ", ".join(tag_order[:3]) if tag_order else "multiple areas"

    lines = [
        "### Overview",
        "",
        (
            f"This release includes {len(entries)} changelog updates across "
            f"{len(groups)} grouped workstreams, focused on {top_focus}."
        ),
        "",
    ]

    section_map = {
        "Bug Fix": "Bug Fixes",
        "New Feature": "New Features",
        "Code Refactoring": "Improvements",
        "Configuration Cleanup": "Improvements",
        "Build / Packaging": "Build and Packaging",
        "Documentation Update": "Documentation",
        "Test Update": "Testing",
        "Dependency Update": "Dependencies",
        "UI Improvement": "UI Improvements",
        "Performance Improvement": "Performance Improvements",
    }

    for tag in tag_order:
        title = section_map.get(tag, tag)
        tag_groups = sorted(
            buckets[tag],
            key=lambda g: (g["entry_count"], g["latest_date"], g["headline"]),
            reverse=True,
        )
        lines.append(f"### {title}")
        lines.append(f"- {_intelligent_tag_summary(tag, tag_groups)}")
        lines.append("")

    return "\n".join(lines).strip()


def summarize_version(version: str, entries: list[dict], config: dict, force: bool = False) -> str | None:
    """Summarize a version using the configured LLM backend."""
    if not entries:
        return None

    # Check cache
    cache = load_summaries()
    version_hash = compute_version_hash(entries)
    cache_key = f"{version}:{version_hash}"

    if not force and cache_key in cache:
        print(f"  [{version}] Using cached summary")
        return cache[cache_key]

    print(f"  [{version}] Calling LLM...")

    prompt = format_entries_for_prompt(entries, version, config)
    backend = config.get("backend", "intelligent")

    summary = None
    if backend == "intelligent":
        summary = _build_intelligent_summary(entries, version)
    else:
        # Use fallback logic for LLM backends
        summary, used_backend = run_llm_with_fallback(prompt, config, preferred_backend=backend, entries=entries)
        if not summary:
            print(f"  [{version}] Fallback: using intelligent summarizer.")
            summary = _build_intelligent_summary(entries, version)

    if not summary:
        print(f"  [{version}] Failed to generate summary", file=sys.stderr)
        return None

    # Update cache
    cache[cache_key] = summary
    save_summaries(cache)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate LLM-based changelog summaries")

    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--all", action="store_true", help="Summarize all versions (unreleased + released)")
    mode.add_argument("--unreleased", action="store_true", help="Summarize only unreleased entries")
    mode.add_argument(
        "--version",
        metavar="VERSION",
        help="Summarize a specific version",
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="Regenerate summaries even if cached",
    )
    parser.add_argument(
        "--backend",
        choices=["claude-cli", "codex", "copilot", "gemini", "lmstudio", "intelligent"],
        help="Override the configured LLM backend",
    )

    args = parser.parse_args()

    # Validate summary cache before any writes so malformed JSON never gets silently replaced.
    try:
        load_summaries()
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    # Load data
    current_entries = load_entries(CHANGELOG_JSON)
    archive_entries = load_entries(CHANGELOG_ARCHIVE_JSON)
    all_entries = archive_entries + current_entries

    # Load config
    config = load_config()
    if args.backend:
        config["backend"] = args.backend

    # Determine what to summarize
    if args.unreleased:
        target_entries = [e for e in current_entries if e.get("plugin_version") == "unreleased"]
        versions_to_summarize = {"unreleased": target_entries}
    elif args.version:
        target_entries = [e for e in all_entries if e.get("plugin_version") == args.version]
        versions_to_summarize = {args.version: target_entries}
    elif args.all:
        versions_to_summarize = group_entries_by_version(all_entries)
    else:
        # Default: unreleased only
        target_entries = [e for e in current_entries if e.get("plugin_version") == "unreleased"]
        versions_to_summarize = {"unreleased": target_entries}

    if not versions_to_summarize:
        print("No entries to summarize.")
        return 0

    print(f"Summarizing {len(versions_to_summarize)} version(s) using backend: {config.get('backend', 'intelligent')}")
    print()

    # Sort versions for predictable processing (unreleased first, then by version desc)
    def sort_key(item: tuple[str, list]) -> tuple[bool, tuple]:
        version = item[0]
        if version == "unreleased":
            return (0, (0, 0, 0))
        try:
            parts = tuple(int(p) for p in version.split("."))
            return (1, tuple(-p for p in parts))
        except:
            return (1, (0, 0, 0))

    sorted_versions = sorted(versions_to_summarize.items(), key=sort_key)

    success_count = 0
    resolved_hashes: dict[str, str] = {}
    for version, entries in sorted_versions:
        resolved_hashes[version] = compute_version_hash(entries) if entries else ""
        result = summarize_version(version, entries, config, force=args.force)
        if result:
            success_count += 1

    # Keep cache clean for processed versions when force-regenerating.
    # Also always prune stale unreleased cache keys on unreleased/default runs.
    unreleased_mode = args.unreleased or (not args.version and not args.all)
    versions_to_prune: set[str] = set()
    if args.force:
        versions_to_prune.update(resolved_hashes.keys())
    if unreleased_mode and "unreleased" in resolved_hashes:
        versions_to_prune.add("unreleased")

    if versions_to_prune:
        cache = load_summaries()
        updated = False
        for version in versions_to_prune:
            vhash = resolved_hashes.get(version, "")
            keep_key = f"{version}:{vhash}" if vhash else None
            for key in list(cache.keys()):
                if not key.startswith(f"{version}:"):
                    continue
                if keep_key and key == keep_key:
                    continue
                del cache[key]
                updated = True
        if updated:
            save_summaries(cache)

    print()
    print(f"Successfully generated {success_count}/{len(versions_to_summarize)} summaries")
    return 0 if success_count > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
