"""
Shared utilities for changelog and release note scripts.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from typing import Any, List, Optional, Tuple, Dict
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from pathlib import Path

# Paths — changelog data lives in the TARGET WORKSPACE, not the agent runtime.
# AGENT_WORKSPACE_ROOT is set by install.py/manage_runtime before launching.
# Falls back to cwd so the scripts still work when run from inside the workspace.
_RUNTIME_ROOT = Path(__file__).resolve().parent.parent.parent
_WORKSPACE_ROOT = Path(os.environ.get("AGENT_WORKSPACE_ROOT", "")).resolve() \
    if os.environ.get("AGENT_WORKSPACE_ROOT", "").strip() \
    else Path.cwd().resolve()

# CONFIG_FILE and PYPROJECT_TOML reference the runtime/agent-system repo
CONFIG_FILE = Path(__file__).resolve().parent / "changelog-config.json"
PYPROJECT_TOML = _RUNTIME_ROOT / "pyproject.toml"
RELEASE_PLEASE_MANIFEST = _WORKSPACE_ROOT / ".release-please-manifest.json"

# Changelog paths point at the TARGET WORKSPACE so entries are committed there
CHANGELOG_DIR = _WORKSPACE_ROOT / "agent_system" / "reporting" / "data"
CHANGELOG_JSON = CHANGELOG_DIR / "CHANGELOG.json"
CHANGELOG_ARCHIVE_JSON = CHANGELOG_DIR / "CHANGELOG.archive.json"
CHANGELOG_SUMMARIES_JSON = CHANGELOG_DIR / "CHANGELOG.summaries.json"
CHANGELOG_MD = _WORKSPACE_ROOT / "agent_system" / "CHANGELOG.md"

# Backward-compat alias
PROJECT_ROOT = _WORKSPACE_ROOT

TAG_ORDER = [
    "New Feature",
    "Bug Fix",
    "UI Improvement",
    "Performance Improvement",
    "Code Refactoring",
    "Configuration Cleanup",
    "Documentation Update",
    "Test Update",
    "Dependency Update",
    "Build / Packaging",
]

def load_json(p: Path) -> dict:
    if not p.exists(): return {}
    try: return json.loads(p.read_text(encoding="utf-8-sig"))
    except: return {}

def load_json_list(p: Path) -> List[dict]:
    if not p.exists(): return []
    try: return json.loads(p.read_text(encoding="utf-8-sig"))
    except: return []

def save_json_list(p: Path, obj: List[dict]) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

def dump_json(p: Path, obj: Any) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

def load_config() -> dict:
    if not CONFIG_FILE.exists(): return {}
    return load_json(CONFIG_FILE).get("changelog_summarization", {})

def load_summaries() -> dict:
    return load_json(CHANGELOG_SUMMARIES_JSON)

def save_summaries(summaries: dict) -> None:
    dump_json(CHANGELOG_SUMMARIES_JSON, summaries)

def get_current_version() -> str:
    if not PYPROJECT_TOML.exists(): return "0.0.0"
    content = PYPROJECT_TOML.read_text(encoding="utf-8")
    match = re.search(r'version\s*=\s*"(.*?)"', content)
    return match.group(1) if match else "0.0.0"

def normalize_llm_summary(summary: str, entries: List[dict] = None) -> str:
    if not summary or not summary.strip():
        return summary

    lines = summary.split('\n')
    start_idx = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith('###') or stripped.startswith('##'):
            start_idx = i
            break

    end_idx = len(lines)
    for i in range(len(lines) - 1, -1, -1):
        stripped = lines[i].strip()
        if stripped.startswith('**Note:') or stripped.startswith('Note:'):
            end_idx = i
            break
        elif stripped == '---' and i > start_idx + 2:
            end_idx = i
            break

    content_lines = lines[start_idx:end_idx]
    
    headers_seen = {}
    ranges_to_remove = []
    for i, line in enumerate(content_lines):
        stripped = line.strip()
        if stripped.startswith('###') or stripped.startswith('##'):
            normalized_header = '### ' + stripped.lstrip('#').strip()
            if normalized_header in headers_seen:
                prev_idx = headers_seen[normalized_header]
                ranges_to_remove.append((prev_idx, i))
            headers_seen[normalized_header] = i

    filtered_lines = []
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
            filtered_lines.append(stripped)

    normalized = []
    has_overview = False
    first_section_idx = None
    for i, line in enumerate(filtered_lines):
        stripped = line.rstrip()
        if stripped == '---': continue
        if stripped.startswith('###') and first_section_idx is None:
            first_section_idx = len(normalized)
        if stripped.startswith('### Overview'):
            has_overview = True
        normalized.append(stripped)

    if not has_overview and first_section_idx is not None:
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
            if first_section_idx == 0:
                normalized.insert(0, '### Overview')
                normalized.insert(1, 'Summary of changes in this release.')
                normalized.insert(2, '')
            else:
                normalized.insert(first_section_idx, '')
                normalized.insert(first_section_idx, 'Summary of changes in this release.')
                normalized.insert(first_section_idx, '### Overview')

    final = []
    prev_blank = False
    for line in normalized:
        is_blank = not line.strip()
        if is_blank and prev_blank: continue
        final.append(line)
        prev_blank = is_blank

    return '\n'.join(final).strip()

def run_llm_with_fallback(prompt: str, config: dict, preferred_backend: str = None, entries: List[dict] = None) -> Tuple[Optional[str], Optional[str]]:
    common = config.get("common", {})
    fallback_order = list(common.get("fallback_order", ["local-llm", "opencode", "gemini", "claude-cli", "codex", "copilot"]))
    if preferred_backend and preferred_backend in fallback_order:
        fallback_order.remove(preferred_backend)
        fallback_order.insert(0, preferred_backend)

    for backend in fallback_order:
        method_name = f"call_{backend.replace('-', '_')}"
        if backend == "claude-cli": method_name = "call_claude_cli"
        if backend == "codex": method_name = "call_codex_cli"
        if backend == "gemini": method_name = "call_gemini_cli"
        if backend == "opencode": method_name = "call_opencode_cli"
        if backend == "copilot": method_name = "call_copilot_cli"
        
        if hasattr(sys.modules[__name__], method_name):
            method = getattr(sys.modules[__name__], method_name)
            result = method(prompt, config)
            if result: return result, backend
    return None, "none"

def call_local_llm(prompt: str, config: dict) -> Optional[str]:
    import requests
    local_cfg = config.get("local_llm", {})
    url = local_cfg.get("base_url", "http://localhost:11434/v1").rstrip('/') + "/chat/completions"
    model = local_cfg.get("model", "local-model")
    
    try:
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1
        }
        res = requests.post(url, json=payload, timeout=config.get("common", {}).get("timeout_seconds", 300))
        res.raise_for_status()
        return res.json()['choices'][0]['message']['content']
    except Exception as e:
        print(f"DEBUG: local-llm failed: {e}")
        return None

def call_claude_cli(prompt: str, config: dict) -> Optional[str]:
    import subprocess
    model = config.get("claude_cli", {}).get("model")
    cmd = ["claude", "-p", prompt]
    if model: cmd.extend(["-m", model])
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=config.get("common", {}).get("timeout_seconds", 300))
        return res.stdout if res.returncode == 0 else None
    except: return None

def call_codex_cli(prompt: str, config: dict) -> Optional[str]:
    import subprocess
    model = config.get("codex", {}).get("model")
    cmd = ["codex", "exec", "-"]
    if model: cmd.extend(["--model", model])
    try:
        res = subprocess.run(cmd, input=prompt, capture_output=True, text=True, timeout=config.get("common", {}).get("timeout_seconds", 300))
        return res.stdout if res.returncode == 0 else None
    except: return None

def call_gemini_cli(prompt: str, config: dict) -> Optional[str]:
    import subprocess
    model = config.get("gemini", {}).get("model")
    cmd = ["gemini", "-p", prompt]
    if model: cmd.extend(["-m", model])
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=config.get("common", {}).get("timeout_seconds", 300))
        return res.stdout if res.returncode == 0 else None
    except: return None

def call_opencode_cli(prompt: str, config: dict) -> Optional[str]:
    import subprocess
    model = config.get("opencode", {}).get("model")
    cmd = ["opencode", "run"]
    if model: cmd.extend(["-m", model])
    cmd.append(prompt)
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=config.get("common", {}).get("timeout_seconds", 300))
        return res.stdout if res.returncode == 0 else None
    except: return None

def call_copilot_cli(prompt: str, config: dict) -> Optional[str]:
    return None # Copilot CLI is hard to automate via subprocess for this

def build_change_groups(entries: List[dict]) -> List[dict]:
    groups = defaultdict(list)
    for e in entries:
        groups[e.get("change_group", "misc")].append(e)
    result = []
    for key, items in groups.items():
        result.append({
            "group_key": key,
            "headline": items[0]["summary"],
            "entry_count": len(items),
            "latest_date": max(i.get("date", "0000-00-00") for i in items),
            "primary_tag": items[0]["summary_tags"][0] if items[0].get("summary_tags") else "Other",
            "explicit_group": key != "misc"
        })
    return result

def group_by_tag(groups: List[dict]) -> dict:
    buckets = defaultdict(list)
    for g in groups:
        buckets[g["primary_tag"]].append(g)
    return buckets

def _intelligent_tag_summary(tag: str, groups: List[dict]) -> str:
    topics = ", ".join(set(g["headline"].lower() for g in groups[:3]))
    return f"{tag}s: {topics}"

def _shorten_group_key(key: str) -> str: return key
def _version_tuple(v: str) -> tuple:
    return tuple(map(int, (re.sub(r'[^0-9.]', '', v).split('.'))))

def get_changes_grouped_by_version():
    released = load_json_list(CHANGELOG_ARCHIVE_JSON)
    unreleased = load_json_list(CHANGELOG_JSON)
    all_changes = unreleased + released
    versions = defaultdict(list)
    for c in all_changes:
        v = c.get("plugin_version", "unreleased")
        versions[v].append(c)
    return versions

def format_version_header(v, date):
    if v == "unreleased": return "## Unreleased"
    return f"## v{v} — {date}"

def get_summaries(): return load_json(CHANGELOG_SUMMARIES_JSON)
