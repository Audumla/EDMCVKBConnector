# Agent Artifacts

This directory is reserved for AI agent execution outputs.

## Changelog

`CHANGELOG.json` lives in `docs/changelog/` (with its companion JSON sources), and `CHANGELOG.md` is at the **repo root**. They are the shared cross-agent record of all changes. Every agent reads them at session start and appends to them at session end.

## Per-agent workspace

- `agent_artifacts/codex/reports/`
- `agent_artifacts/codex/temp/`
- `agent_artifacts/copilot/reports/`
- `agent_artifacts/copilot/temp/`
- `agent_artifacts/claude/reports/`
- `agent_artifacts/claude/temp/`

Runtime files in these directories are gitignored.
