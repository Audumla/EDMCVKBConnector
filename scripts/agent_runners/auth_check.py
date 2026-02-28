"""
auth_check.py - Per-provider authentication state detection and guided setup.

Checks whether each provider is authenticated and, if not, guides the user
through obtaining and storing credentials.

Auth strategies by provider type:
- cli: run a version/status command — if it exits 0 and doesn't print a login
  prompt, auth is assumed good. For providers like Codex, run `codex login status`.
- api_keyed: check for the required env var (or a persisted key file).
- subscription: check the gh auth status for Copilot.
- extension: VS Code extensions (Cline) manage their own auth — we just remind
  the user to sign in via the extension UI.

Key storage (for api_keyed providers that need an explicit key):
  - Primary:  system keychain via `keyring` package (Windows Credential Manager,
              macOS Keychain, Linux SecretService/KWallet)
  - Fallback: a gitignored .env file at <workspace>/.agent-secrets.env

Pure stdlib for detection; `keyring` is used only if already importable (it's
an optional venv dependency — import guarded with try/except).
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Auth spec: what each provider needs
# ---------------------------------------------------------------------------

@dataclass
class AuthSpec:
    name: str                         # matches provider name in delegation-config
    label: str                        # human-readable
    auth_type: str                    # "cli_login" | "api_key" | "subscription" | "local" | "extension"
    # For api_key type: env var(s) that hold the key (first found wins)
    env_vars: list[str] = field(default_factory=list)
    # For cli_login type: command to run to check auth state
    check_cmd: list[str] = field(default_factory=list)
    # Success criteria: if check_cmd stdout/stderr contains this string, assume logged in
    logged_in_hint: str = ""
    # Failure hint: if this appears in output, definitely not logged in
    logged_out_hint: str = ""
    # keyring service name (for secure storage)
    keyring_service: str = ""
    # How to get credentials if missing
    setup_hint: str = ""
    # URL for manual auth (opened if user chooses)
    auth_url: str = ""
    # API base URL (for api_key providers that can be validated with a test call)
    api_base_url: str = ""


AUTH_SPECS: list[AuthSpec] = [
    AuthSpec(
        name="claude",
        label="Claude (Anthropic Claude Code)",
        auth_type="cli_login",
        check_cmd=["claude", "--version"],
        logged_in_hint="",            # Any successful run means auth is fine
        logged_out_hint="not logged in",
        setup_hint="Run: claude login",
        auth_url="https://claude.ai",
    ),
    AuthSpec(
        name="gemini",
        label="Gemini (Google Gemini CLI)",
        auth_type="cli_login",
        check_cmd=["gemini", "auth", "status"],
        logged_in_hint="authenticated",
        logged_out_hint="not authenticated",
        setup_hint="Run: gemini auth login",
        auth_url="https://gemini.google.com",
    ),
    AuthSpec(
        name="opencode",
        label="OpenCode",
        auth_type="cli_login",
        check_cmd=["opencode", "--version"],
        logged_in_hint="",
        logged_out_hint="not logged in",
        setup_hint="Run: opencode auth login",
        auth_url="https://opencode.ai",
    ),
    AuthSpec(
        name="codex",
        label="Codex (OpenAI Codex CLI)",
        auth_type="cli_login",
        check_cmd=["codex", "login", "status"],
        logged_in_hint="logged in",
        logged_out_hint="not logged in",
        setup_hint="Run: codex login",
        auth_url="https://platform.openai.com/api-keys",
    ),
    AuthSpec(
        name="cline",
        label="Cline (VS Code extension)",
        auth_type="extension",
        setup_hint="Open VS Code → Cline extension → sign in with your Anthropic/OpenAI API key",
        auth_url="https://docs.cline.bot",
    ),
    AuthSpec(
        name="copilot",
        label="GitHub Copilot",
        auth_type="subscription",
        check_cmd=["gh", "auth", "status"],
        logged_in_hint="Logged in to github.com",
        logged_out_hint="not logged in",
        setup_hint="Run: gh auth login",
        auth_url="https://github.com/features/copilot",
    ),
    AuthSpec(
        name="ollama",
        label="Ollama",
        auth_type="local",
        setup_hint="Start Ollama: ollama serve  (or install from https://ollama.com/download)",
    ),
    AuthSpec(
        name="lmstudio",
        label="LM Studio",
        auth_type="local",
        setup_hint="Open LM Studio app, load a model, then start the local server (port 1234)",
        auth_url="https://lmstudio.ai",
    ),
]

# Index by name for fast lookup
_AUTH_SPEC_BY_NAME: dict[str, AuthSpec] = {s.name: s for s in AUTH_SPECS}


# ---------------------------------------------------------------------------
# Auth result
# ---------------------------------------------------------------------------

@dataclass
class AuthResult:
    spec: AuthSpec
    checked: bool = False            # Was a check actually performed?
    authenticated: bool = False
    detail: str = ""                 # Short human-readable status note
    key_source: str = ""             # Where the key came from, if api_key type


# ---------------------------------------------------------------------------
# Keyring helpers (optional — gracefully absent)
# ---------------------------------------------------------------------------

KEYRING_AVAILABLE = False
try:
    import keyring as _keyring  # type: ignore
    KEYRING_AVAILABLE = True
except ImportError:
    pass

KEYRING_USERNAME = "agent-system"


def _keyring_get(service: str) -> Optional[str]:
    if not KEYRING_AVAILABLE or not service:
        return None
    try:
        return _keyring.get_password(service, KEYRING_USERNAME)
    except Exception:
        return None


def _keyring_set(service: str, secret: str) -> bool:
    if not KEYRING_AVAILABLE or not service:
        return False
    try:
        _keyring.set_password(service, KEYRING_USERNAME, secret)
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# .env file helpers
# ---------------------------------------------------------------------------

ENV_FILE_NAME = ".agent-secrets.env"
_ENV_COMMENT = "# agent-system secrets — DO NOT COMMIT (gitignored by agent-system installer)\n"


def _env_file_path(workspace: Optional[Path] = None) -> Path:
    base = workspace or Path.cwd()
    return base / ENV_FILE_NAME


def _read_env_file(workspace: Optional[Path] = None) -> dict[str, str]:
    p = _env_file_path(workspace)
    if not p.exists():
        return {}
    result: dict[str, str] = {}
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            k, _, v = line.partition("=")
            result[k.strip()] = v.strip().strip('"').strip("'")
    return result


def _write_env_file(data: dict[str, str], workspace: Optional[Path] = None) -> None:
    p = _env_file_path(workspace)
    existing = _read_env_file(workspace)
    existing.update(data)
    lines = [_ENV_COMMENT]
    for k, v in sorted(existing.items()):
        lines.append(f'{k}="{v}"\n')
    p.write_text("".join(lines), encoding="utf-8")


def _get_env_key(env_var: str, workspace: Optional[Path] = None) -> tuple[str, str]:
    """Return (value, source) for an API key env var.
    Source is one of: 'env', 'keyring', 'env_file', ''.
    """
    # 1. Live environment
    val = os.environ.get(env_var, "").strip()
    if val:
        return val, "env"

    # 2. Keyring
    val = _keyring_get(f"agent-system:{env_var}") or ""
    if val:
        return val, "keyring"

    # 3. .env file
    env_data = _read_env_file(workspace)
    val = env_data.get(env_var, "").strip()
    if val:
        return val, "env_file"

    return "", ""


# ---------------------------------------------------------------------------
# Individual auth checks
# ---------------------------------------------------------------------------

def _check_cli_login(spec: AuthSpec) -> AuthResult:
    r = AuthResult(spec=spec, checked=True)
    if not spec.check_cmd:
        r.authenticated = True
        r.detail = "no check configured"
        return r

    binary = spec.check_cmd[0]
    if not shutil.which(binary):
        r.authenticated = False
        r.detail = f"{binary} not found in PATH"
        return r

    try:
        result = subprocess.run(
            spec.check_cmd,
            capture_output=True, text=True, timeout=15,
        )
        combined = (result.stdout + result.stderr).lower()

        if spec.logged_out_hint and spec.logged_out_hint.lower() in combined:
            r.authenticated = False
            r.detail = "not logged in"
        elif spec.logged_in_hint and spec.logged_in_hint.lower() in combined:
            r.authenticated = True
            r.detail = "logged in"
        elif result.returncode == 0:
            # No specific hint matched — treat exit 0 as authenticated
            r.authenticated = True
            r.detail = "OK (exit 0)"
        else:
            r.authenticated = False
            r.detail = f"exit {result.returncode}"
    except subprocess.TimeoutExpired:
        r.authenticated = False
        r.detail = "check timed out"
    except Exception as exc:
        r.authenticated = False
        r.detail = str(exc)

    return r


def _check_api_key(spec: AuthSpec, workspace: Optional[Path] = None) -> AuthResult:
    r = AuthResult(spec=spec, checked=True)
    for env_var in spec.env_vars:
        val, source = _get_env_key(env_var, workspace)
        if val:
            r.authenticated = True
            r.detail = f"{env_var} found ({source})"
            r.key_source = source
            # Export into current process env so runners can use it
            os.environ[env_var] = val
            return r
    r.authenticated = False
    r.detail = f"no key found for: {', '.join(spec.env_vars)}"
    return r


def _check_local(spec: AuthSpec) -> AuthResult:
    """Local services don't need credentials — just note if the server is reachable."""
    import urllib.request
    r = AuthResult(spec=spec, checked=True)
    # Best-effort HTTP ping — not a hard requirement
    urls = {
        "ollama": "http://localhost:11434/api/tags",
        "lmstudio": "http://localhost:1234/v1/models",
    }
    url = urls.get(spec.name)
    if not url:
        r.authenticated = True
        r.detail = "no check needed"
        return r
    try:
        req = urllib.request.urlopen(url, timeout=2)
        r.authenticated = True
        r.detail = f"server reachable ({req.getcode()})"
    except Exception:
        r.authenticated = False
        r.detail = "server not reachable (start it manually)"
    return r


