"""
Shared utilities for changelog and release note scripts.

Handles:
- Configuration loading
- JSON I/O
- LLM backend resolution and execution
- Output normalization
- Fallback strategies
"""

import json
import os
import re
import shutil
import subprocess
import sys
import urllib.request
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import tempfile
import time
from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CHANGELOG_DIR = PROJECT_ROOT / "docs" / "changelog"
CHANGELOG_JSON = CHANGELOG_DIR / "CHANGELOG.json"
CHANGELOG_ARCHIVE_JSON = CHANGELOG_DIR / "CHANGELOG.archive.json"
CHANGELOG_SUMMARIES_JSON = CHANGELOG_DIR / "CHANGELOG.summaries.json"
CHANGELOG_MD = PROJECT_ROOT / "CHANGELOG.md"
CONFIG_FILE = CHANGELOG_DIR / "changelog-config.json"
PYPROJECT_TOML = PROJECT_ROOT / "pyproject.toml"
RELEASE_PLEASE_MANIFEST = PROJECT_ROOT / ".release-please-manifest.json"

# Regex
VERSION_RE = re.compile(r'^\s*version\s*=\s*"(?P<version>\d+\.\d+\.\d+)"\s*$', re.MULTILINE)
RELEASE_TITLE_RE = re.compile(r"release\s+(?P<version>\d+\.\d+\.\d+)", re.IGNORECASE)

# Default fallback order if not specified in config
DEFAULT_FALLBACK_ORDER = ["claude-cli", "codex", "gemini", "copilot", "lmstudio"]

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

# ---------------------------------------------------------------------------
# Versioning & Git Utilities
# ---------------------------------------------------------------------------

def parse_semver(text: str) -> tuple[int, int, int]:
    """Parse semver string into (major, minor, patch) tuple."""
    parts = text.strip().split(".")
    if len(parts) != 3:
        raise ValueError(f"Invalid semantic version: {text!r}")
    return int(parts[0]), int(parts[1]), int(parts[2])

def bump_version(version: str, part: str) -> str:
    """Bump a version string by part (major, minor, patch)."""
    major, minor, patch = parse_semver(version)
    if part == "major":
        major += 1
        minor = 0
        patch = 0
    elif part == "minor":
        minor += 1
        patch = 0
    elif part == "patch":
        patch += 1
    else:
        raise ValueError(f"Unsupported bump part: {part}")
    return f"{major}.{minor}.{patch}"

def read_current_version() -> str:
    """Read current version from manifest or pyproject.toml."""
    if RELEASE_PLEASE_MANIFEST.exists():
        try:
            manifest = json.loads(RELEASE_PLEASE_MANIFEST.read_text(encoding="utf-8"))
            root_version = manifest.get(".")
            if isinstance(root_version, str) and re.fullmatch(r"\d+\.\d+\.\d+", root_version):
                return root_version
        except Exception:
            pass

    if not PYPROJECT_TOML.exists():
        return "0.0.0"
        
    text = PYPROJECT_TOML.read_text(encoding="utf-8")
    match = VERSION_RE.search(text)
    if not match:
        return "0.0.0"
    return match.group("version")

def _version_tuple(v: str) -> tuple[int, ...]:
    """Convert version string to comparable tuple."""
    parts = []
    for p in str(v).split("."):
        try:
            parts.append(int(p))
        except ValueError:
            parts.append(0)
    return tuple(parts)

def get_git_dirty_files(include_untracked: bool = False) -> list[str]:
    """Return list of modified files in git."""
    args = ["git", "status", "--porcelain"]
    if not include_untracked:
        args.append("--untracked-files=no")
        
    proc = subprocess.run(
        args,
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return []

    files = []
    for raw in (proc.stdout or "").splitlines():
        line = raw.rstrip()
        if len(line) >= 4:
            files.append(line[3:])
    return files

def find_open_release_pr_version(gh_bin: str = "gh") -> str | None:
    """Return version of open release-please PR if present."""
    cmd = [
        gh_bin,
        "pr",
        "list",
        "--state",
        "open",
        "--search",
        "head:release-please--branches--main",
        "--json",
        "title",
    ]
    try:
        proc = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True)
        if proc.returncode != 0:
            return None
        rows = json.loads(proc.stdout or "[]")
        if not rows:
            return None
        title = str(rows[0].get("title", "")).strip()
        match = RELEASE_TITLE_RE.search(title)
        return match.group("version") if match else None
    except Exception:
        return None

# ---------------------------------------------------------------------------
# IO Helpers
# ---------------------------------------------------------------------------

