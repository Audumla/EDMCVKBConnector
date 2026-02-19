# Changelog

## [0.5.0](https://github.com/Audumla/EDMCVKBConnector/compare/v0.4.0...v0.5.0) (2026-02-19)


### Features

* Repaired deployment scripts ([1e4b58f](https://github.com/Audumla/EDMCVKBConnector/commit/1e4b58fdbbfc072109f1f26e910c5607ce1ba54f))

## [0.4.0](https://github.com/Audumla/EDMCVKBConnector/compare/v0.3.0...v0.4.0) (2026-02-19)


### Features

* 0.3.0 release ([9f738e8](https://github.com/Audumla/EDMCVKBConnector/commit/9f738e8792dce66fd35c97c45d99b8a02ff89884))
* add log_change.py so agents run one command to record changes (CHG-007) ([142a7e2](https://github.com/Audumla/EDMCVKBConnector/commit/142a7e2a71f6fd76bf0bcfa0dc80a1b47fef5280))
* add release notes generation from CHANGELOG.json ([8af41e7](https://github.com/Audumla/EDMCVKBConnector/commit/8af41e7fb757bfc0292cd8239b500832ecb10f38))

## Changelog

All agent-driven changes to this repository are logged here.  
Source of truth (full structured data): [`CHANGELOG.json`](CHANGELOG.json)

---

## Summary

| ID | Date | Agent | Tags | Summary |
|----|------|-------|------|---------|
| CHG-001 | 2026-02-19 | claude | Bug Fix, Build / Packaging | Fix package_plugin.py missing 5 modules from INCLUDE list |
| CHG-007 | 2026-02-19 | copilot | Build / Packaging, Documentation Update | Added log_change.py script so agents run one command to record changes instead of editing files manually |
| CHG-006 | 2026-02-19 | copilot | Build / Packaging | Added `CHANGELOG.archive.json` to keep `CHANGELOG.json` small for agent reads |
| CHG-005 | 2026-02-19 | copilot | Build / Packaging, Documentation Update | Adopted `unreleased` version sentinel so changelog entries always track the next release, not the last |
| CHG-004 | 2026-02-19 | copilot | Build / Packaging, New Feature | Added release notes generation script and wired it into the release workflow and ZIP packaging |
| CHG-003 | 2026-02-19 | copilot | Documentation Update | Strengthened changelog policy: recording is now required after every task, not at end of session |
| CHG-002 | 2026-02-19 | copilot | Documentation Update, Configuration Cleanup | Established cross-agent changelog infrastructure committed to the repository |
| CHG-001 | 2026-02-19 | copilot | Configuration Cleanup, Code Refactoring | Moved bundled data files to `data/` subdirectory and centralised path references |

---

## Detail

### CHG-001 — 2026-02-19 · claude · unreleased

**Tags:** Bug Fix, Build / Packaging

**Summary:** Fix package_plugin.py missing 5 modules from INCLUDE list

**Changes:**
- Added paths.py, event_recorder.py, prefs_panel.py, ui_components.py, unregistered_events_tracker.py
- Missing files caused ModuleNotFoundError when plugin was installed from zip

### CHG-007 — 2026-02-19 · copilot · unreleased

**Tags:** Build / Packaging, Documentation Update

**Summary:** Added log_change.py script so agents run one command to record changes instead of editing files manually

**Changes:**
- Created scripts/log_change.py: auto-increments CHG-NNN, appends to CHANGELOG.json, prepends row and section to CHANGELOG.md
- Accepts --agent, --tags, --summary, --details, --date, --dry-run flags
- Validates tags against approved vocabulary; rejects unknown values
- Updated CLAUDE.md, AGENTS.md, copilot-instructions.md: replace manual editing instructions with single script call

### CHG-006 — 2026-02-19 · copilot · unreleased

**Tags:** Build / Packaging

**Summary:** Added `CHANGELOG.archive.json` to keep `CHANGELOG.json` small for agent reads

**Changes:**
- `generate_release_notes.py --stamp --archive` moves stamped entries to `CHANGELOG.archive.json` after release
- `CHANGELOG.json` retains only `"unreleased"` entries — agent read cost stays constant per release cycle, not growing with history
- `release-please.yml` updated to pass `--archive` and commit `CHANGELOG.archive.json` alongside `CHANGELOG.json`

### CHG-005 — 2026-02-19 · copilot · unreleased

**Tags:** Build / Packaging, Documentation Update

**Summary:** Adopted `unreleased` version sentinel so changelog entries always track the next release, not the last

**Changes:**
- Changed agent instructions: `plugin_version` must always be `"unreleased"`, never read from `version.py`
- Rewrote `generate_release_notes.py`: default mode previews unreleased entries; `--stamp <VERSION>` stamps them in-place and writes `RELEASE_NOTES.md`
- Updated `release-please.yml`: use `--stamp` so CI stamps and commits `CHANGELOG.json` on every release
- Added `commit-stamped-changelog` step to workflow so stamps persist in the repo after each release
- Backfilled all existing entries (CHG-001 to CHG-004) from `"0.2.0"` to `"unreleased"`

### CHG-004 — 2026-02-19 · copilot · unreleased

**Tags:** Build / Packaging, New Feature

**Summary:** Added release notes generation script and wired it into the release workflow and ZIP packaging

**Changes:**
- Created `scripts/generate_release_notes.py`: reads `CHANGELOG.json`, filters by version, groups by summary tag, outputs `RELEASE_NOTES.md`
- Supports `--version`, `--since`, `--all`, `--output`, `--stdout` flags for flexible local and CI use
- Updated `package_plugin.py` to include `dist/RELEASE_NOTES.md` in the distributable ZIP when present
- Updated `.github/workflows/release-please.yml` to generate release notes before packaging and use them as the GitHub release body

### CHG-003 — 2026-02-19 · copilot · unreleased

**Tags:** Documentation Update

**Summary:** Strengthened changelog policy: recording is now required after every task, not at end of session

**Changes:**
- Changed trigger from "end of session" to "after completing any task that modifies files"
- Added explicit instruction: do not skip, do not wait for the user to ask
- Updated `CLAUDE.md`, `AGENTS.md`, and `.github/copilot-instructions.md` with new wording

### CHG-002 — 2026-02-19 · copilot · unreleased

**Tags:** Documentation Update, Configuration Cleanup

**Summary:** Established cross-agent changelog infrastructure committed to the repository

**Changes:**
- Created `CHANGELOG.json` at repo root as structured machine-readable history for all agents
- Created `CHANGELOG.md` at repo root as human-readable summary table and detail sections
- Added changelog policy (read at session start, write at session end) to `CLAUDE.md`, `AGENTS.md`, and `.github/copilot-instructions.md`
- Removed `CLAUDE.md`, `AGENTS.md`, and `.github/` from `.gitignore` so agent instructions travel with the repo across machines
- Per-agent runtime scratch dirs (`agent_artifacts/claude|codex|copilot/`) remain gitignored
- Updated `agent_artifacts/README.md` to reflect new structure

### CHG-001 — 2026-02-19 · copilot · unreleased

**Tags:** Configuration Cleanup, Code Refactoring

**Summary:** Moved bundled data files to `data/` subdirectory and centralised path references

**Changes:**
- Created `data/` directory to hold all bundled plugin data and example files
- Moved `signals_catalog.json`, `rules.json.example`, `icon_map.json`, `dev_paths.json.example` to `data/` via `git mv`
- Created `src/edmcruleengine/paths.py` as single source of truth: `PLUGIN_DATA_DIR` constant and `data_path()` helper
- Added `DATA_DIR = PROJECT_ROOT / "data"` to `scripts/dev_paths.py` for script-side consistency
- Updated 18 files across `src/`, `scripts/`, and `test/` to reference new `data/` paths
- Fixed packaging bug: `icon_map.json` was previously not included in the distributable ZIP
