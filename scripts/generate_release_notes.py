"""
Generate compact release notes from changelog data.

Source-of-truth files:
- CHANGELOG.json: active unreleased entries
- CHANGELOG.archive.json: stamped/released history

Release notes are intentionally compact: iterative changelog updates are condensed
into grouped workstreams so release bodies do not list every micro-change.
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CHANGELOG_PATH = PROJECT_ROOT / "docs" / "changelog" / "CHANGELOG.json"
CHANGELOG_ARCHIVE_PATH = PROJECT_ROOT / "docs" / "changelog" / "CHANGELOG.archive.json"
DEFAULT_OUTPUT = PROJECT_ROOT / "dist" / "RELEASE_NOTES.md"
CONFIG_DEFAULTS = PROJECT_ROOT / "docs" / "changelog" / "changelog-config.json"
CHANGELOG_SUMMARIES_PATH = PROJECT_ROOT / "docs" / "changelog" / "CHANGELOG.summaries.json"

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

TOPIC_PATTERNS: list[tuple[str, str]] = [
    ("developer documentation", r"\b(readme|docs?|guide|tutorial)\b"),
    ("release process", r"\b(release|release-please|workflow|pipeline|stamp|archive)\b"),
    ("changelog tooling", r"\b(changelog|log_change|change group|grouped|release notes?)\b"),
    ("vkb-link lifecycle", r"\b(vkb-?link|startup|shutdown|reconnect|connection|ini)\b"),
    ("rule engine", r"\b(rule|rules\.json|catalog|signal|operator)\b"),
    ("ui and preferences", r"\b(ui|panel|status|layout|preferences|button|font)\b"),
    ("tests", r"\b(test|pytest|coverage|assert)\b"),
    ("packaging", r"\b(package|packaging|zip|build|artifact)\b"),
    ("configuration", r"\b(config|defaults|settings|manifest)\b"),
    ("process reliability", r"\b(crash|health|monitor|timeout|retry|single-instance)\b"),
]

# Generic terms stripped from summary matching to catch iterative rewrites
SIMILARITY_STOPWORDS = {
    "a",
    "an",
    "and",
    "for",
    "in",
    "of",
    "on",
    "the",
    "to",
    "with",
    "add",
    "added",
    "adds",
    "adding",
    "change",
    "changes",
    "enhance",
    "enhanced",
    "enhancement",
    "enhancements",
    "fix",
    "fixed",
    "fixes",
    "fixing",
    "improve",
    "improved",
    "improves",
    "improving",
    "refactor",
    "refactored",
    "update",
    "updated",
    "updates",
    "updating",
}

TAG_SUMMARY_TEMPLATES = {
    "New Feature": "Added new capabilities for {topics}.",
    "Bug Fix": "Fixed issues in {topics}.",
    "UI Improvement": "Improved UI workflows for {topics}.",
    "Performance Improvement": "Improved performance for {topics}.",
    "Code Refactoring": "Refactored {topics} for maintainability.",
    "Configuration Cleanup": "Cleaned up configuration for {topics}.",
    "Build / Packaging": "Improved build and packaging for {topics}.",
    "Dependency Update": "Updated dependencies for {topics}.",
    "Test Update": "Expanded test coverage for {topics}.",
    "Documentation Update": "Updated documentation for {topics}.",
    "Other": "Updated {topics}.",
}


def get_current_version() -> str:
    ns: dict = {}
    exec((PROJECT_ROOT / "src" / "edmcruleengine" / "version.py").read_text(), ns)
    return str(ns.get("__version__", "0.0.0"))


def _load_json_list(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        print(f"ERROR: {path} must be a JSON list.", file=sys.stderr)
        sys.exit(1)
    return [e for e in data if isinstance(e, dict)]


def load_current_changelog() -> list[dict]:
    if not CHANGELOG_PATH.exists():
        print(f"ERROR: {CHANGELOG_PATH} not found.", file=sys.stderr)
        sys.exit(1)
    return _load_json_list(CHANGELOG_PATH)


def load_archive_changelog() -> list[dict]:
    return _load_json_list(CHANGELOG_ARCHIVE_PATH)


def save_current_changelog(entries: list[dict]) -> None:
    with open(CHANGELOG_PATH, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)
        f.write("\n")


def save_archive_changelog(entries: list[dict]) -> None:
    with open(CHANGELOG_ARCHIVE_PATH, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)
        f.write("\n")


def _load_summaries() -> dict:
    if not CHANGELOG_SUMMARIES_PATH.exists():
        return {}
    try:
        with open(CHANGELOG_SUMMARIES_PATH, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_summaries(data: dict) -> None:
    with open(CHANGELOG_SUMMARIES_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def _version_tuple(v: str) -> tuple[int, ...]:
    parts = []
    for p in str(v).split("."):
        try:
            parts.append(int(p))
        except ValueError:
            parts.append(0)
    return tuple(parts)


def _entry_sort_key(entry: dict) -> tuple[str, str]:
    return (str(entry.get("date", "") or ""), str(entry.get("id", "") or ""))


def _entries_hash(entries: list[dict]) -> str:
    ids = sorted(str(e.get("id", "") or "") for e in entries if str(e.get("id", "") or ""))
    content = "\n".join(ids)
    return hashlib.sha256(content.encode()).hexdigest()[:12]


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

    # Historical version filter - never includes "unreleased" entries
    target = _version_tuple(version) if version else None
    since_t = _version_tuple(since) if since else None

    result = []
    for entry in entries:
        ev_raw = entry.get("plugin_version", "0.0.0")
        if ev_raw == "unreleased":
            continue
        ev = _version_tuple(str(ev_raw))
        if target and since_t:
            if since_t < ev <= target:
                result.append(entry)
        elif target:
            if ev == target:
                result.append(entry)
    return result


def _primary_tag(entry: dict) -> str:
    tags = entry.get("summary_tags")
    if isinstance(tags, list) and tags:
        return str(tags[0])
    return "Other"


def _normalise_summary(text: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()
    if not cleaned:
        return ""
    tokens = [t for t in cleaned.split() if t and t not in SIMILARITY_STOPWORDS]
    return " ".join(tokens)


def _summary_tokens(text: str) -> set[str]:
    return set(_normalise_summary(text).split())


def _summaries_similar(a: str, b: str) -> bool:
    if not a or not b:
        return False
    if a == b:
        return True

    if len(a) >= 18 and a in b:
        return True
    if len(b) >= 18 and b in a:
        return True

    seq_ratio = SequenceMatcher(None, a, b).ratio()
    if seq_ratio >= 0.86:
        return True

    ta = _summary_tokens(a)
    tb = _summary_tokens(b)
    if not ta or not tb:
        return False

    jaccard = len(ta.intersection(tb)) / len(ta.union(tb))
    return jaccard >= 0.80


def _summary_fingerprint(summary: str) -> str:
    tokens = _normalise_summary(summary).split()
    if not tokens:
        return "misc"
    return "-".join(tokens[:6])


def _entry_group_key(entry: dict) -> tuple[str, bool]:
    raw = str(entry.get("change_group", "") or "").strip()
    if raw:
        return raw, True
    summary = str(entry.get("summary", "") or "")
    return f"legacy:{_summary_fingerprint(summary)}", False


def _dedupe_group_summaries(entries: list[dict]) -> list[str]:
    clusters: list[dict] = []
    for entry in entries:
        summary = str(entry.get("summary", "") or "").strip()
        if not summary:
            continue
        normalised = _normalise_summary(summary)
        merged = False
        for cluster in clusters:
            if _summaries_similar(normalised, cluster["normalised"]):
                # Keep the latest wording as representative.
                cluster["summary"] = summary
                cluster["normalised"] = normalised
                cluster["count"] += 1
                merged = True
                break
        if not merged:
            clusters.append(
                {
                    "summary": summary,
                    "normalised": normalised,
                    "count": 1,
                }
            )
    return [c["summary"] for c in clusters]


def build_change_groups(entries: list[dict]) -> list[dict]:
    grouped_entries: dict[str, dict] = {}
    for entry in sorted(entries, key=_entry_sort_key):
        group_key, explicit = _entry_group_key(entry)
        if group_key not in grouped_entries:
            grouped_entries[group_key] = {
                "group_key": group_key,
                "explicit_group": explicit,
                "entries": [],
            }
        grouped_entries[group_key]["entries"].append(entry)
        grouped_entries[group_key]["explicit_group"] = grouped_entries[group_key]["explicit_group"] or explicit

    groups: list[dict] = []
    for group in grouped_entries.values():
        group_entries = sorted(group["entries"], key=_entry_sort_key)
        unique_summaries = _dedupe_group_summaries(group_entries)
        latest_entry = group_entries[-1]

        headline = unique_summaries[-1] if unique_summaries else str(latest_entry.get("summary", "") or "")
        if not headline:
            headline = "Miscellaneous updates"

        tag_counts = Counter(_primary_tag(e) for e in group_entries)
        primary_tag = "Other"
        if tag_counts:
            primary_tag = sorted(tag_counts.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]

        groups.append(
            {
                "group_key": group["group_key"],
                "explicit_group": group["explicit_group"],
                "entry_count": len(group_entries),
                "summary_count": len(unique_summaries) if unique_summaries else 1,
                "headline": headline,
                "primary_tag": primary_tag,
                "latest_date": str(latest_entry.get("date", "") or ""),
            }
        )

    return sorted(groups, key=lambda g: (g["latest_date"], g["entry_count"], g["headline"]), reverse=True)


def group_by_tag(groups: list[dict]) -> dict[str, list[dict]]:
    buckets: dict[str, list[dict]] = defaultdict(list)
    for group in groups:
        buckets[group["primary_tag"]].append(group)
    return buckets


def _infer_topics(text: str) -> list[str]:
    lower = text.lower()
    matched: list[str] = []
    for topic, pattern in TOPIC_PATTERNS:
        if re.search(pattern, lower):
            matched.append(topic)
    return matched


def _shorten_group_key(key: str, max_len: int = 50) -> str:
    """Shorten a group key to fit nicely in display (tables, etc).

    Most group keys should fit in 50 chars. Only truncates if necessary,
    and truncates at word boundaries (dashes) to preserve meaningful phrases.
    """
    if len(key) <= max_len:
        return key
    # Truncate at word boundaries (dashes in kebab-case)
    truncated = key[:max_len]
    last_dash = truncated.rfind("-")
    # Only truncate at dash if we have meaningful content before it
    if last_dash > 15:  # Keep at least 15 chars of meaningful content
        truncated = truncated[:last_dash]
    return truncated + "…" if truncated != key else truncated


def _format_topics_for_tag(tag: str, topics: list[str]) -> str:
    if not topics:
        return "multiple areas"

    normalized = list(dict.fromkeys(topics))

    # Prefer concise language for documentation-focused summaries.
    if tag == "Documentation Update":
        has_dev_docs = "developer documentation" in normalized
        has_changelog = "changelog tooling" in normalized
        has_release = "release process" in normalized
        if has_dev_docs and (has_changelog or has_release):
            return "developer and release-process documentation"
        if has_changelog and not has_dev_docs:
            return "release-process documentation"

    # Build/packaging summaries should avoid "documentation" unless nothing else applies.
    if tag == "Build / Packaging":
        preferred = [t for t in normalized if t not in {"developer documentation"}]
        if preferred:
            normalized = preferred

    if len(normalized) == 1:
        return normalized[0]
    return f"{normalized[0]} and {normalized[1]}"


def _intelligent_tag_summary(tag: str, tag_groups: list[dict]) -> str:
    topic_counter: Counter[str] = Counter()
    for group in tag_groups:
        combined = f"{group.get('headline', '')} {group.get('group_key', '')}"
        for topic in _infer_topics(combined):
            topic_counter[topic] += 1

    top_topics = [name for name, _ in topic_counter.most_common(3)]
    topics_phrase = _format_topics_for_tag(tag, top_topics)

    template = TAG_SUMMARY_TEMPLATES.get(tag, TAG_SUMMARY_TEMPLATES["Other"])
    summary = template.format(topics=topics_phrase)
    return summary


def _date_range(entries: list[dict]) -> str:
    dates = [str(e.get("date", "") or "") for e in entries if str(e.get("date", "") or "")]
    if not dates:
        return ""
    lo, hi = min(dates), max(dates)
    return lo if lo == hi else f"{lo} - {hi}"


def load_config() -> dict:
    """Load changelog summarizer config from config_changelog-config.json."""
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


def _format_entries_for_llm(entries: list[dict], version: str, config: dict | None = None) -> str:
    """Format changelog entries into a prompt for the LLM."""
    if config is None:
        config = {}
    lines = [f"# Generate release notes for version {version}", ""]

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
        "release_notes_prompt_requirements",
        [
            "Group changes logically by category (Bug Fixes, New Features, Improvements)",
            "Use plain English that end users understand",
            "Omit internal IDs and workstream slugs",
            "Start each section with a clear heading",
            "Include only the most important/impactful changes",
            "Return only the markdown content (no extra commentary)",
        ],
    )
    lines.append("Write concise release notes that:")
    for requirement in requirements:
        lines.append(f"- {requirement}")

    return "\n".join(lines)


def _find_git_bash() -> str | None:
    """Find git bash executable for Claude Code on Windows."""
    if val := os.environ.get("CLAUDE_CODE_GIT_BASH_PATH"):
        return val
    bash = shutil.which("bash")
    if bash:
        try:
            result = subprocess.run(
                ["cygpath", "-w", bash], capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        return bash
    for candidate in [
        r"C:\Program Files\Git\bin\bash.exe",
        r"C:\Program Files\Git\usr\bin\bash.exe",
    ]:
        if os.path.exists(candidate):
            return candidate
    return None


def _resolve_claude_cli_command() -> list[str]:
    """Resolve an executable command for Claude CLI across Windows wrappers."""
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

    return ["claude"]


def _normalize_windowsish_path(path_value: str) -> str:
    if not path_value or not path_value.startswith("/") or len(path_value) < 3:
        return path_value
    if len(path_value) >= 3 and path_value[1].isalpha() and path_value[2] == "/":
        drive = path_value[1].upper()
        rest = path_value[3:].replace("/", "\\")
        return f"{drive}:\\{rest}"
    return path_value


def _discover_vscode_codex() -> str | None:
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
    resolved = shutil.which("codex") or shutil.which("codex.exe")
    if resolved:
        return [resolved]
    if sys.platform == "win32":
        discovered = _discover_vscode_codex()
        if discovered:
            return [discovered]
    return ["codex"]


def _resolve_gemini_command() -> list[str]:
    """Resolve Google Gemini CLI command."""
    resolved = shutil.which("gemini") or shutil.which("gemini.exe") or shutil.which("gemini.cmd")
    if resolved:
        return [resolved]
    return ["gemini"]


def _resolve_copilot_command() -> list[str]:
    """Resolve GitHub Copilot CLI command (installed as Windows app)."""
    candidates = ["copilot", "copilot.exe"]
    for candidate in candidates:
        resolved = shutil.which(candidate)
        if resolved:
            return [resolved]
    return ["copilot"]


def _call_claude_cli_for_summary(prompt: str, config: dict) -> str | None:
    """Call Claude CLI for release notes summary."""
    try:
        env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
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


def _call_copilot_cli_for_summary(prompt: str, config: dict) -> str | None:
    """Call GitHub Copilot CLI for release notes summary (non-interactive mode).

    Uses: GPT-4.1 model by default (included with Copilot, no token usage)
    """
    try:
        copilot_cmd = _resolve_copilot_command()
        provider = _provider_cfg(config, "copilot")
        model = str(provider.get("model", "gpt-4.1")).strip() or "gpt-4.1"

        # Build the copilot command with -s for silent mode to output only the response
        args = [*copilot_cmd, "-s", "--allow-all", "--model", model]

        # Pass prompt via stdin to handle multiline/special characters properly
        result = subprocess.run(
            args,
            input=prompt,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=_runtime_timeout(config, "copilot"),
        )

        if result.returncode != 0:
            stderr = (result.stderr or "").strip()
            print(f"ERROR: GitHub Copilot CLI failed: {stderr}", file=sys.stderr)
            return None

        output = result.stdout.strip()
        return output if output else None

    except FileNotFoundError:
        print(
            "ERROR: GitHub Copilot CLI not found. Install from: "
            "https://docs.github.com/en/copilot/how-tos/copilot-cli/set-up-copilot-cli/install-copilot-cli",
            file=sys.stderr,
        )
        return None
    except Exception as e:
        print(f"ERROR: Failed to call GitHub Copilot: {e}", file=sys.stderr)
        return None


def _call_gemini_cli_for_summary(prompt: str, config: dict) -> str | None:
    """Call Google Gemini CLI for release notes summary (non-interactive mode)."""
    try:
        gemini_cmd = _resolve_gemini_command()
        provider = _provider_cfg(config, "gemini")
        model = str(provider.get("model", "")).strip()

        # Build the gemini command with -p for prompt mode (non-interactive)
        args = [*gemini_cmd, "-p", prompt, "-y"]

        if model:
            args.extend(["-m", model])

        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=_runtime_timeout(config, "gemini"),
        )

        if result.returncode != 0:
            stderr = (result.stderr or "").strip()
            print(f"ERROR: Google Gemini CLI failed: {stderr}", file=sys.stderr)
            return None

        output = result.stdout.strip()
        return output if output else None

    except FileNotFoundError:
        print(
            "ERROR: Google Gemini CLI not found. Install from: "
            "https://github.com/google-gemini/cli or run: npm install -g @google-gemini/cli",
            file=sys.stderr,
        )
        return None
    except Exception as e:
        print(f"ERROR: Failed to call Google Gemini: {e}", file=sys.stderr)
        return None


def _call_codex_api_for_summary(prompt: str, config: dict) -> str | None:
    """Call Codex CLI for release notes summary."""
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
                print(f"ERROR: Codex failed: {result.stderr}", file=sys.stderr)
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


def _normalize_llm_summary(summary: str) -> str:
    """Normalize LLM output (Claude/Codex/Gemini/Copilot) to match the standard template.

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

    # Find the first ### or ## section header that marks actual content start
    start_idx = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith('###') or stripped.startswith('##'):
            start_idx = i
            break

    # Find the end of actual content (before "**Note:**", "Note:", or final ---)
    end_idx = len(lines)
    for i in range(len(lines) - 1, -1, -1):
        stripped = lines[i].strip()
        if stripped.startswith('**Note:') or stripped.startswith('Note:'):
            end_idx = i
            break
        elif stripped == '---' and i > start_idx + 2:  # Skip early ---
            end_idx = i
            break

    content_lines = lines[start_idx:end_idx]

    # First pass: identify duplicate headers and mark ranges to remove
    # Keep the SECOND occurrence (which has the real content), remove the FIRST
    headers_seen = {}
    ranges_to_remove = []

    for i, line in enumerate(content_lines):
        stripped = line.strip()
        if stripped.startswith('###') or stripped.startswith('##'):
            # Normalize to ### for comparison
            normalized_header = '### ' + stripped.lstrip('#').strip()
            if normalized_header in headers_seen:
                prev_idx = headers_seen[normalized_header]
                ranges_to_remove.append((prev_idx, i))
            headers_seen[normalized_header] = i

    # Second pass: filter out marked ranges and normalize headers to ###
    filtered = []
    for i, line in enumerate(content_lines):
        skip = False
        for start, end in ranges_to_remove:
            if start <= i < end:
                skip = True
                break
        if not skip:
            stripped = line.rstrip()
            if stripped.startswith('##') and not stripped.startswith('###'):
                stripped = '### ' + stripped.lstrip('#').strip()
            filtered.append(stripped)

    # Third pass: clean up formatting and ensure ### Overview section
    normalized = []
    has_overview = False
    first_section_idx = None

    for i, line in enumerate(filtered):
        stripped = line.rstrip()

        # Skip pure separator lines (---)
        if stripped == '---':
            continue

        # Track first ### section
        if stripped.startswith('###') and first_section_idx is None:
            first_section_idx = len(normalized)

        # Mark Overview as seen
        if stripped.startswith('### Overview'):
            has_overview = True

        # Add the line
        normalized.append(stripped)

    # If no Overview section found, create one from the first section content
    if not has_overview and first_section_idx is not None:
        # Extract intro text before first section (if any)
        intro_text = None
        for i in range(first_section_idx):
            if normalized[i].strip():
                intro_text = normalized[i]
                break

        if intro_text and not intro_text.startswith('###'):
            normalized.insert(first_section_idx, '')
            normalized.insert(first_section_idx, intro_text)
            normalized.insert(first_section_idx, '### Overview')
        else:
            normalized.insert(first_section_idx, '')
            normalized.insert(first_section_idx, 'Summary of changes in this release.')
            normalized.insert(first_section_idx, '### Overview')

    # Final cleanup
    while normalized and not normalized[-1]:
        normalized.pop()

    final = []
    prev_blank = False
    for line in normalized:
        is_blank = not line.strip()
        if is_blank and prev_blank:
            continue
        final.append(line)
        prev_blank = is_blank

    return '\n'.join(final).strip()


