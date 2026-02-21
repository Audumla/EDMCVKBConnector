# Development Guide

This document is for contributors and maintainers. End-user installation is documented in `README.md`.

## Repository Layout
- `load.py`: EDMC plugin entrypoint and plugin preferences UI.
- `src/edmcruleengine/`: runtime modules (rules engine, signal derivation, VKB client, trackers).
- `signals_catalog.json`: signal/operator catalog used by the runtime and rule editor.
- `rules.json.example`: starter rules file copied on first run.
- `scripts/`: maintained development and packaging utilities.
- `test/`: automated tests.

## Local Development Workflow
1. Bootstrap local dev environment:
```bash
python scripts/bootstrap_dev_env.py
```
2. Launch EDMC using isolated dev config:
```bash
python scripts/run_edmc_from_dev.py
```
3. Package release ZIP:
```bash
python scripts/package_plugin.py
```

## Runtime Flow (High Level)
1. `plugin_start3` builds `Config`, `EventHandler`, and `EventRecorder`.
2. `EventHandler` loads `signals_catalog.json` and `rules.json`.
3. EDMC notifications (`journal`, `dashboard`, `capi`, `capi_fleetcarrier`) are normalized into one rule pipeline.
4. `SignalDerivation` derives catalog signals from incoming payloads.
5. `RuleEngine` evaluates rules and emits edge-triggered actions.
6. VKB actions are encoded as `VKBShiftBitmap` packets and sent through `VKBClient`.
7. Optionally, events not present in the catalog are recorded by `UnregisteredEventsTracker` (controlled by the **Capture missed events** checkbox in the **Events** tab; off by default).

## Testing
Run targeted tests:
```bash
python -m pytest test/test_rules.py
python -m pytest test/test_multisource_signals.py
```
Run all tests:
```bash
python -m pytest
```

## Maintained Scripts
- `scripts/bootstrap_dev_env.py`: setup and linking workflow.
- `scripts/run_edmc_from_dev.py`: launch EDMC dev instance.
- `scripts/package_plugin.py`: build distributable ZIP.
- `scripts/log_change.py`: append a grouped changelog entry with a globally unique CHG id.
- `scripts/build_changelog.py`: rebuild `CHANGELOG.md` from `docs/changelog/CHANGELOG.json` + `docs/changelog/CHANGELOG.archive.json`.
- `scripts/changelog_activity.py`: pre-release activity (rebuild changelog + compact release-notes preview).
- `scripts/signal_catalog_editor.py`: interactive catalog editor.
- `scripts/validate_signal_catalog.py`: validate catalog structure/operators/event refs.
- `scripts/verify_catalog_coverage.py`: coverage checks against known ED events.
- `scripts/dev_paths.py`: shared path resolution for dev scripts.

## Changelog and Release Prep
1. Record each task with a stable workstream group:
```bash
python scripts/log_change.py \
    --agent codex \
    --group "<workstream-slug>" \
    --tags "Bug Fix" \
    --summary "One-line summary" \
    --details "Detail one" "Detail two"
```
2. Before pushing for release creation, run the activity:
```bash
python scripts/changelog_activity.py --strict
```
3. Review `dist/RELEASE_NOTES.preview.md`, then push and let Release Please create the release.

## Documentation Set
- `README.md`: quick start and documentation map.
- `docs/VKB_LINK_SETUP.md`: practical VKBDevCfg and VKB-Link setup plus managed/manual operation modes.
- `docs/RULE_EDITOR_TUTORIAL.md`: UI guide for creating and managing rules through the plugin settings panel.
- `docs/RULES_GUIDE.md`: complete `rules.json` file format reference (fields, operators, actions, validation).
- `docs/SIGNALS_REFERENCE.md`: complete signal catalog reference (sources/triggers/samples).
- `docs/EDMC_EVENTS_CATALOG.md`: raw event catalog used for validation and reference.
