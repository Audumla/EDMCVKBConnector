# Changelog

## [0.4.0](https://github.com/Audumla/EDMCVKBConnector/compare/v0.3.0...v0.4.0) (2026-02-19)


### Features

* 0.3.0 release ([9f738e8](https://github.com/Audumla/EDMCVKBConnector/commit/9f738e8792dce66fd35c97c45d99b8a02ff89884))
* add log_change.py so agents run one command to record changes (CHG-007) ([142a7e2](https://github.com/Audumla/EDMCVKBConnector/commit/142a7e2a71f6fd76bf0bcfa0dc80a1b47fef5280))
* add release notes generation from CHANGELOG.json ([8af41e7](https://github.com/Audumla/EDMCVKBConnector/commit/8af41e7fb757bfc0292cd8239b500832ecb10f38))

## Changelog

All changes to this repository are logged here.  
Source of truth (full structured data): [`CHANGELOG.json`](CHANGELOG.json)

---

## Summary

| ID | Date | Tags | Summary |
|----|------|------|---------|
| CHG-028 | 2026-02-19 | Bug Fix, UI Improvement | Fix countdown logs, wrong endpoint on reconnect, and disconnected vs reconnecting status mismatch |
| CHG-027 | 2026-02-19 | Bug Fix | Fix VKB-Link restart blocking main thread and status messages never rendering |
| CHG-026 | 2026-02-19 | Bug Fix, UI Improvement | Add diagnostic logging and safety auto-start for VKB-Link during polling |
| CHG-025 | 2026-02-19 | Bug Fix, UI Improvement | Restart VKB-Link when host/port settings change to apply new endpoint configuration |
| CHG-024 | 2026-02-19 | Code Refactoring | Centralize VKB-Link control with consistent 5s post-start delay and unified logging |
| CHG-023 | 2026-02-19 | Bug Fix, Documentation Update | Made VKB-Link startup/shutdown lifecycle status consistently visible in INFO logs |
| CHG-022 | 2026-02-19 | Bug Fix | Ensure shift/subshift state is resent on every new VKB socket connection |
| CHG-021 | 2026-02-19 | Bug Fix, UI Improvement | Reduce false INI mismatch status by syncing path and normalizing host comparison |
| CHG-020 | 2026-02-19 | Bug Fix, UI Improvement | Apply 5s reconnect delay after VKB-Link start/restart recovery and expand lifecycle logging |
| CHG-019 | 2026-02-19 | Bug Fix, UI Improvement | Delay startup connect after launching VKB-Link and show transient connection state |
| CHG-018 | 2026-02-19 | Documentation Update, Code Refactoring | Removed agent source names from changelog storage and rendered outputs |
| CHG-017 | 2026-02-19 | UI Improvement | Speed up pending INI dots and alternate warning color |
| CHG-016 | 2026-02-19 | UI Improvement | Add restart-phase status and dotted INI pending indicator |
| CHG-015 | 2026-02-19 | Bug Fix, UI Improvement | Remove Configure INI button and prioritize standalone INI status messages |
| CHG-014 | 2026-02-19 | UI Improvement | Match VKB-Link status label font and center the row |
| CHG-013 | 2026-02-19 | Bug Fix, UI Improvement | Fix VKB-Link INI button packing when status row moved |
| CHG-012 | 2026-02-19 | UI Improvement | Left-align VKB-Link status text next to its label |
| CHG-011 | 2026-02-19 | UI Improvement | Separated VKB-Link status line into its own frame |
| CHG-010 | 2026-02-19 | Bug Fix, UI Improvement | Fix NameError in VKB-Link prefs and move Update button to status line |
| CHG-009 | 2026-02-19 | UI Improvement | Streamline VKB-Link preferences panel layout and auto-INI synchronization |
| CHG-008 | 2026-02-19 | New Feature | Auto-install cryptography library silently when not present |
| CHG-007 | 2026-02-19 | New Feature | Implement automated VKB-Link download from MEGA public folder with AES-CTR decryption |
| CHG-006 | 2026-02-19 | UI Improvement | Align initial VKB-Link status text with simplified display |
| CHG-005 | 2026-02-19 | Bug Fix, UI Improvement | Improve VKB-Link update discovery and status/error display |
| CHG-004 | 2026-02-19 | New Feature | Add VKB-Link startup/shutdown handling and detailed lifecycle logging |
| CHG-003 | 2026-02-19 | Configuration Cleanup | Added project Codex config for on-request approvals and workspace writes |
| CHG-002 | 2026-02-19 | New Feature, UI Improvement | Added VKB-Link auto-management with download/update and UI controls |
| CHG-001 | 2026-02-19 | Documentation Update | Release notes now show only one-line summaries, not detail bullets |
| CHG-007 | 2026-02-19 | Build / Packaging, Documentation Update | Added log_change.py script so agents run one command to record changes instead of editing files manually |
| CHG-006 | 2026-02-19 | Build / Packaging | Added `CHANGELOG.archive.json` to keep `CHANGELOG.json` small for agent reads |
| CHG-005 | 2026-02-19 | Build / Packaging, Documentation Update | Adopted `unreleased` version sentinel so changelog entries always track the next release, not the last |
| CHG-004 | 2026-02-19 | Build / Packaging, New Feature | Added release notes generation script and wired it into the release workflow and ZIP packaging |
| CHG-003 | 2026-02-19 | Documentation Update | Strengthened changelog policy: recording is now required after every task, not at end of session |
| CHG-002 | 2026-02-19 | Documentation Update, Configuration Cleanup | Established cross-agent changelog infrastructure committed to the repository |
| CHG-001 | 2026-02-19 | Configuration Cleanup, Code Refactoring | Moved bundled data files to `data/` subdirectory and centralised path references |

---

## Detail

### CHG-028 — 2026-02-19 · unreleased

**Tags:** Bug Fix, UI Improvement

**Summary:** Fix countdown logs, wrong endpoint on reconnect, and disconnected vs reconnecting status mismatch

**Changes:**
- Suppress _attempt_vkb_link_recovery during intentional endpoint changes via _endpoint_change_active flag
- Remove countdown logs from all _apply_post_start_delay call sites (countdown=False everywhere)
- Add is_reconnecting() to VKBClient returning True when reconnect worker is active but not yet connected
- Show 'Reconnecting...' (blue) in preferences status panel instead of 'Disconnected' when reconnect worker is running

### CHG-027 — 2026-02-19 · unreleased

**Tags:** Bug Fix

**Summary:** Fix VKB-Link restart blocking main thread and status messages never rendering

**Changes:**
- Moved _apply_endpoint_change() call into a background thread so status updates render before blocking work starts
- Added ini_action_inflight guard to prevent concurrent endpoint-change operations
- Rewrote _poll_vkb_status() to keep main thread clear of subprocess calls; safety auto-start runs in a dedicated background thread with its own inflight guard
- Fixed _apply_endpoint_change() to clear connection_status_override on both success and failure reconnect paths

### CHG-026 — 2026-02-19 · unreleased

**Tags:** Bug Fix, UI Improvement

**Summary:** Add diagnostic logging and safety auto-start for VKB-Link during polling

**Changes:**
- Added diagnostic logging to _apply_ini_update() to reveal why restart may not occur (auto_manage disabled or event_handler unavailable)
- Added safety mechanism in _poll_vkb_status() to auto-start VKB-Link if configured but not running
- Polling loop now checks every 2s if VKB-Link should be running, and starts it if needed (crash recovery)
- Auto-started VKB-Link applies 5s warmup delay and reconnects to ensure stable connection

### CHG-025 — 2026-02-19 · unreleased

**Tags:** Bug Fix, UI Improvement

**Summary:** Restart VKB-Link when host/port settings change to apply new endpoint configuration

**Changes:**
- Added _apply_endpoint_change() to EventHandler that stops VKB-Link, updates INI, restarts process, and reconnects
- Modified prefs_panel to call endpoint change handler instead of just updating INI file
- Added countdown parameter to _apply_post_start_delay() for silent 5s wait without per-second UI updates or logs
- New flow: settings change -> 4s timer -> VKB-Link restart with new endpoint -> 5s silent warmup -> reconnect

### CHG-024 — 2026-02-19 · unreleased

**Tags:** Code Refactoring

**Summary:** Centralize VKB-Link control with consistent 5s post-start delay and unified logging

**Changes:**
- Added action_taken field to VKBLinkActionResult to track lifecycle actions (started/restarted/stopped/none)
- Created _apply_post_start_delay() helper on EventHandler as single point for post-start warmup delay logic
- Replaced string-inspection delay checks with typed action_taken field across startup and recovery paths
- Improved VKB-Link lifecycle logging with clear action state messages (starting/stopping/restarting)

### CHG-023 — 2026-02-19 · unreleased

**Tags:** Bug Fix, Documentation Update

**Summary:** Made VKB-Link startup/shutdown lifecycle status consistently visible in INFO logs

**Changes:**
- Set plugin logger minimum level to INFO in load.py so lifecycle messages are not dropped by higher default levels
- Added explicit startup post-action VKB-Link status logs including running state, exe path, version, and managed flag
- Added explicit shutdown pre-stop and post-stop VKB-Link status logs with started-by-plugin context

### CHG-022 — 2026-02-19 · unreleased

**Tags:** Bug Fix

**Summary:** Ensure shift/subshift state is resent on every new VKB socket connection

**Changes:**
- Re-applied the on-connected callback before connect and recovery reconnect calls
- Added explicit connection log lines showing forced state resend payload
- Updated shift-state sender to return success/failure so resend issues are logged clearly

### CHG-021 — 2026-02-19 · unreleased

**Tags:** Bug Fix, UI Improvement

**Summary:** Reduce false INI mismatch status by syncing path and normalizing host comparison

**Changes:**
- Persisted vkb_ini_path in EDMC config after auto-INI writes from the preferences timer
- Synced the panel's cached INI path from config before status comparisons
- Normalized localhost/loopback host values during INI-vs-prefs checks to avoid false 'INI out of date' alerts

### CHG-020 — 2026-02-19 · unreleased

**Tags:** Bug Fix, UI Improvement

**Summary:** Apply 5s reconnect delay after VKB-Link start/restart recovery and expand lifecycle logging

**Changes:**
- Added reconnect deferral support in VKBClient so retries can be paused after process launch
- Updated recovery flow to wait 5 seconds with status/countdown before reconnect when VKB-Link was started or restarted
- Expanded VKB-Link process lifecycle logs for start/stop/restart actions and INI-update connection state

### CHG-019 — 2026-02-19 · unreleased

**Tags:** Bug Fix, UI Improvement

**Summary:** Delay startup connect after launching VKB-Link and show transient connection state

**Changes:**
- Added startup sequencing so connect waits for VKB-Link start task and pauses 5 seconds when VKB-Link was launched by the plugin
- Exposed temporary connection status overrides on EventHandler for UI visibility during startup/connect
- Updated preferences status polling to display connection override text before normal connected/disconnected state

### CHG-018 — 2026-02-19 · unreleased

**Tags:** Documentation Update, Code Refactoring

**Summary:** Removed agent source names from changelog storage and rendered outputs

**Changes:**
- Updated scripts/log_change.py to stop writing agent fields and to render markdown rows/sections without an Agent column
- Updated scripts/generate_release_notes.py to remove the Agent column from generated release notes tables
- Sanitized existing CHANGELOG.json, CHANGELOG.archive.json, and CHANGELOG.md entries to remove agent source names from recorded metadata and headings

### CHG-017 — 2026-02-19 · unreleased

**Tags:** UI Improvement

**Summary:** Speed up pending INI dots and alternate warning color

**Changes:**
- Increased pending-status dot cadence to 333ms (three dots per second)
- Alternated pending-status color between #f39c12 and darker orange #d68910
- Updated status override matching so dotted 'Settings Changed...' remains in warning style

### CHG-016 — 2026-02-19 · unreleased

**Tags:** UI Improvement

**Summary:** Add restart-phase status and dotted INI pending indicator

**Changes:**
- Added a delayed 'Restarting VKB-Link...' status phase during update actions
- Animated pending INI status by appending dots while waiting for the 4-second auto-write timer
- Added timer cancellation guards so dot animation stops cleanly on apply or focus reset

### CHG-015 — 2026-02-19 · unreleased

**Tags:** Bug Fix, UI Improvement

**Summary:** Remove Configure INI button and prioritize standalone INI status messages

**Changes:**
- Removed the Configure INI control and its visibility logic from the VKB-Link preferences panel
- Made INI status states ('Settings Changed' and 'Updating INI Settings') override connection polling text
- Changed out-of-date INI display to show a standalone 'INI out of date' status instead of appending to established status

### CHG-014 — 2026-02-19 · unreleased

**Tags:** UI Improvement

**Summary:** Match VKB-Link status label font and center the row

**Changes:**
- Set the status label font to match the message size
- Switched the status line to grid layout for consistent vertical centering

### CHG-013 — 2026-02-19 · unreleased

**Tags:** Bug Fix, UI Improvement

**Summary:** Fix VKB-Link INI button packing when status row moved

**Changes:**
- Avoided packing the INI button relative to a widget in a different frame
- Kept INI button ordering relative to Locate button when visible

### CHG-012 — 2026-02-19 · unreleased

**Tags:** UI Improvement

**Summary:** Left-align VKB-Link status text next to its label

**Changes:**
- Set the status label anchor to west so the text starts immediately after the label

### CHG-011 — 2026-02-19 · unreleased

**Tags:** UI Improvement

**Summary:** Separated VKB-Link status line into its own frame

**Changes:**
- Wrapped the VKB-Link status row in a dedicated frame
- Moved the status controls to the new frame to stabilize vertical spacing

### CHG-010 — 2026-02-19 · unreleased

**Tags:** Bug Fix, UI Improvement

**Summary:** Fix NameError in VKB-Link prefs and move Update button to status line

**Changes:**
- Fixed undefined variable reference: changed vkb_app_status_var to vkb_status_var in _run_manager_action()
- Moved Update button to status_row and positioned right-aligned with status indicator
- Removed duplicate _get_vkb_manager() and _check_updates() function definitions

### CHG-009 — 2026-02-19 · unreleased

**Tags:** UI Improvement

**Summary:** Streamline VKB-Link preferences panel layout and auto-INI synchronization

**Changes:**
- Removed 'Manage' button and 'Relocate' function; auto-manage checkbox now on same line as Host/Port fields
- Added 'VKB-Link status:' label; changed status text to 'Link Established vX.X.X' when connected, 'Disconnected' when not
- Removed 'VKB-Link.exe vX.X.X' display; replaced 'Check Updates' button with single 'Update' button
- Implemented auto-INI update: saves INI file 4 seconds after Host/Port change (if auto-manage enabled); timer resets on field focus; shows 'Settings Changed' / 'Updating INI Settings' status

### CHG-008 — 2026-02-19 · unreleased

**Tags:** New Feature

**Summary:** Auto-install cryptography library silently when not present

**Changes:**
- Added _ensure_cryptography() helper that pip-installs the cryptography package via sys.executable if it is not importable
- _fetch_latest_release() and _mega_download() now call _ensure_cryptography() instead of raising ImportError; no user action required

### CHG-007 — 2026-02-19 · unreleased

**Tags:** New Feature

**Summary:** Implement automated VKB-Link download from MEGA public folder with AES-CTR decryption

**Changes:**
- Added MEGA API integration to vkb_link_manager.py: folder listing via https://g.api.mega.co.nz/cs, AES-ECB node-key decryption, AES-CBC attribute decryption, AES-CTR file decryption
- _fetch_latest_release() now queries MEGA as primary source (folder 980CgDDL) and falls back to VKB homepage scraping if unavailable
- New _mega_download() method on VKBLinkManager: requests per-file download URL from MEGA API, streams and decrypts with AES-128-CTR, saves valid zip to disk
- Extended VKBLinkRelease dataclass with mega_node_handle and mega_raw_key optional fields
- Fixed package_plugin.py INCLUDE list: added event_recorder, paths, prefs_panel, ui_components, unregistered_events_tracker, and vkb_link_manager modules

### CHG-006 — 2026-02-19 · unreleased

**Tags:** UI Improvement

**Summary:** Align initial VKB-Link status text with simplified display

**Changes:**
- Initialize VKB-Link status line to 'VKB-Link.exe v?'

### CHG-005 — 2026-02-19 · unreleased

**Tags:** Bug Fix, UI Improvement

**Summary:** Improve VKB-Link update discovery and status/error display

**Changes:**
- Extract OneDrive links specifically from the Software section before scanning for VKB-Link archives
- Show VKB-Link status as '<exe> v<version>' and surface action errors in the status line

### CHG-004 — 2026-02-19 · unreleased

**Tags:** New Feature

**Summary:** Add VKB-Link startup/shutdown handling and detailed lifecycle logging

**Changes:**
- Start VKB-Link on plugin startup when not already running and stop it on plugin shutdown if started by the plugin
- Add step-by-step logging for VKB-Link status, updates, installs, and process control

### CHG-003 — 2026-02-19 · unreleased

**Tags:** Configuration Cleanup

**Summary:** Added project Codex config for on-request approvals and workspace writes

**Changes:**
- Added .codex/config.toml with approval_policy = on-request
- Set sandbox_mode = workspace-write for project-scoped access

### CHG-002 — 2026-02-19 · unreleased

**Tags:** New Feature, UI Improvement

**Summary:** Added VKB-Link auto-management with download/update and UI controls

**Changes:**
- Added VKB-Link manager for process detection, INI sync, and download/update flows
- Hooked recovery into connection failures with configurable auto-manage and cooldown
- Extended preferences UI with VKB-Link management, update, locate, and relocate controls

### CHG-001 — 2026-02-19 · unreleased

**Tags:** Documentation Update

**Summary:** Release notes now show only one-line summaries, not detail bullets

**Changes:**
- Changed group_by_tag() to use entry 'summary' field instead of 'details' list
- Keeps the tag-grouped sections and summary table; removes verbose bullet points

### CHG-007 — 2026-02-19 · unreleased

**Tags:** Build / Packaging, Documentation Update

**Summary:** Added log_change.py script so agents run one command to record changes instead of editing files manually

**Changes:**
- Created scripts/log_change.py: auto-increments CHG-NNN, appends to CHANGELOG.json, prepends row and section to CHANGELOG.md
- Accepts --agent, --tags, --summary, --details, --date, --dry-run flags
- Validates tags against approved vocabulary; rejects unknown values
- Updated CLAUDE.md, AGENTS.md, copilot-instructions.md: replace manual editing instructions with single script call

### CHG-006 — 2026-02-19 · unreleased

**Tags:** Build / Packaging

**Summary:** Added `CHANGELOG.archive.json` to keep `CHANGELOG.json` small for agent reads

**Changes:**
- `generate_release_notes.py --stamp --archive` moves stamped entries to `CHANGELOG.archive.json` after release
- `CHANGELOG.json` retains only `"unreleased"` entries — agent read cost stays constant per release cycle, not growing with history
- `release-please.yml` updated to pass `--archive` and commit `CHANGELOG.archive.json` alongside `CHANGELOG.json`

### CHG-005 — 2026-02-19 · unreleased

**Tags:** Build / Packaging, Documentation Update

**Summary:** Adopted `unreleased` version sentinel so changelog entries always track the next release, not the last

**Changes:**
- Changed agent instructions: `plugin_version` must always be `"unreleased"`, never read from `version.py`
- Rewrote `generate_release_notes.py`: default mode previews unreleased entries; `--stamp <VERSION>` stamps them in-place and writes `RELEASE_NOTES.md`
- Updated `release-please.yml`: use `--stamp` so CI stamps and commits `CHANGELOG.json` on every release
- Added `commit-stamped-changelog` step to workflow so stamps persist in the repo after each release
- Backfilled all existing entries (CHG-001 to CHG-004) from `"0.2.0"` to `"unreleased"`

### CHG-004 — 2026-02-19 · unreleased

**Tags:** Build / Packaging, New Feature

**Summary:** Added release notes generation script and wired it into the release workflow and ZIP packaging

**Changes:**
- Created `scripts/generate_release_notes.py`: reads `CHANGELOG.json`, filters by version, groups by summary tag, outputs `RELEASE_NOTES.md`
- Supports `--version`, `--since`, `--all`, `--output`, `--stdout` flags for flexible local and CI use
- Updated `package_plugin.py` to include `dist/RELEASE_NOTES.md` in the distributable ZIP when present
- Updated `.github/workflows/release-please.yml` to generate release notes before packaging and use them as the GitHub release body

### CHG-003 — 2026-02-19 · unreleased

**Tags:** Documentation Update

**Summary:** Strengthened changelog policy: recording is now required after every task, not at end of session

**Changes:**
- Changed trigger from "end of session" to "after completing any task that modifies files"
- Added explicit instruction: do not skip, do not wait for the user to ask
- Updated `CLAUDE.md`, `AGENTS.md`, and `.github/copilot-instructions.md` with new wording

### CHG-002 — 2026-02-19 · unreleased

**Tags:** Documentation Update, Configuration Cleanup

**Summary:** Established cross-agent changelog infrastructure committed to the repository

**Changes:**
- Created `CHANGELOG.json` at repo root as structured machine-readable history for all agents
- Created `CHANGELOG.md` at repo root as human-readable summary table and detail sections
- Added changelog policy (read at session start, write at session end) to `CLAUDE.md`, `AGENTS.md`, and `.github/copilot-instructions.md`
- Removed `CLAUDE.md`, `AGENTS.md`, and `.github/` from `.gitignore` so agent instructions travel with the repo across machines
- Per-agent runtime scratch dirs (`agent_artifacts/claude|codex|copilot/`) remain gitignored
- Updated `agent_artifacts/README.md` to reflect new structure

### CHG-001 — 2026-02-19 · unreleased

**Tags:** Configuration Cleanup, Code Refactoring

**Summary:** Moved bundled data files to `data/` subdirectory and centralised path references

**Changes:**
- Created `data/` directory to hold all bundled plugin data and example files
- Moved `signals_catalog.json`, `rules.json.example`, `icon_map.json`, `dev_paths.json.example` to `data/` via `git mv`
- Created `src/edmcruleengine/paths.py` as single source of truth: `PLUGIN_DATA_DIR` constant and `data_path()` helper
- Added `DATA_DIR = PROJECT_ROOT / "data"` to `scripts/dev_paths.py` for script-side consistency
- Updated 18 files across `src/`, `scripts/`, and `test/` to reference new `data/` paths
- Fixed packaging bug: `icon_map.json` was previously not included in the distributable ZIP

