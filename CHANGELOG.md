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
| CHG-063 | 2026-02-20 | Bug Fix, Test Update | Suppressed send-failed VKB recovery before first successful connection to prevent startup restart loops |
| CHG-062 | 2026-02-20 | Bug Fix, Test Update | Fixed Windows VKB process discovery normalization to stop false duplicate-instance restarts |
| CHG-061 | 2026-02-20 | Bug Fix, Test Update | Prevented duplicate VKB-Link launches by serializing lifecycle operations and closing safety-start race |
| CHG-060 | 2026-02-20 | Bug Fix, Test Update | Added VKB-Link TCP listener readiness wait before reconnect attempts after start/restart |
| CHG-059 | 2026-02-20 | Bug Fix, Test Update | Enforced VKB-Link single-instance behavior by stopping all detected duplicates before restart/stop/update actions |
| CHG-058 | 2026-02-20 | Bug Fix, Configuration Cleanup | Harden VKB-Link restart shutdown timing so low operation timeout does not cause premature force-kill |
| CHG-057 | 2026-02-20 | New Feature, Bug Fix, Test Update | Added configurable VKB-Link launch mode and restored legacy startup behavior by default |
| CHG-056 | 2026-02-19 | Bug Fix, Test Update | Config helper lookups now honor config_defaults values instead of hardcoded fallback literals |
| CHG-055 | 2026-02-19 | Bug Fix, Configuration Cleanup | Start VKB-Link as a detached child process while preserving clean stop behavior |
| CHG-054 | 2026-02-19 | Configuration Cleanup, Test Update | Consolidated VKB-Link and UI timer settings into a smaller shared set |
| CHG-053 | 2026-02-19 | Test Update | Validated Codex delegation script updates with a live test_scripts run |
| CHG-052 | 2026-02-19 | Configuration Cleanup, Test Update, Build / Packaging | Externalized VKB-Link timing defaults to config_defaults and wired runtime modules to config-driven values |
| CHG-051 | 2026-02-19 | Code Refactoring | Fixed pricing and cost calculation approach: no duplication, minimal tokens |
| CHG-050 | 2026-02-19 | Bug Fix | Fixed script issues: --refresh persistence and duplicate pricing table |
| CHG-049 | 2026-02-19 | Test Update | Extend live VKB-Link test to execute real UI endpoint-change flow |
| CHG-048 | 2026-02-19 | New Feature, Documentation Update | Added formatted /codex-results reporting with Codex token and estimated-cost visibility |
| CHG-047 | 2026-02-19 | Test Update, Code Refactoring | Add thorough VKB-Link control tests for UI endpoint-change flow and live stop/start cycle |
| CHG-046 | 2026-02-19 | Bug Fix, Test Update | Use graceful VKB-Link shutdown with forced fallback and wait for INI creation after shutdown |
| CHG-045 | 2026-02-19 | Test Update, Code Refactoring | Move INI patch assertions to pure text tests so tests do not write INI files directly |
| CHG-044 | 2026-02-19 | Bug Fix, Test Update | Update VKB-Link INI in place without overwriting unrelated settings |
| CHG-043 | 2026-02-19 | Performance Improvement, Documentation Update | Optimized Codex delegation token estimates and event parsing |
| CHG-042 | 2026-02-19 | Bug Fix, Test Update | Bootstrap VKB-Link once after fresh install before applying managed INI settings |
| CHG-041 | 2026-02-19 | Documentation Update | Comprehensive code review completed identifying critical security and correctness issues |
| CHG-040 | 2026-02-19 | Test Update | Live VKB-Link test now uses a repo-local runtime directory under test/ |
| CHG-039 | 2026-02-19 | Test Update | Made VKB-Link live integration test run by default on Windows |
| CHG-038 | 2026-02-19 | Documentation Update | Added /codex label convention to CLAUDE.md for delegating tasks to Codex via claude_run_plan.py |
| CHG-037 | 2026-02-19 | New Feature | Added claude_run_plan.py wrapper that appends claude_report.json to Codex run directories |
| CHG-036 | 2026-02-19 | Bug Fix, Test Update | Removed OneDrive/homepage fallback and made VKB-Link release discovery MEGA-only with explicit live-test artifact cleanup |
| CHG-035 | 2026-02-19 | New Feature | Verified run_codex_plan.py live end-to-end with VSCode-bundled codex binary |
| CHG-034 | 2026-02-19 | Bug Fix, Test Update | Force first-run INI targeting to the downloaded executable directory before VKB-Link start |
| CHG-033 | 2026-02-19 | Bug Fix, Test Update | Write VKB-Link INI before starting process after install/download flows |
| CHG-032 | 2026-02-19 | Test Update | Added comprehensive VKB-Link manager tests including an opt-in live production integration path |
| CHG-031 | 2026-02-19 | Bug Fix, New Feature, Documentation Update | Auto-discover VS Code bundled Codex CLI when codex is missing from PATH |
| CHG-030 | 2026-02-19 | Documentation Update | Created test plan and dry-ran run_codex_plan.py to verify plan handoff |
| CHG-029 | 2026-02-19 | New Feature, Documentation Update | Added a Codex plan runner script that writes monitorable run artifacts under agent outputs |
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