def _check_extension(spec: AuthSpec) -> AuthResult:
    """VS Code extensions handle their own auth — we can't check programmatically."""
    r = AuthResult(spec=spec, checked=False)
    r.authenticated = True   # Assume OK — user must manage this in VS Code
    r.detail = "managed by VS Code extension (cannot verify)"
    return r


def check_provider(spec: AuthSpec, workspace: Optional[Path] = None) -> AuthResult:
    if spec.auth_type == "cli_login":
        return _check_cli_login(spec)
    elif spec.auth_type == "api_key":
        return _check_api_key(spec, workspace)
    elif spec.auth_type == "subscription":
        return _check_cli_login(spec)
    elif spec.auth_type == "local":
        return _check_local(spec)
    elif spec.auth_type == "extension":
        return _check_extension(spec)
    else:
        r = AuthResult(spec=spec, checked=False)
        r.detail = f"unknown auth_type: {spec.auth_type}"
        return r


def check_all(provider_names: list[str], workspace: Optional[Path] = None) -> list[AuthResult]:
    """Run auth checks for a list of provider names."""
    results: list[AuthResult] = []
    for name in provider_names:
        spec = _AUTH_SPEC_BY_NAME.get(name)
        if spec is None:
            continue
        results.append(check_provider(spec, workspace))
    return results


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def print_auth_report(results: list[AuthResult]) -> None:
    col_w = 38
    print()
    print("  Authentication Status")
    print("  " + "-" * (col_w + 30))
    print(f"  {'Provider':<{col_w}} {'Auth'}")
    print("  " + "-" * (col_w + 30))
    for r in results:
        if not r.checked:
            status = "[~] " + r.detail
        elif r.authenticated:
            status = "[OK] " + r.detail
        else:
            status = "[!!] " + r.detail
        print(f"  {r.spec.label:<{col_w}} {status}")
    print("  " + "-" * (col_w + 30))
    print()


