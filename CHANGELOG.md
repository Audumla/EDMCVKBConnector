# Changelog

All agent-driven changes to this repository are logged here.  
Source of truth (full structured data): [`CHANGELOG.json`](CHANGELOG.json)

---

## Summary

| ID | Date | Agent | Tags | Summary |
|----|------|-------|------|---------|
| CHG-001 | 2026-02-19 | copilot | Configuration Cleanup, Code Refactoring | Moved bundled data files to `data/` subdirectory and centralised path references |

---

## Detail

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