### CHG-063 — 2026-02-20 · unreleased

**Tags:** Bug Fix, Test Update

**Summary:** Suppressed send-failed VKB recovery before first successful connection to prevent startup restart loops

**Changes:**
- Added EventHandler connection state flag that is set on first successful socket connection
- _attempt_vkb_link_recovery now skips send_failed-triggered process recovery until a successful connection has been established
- Added unit test for suppressed early send_failed recovery and reran event-handler + manager suites

### CHG-062 — 2026-02-20 · unreleased

**Tags:** Bug Fix, Test Update

**Summary:** Fixed Windows VKB process discovery normalization to stop false duplicate-instance restarts

**Changes:**
- Changed _find_running_processes_windows to prefer unique PID-based results and only run WMIC fallback when PowerShell yields no actionable PID entries
- Hardened WMIC parsing against malformed blank-line blocks so path-only/pid-only partial records no longer create phantom duplicate processes
- Added Windows unit test covering duplicate partial discovery output and verified test_vkb_link_manager.py passes

### CHG-061 — 2026-02-20 · unreleased

**Tags:** Bug Fix, Test Update

**Summary:** Prevented duplicate VKB-Link launches by serializing lifecycle operations and closing safety-start race

**Changes:**
- Added a manager lifecycle lock so ensure_running/update_to_latest/stop_running cannot run concurrently and race into duplicate starts
- Added pre-start recheck paths in ensure_running so if another path starts VKB-Link first, duplicate launch is skipped
- Moved prefs-panel safety inflight flag assignment before thread start and updated manager tests to fully mock multi-process discovery without touching live processes

### CHG-060 — 2026-02-20 · unreleased

**Tags:** Bug Fix, Test Update

**Summary:** Added VKB-Link TCP listener readiness wait before reconnect attempts after start/restart

**Changes:**
- EventHandler now probes host:port readiness (using vkb_link_operation_timeout_seconds and vkb_link_poll_interval_ms) before attempting connect after warmup
- Wired readiness wait into startup connect flow, endpoint-change restart flow, recovery flow, and polling safety auto-start flow
- Updated endpoint-change tests to account for listener readiness probe and re-ran event-handler + manager test suites

### CHG-059 — 2026-02-20 · unreleased

**Tags:** Bug Fix, Test Update

**Summary:** Enforced VKB-Link single-instance behavior by stopping all detected duplicates before restart/stop/update actions

**Changes:**
- Added multi-process discovery helpers for Windows and POSIX so manager can enumerate all running VKB-Link instances
- Updated ensure_running/update_to_latest/stop_running to stop all detected processes when needed and then continue with a single controlled start
- Added regression tests for duplicate-process cleanup in ensure_running and stop_running; test/test_vkb_link_manager.py passes

### CHG-058 — 2026-02-20 · unreleased

**Tags:** Bug Fix, Configuration Cleanup

