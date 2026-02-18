# Changelog

All agent-driven changes to this repository are logged here.  
Source of truth (full structured data): [`CHANGELOG.json`](CHANGELOG.json)

---

## Summary

| ID | Date | Agent | Tags | Summary |
|----|------|-------|------|---------|
| CHG-003 | 2026-02-19 | copilot | Documentation Update | Strengthened changelog policy: recording is now required after every task, not at end of session |
| CHG-002 | 2026-02-19 | copilot | Documentation Update, Configuration Cleanup | Established cross-agent changelog infrastructure committed to the repository |
| CHG-001 | 2026-02-19 | copilot | Configuration Cleanup, Code Refactoring | Moved bundled data files to `data/` subdirectory and centralised path references |

---

## Detail

### CHG-003 — 2026-02-19 · copilot · plugin v0.2.0

**Tags:** Documentation Update

**Summary:** Strengthened changelog policy: recording is now required after every task, not at end of session

**Changes:**
- Changed trigger from "end of session" to "after completing any task that modifies files"
- Added explicit instruction: do not skip, do not wait for the user to ask
- Updated `CLAUDE.md`, `AGENTS.md`, and `.github/copilot-instructions.md` with new wording

### CHG-002 — 2026-02-19 · copilot · plugin v0.2.0

**Tags:** Documentation Update, Configuration Cleanup

**Summary:** Established cross-agent changelog infrastructure committed to the repository

**Changes:**
- Created `CHANGELOG.json` at repo root as structured machine-readable history for all agents
- Created `CHANGELOG.md` at repo root as human-readable summary table and detail sections
- Added changelog policy (read at session start, write at session end) to `CLAUDE.md`, `AGENTS.md`, and `.github/copilot-instructions.md`
- Removed `CLAUDE.md`, `AGENTS.md`, and `.github/` from `.gitignore` so agent instructions travel with the repo across machines
- Per-agent runtime scratch dirs (`agent_artifacts/claude|codex|copilot/`) remain gitignored
- Updated `agent_artifacts/README.md` to reflect new structure

### CHG-001 — 2026-02-19 · copilot · plugin v0.2.0

**Tags:** Configuration Cleanup, Code Refactoring

**Summary:** Moved bundled data files to `data/` subdirectory and centralised path references

**Changes:**
- Created `data/` directory to hold all bundled plugin data and example files
- Moved `signals_catalog.json`, `rules.json.example`, `icon_map.json`, `dev_paths.json.example` to `data/` via `git mv`
- Created `src/edmcruleengine/paths.py` as single source of truth: `PLUGIN_DATA_DIR` constant and `data_path()` helper
- Added `DATA_DIR = PROJECT_ROOT / "data"` to `scripts/dev_paths.py` for script-side consistency
- Updated 18 files across `src/`, `scripts/`, and `test/` to reference new `data/` paths
- Fixed packaging bug: `icon_map.json` was previously not included in the distributable ZIP