def build_markdown(
    version: str,
    entries: list[dict],
    max_groups_per_tag: int = 5,
    summary_mode: str = "intelligent",
    config: dict | None = None,
) -> str:
    title_version = "Unreleased" if str(version).lower() == "unreleased" else f"v{version}"

    if not entries:
        return f"# Release Notes - {title_version}\n\nNo changelog entries found.\n"

    # Use LLM-based summarization if requested
    if summary_mode == "llm":
        if config is None:
            config = load_config()

        print(f"Generating LLM-based release notes for v{version}...")
        prompt = _format_entries_for_llm(entries, version, config)
        backend = config.get("backend", "intelligent")

        if backend == "codex":
            llm_summary = _call_codex_api_for_summary(prompt, config)
        elif backend == "claude-cli":
            llm_summary = _call_claude_cli_for_summary(prompt, config)
        elif backend == "copilot":
            llm_summary = _call_copilot_cli_for_summary(prompt, config)
        elif backend == "gemini":
            llm_summary = _call_gemini_cli_for_summary(prompt, config)
        else:
            print(
                f"WARNING: Unsupported llm backend '{backend}' for release notes; "
                "falling back to intelligent mode.",
                file=sys.stderr,
            )
            llm_summary = None

        if llm_summary:
            # Normalize LLM output
            llm_summary = _normalize_llm_summary(llm_summary)

            lines = [f"# Release Notes - {title_version}", ""]
            date_range = _date_range(entries)
            if date_range:
                lines.append(f"_{date_range}_")
                lines.append("")
            lines.append(llm_summary)
            lines.append("")
            return "\n".join(lines)
        else:
            print(f"WARNING: LLM summary failed; falling back to intelligent mode.", file=sys.stderr)
            summary_mode = "intelligent"

    groups = build_change_groups(entries)
    buckets = group_by_tag(groups)

    lines = [f"# Release Notes - {title_version}"]

    date_range = _date_range(entries)
    if date_range:
        lines.append(f"\n_{date_range}_")

    ordered_tags = [t for t in TAG_ORDER if t in buckets]
    remaining = [t for t in sorted(buckets) if t not in TAG_ORDER]

    for tag in ordered_tags + remaining:
        lines.append(f"## {tag}")
        tag_groups = sorted(
            buckets[tag],
            key=lambda g: (g["entry_count"], g["latest_date"], g["headline"]),
            reverse=True,
        )

        if summary_mode == "intelligent":
            lines.append(f"- {_intelligent_tag_summary(tag, tag_groups)}")
        else:
            visible_groups = tag_groups[:max_groups_per_tag]
            hidden_count = len(tag_groups) - len(visible_groups)

            for group in visible_groups:
                bullet = group["headline"]
                if group["explicit_group"]:
                    bullet += f" (group: `{_shorten_group_key(group['group_key'])}`)"
                lines.append(f"- {bullet}")
            if hidden_count > 0:
                lines.append(f"- Additional {hidden_count} grouped updates in this category.")
        lines.append("")

    explicit_groups = [g for g in groups if g["explicit_group"]]
    if explicit_groups:
        lines.append("## Change Group Index")
        lines.append("")
        lines.append("| Group | Entries | Primary Tag |")
        lines.append("|-------|---------|-------------|")
        for group in explicit_groups:
            short_key = _shorten_group_key(group['group_key'])
            lines.append(
                f"| {short_key} | {group['entry_count']} | {group['primary_tag']} |"
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


def archive_stamped(current_entries: list[dict]) -> tuple[list[dict], list[dict], int]:
    """Split entries into (remaining_current, appended_to_archive, skipped_duplicates) and persist archive."""
    remaining_current = [e for e in current_entries if e.get("plugin_version") == "unreleased"]
    stamped_to_archive = [e for e in current_entries if e.get("plugin_version") != "unreleased"]
    skipped_duplicates = 0
    appended_to_archive: list[dict] = []

    if stamped_to_archive:
        existing_archive = load_archive_changelog()
        seen_ids = {str(e.get("id", "")) for e in existing_archive if str(e.get("id", ""))}
        for entry in stamped_to_archive:
            cid = str(entry.get("id", ""))
            if cid and cid in seen_ids:
                skipped_duplicates += 1
                continue
            appended_to_archive.append(entry)
            if cid:
                seen_ids.add(cid)
        if appended_to_archive:
            save_archive_changelog(existing_archive + appended_to_archive)

    return remaining_current, appended_to_archive, skipped_duplicates


def _build_changelog_summary_markdown(entries: list[dict]) -> str | None:
    """Build deterministic CHANGELOG section markdown for a released version."""
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


def ensure_version_summary_cache(stamped_entries: list[dict], stamped_version: str) -> str:
    """
    Ensure a summary cache entry exists for the stamped version.

    Returns one of: "existing", "promoted", "generated", "missing".
    """
    if not stamped_entries:
        return "missing"

    summaries = _load_summaries()
    if not summaries:
        summaries = {}

    stamped_hash = _entries_hash(stamped_entries)
    new_key = f"{stamped_version}:{stamped_hash}"
    existing = summaries.get(new_key)
    if isinstance(existing, str) and existing.strip():
        return "existing"

    old_key = f"unreleased:{stamped_hash}"
    generated = _build_changelog_summary_markdown(stamped_entries)
    if generated:
        # Always prefer normalized deterministic release-format summaries.
        summaries[new_key] = generated
        result = "generated"
    else:
        old_summary = summaries.get(old_key)
        if not (isinstance(old_summary, str) and old_summary.strip()):
            return "missing"
        summaries[new_key] = old_summary
        result = "promoted"

    summaries.pop(old_key, None)

    # Start the next cycle clean: remove stale unreleased summaries.
    for key in list(summaries.keys()):
        if key.startswith("unreleased:"):
            summaries.pop(key, None)

    _save_summaries(summaries)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate compact release notes from changelog JSON data")

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
    parser.add_argument(
        "--max-groups-per-tag",
        type=int,
        default=5,
        help="Maximum grouped bullets per tag section in output (default: 5)",
    )
    parser.add_argument(
        "--summary-mode",
        choices=["intelligent", "grouped", "llm"],
        default="intelligent",
        help=(
            "Release-note rendering style: intelligent (single area summary per tag), "
            "grouped (headline list per change group), or llm (LLM-generated narrative). "
            "Default: intelligent."
        ),
    )
    args = parser.parse_args()

    current_entries = load_current_changelog()
    archive_entries = load_archive_changelog()
    all_entries = archive_entries + current_entries

    if args.stamp:
        display_version = args.stamp
        filtered = filter_entries(current_entries, None, None, False, unreleased_only=True)
        if not filtered:
            print("WARNING: No 'unreleased' entries found in CHANGELOG.json.", file=sys.stderr)
    elif args.all_entries:
        display_version = get_current_version()
        filtered = filter_entries(all_entries, None, None, True, False)
    elif args.version:
        display_version = args.version
        filtered = filter_entries(all_entries, args.version, args.since, False, False)
    else:
        # Default: preview unreleased entries
        display_version = "unreleased"
        filtered = filter_entries(current_entries, None, None, False, unreleased_only=True)
        if not filtered:
            print(
                "WARNING: No 'unreleased' entries found. "
                "Use --version <ver> for historical notes or --all for everything.",
                file=sys.stderr,
            )

    max_groups = max(1, int(args.max_groups_per_tag))
    config = load_config() if args.summary_mode == "llm" else None
    md = build_markdown(
        display_version,
        filtered,
        max_groups_per_tag=max_groups,
        summary_mode=args.summary_mode,
        config=config,
    )

    if args.stdout:
        print(md)
    else:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(md, encoding="utf-8")
        print(f"Release notes written to {output}")

    # Stamp CHANGELOG.json only when explicitly requested
    if args.stamp and filtered:
        stamped_count = stamp_changelog(current_entries, args.stamp)
        if args.archive:
            remaining, archived, duplicate_count = archive_stamped(current_entries)
            save_current_changelog(remaining)
            summary_status = ensure_version_summary_cache(archived, args.stamp)
            print(
                f"Stamped {stamped_count} entries as v{args.stamp}, "
                f"archived {len(archived)} to CHANGELOG.archive.json"
            )
            if duplicate_count:
                print(
                    f"Skipped {duplicate_count} duplicate changelog ID(s) already present in CHANGELOG.archive.json"
                )
            if summary_status == "promoted":
                print(f"Promoted cached unreleased summary to version v{args.stamp}")
            elif summary_status == "generated":
                print(f"Generated version summary cache for v{args.stamp}")
            elif summary_status == "existing":
                print(f"Kept existing version summary cache for v{args.stamp}")
        else:
            save_current_changelog(current_entries)
            summary_status = ensure_version_summary_cache(filtered, args.stamp)
            print(f"Stamped {stamped_count} entries in CHANGELOG.json as v{args.stamp}")
            if summary_status == "promoted":
                print(f"Promoted cached unreleased summary to version v{args.stamp}")
            elif summary_status == "generated":
                print(f"Generated version summary cache for v{args.stamp}")
            elif summary_status == "existing":
                print(f"Kept existing version summary cache for v{args.stamp}")


if __name__ == "__main__":
    main()