**Summary:** Harden VKB-Link restart shutdown timing so low operation timeout does not cause premature force-kill

**Changes:**
- Found restart oddness correlated with vkb_link_operation_timeout_seconds set to 2 in config_defaults
- Updated _stop_process to use minimum command timeout 10s and minimum graceful exit wait 8s before escalation
- Validated manager test suite after change

### CHG-057 — 2026-02-20 · unreleased

**Tags:** New Feature, Bug Fix, Test Update

**Summary:** Added configurable VKB-Link launch mode and restored legacy startup behavior by default

**Changes:**
- Introduced vkb_link_launch_mode config key (legacy|detached), defaulting to legacy so plugin-launched behavior matches prior implementation
- Detached startup remains available for troubleshooting via config without code edits
- Updated config helper fallback behavior tests and endpoint-change assertions to follow configured warmup values

### CHG-056 — 2026-02-19 · unreleased

**Tags:** Bug Fix, Test Update

**Summary:** Config helper lookups now honor config_defaults values instead of hardcoded fallback literals

**Changes:**
- Updated EventHandler, VKBLinkManager, and prefs panel config helper methods to call config.get(key) first and only apply literal fallback when missing/invalid
- This fixes warmup/timer overrides from config_defaults.json not taking effect (e.g., vkb_link_warmup_delay_seconds)
- Updated affected tests to assert configured defaults rather than hardcoded timer literals and re-ran targeted suites

### CHG-055 — 2026-02-19 · unreleased

**Tags:** Bug Fix, Configuration Cleanup

**Summary:** Start VKB-Link as a detached child process while preserving clean stop behavior

**Changes:**
- Updated VKBLinkManager._start_process to launch VKB-Link with detached process flags and DEVNULL stdio so it runs independently from the plugin host
- Kept graceful shutdown first and adjusted stop wait window to at least 5 seconds before force termination to improve clean exits
- Validated with test_vkb_link_manager.py and live start/stop/restart integration test

### CHG-054 — 2026-02-19 · unreleased

**Tags:** Configuration Cleanup, Test Update

**Summary:** Consolidated VKB-Link and UI timer settings into a smaller shared set

**Changes:**
- Replaced multiple VKB-Link timer keys with warmup/operation-timeout/poll/restart settings and updated event handler and manager call sites
- Replaced multiple preferences timer keys with UI apply/poll/feedback settings and derived follow-up delay from feedback interval
- Updated defaults/tests and re-ran unit plus live VKB-Link test suites successfully

### CHG-053 — 2026-02-19 · unreleased

**Tags:** Test Update

**Summary:** Validated Codex delegation script updates with a live test_scripts run

**Changes:**
- Executed scripts/claude_run_plan.py with agent_artifacts/claude/temp/test_scripts.md and completed successfully
- Verified status.json cost_estimate matched claude_report.json codex_execution.cost_estimate exactly
- Confirmed scripts/codex_results.py --refresh rewrites codex_results.md and persists regenerated content

### CHG-052 — 2026-02-19 · unreleased

**Tags:** Configuration Cleanup, Test Update, Build / Packaging

**Summary:** Externalized VKB-Link timing defaults to config_defaults and wired runtime modules to config-driven values

**Changes:**
- Added src/edmcruleengine/config_defaults.json and updated config.py to load defaults from this file with a matching fallback map
- Replaced hardcoded VKB-Link and preferences-panel timing constants with config-backed values in event_handler.py, vkb_link_manager.py, and prefs_panel.py
- Updated packaging include list and expanded config tests; re-ran unit + live VKB-Link tests successfully

### CHG-051 — 2026-02-19 · unreleased

**Tags:** Code Refactoring

**Summary:** Fixed pricing and cost calculation approach: no duplication, minimal tokens

**Changes:**
- Reverted run_codex_plan.py to keep CODEX_PRICING local (no imports)
- Modified claude_run_plan.py to read cost_estimate from status.json instead of recalculating
- Falls back to recalculating only if rate overrides are provided or status.json cost is missing
- Result: no duplicate pricing tables, no imports between scripts, no token waste on duplicate calculations

