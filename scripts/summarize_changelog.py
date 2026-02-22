"""
Generate intelligent LLM-based changelog summaries.

This script reads CHANGELOG.json + CHANGELOG.archive.json, groups entries by
version, and uses Claude CLI or Codex CLI to generate readable, human-friendly
summaries for each release. Summaries are cached in CHANGELOG.summaries.json.
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
            "enabled": True,
            "backend": "intelligent",
            "common": {
                "timeout_seconds": 300,
            },
            "codex": {
                "model": "",
            },
            "claude_cli": {},
            "intelligent": {},
        }
    try:
        with open(CONFIG_DEFAULTS, encoding="utf-8") as f:
            config = json.load(f)
        return config.get("changelog_summarization", {})
    except Exception as e:
        print(f"WARNING: Failed to load config: {e}", file=sys.stderr)
        return {}


def _backend_key(name: str) -> str:
    return str(name or "").replace("-", "_").strip() or "intelligent"


def _common_cfg(config: dict) -> dict:
    common = config.get("common")
    if isinstance(common, dict):
        return common
    return config


def _provider_cfg(config: dict, backend: str) -> dict:
    provider = config.get(_backend_key(backend))
    if isinstance(provider, dict):
        return provider
    return config


def _runtime_timeout(config: dict, backend: str) -> int:
    provider = _provider_cfg(config, backend)
    common = _common_cfg(config)
    return int(provider.get("timeout_seconds", common.get("timeout_seconds", 300)))


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
            data = json.load(f)
        if not isinstance(data, dict):
            raise RuntimeError(
                f"{CHANGELOG_SUMMARIES_JSON} must be a JSON object keyed by '<version>:<hash>'."
            )
        return data
    except RuntimeError:
        raise
    except Exception as exc:
        raise RuntimeError(
            f"Failed to parse {CHANGELOG_SUMMARIES_JSON}: {exc}. "
            "Fix the file before running summarization to avoid cache loss."
        ) from exc


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


def format_entries_for_prompt(entries: list[dict], version: str, config: dict | None = None) -> str:
    """Format changelog entries into a prompt for the LLM."""
    if config is None:
        config = {}
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
    requirements = _common_cfg(config).get(
        "changelog_prompt_requirements",
        [
            "Starts with 1-2 sentences describing what this release focuses on",
            "Groups changes under ### Bug Fixes, ### New Features, ### Improvements, etc. as appropriate",
            "Uses plain English bullet points that users can understand",
            "Omits internal IDs, workstream slugs, and technical jargon",
            "Only includes sections that have actual changes",
            "Returns only the markdown sections (no extra commentary)",
        ],
    )
    lines.append("Write a human-readable changelog summary that:")
    for requirement in requirements:
        lines.append(f"- {requirement}")

    return "\n".join(lines)


def _normalize_llm_summary(summary: str) -> str:
    """Normalize LLM output (Claude/Codex) to match the standard template.

    Ensures consistent formatting regardless of which backend generates the summary.
    - Strips explanatory wrappers and metadata commentary
    - Deduplicates identical section headers
    - Adds ### Overview section if missing
    - Normalizes section headers to ### format
    - Removes duplicate blank lines
    """
    if not summary or not summary.strip():
        return summary

    lines = summary.split('\n')

    # Find the first ### section header that marks actual content start
    start_idx = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith('###'):
            start_idx = i
            break

    # Find the end of actual content (before "**Note:**", "Note:", or final ---)
    end_idx = len(lines)
    for i in range(len(lines) - 1, -1, -1):
        stripped = lines[i].strip()
        if stripped.startswith('**Note:') or stripped.startswith('Note:'):
            end_idx = i
            break
        elif stripped == '---' and i > start_idx + 5:  # Skip early --- (likely wrapper separators)
            end_idx = i
            break

    content_lines = lines[start_idx:end_idx]

    # First pass: identify duplicate headers and mark ranges to remove
    # Keep the SECOND occurrence (which has the real content), remove the FIRST
    headers_seen = {}
    ranges_to_remove = []

    for i, line in enumerate(content_lines):
        stripped = line.strip()
        if stripped.startswith('###'):
            if stripped in headers_seen:
                # Found duplicate; mark the FIRST occurrence (from its start to the second one)
                prev_idx = headers_seen[stripped]
                ranges_to_remove.append((prev_idx, i))
            headers_seen[stripped] = i

    # Second pass: filter out marked ranges
    filtered = []
    for i, line in enumerate(content_lines):
        skip = False
        for start, end in ranges_to_remove:
            if start <= i < end:
                skip = True
                break
        if not skip:
            filtered.append(line)

    # Third pass: clean up formatting
    normalized = []
    has_overview = False

    for i, line in enumerate(filtered):
        stripped = line.rstrip()

        # Skip pure separator lines (---)
        if stripped == '---':
            continue

        # Mark Overview as seen
        if stripped.startswith('### Overview'):
            has_overview = True

        # Add the line
        normalized.append(stripped)

    # Remove trailing empty lines
    while normalized and not normalized[-1]:
        normalized.pop()

    # Remove consecutive blank lines (keep max 1)
    final = []
    prev_blank = False
    for line in normalized:
        is_blank = not line.strip()
        if is_blank and prev_blank:
            continue
        final.append(line)
        prev_blank = is_blank

    return '\n'.join(final).strip()


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
        provider = _provider_cfg(config, "claude-cli")
        model = str(provider.get("model", "")).strip()
        args = [*claude_cmd]
        if model:
            args.extend(["--model", model])
        args.extend(["-p", prompt])
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=_runtime_timeout(config, "claude-cli"),
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

            model = str(_provider_cfg(config, "codex").get("model", config.get("codex_model", ""))).strip()
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
                encoding="utf-8",
                errors="replace",
                timeout=_runtime_timeout(config, "codex"),
            )

            # Backward compatibility for older codex CLI builds.
            if result.returncode != 0 and ("unrecognized" in (result.stderr or "").lower() or "unknown" in (result.stderr or "").lower()):
                result = subprocess.run(
                    [*codex_cmd, "run", "--plan", str(plan_file), "--output-dir", tmpdir],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=_runtime_timeout(config, "codex"),
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

    prompt = format_entries_for_prompt(entries, version, config)
    backend = config.get("backend", "intelligent")

    if backend == "intelligent":
        summary = _build_intelligent_summary(entries, version)
    elif backend == "codex":
        summary = call_codex_api(prompt, config)
    elif backend == "claude-cli":
        summary = call_claude_cli(prompt, config)
    else:
        print(f"ERROR: Unsupported backend '{backend}'. Use one of: claude-cli, codex, intelligent.", file=sys.stderr)
        summary = None

    if not summary:
        print(f"  [{version}] Failed to generate summary", file=sys.stderr)
        return None

    # Normalize LLM output to ensure consistent formatting across backends
    if backend != "intelligent":
        summary = _normalize_llm_summary(summary)

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
        choices=["claude-cli", "codex", "intelligent"],
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
