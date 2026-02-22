"""
Watch for release-please stamp commits and fast-forward local main automatically.

Intended use:
- Triggered from a local git post-merge hook after merging a release PR into main.
- Polls origin/main until the stamp commit from release workflow appears.
- Performs `git pull --ff-only` when safe (clean tracked worktree).
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def run_git(args: list[str], capture: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=PROJECT_ROOT,
        capture_output=capture,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def git_text(args: list[str]) -> str:
    proc = run_git(args, capture=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or f"git {' '.join(args)} failed")
    return (proc.stdout or "").strip()


def current_branch() -> str:
    return git_text(["rev-parse", "--abbrev-ref", "HEAD"])


def is_clean_tracked() -> bool:
    proc = run_git(["status", "--porcelain", "--untracked-files=no"], capture=True)
    return proc.returncode == 0 and not (proc.stdout or "").strip()


def is_ancestor(older: str, newer: str) -> bool:
    proc = run_git(["merge-base", "--is-ancestor", older, newer], capture=False)
    return proc.returncode == 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Auto pull after release-please stamp commit appears on remote.")
    parser.add_argument("--branch", default="main", help="Branch to watch (default: main)")
    parser.add_argument("--remote", default="origin", help="Remote name (default: origin)")
    parser.add_argument("--poll-seconds", type=int, default=15, help="Poll interval seconds (default: 15)")
    parser.add_argument("--timeout-seconds", type=int, default=1800, help="Timeout seconds (default: 1800)")
    parser.add_argument(
        "--subject-prefix",
        default="chore: stamp changelog entries as v",
        help="Only auto-pull when remote tip subject starts with this prefix.",
    )
    parser.add_argument(
        "--pull-on-any-remote-advance",
        action="store_true",
        help="Pull any fast-forward remote advance (not just stamp commit subject).",
    )
    parser.add_argument(
        "--allow-dirty",
        action="store_true",
        help="Allow pull even when tracked files are dirty.",
    )
    args = parser.parse_args()

    branch = current_branch()
    if branch != args.branch:
        print(f"Skipping auto-pull: current branch is '{branch}', expected '{args.branch}'.")
        return 0

    deadline = time.time() + max(1, int(args.timeout_seconds))
    remote_ref = f"{args.remote}/{args.branch}"

    print(f"Watching {remote_ref} for release stamp commit...")
    while time.time() < deadline:
        fetch = run_git(["fetch", "--prune", args.remote], capture=True)
        if fetch.returncode != 0:
            print(f"WARNING: git fetch failed: {(fetch.stderr or '').strip()}", file=sys.stderr)
            time.sleep(max(1, int(args.poll_seconds)))
            continue

        try:
            local_sha = git_text(["rev-parse", args.branch])
            remote_sha = git_text(["rev-parse", remote_ref])
        except RuntimeError as exc:
            print(f"WARNING: {exc}", file=sys.stderr)
            time.sleep(max(1, int(args.poll_seconds)))
            continue

        if local_sha == remote_sha:
            time.sleep(max(1, int(args.poll_seconds)))
            continue

        if not is_ancestor(local_sha, remote_sha):
            print(
                f"Remote {remote_ref} is not a fast-forward from local {args.branch}; manual sync required.",
                file=sys.stderr,
            )
            return 3

        subject = git_text(["log", "-1", "--pretty=%s", remote_ref])
        if not args.pull_on_any_remote_advance and not subject.startswith(args.subject_prefix):
            # Wait specifically for the release stamp commit created by workflow.
            time.sleep(max(1, int(args.poll_seconds)))
            continue

        if not args.allow_dirty and not is_clean_tracked():
            print(
                "Auto-pull skipped: tracked files are locally modified. Commit/stash changes and pull manually.",
                file=sys.stderr,
            )
            return 2

        pull = run_git(["pull", "--ff-only", args.remote, args.branch], capture=True)
        if pull.returncode != 0:
            print(f"ERROR: git pull failed: {(pull.stderr or '').strip()}", file=sys.stderr)
            return pull.returncode

        print(f"Auto-pull complete. Synced {args.branch} to {remote_sha[:12]}.")
        return 0

    print(f"Timed out after {args.timeout_seconds}s waiting for release stamp commit.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