### CHG-050 — 2026-02-19 · unreleased

**Tags:** Bug Fix

**Summary:** Fixed script issues: --refresh persistence and duplicate pricing table

**Changes:**
- Fixed codex_results.py so --refresh flag now persists regenerated content to codex_results.md file
- Removed duplicate CODEX_PRICING table from run_codex_plan.py; now imports from claude_run_plan.py for single source of truth
- Updated CLAUDE.md to document --refresh and --write flag behavior

### CHG-049 — 2026-02-19 · unreleased

**Tags:** Test Update

**Summary:** Extend live VKB-Link test to execute real UI endpoint-change flow

**Changes:**
- Live test now calls EventHandler._apply_endpoint_change with a new port after an explicit stop/start cycle
- Uses EventHandler with the live VKBClient and manager to validate stop, INI patch, restart, reconnect, and send on the new endpoint
- Stubs EventHandler catalog/rules loading in that live-only phase to keep focus on VKB-Link control behavior

### CHG-048 — 2026-02-19 · unreleased

**Tags:** New Feature, Documentation Update

**Summary:** Added formatted /codex-results reporting with Codex token and estimated-cost visibility

**Changes:**
- Enhanced scripts/claude_run_plan.py to estimate Codex execution cost from input/cached/output tokens, include model/rate metadata, and emit codex_results.md alongside claude_report.json
- Enhanced scripts/run_codex_plan.py status.json with structured token_usage and best-effort cost_estimate fields sourced from turn.completed usage events
- Added scripts/codex_results.py plus CLAUDE.md and scripts/README.md updates so /codex-results can print a polished summary including final message, token usage, and estimated spend

### CHG-047 — 2026-02-19 · unreleased

**Tags:** Test Update, Code Refactoring

**Summary:** Add thorough VKB-Link control tests for UI endpoint-change flow and live stop/start cycle

**Changes:**
- Updated EventHandler endpoint-change logic to resolve INI path via _resolve_or_default_ini_path for robust host/port patching
- Added new test_event_handler_vkb_link unit tests covering stop/start, INI patch, config/client endpoint updates, reconnect behavior, and missing-manager handling
- Expanded live VKB-Link test to include an explicit mid-cycle stop/start/reconnect/send sequence before update and cleanup

### CHG-046 — 2026-02-19 · unreleased

**Tags:** Bug Fix, Test Update

**Summary:** Use graceful VKB-Link shutdown with forced fallback and wait for INI creation after shutdown

**Changes:**
- Bootstrap flow now polls for new/touched VKB INI files for several seconds after stopping VKB-Link to catch delayed file writes
- Process stop now attempts graceful termination first (taskkill /T or pkill) and only escalates to force kill if still running
- Updated stop-process test assertions and reran manager + live VKB-Link tests

### CHG-045 — 2026-02-19 · unreleased

**Tags:** Test Update, Code Refactoring

**Summary:** Move INI patch assertions to pure text tests so tests do not write INI files directly

**Changes:**
- Extracted INI update logic into _patch_ini_text and kept _write_ini as thin file I/O wrapper
- Replaced direct _write_ini file-based tests with pure _patch_ini_text assertions
- Reran VKB-Link manager test suite with all tests passing

### CHG-044 — 2026-02-19 · unreleased

**Tags:** Bug Fix, Test Update

**Summary:** Update VKB-Link INI in place without overwriting unrelated settings

**Changes:**
- Reworked _write_ini to patch only [TCP] Adress and Port keys while preserving other sections/comments and inline key comments
- Added fallback behavior to create a minimal [TCP] section when no TCP section exists
- Added unit coverage asserting unrelated INI content survives endpoint updates and reran VKB-Link manager tests

### CHG-043 — 2026-02-19 · unreleased

**Tags:** Performance Improvement, Documentation Update

**Summary:** Optimized Codex delegation token estimates and event parsing

**Changes:**
- Reduced default token estimates from 35k/25k to 5k/2k for typical plan files (80-85% cost reduction)
- Optimized parse_codex_events() to use single-pass event parsing instead of storing all events in memory
- Updated CLAUDE.md documentation to reflect new token defaults and clarify when to override estimates

