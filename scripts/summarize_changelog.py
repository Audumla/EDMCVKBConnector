"""
Generate intelligent LLM-based changelog summaries.

This script reads CHANGELOG.json + CHANGELOG.archive.json, groups entries by
version, and uses Claude or Codex to generate readable, human-friendly summaries
for each release. Summaries are cached in CHANGELOG.summaries.json.
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CHANGELOG_JSON = PROJECT_ROOT / "docs" / "changelog" / "CHANGELOG.json"
CHANGELOG_ARCHIVE_JSON = PROJECT_ROOT / "docs" / "changelog" / "CHANGELOG.archive.json"
CHANGELOG_SUMMARIES_JSON = PROJECT_ROOT / "docs" / "changelog" / "CHANGELOG.summaries.json"
CONFIG_DEFAULTS = PROJECT_ROOT / "docs" / "changelog" / "changelog-config.json"


def load_config() -> dict:
    """Load changelog summarizer config from changelog-config.json."""
    if not CONFIG_DEFAULTS.exists():
        return {
            "backend": "claude",
            "claude_model": "claude-haiku-4-5-20251001",
            "max_tokens": 1500,
            "codex_model": "gpt-5-mini",
        }
    try:
        with open(CONFIG_DEFAULTS, encoding="utf-8") as f:
            config = json.load(f)
        return config.get("changelog_summarization", {})
    except Exception as e:
        print(f"WARNING: Failed to load config: {e}", file=sys.stderr)
        return {}


def load_entries(path: Path) -> list[dict]:
    """Load changelog entries from JSON file."""
    if not path.exists():
        return []
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return [e for e in data if isinstance(e, dict)] if isinstance(data, list) else []
    except Exception as e:
        print(f"ERROR: Failed to load {path}: {e}", file=sys.stderr)
        return []


def load_summaries() -> dict:
    """Load cached summaries from CHANGELOG.summaries.json."""
    if not CHANGELOG_SUMMARIES_JSON.exists():
        return {}
    try:
        with open(CHANGELOG_SUMMARIES_JSON, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_summaries(summaries: dict) -> None:
    """Save summaries to CHANGELOG.summaries.json."""
    with open(CHANGELOG_SUMMARIES_JSON, "w", encoding="utf-8") as f:
        json.dump(summaries, f, indent=2, ensure_ascii=False)
        f.write("\n")


def group_entries_by_version(entries: list[dict]) -> dict[str, list[dict]]:
    """Group entries by plugin_version."""
    grouped: dict[str, list[dict]] = defaultdict(list)
    for entry in entries:
        version = str(entry.get("plugin_version", "unreleased"))
        grouped[version].append(entry)
    return dict(grouped)


def compute_version_hash(entries: list[dict]) -> str:
    """Compute a hash of entry IDs to detect changes."""
    ids = sorted(str(e.get("id", "")) for e in entries)
    content = "\n".join(ids)
    return hashlib.sha256(content.encode()).hexdigest()[:12]


def format_entries_for_prompt(entries: list[dict], version: str) -> str:
    """Format changelog entries into a prompt for the LLM."""
    lines = [f"# Summarize changelog entries for version {version}", ""]

    if not entries:
        lines.append("(No entries)")
        return "\n".join(lines)

    lines.append("Entries:")
    lines.append("")

    for entry in entries:
        tags = entry.get("summary_tags", [])
        tag_str = ", ".join(str(t) for t in tags) if tags else "Other"
        summary = str(entry.get("summary", "")).strip()

        lines.append(f"[{tag_str}] {summary}")

        details = entry.get("details", [])
        if isinstance(details, list):
            for detail in details:
                lines.append(f"  - {detail}")

        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append(
        "Write a human-readable changelog summary that:\n"
        "- Starts with 1-2 sentences describing what this release focuses on\n"
        "- Groups changes under ### Bug Fixes, ### New Features, ### Improvements, etc. as appropriate\n"
        "- Uses plain English bullet points that users can understand\n"
        "- Omits internal IDs, workstream slugs, and technical jargon\n"
        "- Only includes sections that have actual changes\n"
        "- Returns only the markdown sections (no extra commentary)"
    )

    return "\n".join(lines)


def call_claude_api(prompt: str, config: dict) -> str | None:
    """Call Claude API for summarization."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY environment variable not set", file=sys.stderr)
        return None

    try:
        from anthropic import Anthropic
    except ImportError:
        print("ERROR: anthropic package not installed. Run: pip install anthropic", file=sys.stderr)
        return None

    try:
        client = Anthropic(api_key=api_key)
        model = config.get("claude_model", "claude-haiku-4-5-20251001")
        max_tokens = config.get("max_tokens", 1500)

        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )

        return response.content[0].text if response.content else None
    except Exception as e:
        print(f"ERROR: Failed to call Claude API: {e}", file=sys.stderr)
        return None


def call_codex_api(prompt: str, config: dict) -> str | None:
    """Call Codex CLI for summarization."""
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            plan_file = Path(tmpdir) / "plan.md"
            plan_file.write_text(prompt, encoding="utf-8")

            result = subprocess.run(
                ["codex", "run", "--plan", str(plan_file), "--output-dir", tmpdir],
                capture_output=True,
                text=True,
                timeout=300,
            )

            if result.returncode != 0:
                print(f"ERROR: Codex failed: {result.stderr}", file=sys.stderr)
                return None

            # Try to read the Codex output file
            output_file = Path(tmpdir) / "output.md"
            if output_file.exists():
                return output_file.read_text(encoding="utf-8")

            return result.stdout if result.stdout else None

    except FileNotFoundError:
        print("ERROR: codex CLI not found. Install or add to PATH.", file=sys.stderr)
        return None
    except Exception as e:
        print(f"ERROR: Failed to call Codex: {e}", file=sys.stderr)
        return None


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

    prompt = format_entries_for_prompt(entries, version)
    backend = config.get("backend", "claude")

    if backend == "codex":
        summary = call_codex_api(prompt, config)
    else:  # default to claude
        summary = call_claude_api(prompt, config)

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
        choices=["claude", "codex"],
        help="Override the configured LLM backend",
    )

    args = parser.parse_args()

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

    print(f"Summarizing {len(versions_to_summarize)} version(s) using backend: {config.get('backend', 'claude')}")
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
    for version, entries in sorted_versions:
        result = summarize_version(version, entries, config, force=args.force)
        if result:
            success_count += 1

    print()
    print(f"Successfully generated {success_count}/{len(versions_to_summarize)} summaries")
    return 0 if success_count > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
