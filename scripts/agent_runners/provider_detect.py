"""
provider_detect.py - Detect installed AI agent CLI tools and VS Code extensions.

Used by install.py during workspace setup to discover what providers are available
and offer an interactive selection to enable/disable them in delegation-config.json.

Pure stdlib — safe to run before the venv exists.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Provider registry
# ---------------------------------------------------------------------------
# Each entry describes one provider the agent system knows about.
# install_hint: shown when the provider is not found.
# vscode_extensions: list of extension IDs that count as "present" for this provider.
# cli_bins: executable names to probe (first found wins).
# check_args: args to pass to confirm the binary actually works (e.g. --version).
# npm_packages: npm global package names to check as a fallback.

@dataclass
class ProviderSpec:
    name: str                              # canonical name (matches delegation-config.json)
    label: str                             # human-readable name
    provider_type: str                     # "cli" | "subscription" | "api_keyed" | "extension"
    cli_bins: list[str] = field(default_factory=list)
    check_args: list[str] = field(default_factory=lambda: ["--version"])
    npm_packages: list[str] = field(default_factory=list)
    vscode_extensions: list[str] = field(default_factory=list)
    install_hint: str = ""


KNOWN_PROVIDERS: list[ProviderSpec] = [
    ProviderSpec(
        name="claude",
        label="Claude (Anthropic Claude Code CLI)",
        provider_type="cli",
        cli_bins=["claude"],
        check_args=["--version"],
        npm_packages=["@anthropic-ai/claude-code"],
        vscode_extensions=["anthropic.claude-code"],
        install_hint="npm install -g @anthropic-ai/claude-code",
    ),
    ProviderSpec(
        name="gemini",
        label="Gemini (Google Gemini CLI)",
        provider_type="cli",
        cli_bins=["gemini"],
        check_args=["--version"],
        npm_packages=["@google/gemini-cli"],
        vscode_extensions=["google.gemini-cli-vscode-ide-companion", "google.google-gemini"],
        install_hint="npm install -g @google/gemini-cli",
    ),
    ProviderSpec(
        name="opencode",
        label="OpenCode",
        provider_type="cli",
        cli_bins=["opencode"],
        check_args=["--version"],
        npm_packages=["opencode-ai"],
        vscode_extensions=[],
        install_hint="npm install -g opencode-ai",
    ),
    ProviderSpec(
        name="codex",
        label="Codex (OpenAI Codex CLI)",
        provider_type="cli",
        cli_bins=["codex"],
        check_args=["--version"],
        npm_packages=["@openai/codex"],
        # openai.chatgpt is the ChatGPT extension — separate from the Codex CLI
        vscode_extensions=["openai.chatgpt"],
        install_hint="npm install -g @openai/codex",
    ),
    ProviderSpec(
        name="cline",
        label="Cline (VS Code extension)",
        provider_type="extension",
        cli_bins=[],
        npm_packages=[],
        vscode_extensions=["saoudrizwan.claude-dev"],
        install_hint="Install 'Cline' from the VS Code marketplace (saoudrizwan.claude-dev)",
    ),
    ProviderSpec(
        name="copilot",
        label="GitHub Copilot (gh CLI + extension)",
        provider_type="subscription",
        cli_bins=["gh"],
        check_args=["copilot", "--version"],
        npm_packages=[],
        vscode_extensions=["github.copilot", "github.copilot-chat"],
        install_hint="gh extension install github/gh-copilot",
    ),
    ProviderSpec(
        name="ollama",
        label="Ollama (local CLI daemon)",
        provider_type="api_keyed",
        cli_bins=["ollama"],
        check_args=["--version"],
        npm_packages=[],
        vscode_extensions=[],
        install_hint="https://ollama.com/download",
    ),
    ProviderSpec(
        name="lmstudio",
        label="LM Studio (local GUI + API)",
        provider_type="api_keyed",
        cli_bins=["lms"],          # LM Studio CLI (lms), available in newer versions
        check_args=["--version"],
        npm_packages=[],
        vscode_extensions=[],
        install_hint="https://lmstudio.ai/download",
    ),
]

# ---------------------------------------------------------------------------
# Install directory hints for filesystem-based detection (no CLI required)
# ---------------------------------------------------------------------------
# Maps provider name -> list of candidate install dirs to check for existence.
# Used as a supplementary detection signal when the CLI binary isn't in PATH.

_INSTALL_DIR_HINTS: dict[str, list[Path]] = {
    "ollama": [
        Path.home() / ".ollama",
        Path("C:/Program Files/Ollama"),
        Path.home() / "AppData/Local/Programs/Ollama",
    ],
    "lmstudio": [
        Path.home() / ".lmstudio",
        Path.home() / "AppData/Local/LM Studio",
        Path.home() / "AppData/Local/Programs/LM Studio",
        Path("/Applications/LM Studio.app"),               # macOS
    ],
}


# ---------------------------------------------------------------------------
# Detection result
# ---------------------------------------------------------------------------

@dataclass
class DetectionResult:
    spec: ProviderSpec
    cli_found: bool = False
    cli_bin: str = ""
    cli_version: str = ""
    extension_found: bool = False
    extension_ids: list[str] = field(default_factory=list)
    install_dir_found: bool = False
    install_dir: str = ""

    @property
    def available(self) -> bool:
        return self.cli_found or self.extension_found or self.install_dir_found

    def summary_line(self) -> str:
        parts = []
        if self.cli_found:
            ver = f" ({self.cli_version})" if self.cli_version else ""
            parts.append(f"CLI:{self.cli_bin}{ver}")
        if self.extension_found:
            parts.append(f"ext:{','.join(self.extension_ids)}")
        if self.install_dir_found and not self.cli_found:
            parts.append(f"dir:{self.install_dir}")
        if not parts:
            return "not found"
        return "  ".join(parts)


# ---------------------------------------------------------------------------
# VS Code extension list (cached for the session)
# ---------------------------------------------------------------------------

_vscode_extensions: Optional[set[str]] = None

# Candidate directories where VS Code stores extensions.
# Checked in order; first existing dir wins.
_VSCODE_EXT_DIRS: list[Path] = [
    Path.home() / ".vscode" / "extensions",                    # standard
    Path.home() / ".vscode-insiders" / "extensions",           # VS Code Insiders
    Path(os.environ.get("APPDATA", "")) / "Code" / "extensions" if os.name == "nt" else Path("/dev/null"),
]


def _get_vscode_extensions() -> set[str]:
    """
    Return the set of installed VS Code extension IDs (lower-case).

    Strategy:
    1. Scan ~/.vscode/extensions/ on disk — most reliable cross-platform, no
       dependency on `code` being in PATH.
    2. Fall back to `code --list-extensions` (or `code.cmd` on Windows) if the
       extensions directory is not found.
    """
    global _vscode_extensions
    if _vscode_extensions is not None:
        return _vscode_extensions

    # --- Strategy 1: filesystem scan ---
    for ext_dir in _VSCODE_EXT_DIRS:
        if ext_dir.is_dir():
            ids: set[str] = set()
            for entry in ext_dir.iterdir():
                if not entry.is_dir():
                    continue
                # Folder names are like "publisher.name-1.2.3" or "publisher.name-1.2.3-platform"
                # Strip the trailing version segment(s) to get "publisher.name"
                parts = entry.name.split("-")
                # Find the first version-looking segment (starts with a digit)
                ext_id = parts[0]
                for i, p in enumerate(parts[1:], 1):
                    if p and p[0].isdigit():
                        ext_id = "-".join(parts[:i])
                        break
                ids.add(ext_id.lower())
            _vscode_extensions = ids
            return _vscode_extensions

    # --- Strategy 2: shell out to code CLI ---
    for code_cmd in (["code.cmd"] if os.name == "nt" else []) + ["code"]:
        if not shutil.which(code_cmd):
            continue
        try:
            result = subprocess.run(
                [code_cmd, "--list-extensions"],
                capture_output=True, text=True, timeout=15,
                shell=(os.name == "nt"),  # needed for .cmd files on Windows
            )
            if result.returncode == 0:
                _vscode_extensions = {
                    e.strip().lower() for e in result.stdout.splitlines() if e.strip()
                }
                return _vscode_extensions
        except Exception:
            continue

    _vscode_extensions = set()
    return _vscode_extensions


# ---------------------------------------------------------------------------
# CLI probe
# ---------------------------------------------------------------------------

def _probe_cli(spec: ProviderSpec) -> tuple[bool, str, str]:
    """Return (found, bin_name, version_string)."""
    for bin_name in spec.cli_bins:
        resolved = shutil.which(bin_name)
        if not resolved:
            continue
        # Try to get a version string
        try:
            r = subprocess.run(
                [bin_name] + spec.check_args,
                capture_output=True, text=True, timeout=10,
            )
            output = (r.stdout + r.stderr).strip()
            # Take first non-empty line as version
            version = next((ln.strip() for ln in output.splitlines() if ln.strip()), "")
            # Trim very long outputs
            if len(version) > 80:
                version = version[:77] + "..."
            return True, bin_name, version
        except Exception:
            # Binary exists but check_args failed — still count as found
            return True, bin_name, ""
    return False, "", ""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def detect_all() -> list[DetectionResult]:
    """Run detection for all known providers."""
    try:
        vscode_exts = _get_vscode_extensions()
    except Exception:
        vscode_exts = set()

    results: list[DetectionResult] = []
    for spec in KNOWN_PROVIDERS:
        r = DetectionResult(spec=spec)

        # CLI probe
        r.cli_found, r.cli_bin, r.cli_version = _probe_cli(spec)

        # VS Code extension probe
        for ext_id in spec.vscode_extensions:
            if ext_id.lower() in vscode_exts:
                r.extension_found = True
                r.extension_ids.append(ext_id)

        # Install directory probe (for GUI apps without a CLI in PATH)
        if not r.cli_found:
            for hint_dir in _INSTALL_DIR_HINTS.get(spec.name, []):
                if hint_dir.exists():
                    r.install_dir_found = True
                    r.install_dir = str(hint_dir)
                    break

        results.append(r)
    return results


def print_detection_report(results: list[DetectionResult]) -> None:
    """Print a human-readable detection table to stdout."""
    col_w = 38
    print()
    print("  Agent Provider Detection")
    print("  " + "-" * (col_w + 30))
    print(f"  {'Provider':<{col_w}} {'Status'}")
    print("  " + "-" * (col_w + 30))
    for r in results:
        status = "[+] " + r.summary_line() if r.available else "[-] not installed"
        print(f"  {r.spec.label:<{col_w}} {status}")
    print("  " + "-" * (col_w + 30))
    print()


def interactive_select(results: list[DetectionResult]) -> list[str]:
    """
    Present an interactive menu and return a list of provider names the user
    chose to enable.  Pre-selects all available providers.

    Returns empty list if stdin is not a TTY (non-interactive mode).
    """
    if not sys.stdin.isatty():
        # Non-interactive: enable all found providers
        return [r.spec.name for r in results if r.available]

    print("  Select providers to enable (press Enter to accept defaults).")
    print("  Available providers are pre-selected [y]. Type y/n for each.\n")

    enabled: list[str] = []
    for r in results:
        default = "y" if r.available else "n"
        avail_str = r.summary_line() if r.available else "not installed"
        prompt = f"  Enable {r.spec.label} [{default.upper()}]? ({avail_str}): "
        try:
            raw = input(prompt).strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        choice = raw if raw in ("y", "n") else default
        if choice == "y":
            if not r.available:
                print(f"    NOTE: {r.spec.label} is not installed. It will be marked enabled")
                print(f"          but may fail at runtime.")
                print(f"          Install with: {r.spec.install_hint}")
            enabled.append(r.spec.name)

    return enabled


def apply_to_config(
    config_path: Path,
    enabled_providers: list[str],
    results: list[DetectionResult],
) -> bool:
    """
    Update delegation-config.json so each provider's enabled flag matches
    the user's selection.  Returns True if the file was changed.
    """
    if not config_path.exists():
        return False

    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except Exception:
        return False

    enabled_set = set(enabled_providers)
    changed = False

    for section in ("planners", "executors"):
        section_data = config.get(section, {})
        for name, cfg in section_data.items():
            should_enable = name in enabled_set
            if cfg.get("enabled") != should_enable:
                cfg["enabled"] = should_enable
                changed = True

    # Also update providers section if present
    providers_data = config.get("providers", {})
    for name in providers_data:
        # providers section doesn't have enabled flag by default — skip
        pass

    if changed:
        config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")

    return changed


# ---------------------------------------------------------------------------
# CLI for standalone use
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    results = detect_all()
    print_detection_report(results)