### CHG-042 — 2026-02-19 · unreleased

**Tags:** Bug Fix, Test Update

**Summary:** Bootstrap VKB-Link once after fresh install before applying managed INI settings

**Changes:**
- ensure_running now performs a bootstrap start/stop cycle after first install when no INI exists, then writes host/port and performs the managed start
- INI resolution now prefers a persisted INI path when it belongs to the active executable directory to avoid stale cross-install paths
- Added unit coverage for the bootstrap sequence and reran VKB-Link manager unit + live tests

### CHG-041 — 2026-02-19 · unreleased

**Tags:** Documentation Update

**Summary:** Comprehensive code review completed identifying critical security and correctness issues

**Changes:**
- Executed static code review via Codex agent covering VKB-Link integration, preferences UI, rules engine, and test suite
- Identified 2 critical security issues: missing executable signature verification, runtime pip auto-install
- Identified 5 high-priority correctness issues: duplicate rule IDs not prevented, incomplete process detection, subshift range inconsistency, rule editor crash path, numeric type casting bugs
- Identified 6 medium-priority issues: stale INI path references, UX inconsistencies, callback accumulation, race condition in safety auto-start, flaky live tests, under-tested recovery paths
- Review artifacts stored in agent_artifacts/codex/reports/plan_runs/20260219T111945Z_code-review/

### CHG-040 — 2026-02-19 · unreleased

**Tags:** Test Update

**Summary:** Live VKB-Link test now uses a repo-local runtime directory under test/

**Changes:**
- Updated test_vkb_link_manager_live to create runtime paths under test/_live_runtime instead of system temp
- Kept per-run isolation with run-<timestamp>-<pid> directories inside test/_live_runtime
- Verified cleanup removes run artifacts and deletes test/_live_runtime when empty

### CHG-039 — 2026-02-19 · unreleased

**Tags:** Test Update

**Summary:** Made VKB-Link live integration test run by default on Windows

**Changes:**
- Removed RUN_VKB_LINK_LIVE env-gate from test/test_vkb_link_manager_live.py so the live test is no longer opt-in
- Removed runtime skip that previously bypassed the test when VKB-Link was already running
- Executed test/test_vkb_link_manager_live.py directly; it now runs automatically and currently xfails on TCP port refusal after successful download/install/start

### CHG-038 — 2026-02-19 · unreleased

**Tags:** Documentation Update

**Summary:** Added /codex label convention to CLAUDE.md for delegating tasks to Codex via claude_run_plan.py

**Changes:**
- Added 'Codex Delegation' section defining the /codex prompt label and the exact steps Claude must follow when it appears
- Steps cover: writing the plan file, calling claude_run_plan.py with token/model args, reporting the outcome, and updating the changelog

### CHG-037 — 2026-02-19 · unreleased

**Tags:** New Feature

**Summary:** Added claude_run_plan.py wrapper that appends claude_report.json to Codex run directories

**Changes:**
- Created scripts/claude_run_plan.py as Claude's entry point for plan execution: calls run_codex_plan.py, then writes claude_report.json alongside the run artifacts
- claude_report.json captures Claude model, input/output tokens, cost estimate (with per-model pricing table), Codex event breakdown (commands/reasoning/messages), token usage with cache hit %, duration, and final_message
- Handles both live and --dry-run modes by matching 'Run directory:' and 'Dry run created:' output prefixes to locate the run directory

### CHG-036 — 2026-02-19 · unreleased

**Tags:** Bug Fix, Test Update

**Summary:** Removed OneDrive/homepage fallback and made VKB-Link release discovery MEGA-only with explicit live-test artifact cleanup

**Changes:**
- Updated src/edmcruleengine/vkb_link_manager.py to remove OneDrive/homepage scraping fallback in _fetch_latest_release; MEGA is now the sole release source
- Removed obsolete OneDrive/fallback tests and replaced them with MEGA-unavailable/MEGA-listing-failure expectations in test/test_vkb_link_manager.py
- Updated test/test_vkb_link_manager_live.py cleanup to explicitly delete downloaded/expanded install artifacts after each run

