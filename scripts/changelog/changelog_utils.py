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
DEFAULT_FALLBACK_ORDER = ["claude-cli", "codex", "gemini", "copilot"]

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
        
        args = [*cmd, "-p", prompt, "-y"]
        if model:
            args.extend(["-m", model])

        result = subprocess.run(
            args,
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

# ---------------------------------------------------------------------------
# Normalization & Orchestration
# ---------------------------------------------------------------------------

def normalize_llm_summary(summary: str) -> str:
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
    headers_seen = set()
    final_lines = []
    
    current_header = None
    header_content = {} # header -> list of lines
    
    # Pass 1: Group content by normalized header
    for line in content_lines:
        stripped = line.strip()
        if stripped.startswith('###') or stripped.startswith('##'):
            current_header = '### ' + stripped.lstrip('#').strip()
            if current_header not in header_content:
                header_content[current_header] = []
        elif current_header:
            header_content[current_header].append(line)
        else:
            # Lines before first header (intro)
            if "_intro_" not in header_content:
                header_content["_intro_"] = []
            header_content["_intro_"].append(line)

    # Pass 2: Reconstruct with single headers
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
    
    # Handle intro
    if "_intro_" in header_content:
        final_lines.extend(header_content["_intro_"])
        
    for h in headers_order:
        final_lines.append("")
        final_lines.append(h)
        final_lines.extend(header_content[h])

    # 4. Ensure Overview section
    has_overview = any(h.startswith('### Overview') for h in headers_order)
    if not has_overview:
        intro_text = None
        if "_intro_" in header_content:
            for line in header_content["_intro_"]:
                if line.strip():
                    intro_text = line.strip()
                    break
        
        insert_text = intro_text if (intro_text and not intro_text.startswith('###')) else "Summary of changes in this release."
        
        # Remove intro from its original place if we're moving it to Overview
        if intro_text and "_intro_" in header_content:
             header_content["_intro_"] = [l for l in header_content["_intro_"] if l.strip() != intro_text]
        
        # Re-reconstruct with overview at top
        new_final = ["### Overview", insert_text]
        if "_intro_" in header_content:
            new_final.extend(header_content["_intro_"])
        
        for h in headers_order:
            new_final.append("")
            new_final.append(h)
            new_final.extend(header_content[h])
        final_lines = new_final

    # 5. Final cleanup of whitespace and consecutive blanks
    output = []
    prev_blank = False
    for line in final_lines:
        is_blank = not line.strip()
        if is_blank and prev_blank:
            continue
        output.append(line.rstrip())
        prev_blank = is_blank

    return '\n'.join(output).strip()

def run_llm_with_fallback(prompt: str, config: dict, preferred_backend: str | None = None) -> tuple[str | None, str]:
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
        else:
            print(f"    Skipping unknown backend: {backend}")
            continue

        if result:
            print(f"    Success with {backend}.")
            return normalize_llm_summary(result), backend
        else:
            print(f"    Failed or empty output from {backend}.")

    return None, "none"