# ---------------------------------------------------------------------------
# Interactive guided setup
# ---------------------------------------------------------------------------

def prompt_api_key(spec: AuthSpec, workspace: Optional[Path] = None) -> bool:
    """Prompt the user to enter an API key and store it."""
    if not sys.stdin.isatty():
        return False

    print(f"\n  {spec.label} requires an API key.")
    print(f"  {spec.setup_hint}")
    if spec.auth_url:
        print(f"  Get your key at: {spec.auth_url}")

    for env_var in spec.env_vars:
        try:
            raw = input(f"  Enter {env_var} (or press Enter to skip): ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return False

        if not raw:
            continue

        # Store: keyring preferred, .env file fallback
        stored = False
        if KEYRING_AVAILABLE and spec.keyring_service:
            stored = _keyring_set(f"agent-system:{env_var}", raw)
            if stored:
                print(f"  Saved {env_var} to system keychain.")

        if not stored:
            _write_env_file({env_var: raw}, workspace)
            print(f"  Saved {env_var} to {ENV_FILE_NAME} (gitignored).")

        os.environ[env_var] = raw
        return True

    return False


def guided_setup(results: list[AuthResult], workspace: Optional[Path] = None) -> list[str]:
    """
    For each failed auth check, guide the user to fix it.
    Returns list of provider names that are now resolved.
    """
    if not sys.stdin.isatty():
        return []

    resolved: list[str] = []
    needs_action = [r for r in results if not r.authenticated]

    if not needs_action:
        return resolved

    print(f"\n  {len(needs_action)} provider(s) need authentication:\n")

    for r in needs_action:
        spec = r.spec
        print(f"  [{spec.name}] {spec.label}")

        if spec.auth_type == "extension":
            print(f"    Sign in via VS Code: {spec.setup_hint}")
            print(f"    (cannot be automated — skip this and sign in manually)")
            continue

        if spec.auth_type == "local":
            print(f"    {spec.setup_hint}")
            if spec.auth_url:
                print(f"    Download: {spec.auth_url}")
            continue

        if spec.auth_type == "api_key":
            ok = prompt_api_key(spec, workspace)
            if ok:
                resolved.append(spec.name)
            continue

        # cli_login / subscription
        if spec.setup_hint:
            print(f"    {spec.setup_hint}")
        if spec.auth_url:
            print(f"    Info: {spec.auth_url}")
        print()

    return resolved


# ---------------------------------------------------------------------------
# Gitignore helper — ensure .agent-secrets.env is ignored
# ---------------------------------------------------------------------------

def ensure_secrets_gitignored(workspace: Path) -> None:
    """Add .agent-secrets.env to .gitignore if not already present."""
    gitignore = workspace / ".gitignore"
    pattern = ENV_FILE_NAME
    if gitignore.exists():
        content = gitignore.read_text(encoding="utf-8")
        if pattern in content:
            return
        gitignore.write_text(content.rstrip("\n") + f"\n{pattern}\n", encoding="utf-8")
    else:
        gitignore.write_text(f"{pattern}\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Standalone CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Check auth status for AI providers")
    parser.add_argument("providers", nargs="*",
                        default=[s.name for s in AUTH_SPECS],
                        help="Provider names to check (default: all)")
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    parser.add_argument("--fix", action="store_true",
                        help="Prompt to fix missing auth interactively")
    args = parser.parse_args()

    results = check_all(args.providers, workspace=args.workspace)
    print_auth_report(results)

    if args.fix:
        guided_setup(results, workspace=args.workspace)