def load_config() -> dict:
    """Load changelog configuration."""
    if not CONFIG_FILE.exists():
        return {}
    try:
        with open(CONFIG_FILE, encoding="utf-8") as f:
            return json.load(f).get("changelog_summarization", {})
    except Exception as e:
        print(f"WARNING: Failed to load config: {e}", file=sys.stderr)
        return {}

def load_json_list(path: Path) -> list[dict]:
    """Load a list of dicts from a JSON file."""
    if not path.exists():
        return []
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return [e for e in data if isinstance(e, dict)] if isinstance(data, list) else []
    except Exception as e:
        print(f"ERROR: Failed to load {path}: {e}", file=sys.stderr)
        return []

def save_json_list(path: Path, data: list[dict]) -> None:
    """Save a list of dicts to a JSON file."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")

def load_summaries() -> dict:
    """Load cached summaries."""
    if not CHANGELOG_SUMMARIES_JSON.exists():
        return {}
    try:
        with open(CHANGELOG_SUMMARIES_JSON, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}

def save_summaries(data: dict) -> None:
    """Save summaries cache."""
    with open(CHANGELOG_SUMMARIES_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")

# ---------------------------------------------------------------------------
# Path Resolution Helpers
# ---------------------------------------------------------------------------

def _find_git_bash() -> str | None:
    """Find git bash executable for Claude Code on Windows."""
    if val := os.environ.get("CLAUDE_CODE_GIT_BASH_PATH"):
        return val
    bash = shutil.which("bash")
    if bash:
        try:
            # Check if it's cygwin/msys
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
    """Resolve Claude CLI command."""
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
    candidates = []
    roots = []
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
    resolved = shutil.which("gemini") or shutil.which("gemini.exe") or shutil.which("gemini.cmd")
    if resolved:
        return [resolved]
    return ["gemini"]

def _resolve_copilot_command() -> list[str]:
    candidates = ["copilot", "copilot.exe"]
    for candidate in candidates:
        resolved = shutil.which(candidate)
        if resolved:
            return [resolved]
    return ["copilot"]

# ---------------------------------------------------------------------------
# Backend Invocation
# ---------------------------------------------------------------------------

def _get_timeout(config: dict, backend: str) -> int:
    common = config.get("common", {})
    provider = config.get(backend.replace("-", "_"), {})
    return int(provider.get("timeout_seconds", common.get("timeout_seconds", 300)))

def call_claude_cli(prompt: str, config: dict) -> str | None:
    try:
        env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
        if sys.platform == "win32" and "CLAUDE_CODE_GIT_BASH_PATH" not in env:
            bash_path = _find_git_bash()
            if bash_path:
                env["CLAUDE_CODE_GIT_BASH_PATH"] = bash_path

        cmd = _resolve_claude_cli_command()
        provider = config.get("claude_cli", {})
        model = str(provider.get("model", "")).strip()
        
        args = [*cmd]
        if model:
            args.extend(["--model", model])
        args.extend(["-p", prompt])

        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=_get_timeout(config, "claude-cli"),
            env=env,
        )
        if result.returncode != 0:
            print(f"DEBUG: Claude CLI error: {result.stderr.strip()}", file=sys.stderr)
            return None
        return result.stdout.strip() or None
    except Exception as e:
        print(f"DEBUG: Failed call_claude_cli: {e}", file=sys.stderr)
        return None

def call_codex_cli(prompt: str, config: dict) -> str | None:
    try:
        cmd = _resolve_codex_command()
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "output.md"
            
            provider = config.get("codex", {})
            model = str(provider.get("model", "")).strip()
            
            # Using 'exec' mode with stdin
            exec_cmd = [
                *cmd,
                "--sandbox", "read-only",
                "--ask-for-approval", "never",
                "exec",
                "--cd", str(PROJECT_ROOT),
                "--output-last-message", str(output_file),
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
                timeout=_get_timeout(config, "codex"),
            )
            
            if result.returncode != 0:
                 # Try fallback to 'run --plan' if exec fails (older codex versions)
                plan_file = Path(tmpdir) / "plan.md"
                plan_file.write_text(prompt, encoding="utf-8")
                result = subprocess.run(
                    [*cmd, "run", "--plan", str(plan_file), "--output-dir", tmpdir],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=_get_timeout(config, "codex"),
                )

            if result.returncode != 0:
                print(f"DEBUG: Codex CLI error: {result.stderr.strip()}", file=sys.stderr)
                return None

            if output_file.exists():
                return output_file.read_text(encoding="utf-8")
            return result.stdout.strip() or None
    except Exception as e:
        print(f"DEBUG: Failed call_codex_cli: {e}", file=sys.stderr)
        return None

def call_gemini_cli(prompt: str, config: dict) -> str | None:
    try:
        cmd = _resolve_gemini_command()
        provider = config.get("gemini", {})
        model = str(provider.get("model", "")).strip()
        
        # Use stdin for prompt to handle large multi-line inputs reliably
        args = [*cmd, "-y"]
        if model:
            args.extend(["-m", model])

        result = subprocess.run(
            args,
            input=prompt,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=_get_timeout(config, "gemini"),
        )
        if result.returncode != 0:
            print(f"DEBUG: Gemini CLI error: {result.stderr.strip()}", file=sys.stderr)
            return None
        return result.stdout.strip() or None
    except Exception as e:
        print(f"DEBUG: Failed call_gemini_cli: {e}", file=sys.stderr)
        return None

def call_copilot_cli(prompt: str, config: dict) -> str | None:
    try:
        cmd = _resolve_copilot_command()
        provider = config.get("copilot", {})
        model = str(provider.get("model", "gpt-4.1")).strip()
        
        args = [*cmd, "-s", "--allow-all", "--model", model]
        
        result = subprocess.run(
            args,
            input=prompt,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=_get_timeout(config, "copilot"),
        )
        if result.returncode != 0:
            print(f"DEBUG: Copilot CLI error: {result.stderr.strip()}", file=sys.stderr)
            return None
        return result.stdout.strip() or None
    except Exception as e:
        print(f"DEBUG: Failed call_copilot_cli: {e}", file=sys.stderr)
        return None

def call_lmstudio(prompt: str, config: dict) -> str | None:
    """Call local LMStudio OpenAI-compatible API."""
    try:
        provider = config.get("lmstudio", {})
        base_url = str(provider.get("base_url", "http://localhost:1234/v1")).rstrip("/")
        model = str(provider.get("model", "")).strip()
        timeout = _get_timeout(config, "lmstudio")

        url = f"{base_url}/chat/completions"
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system", 
                    "content": (
                        "You are a technical writer specializing in software changelogs. "
                        "Generate a concise, professional summary using standard markdown. "
                        "Use '### Section Name' for headers and '-' for bullet points. "
                        "Focus on user-facing impact and maintain a consistent neutral tone."
                    )
                },
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1,
        }
        
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url, 
            data=data, 
            headers={"Content-Type": "application/json"}
        )
        
        with urllib.request.urlopen(req, timeout=timeout) as response:
            if response.getcode() != 200:
                print(f"DEBUG: LMStudio error: HTTP {response.getcode()}", file=sys.stderr)
                return None
            
            resp_data = json.loads(response.read().decode("utf-8"))
            choices = resp_data.get("choices", [])
            if not choices:
                return None
            
            content = choices[0].get("message", {}).get("content", "")
            return content.strip() or None
            
    except Exception as e:
        print(f"DEBUG: Failed call_lmstudio: {e}", file=sys.stderr)
        return None

# ---------------------------------------------------------------------------
# Normalization & Orchestration
# ---------------------------------------------------------------------------

def normalize_llm_summary(summary: str, entries: list[dict] | None = None) -> str:
    """Normalize LLM output (Claude/Codex/Gemini/Copilot) to match the standard template."""
    if not summary or not summary.strip():
        return summary

    lines = [line.rstrip() for line in summary.split('\n')]
    
    # 1. Strip top-level conversational filler
    start_idx = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith('###') or stripped.startswith('##'):
            start_idx = i
            break
    
    # 2. Find the end of actual content (strip everything from "Note:" or "---" to the end)
    end_idx = len(lines)
    for i, line in enumerate(lines):
        if i < start_idx:
            continue
        stripped = line.strip().lower()
        if stripped.startswith('note:') or stripped.startswith('**note:') or (stripped == '---'):
            end_idx = i
            break

    content_lines = lines[start_idx:end_idx]
    
    # 3. Header normalization and deduplication
    # We want to keep all content but only one instance of each header.
    header_content = {} # header -> list of lines
    
    current_header = None
    # Pass 1: Group content by normalized header and standardize bullet points
    for line in content_lines:
        stripped = line.strip()
        
        # Standardize bullet points (convert •, *, + at start of line to -)
        if re.match(r"^[\s]*[•\*+][\s]+", line):
            line = re.sub(r"^([\s]*)[•\*+]([\s]+)", r"\1-\2", line)
            stripped = line.strip()

        if stripped.startswith('###') or stripped.startswith('##'):
            current_header = '### ' + stripped.lstrip('#').strip()
            if current_header not in header_content:
                header_content[current_header] = []
        elif current_header:
            # Skip leading blank lines in a section
            if not header_content[current_header] and not stripped:
                continue
            header_content[current_header].append(line)
        else:
            # Lines before first header (intro)
            if "_intro_" not in header_content:
                header_content["_intro_"] = []
            if not header_content["_intro_"] and not stripped:
                continue
            header_content["_intro_"].append(line)

    # Trim trailing blank lines from all sections
    for h in header_content:
        while header_content[h] and not header_content[h][-1].strip():
            header_content[h].pop()

    # Pass 2: Reconstruct with single headers and standardized spacing
    # We maintain order of appearance of headers
    headers_order = []
    seen_in_order = set()
    for line in content_lines:
        stripped = line.strip()
        if stripped.startswith('###') or stripped.startswith('##'):
            h = '### ' + stripped.lstrip('#').strip()
            if h not in seen_in_order:
                headers_order.append(h)
                seen_in_order.add(h)
    
    # 4. Ensure Overview section and build final content
    has_overview = any(h.startswith('### Overview') for h in headers_order)
    
    if not has_overview:
        intro_text = None
        if "_intro_" in header_content:
            for line in header_content["_intro_"]:
                if line.strip():
                    intro_text = line.strip()
                    break
        
        insert_text = intro_text if (intro_text and not intro_text.startswith('###')) else generate_statistical_overview(entries)
        
        # Move intro content to header_content["### Overview"]
        header_content["### Overview"] = [insert_text]
        if "_intro_" in header_content:
             header_content["### Overview"].extend([l for l in header_content["_intro_"] if l.strip() != intro_text])
        
        headers_order.insert(0, "### Overview")

    # 5. Final Assembly
    final_lines = []
    for h in headers_order:
        if final_lines:
            final_lines.append("") # Blank line between sections
        
        final_lines.append(h)
        if h == "### Overview":
            final_lines.append("") # Spacing after Overview
            
        final_lines.extend(header_content[h])

    # 6. Final cleanup of whitespace and consecutive blanks
    output = []
    prev_blank = False
    for line in final_lines:
        is_blank = not line.strip()
        if is_blank and prev_blank:
            continue
        output.append(line.rstrip())
        prev_blank = is_blank

    return '\n'.join(output).strip()

def run_llm_with_fallback(prompt: str, config: dict, preferred_backend: str | None = None, entries: list[dict] | None = None) -> tuple[str | None, str]:
    """
    Try to run the prompt against backends in order.
    Returns (result_string_or_None, backend_used).
    """
    
    # Determine the order
    order = []
    if preferred_backend and preferred_backend != "intelligent":
        order.append(preferred_backend)
    
    # Add configured fallback order or default
    configured_order = config.get("common", {}).get("fallback_order", DEFAULT_FALLBACK_ORDER)
    for backend in configured_order:
        if backend not in order:
            order.append(backend)
            
    print(f"INFO: Attempting LLM generation with order: {', '.join(order)}")

    for backend in order:
        result = None
        print(f"  > Trying {backend}...")
        
        if backend == "claude-cli":
            result = call_claude_cli(prompt, config)
        elif backend == "codex":
            result = call_codex_cli(prompt, config)
        elif backend == "gemini":
            result = call_gemini_cli(prompt, config)
        elif backend == "copilot":
            result = call_copilot_cli(prompt, config)
        elif backend == "lmstudio":
            result = call_lmstudio(prompt, config)
        else:
            print(f"    Skipping unknown backend: {backend}")
            continue

        if result:
            print(f"    Success with {backend}.")
            return normalize_llm_summary(result, entries=entries), backend
        else:
            print(f"    Failed or empty output from {backend}.")

    return None, "none"

# ---------------------------------------------------------------------------
# Change Grouping & Statistics
# ---------------------------------------------------------------------------

def _entry_sort_key(entry: dict) -> tuple[str, str]:
    return (str(entry.get("date", "") or ""), str(entry.get("id", "") or ""))

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

def _infer_topics(text: str) -> list[str]:
    lower = text.lower()
    matched: list[str] = []
    for topic, pattern in TOPIC_PATTERNS:
        if re.search(pattern, lower):
            matched.append(topic)
    return matched

def generate_statistical_overview(entries: list[dict]) -> str:
    """Generate a descriptive overview sentence based on changelog stats."""
    if not entries:
        return "Summary of changes in this release."
        
    groups = build_change_groups(entries)
    buckets = group_by_tag(groups)
    
    # Calculate top focus areas
    tag_order = [t for t in TAG_ORDER if t in buckets] + [t for t in sorted(buckets) if t not in TAG_ORDER]
    top_focus = ", ".join(tag_order[:3]) if tag_order else "multiple areas"
    
    return (
        f"This release includes {len(entries)} changelog updates across "
        f"{len(groups)} grouped workstreams, focused on {top_focus}."
    )

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
