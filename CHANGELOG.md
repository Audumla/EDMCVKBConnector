# Changelog

## [0.7.0](https://github.com/Audumla/EDMCVKBConnector/compare/v0.6.0...v0.7.0) (2026-02-21)


### Features

* 0.3.0 release ([9f738e8](https://github.com/Audumla/EDMCVKBConnector/commit/9f738e8792dce66fd35c97c45d99b8a02ff89884))
* add log_change.py so agents run one command to record changes (CHG-007) ([142a7e2](https://github.com/Audumla/EDMCVKBConnector/commit/142a7e2a71f6fd76bf0bcfa0dc80a1b47fef5280))
* add release notes generation from CHANGELOG.json ([8af41e7](https://github.com/Audumla/EDMCVKBConnector/commit/8af41e7fb757bfc0292cd8239b500832ecb10f38))
* Repaired deployment scripts ([1e4b58f](https://github.com/Audumla/EDMCVKBConnector/commit/1e4b58fdbbfc072109f1f26e910c5607ce1ba54f))


### Bug Fixes

* Fix NameError in event_handler track_unregistered_events property ([17d3837](https://github.com/Audumla/EDMCVKBConnector/commit/17d38377de255ea006ba44e7e793087853c2f4a0))

## [0.5.1](https://github.com/Audumla/EDMCVKBConnector/compare/v0.5.0...v0.5.1) (2026-02-21)


### Bug Fixes

* Fix NameError in event_handler track_unregistered_events property ([17d3837](https://github.com/Audumla/EDMCVKBConnector/commit/17d38377de255ea006ba44e7e793087853c2f4a0))

## Release Notes - v0.5.0

_2026-02-19 - 2026-02-21_

## New Feature
- Added VKB-Link auto-management with download/update and UI controls
- Add VKB-Link startup/shutdown handling and detailed lifecycle logging
- Implement automated VKB-Link download from MEGA public folder with AES-CTR decryption
- Auto-install cryptography library silently when not present
- Added a Codex plan runner script that writes monitorable run artifacts under agent outputs
- Verified run_codex_plan.py live end-to-end with VSCode-bundled codex binary
- Added claude_run_plan.py wrapper that appends claude_report.json to Codex run directories
- Added formatted /codex-results reporting with Codex token and estimated-cost visibility
- Added configurable VKB-Link launch mode and restored legacy startup behavior by default

## Bug Fix
- Improve VKB-Link update discovery and status/error display
- Fix NameError in VKB-Link prefs and move Update button to status line
- Fix VKB-Link INI button packing when status row moved
- Remove Configure INI button and prioritize standalone INI status messages
- Delay startup connect after launching VKB-Link and show transient connection state
- Apply 5s reconnect delay after VKB-Link start/restart recovery and expand lifecycle logging
- Reduce false INI mismatch status by syncing path and normalizing host comparison
- Ensure shift/subshift state is resent on every new VKB socket connection
- Made VKB-Link startup/shutdown lifecycle status consistently visible in INFO logs
- Restart VKB-Link when host/port settings change to apply new endpoint configuration
- Add diagnostic logging and safety auto-start for VKB-Link during polling
- Fix VKB-Link restart blocking main thread and status messages never rendering
- Fix countdown logs, wrong endpoint on reconnect, and disconnected vs reconnecting status mismatch
- Auto-discover VS Code bundled Codex CLI when codex is missing from PATH
- Write VKB-Link INI before starting process after install/download flows
- Force first-run INI targeting to the downloaded executable directory before VKB-Link start
- Removed OneDrive/homepage fallback and made VKB-Link release discovery MEGA-only with explicit live-test artifact cleanup
- Bootstrap VKB-Link once after fresh install before applying managed INI settings
- Update VKB-Link INI in place without overwriting unrelated settings
- Use graceful VKB-Link shutdown with forced fallback and wait for INI creation after shutdown
- Fixed script issues: --refresh persistence and duplicate pricing table
- Start VKB-Link as a detached child process while preserving clean stop behavior
- Config helper lookups now honor config_defaults values instead of hardcoded fallback literals
- Harden VKB-Link restart shutdown timing so low operation timeout does not cause premature force-kill
- Enforced VKB-Link single-instance behavior by stopping all detected duplicates before restart/stop/update actions
- Added VKB-Link TCP listener readiness wait before reconnect attempts after start/restart
- Prevented duplicate VKB-Link launches by serializing lifecycle operations and closing safety-start race
- Fixed Windows VKB process discovery normalization to stop false duplicate-instance restarts
- Suppressed send-failed VKB recovery before first successful connection to prevent startup restart loops
- Harden VKB-Link post-start settle handling for connect and recovery flows
- Do not stop pre-existing VKB-Link processes on plugin shutdown
- Disable pre-connect listener probing by default to avoid VKB-Link UI stalls
- Send zero VKB shift state before plugin disconnect/shutdown
- Check VKB-Link process existence before any reconnection attempt
- Detect connection failures and handle INI mismatches with intelligent recovery
- Reconnect worker now follows exact same startup sequence as plugin initialization

## UI Improvement
- Align initial VKB-Link status text with simplified display
- Streamline VKB-Link preferences panel layout and auto-INI synchronization
- Separated VKB-Link status line into its own frame
- Left-align VKB-Link status text next to its label
- Match VKB-Link status label font and center the row
- Add restart-phase status and dotted INI pending indicator
- Speed up pending INI dots and alternate warning color

## Performance Improvement
- Optimized Codex delegation token estimates and event parsing

## Code Refactoring
- Centralize VKB-Link control with consistent 5s post-start delay and unified logging
- Fixed pricing and cost calculation approach: no duplication, minimal tokens
- High-level code cleanup: removed redundant imports and constants
- Switch changelog IDs from agent-based to timestamp-based format
- Implement automated timestamp-based changelog ID generation

## Configuration Cleanup
- Added project Codex config for on-request approvals and workspace writes
- Externalized VKB-Link timing defaults to config_defaults and wired runtime modules to config-driven values
- Consolidated VKB-Link and UI timer settings into a smaller shared set
- Simplified workspace VS Code Python settings to avoid duplicate system interpreter discovery

## Test Update
- Added comprehensive VKB-Link manager tests including an opt-in live production integration path
- Made VKB-Link live integration test run by default on Windows
- Live VKB-Link test now uses a repo-local runtime directory under test/
- Move INI patch assertions to pure text tests so tests do not write INI files directly
- Add thorough VKB-Link control tests for UI endpoint-change flow and live stop/start cycle
- Extend live VKB-Link test to execute real UI endpoint-change flow
- Validated Codex delegation script updates with a live test_scripts run

## Documentation Update
- Release notes now show only one-line summaries, not detail bullets
- Removed agent source names from changelog storage and rendered outputs
- Created test plan and dry-ran run_codex_plan.py to verify plan handoff
- Added /codex label convention to CLAUDE.md for delegating tasks to Codex via claude_run_plan.py
- Comprehensive code review completed identifying critical security and correctness issues
- Simplify README and add dedicated VKB-Link setup guide with managed/manual workflows

---

| ID | Date | Summary |
|----|------|---------|
| CHG-001 | 2026-02-19 | Release notes now show only one-line summaries, not detail bullets |
| CHG-002 | 2026-02-19 | Added VKB-Link auto-management with download/update and UI controls |
| CHG-003 | 2026-02-19 | Added project Codex config for on-request approvals and workspace writes |
| CHG-004 | 2026-02-19 | Add VKB-Link startup/shutdown handling and detailed lifecycle logging |
| CHG-005 | 2026-02-19 | Improve VKB-Link update discovery and status/error display |
| CHG-006 | 2026-02-19 | Align initial VKB-Link status text with simplified display |
| CHG-007 | 2026-02-19 | Implement automated VKB-Link download from MEGA public folder with AES-CTR decryption |
| CHG-008 | 2026-02-19 | Auto-install cryptography library silently when not present |
| CHG-009 | 2026-02-19 | Streamline VKB-Link preferences panel layout and auto-INI synchronization |
| CHG-010 | 2026-02-19 | Fix NameError in VKB-Link prefs and move Update button to status line |
| CHG-011 | 2026-02-19 | Separated VKB-Link status line into its own frame |
| CHG-012 | 2026-02-19 | Left-align VKB-Link status text next to its label |
| CHG-013 | 2026-02-19 | Fix VKB-Link INI button packing when status row moved |
| CHG-014 | 2026-02-19 | Match VKB-Link status label font and center the row |
| CHG-015 | 2026-02-19 | Remove Configure INI button and prioritize standalone INI status messages |
| CHG-016 | 2026-02-19 | Add restart-phase status and dotted INI pending indicator |
| CHG-017 | 2026-02-19 | Speed up pending INI dots and alternate warning color |
| CHG-018 | 2026-02-19 | Removed agent source names from changelog storage and rendered outputs |
| CHG-019 | 2026-02-19 | Delay startup connect after launching VKB-Link and show transient connection state |
| CHG-020 | 2026-02-19 | Apply 5s reconnect delay after VKB-Link start/restart recovery and expand lifecycle logging |
| CHG-021 | 2026-02-19 | Reduce false INI mismatch status by syncing path and normalizing host comparison |
| CHG-022 | 2026-02-19 | Ensure shift/subshift state is resent on every new VKB socket connection |
| CHG-023 | 2026-02-19 | Made VKB-Link startup/shutdown lifecycle status consistently visible in INFO logs |
| CHG-024 | 2026-02-19 | Centralize VKB-Link control with consistent 5s post-start delay and unified logging |
| CHG-025 | 2026-02-19 | Restart VKB-Link when host/port settings change to apply new endpoint configuration |
| CHG-026 | 2026-02-19 | Add diagnostic logging and safety auto-start for VKB-Link during polling |
| CHG-027 | 2026-02-19 | Fix VKB-Link restart blocking main thread and status messages never rendering |
| CHG-028 | 2026-02-19 | Fix countdown logs, wrong endpoint on reconnect, and disconnected vs reconnecting status mismatch |
| CHG-029 | 2026-02-19 | Added a Codex plan runner script that writes monitorable run artifacts under agent outputs |
| CHG-030 | 2026-02-19 | Created test plan and dry-ran run_codex_plan.py to verify plan handoff |
| CHG-031 | 2026-02-19 | Auto-discover VS Code bundled Codex CLI when codex is missing from PATH |
| CHG-032 | 2026-02-19 | Added comprehensive VKB-Link manager tests including an opt-in live production integration path |
| CHG-033 | 2026-02-19 | Write VKB-Link INI before starting process after install/download flows |
| CHG-034 | 2026-02-19 | Force first-run INI targeting to the downloaded executable directory before VKB-Link start |
| CHG-035 | 2026-02-19 | Verified run_codex_plan.py live end-to-end with VSCode-bundled codex binary |
| CHG-036 | 2026-02-19 | Removed OneDrive/homepage fallback and made VKB-Link release discovery MEGA-only with explicit live-test artifact cleanup |
| CHG-037 | 2026-02-19 | Added claude_run_plan.py wrapper that appends claude_report.json to Codex run directories |
| CHG-038 | 2026-02-19 | Added /codex label convention to CLAUDE.md for delegating tasks to Codex via claude_run_plan.py |
| CHG-039 | 2026-02-19 | Made VKB-Link live integration test run by default on Windows |
| CHG-040 | 2026-02-19 | Live VKB-Link test now uses a repo-local runtime directory under test/ |
| CHG-041 | 2026-02-19 | Comprehensive code review completed identifying critical security and correctness issues |
| CHG-042 | 2026-02-19 | Bootstrap VKB-Link once after fresh install before applying managed INI settings |
| CHG-043 | 2026-02-19 | Optimized Codex delegation token estimates and event parsing |
| CHG-044 | 2026-02-19 | Update VKB-Link INI in place without overwriting unrelated settings |
| CHG-045 | 2026-02-19 | Move INI patch assertions to pure text tests so tests do not write INI files directly |
| CHG-046 | 2026-02-19 | Use graceful VKB-Link shutdown with forced fallback and wait for INI creation after shutdown |
| CHG-047 | 2026-02-19 | Add thorough VKB-Link control tests for UI endpoint-change flow and live stop/start cycle |
| CHG-048 | 2026-02-19 | Added formatted /codex-results reporting with Codex token and estimated-cost visibility |
| CHG-049 | 2026-02-19 | Extend live VKB-Link test to execute real UI endpoint-change flow |
| CHG-050 | 2026-02-19 | Fixed script issues: --refresh persistence and duplicate pricing table |
| CHG-051 | 2026-02-19 | Fixed pricing and cost calculation approach: no duplication, minimal tokens |
| CHG-052 | 2026-02-19 | Externalized VKB-Link timing defaults to config_defaults and wired runtime modules to config-driven values |
| CHG-053 | 2026-02-19 | Validated Codex delegation script updates with a live test_scripts run |
| CHG-054 | 2026-02-19 | Consolidated VKB-Link and UI timer settings into a smaller shared set |
| CHG-055 | 2026-02-19 | Start VKB-Link as a detached child process while preserving clean stop behavior |
| CHG-056 | 2026-02-19 | Config helper lookups now honor config_defaults values instead of hardcoded fallback literals |
| CHG-057 | 2026-02-20 | Added configurable VKB-Link launch mode and restored legacy startup behavior by default |
| CHG-058 | 2026-02-20 | Harden VKB-Link restart shutdown timing so low operation timeout does not cause premature force-kill |
| CHG-059 | 2026-02-20 | Enforced VKB-Link single-instance behavior by stopping all detected duplicates before restart/stop/update actions |
| CHG-060 | 2026-02-20 | Added VKB-Link TCP listener readiness wait before reconnect attempts after start/restart |
| CHG-061 | 2026-02-20 | Prevented duplicate VKB-Link launches by serializing lifecycle operations and closing safety-start race |
| CHG-062 | 2026-02-20 | Fixed Windows VKB process discovery normalization to stop false duplicate-instance restarts |
| CHG-063 | 2026-02-20 | Suppressed send-failed VKB recovery before first successful connection to prevent startup restart loops |
| CHG-064 | 2026-02-20 | Harden VKB-Link post-start settle handling for connect and recovery flows |
| CHG-065 | 2026-02-20 | Do not stop pre-existing VKB-Link processes on plugin shutdown |
| CHG-066 | 2026-02-20 | Disable pre-connect listener probing by default to avoid VKB-Link UI stalls |
| CHG-067 | 2026-02-20 | Send zero VKB shift state before plugin disconnect/shutdown |
| CHG-068 | 2026-02-20 | Simplify README and add dedicated VKB-Link setup guide with managed/manual workflows |
| CHG-069 | 2026-02-20 | High-level code cleanup: removed redundant imports and constants |
| CHG-070 | 2026-02-21 | Check VKB-Link process existence before any reconnection attempt |
| CHG-071 | 2026-02-21 | Detect connection failures and handle INI mismatches with intelligent recovery |
| CHG-072 | 2026-02-21 | Simplified workspace VS Code Python settings to avoid duplicate system interpreter discovery |
| CHG-073 | 2026-02-21 | Reconnect worker now follows exact same startup sequence as plugin initialization |
| CHG-074 | 2026-02-21 | Switch changelog IDs from agent-based to timestamp-based format |
| CHG-075 | 2026-02-21 | Implement automated timestamp-based changelog ID generation |
