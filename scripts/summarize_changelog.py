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
import shutil
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
            "claude_max_tokens": 1500,
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
    ids = sorted(str(e.get("id", "")) for e in entries if str(e.get("id", "")))
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


def _build_intelligent_summary(entries: list[dict], version: str) -> str | None:
    """Build deterministic grouped summary without external LLM/API calls."""
    if not entries:
        return None

    try:
        from generate_release_notes import TAG_ORDER, build_change_groups, group_by_tag, _intelligent_tag_summary
    except Exception as e:
        print(f"ERROR: Failed loading intelligent summarizer helpers: {e}", file=sys.stderr)
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
        max_tokens = config.get("claude_max_tokens", config.get("max_tokens", 1500))

        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )

        return response.content[0].text if response.content else None
    except Exception as e:
        print(f"ERROR: Failed to call Claude API: {e}", file=sys.stderr)
        return None


def _find_git_bash() -> str | None:
    """Find git bash executable for Claude Code on Windows."""
    # Already set in environment
    if val := os.environ.get("CLAUDE_CODE_GIT_BASH_PATH"):
        return val
    # Try to resolve the current bash via shutil / which
    import shutil
    bash = shutil.which("bash")
    if bash:
        # Convert Unix-style path to Windows path if needed (e.g. when running under MSYS/Git bash)
        try:
            result = subprocess.run(
                ["cygpath", "-w", bash], capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        return bash
    # Common fallback locations
    for candidate in [
        r"C:\Program Files\Git\bin\bash.exe",
        r"C:\Program Files\Git\usr\bin\bash.exe",
    ]:
        if os.path.exists(candidate):
            return candidate
    return None


def _resolve_claude_cli_command() -> list[str]:
    """Resolve an executable command for Claude CLI across Windows wrappers."""
    import shutil

    candidates = ["claude"]
    if sys.platform == "win32":
        candidates.extend(["claude.cmd", "claude.exe", "claude.bat", "claude.ps1"])

    for candidate in candidates:
        resolved = shutil.which(candidate)
        if not resolved:
            continue
        if resolved.lower().endswith(".ps1"):
            return ["pwsh", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", resolved]
        return [resolved]

    # Fall back to plain command so caller gets a consistent FileNotFound error path.
    return ["claude"]


def _normalize_windowsish_path(path_value: str) -> str:
    """Convert /c/... style paths to C:\\... on Windows-like environments."""
    if not path_value or not path_value.startswith("/") or len(path_value) < 3:
        return path_value
    if len(path_value) >= 3 and path_value[1].isalpha() and path_value[2] == "/":
        drive = path_value[1].upper()
        rest = path_value[3:].replace("/", "\\")
        return f"{drive}:\\{rest}"
    return path_value


def _discover_vscode_codex() -> str | None:
    """Find codex.exe bundled in VS Code extension installs."""
    candidates: list[Path] = []
    roots: list[Path] = []

    for env_key in ("USERPROFILE", "HOME"):
        raw = os.environ.get(env_key)
        if not raw:
            continue
        roots.append(Path(_normalize_windowsish_path(raw)))

    for root in roots:
        for vscode_dir in (".vscode", ".vscode-insiders"):
            ext_dir = root / vscode_dir / "extensions"
            if not ext_dir.exists():
                continue
            candidates.extend(ext_dir.glob("openai.chatgpt-*/bin/windows-x86_64/codex.exe"))

    if not candidates:
        return None
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return str(candidates[0])


def _resolve_codex_command() -> list[str]:
    """Resolve codex CLI command, including VS Code bundled fallback on Windows."""
    resolved = shutil.which("codex") or shutil.which("codex.exe")
    if resolved:
        return [resolved]

    if sys.platform == "win32":
        discovered = _discover_vscode_codex()
        if discovered:
            return [discovered]

    return ["codex"]


def call_claude_cli(prompt: str, config: dict) -> str | None:
    """Call the Claude Code CLI for summarization (uses VS Code extension auth, no API key needed)."""
    try:
        # Strip CLAUDECODE so a nested claude process is allowed to start
        env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
        # Ensure Claude Code can locate git bash on Windows
        if sys.platform == "win32" and "CLAUDE_CODE_GIT_BASH_PATH" not in env:
            bash_path = _find_git_bash()
            if bash_path:
                env["CLAUDE_CODE_GIT_BASH_PATH"] = bash_path
        claude_cmd = _resolve_claude_cli_command()
        result = subprocess.run(
            [*claude_cmd, "-p", prompt],
            capture_output=True,
            text=True,
            timeout=120,
            env=env,
        )

        if result.returncode != 0:
            print(f"ERROR: claude CLI failed: {result.stderr.strip()}", file=sys.stderr)
            return None

        output = result.stdout.strip()
        return output if output else None

    except FileNotFoundError:
        print("ERROR: claude CLI not found. Ensure Claude Code is installed and on PATH.", file=sys.stderr)
        return None
    except Exception as e:
        print(f"ERROR: Failed to call claude CLI: {e}", file=sys.stderr)
        return None


def call_codex_api(prompt: str, config: dict) -> str | None:
    """Call Codex CLI for summarization."""
    try:
        codex_cmd = _resolve_codex_command()
        with tempfile.TemporaryDirectory() as tmpdir:
            plan_file = Path(tmpdir) / "plan.md"
            output_file = Path(tmpdir) / "output.md"
            plan_file.write_text(prompt, encoding="utf-8")

            model = str(config.get("codex_model", "")).strip()
            exec_cmd = [
                *codex_cmd,
                "--sandbox",
                "read-only",
                "--ask-for-approval",
                "never",
                "exec",
                "--cd",
                str(PROJECT_ROOT),
                "--output-last-message",
                str(output_file),
            ]
            if model:
                exec_cmd.extend(["--model", model])
            exec_cmd.append("-")

            result = subprocess.run(
                exec_cmd,
                input=prompt,
                capture_output=True,
                text=True,
                timeout=300,
            )

            # Backward compatibility for older codex CLI builds.
            if result.returncode != 0 and ("unrecognized" in (result.stderr or "").lower() or "unknown" in (result.stderr or "").lower()):
                result = subprocess.run(
                    [*codex_cmd, "run", "--plan", str(plan_file), "--output-dir", tmpdir],
                    capture_output=True,
                    text=True,
                    timeout=300,
                )

            if result.returncode != 0:
                stderr = (result.stderr or "").strip()
                print(f"ERROR: Codex failed: {stderr}", file=sys.stderr)
                return None

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

    if backend == "intelligent":
        summary = _build_intelligent_summary(entries, version)
    elif backend == "codex":
        summary = call_codex_api(prompt, config)
    elif backend == "claude-cli":
        summary = call_claude_cli(prompt, config)
    else:  # default to claude (API key)
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
        choices=["claude", "claude-cli", "codex", "intelligent"],
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
    resolved_hashes: dict[str, str] = {}
    for version, entries in sorted_versions:
        resolved_hashes[version] = compute_version_hash(entries) if entries else ""
        result = summarize_version(version, entries, config, force=args.force)
        if result:
            success_count += 1

    # Keep cache clean for processed versions when force-regenerating.
    if args.force and resolved_hashes:
        cache = load_summaries()
        updated = False
        for version, vhash in resolved_hashes.items():
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