### CHG-035 — 2026-02-19 · unreleased

**Tags:** New Feature

**Summary:** Verified run_codex_plan.py live end-to-end with VSCode-bundled codex binary

**Changes:**
- Script auto-discovered codex.exe via discover_vscode_codex() from openai.chatgpt VSCode extension
- Live run completed in ~24s with state=succeeded, return_code=0, 12 events
- Codex correctly listed load.py and PLUGIN_REGISTRY.py without modifying any files

### CHG-034 — 2026-02-19 · unreleased

**Tags:** Bug Fix, Test Update

**Summary:** Force first-run INI targeting to the downloaded executable directory before VKB-Link start

**Changes:**
- Changed _resolve_or_default_ini_path() to prioritize INI resolution near the specific executable being started and create a default <exe_dir>/VKBLink.ini path when missing
- Pre-start/pre-restart INI sync now avoids stale persisted INI paths from prior installs and always targets the active install directory
- Added test_ensure_running_download_ignores_stale_saved_ini_and_targets_exe_dir and reran targeted/full VKB manager tests

### CHG-033 — 2026-02-19 · unreleased

**Tags:** Bug Fix, Test Update

**Summary:** Write VKB-Link INI before starting process after install/download flows

**Changes:**
- Updated src/edmcruleengine/vkb_link_manager.py to resolve/write INI before process start in ensure_running and update_to_latest install paths
- Added _resolve_or_default_ini_path() to default to <exe_dir>/VKBLink.ini when no INI exists yet and persist vkb_ini_path
- Expanded test/test_vkb_link_manager.py with ordering assertions and default-INI coverage; reran deterministic and live suites

### CHG-032 — 2026-02-19 · unreleased

**Tags:** Test Update

**Summary:** Added comprehensive VKB-Link manager tests including an opt-in live production integration path

**Changes:**
- Added test/test_vkb_link_manager.py covering helper parsing, exe/INI discovery, ensure_running paths, update/stop flows, install behavior, and MEGA/fallback release handling
- Added test/test_vkb_link_manager_live.py for real production-like validation (download/start/connect/update/stop) gated behind RUN_VKB_LINK_LIVE=1
- Executed both suites; deterministic suite surfaced five behavior mismatches in current implementation while the live suite was attempted and skipped safely due an already-running VKB-Link process

### CHG-031 — 2026-02-19 · unreleased

**Tags:** Bug Fix, New Feature, Documentation Update

**Summary:** Auto-discover VS Code bundled Codex CLI when codex is missing from PATH

**Changes:**
- Updated scripts/run_codex_plan.py to resolve codex from PATH first, then fall back to .vscode/.vscode-insiders extension bundles (openai.chatgpt-*/bin/windows-x86_64/codex.exe)
- Added Git Bash/MSYS path normalization so /c/Users/... values for HOME or --codex-bin resolve to valid Windows paths
- Documented the fallback behavior in scripts/README.md for cross-agent invocation clarity

### CHG-030 — 2026-02-19 · unreleased

**Tags:** Documentation Update

**Summary:** Created test plan and dry-ran run_codex_plan.py to verify plan handoff

**Changes:**
- Wrote agent_artifacts/claude/temp/test_plan.md as a minimal Codex prompt
- Executed run_codex_plan.py --dry-run and confirmed metadata.json, status.json, command.txt, plan_input.txt are generated correctly
- Verified the codex exec command is built with correct sandbox, approval, workspace, and stdin (-) arguments

### CHG-029 — 2026-02-19 · unreleased

**Tags:** New Feature, Documentation Update

**Summary:** Added a Codex plan runner script that writes monitorable run artifacts under agent outputs

**Changes:**
- Added scripts/run_codex_plan.py to execute codex exec from a plan file and stream logs/events/status into agent_artifacts/codex/reports/plan_runs/<run_id>
- Implemented heartbeat-updated status.json plus stdout/stderr/event/final-message files for external progress monitoring
- Documented the new runner in scripts/README.md so other agents can call it consistently

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

