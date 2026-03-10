# Changelog

> Source of truth: `CHANGELOG.json` (unreleased) and `CHANGELOG.archive.json` (released history).

## [0.13.2](https://github.com/Audumla/EDMCVKBConnector/compare/v0.13.1...v0.13.2) (2026-03-10)


### Documentation

* backfill release summaries since v0.12 ([d772bf0](https://github.com/Audumla/EDMCVKBConnector/commit/d772bf094ed2ce0cbad3bfaa829911dfdeb48310))

## v0.13.1 — 2026-03-10

### Overview

This patch makes release-please consume the project's cached changelog summaries and backfilled release history instead of falling back to conventional-commit bullets.

### Bug Fixes
- Synced release-please changelog generation with the project summary cache so release bodies render structured release history.

### Documentation
- Backfilled missing release history since v0.12.x and documented the summary-backed release workflow.

---

## v0.13.0 — 2026-03-10

### Overview

This release completes the standalone split between the EDMC plugin and the external agent-runner workspace, restoring the plugin repository to runner-independent packaging and source ownership.

### New Features
- Separated the plugin repository from embedded agent-runner code while preserving runner enablement through external installation.

### Improvements
- Restored standalone plugin packaging, removed project-local runner assets from the tracked repository, and tightened separation validation.

### Testing
- Added suite-level VKB-Link shutdown coverage so test runs no longer leave the helper process running.

---

## v0.12.5 — 2026-02-24

### Overview

This patch separates release-please's generated changelog file from the project changelog and fixes version-file path wiring used during release updates.

### Bug Fixes
- Prevented release-please from overwriting the project's curated CHANGELOG.md during release preparation.

### Build and Packaging
- Corrected version-file path wiring so automated version bumps update the packaged plugin source correctly.

---

## v0.12.4 — 2026-02-24

### Overview

This patch prevents the automated changelog stamp step from retriggering CI and creating a release-please loop.

### Bug Fixes
- Added a safe skip-CI path for automated changelog stamp commits so the release PR does not recursively retrigger itself.

### Build and Packaging
- Stabilized the release workflow by breaking the bot-triggered commit loop in patch releases.

---

## v0.12.3 — 2026-02-24

### Overview

This patch hardens the release workflow after the earlier synchronization fixes by tightening post-merge behavior and local sync safety.

### Bug Fixes
- Hardened release synchronization around post-merge changelog handling to reduce local overwrite risk.

### Improvements
- Switched local post-release sync toward a cleaner rebase-based flow.

---

## v0.12.2 — 2026-02-24

### Overview

This release improves release-please synchronization so stamped changelog data and packaged distribution artifacts stay in step.

### Bug Fixes
- Fixed release synchronization so stamped changelog content is included in the resulting release output.

### Build and Packaging
- Included the project changelog files in packaged distribution assets for release validation and support.

---

## v0.12.1 — 2026-02-24

### Overview

This patch stabilizes the release pipeline immediately after v0.12.0 by keeping version metadata aligned across packaged artifacts and release automation.

### Bug Fixes
- Aligned manifest and packaged plugin version values so release builds report the correct version consistently.

### Improvements
- Cleaned up the patch release flow to avoid version drift in subsequent automated releases.

---

## v0.12.0 — 2026-02-24

### Overview

This release includes 41 changelog updates across 9 grouped workstreams, focused on New Feature, Bug Fix, Code Refactoring.

### New Features
- Added new capabilities for developer documentation and configuration.

### Bug Fixes
- Fixed issues in changelog tooling and vkb-link lifecycle.

### Improvements
- Refactored tests for maintainability.

### Improvements
- Cleaned up configuration for changelog tooling and tests.

---

## v0.11.0 — 2026-02-23 to 2026-02-24

### Overview

This release includes 29 changelog updates across 12 grouped workstreams, focused on Bug Fix, Code Refactoring, Configuration Cleanup.

### Bug Fixes
- Fixed issues in vkb-link lifecycle.

### Improvements
- Refactored configuration and changelog tooling for maintainability.

### Improvements
- Cleaned up configuration for changelog tooling and configuration.

### Testing
- Expanded test coverage for tests.

### Documentation
- Updated documentation for ui and preferences and tests.

---

## v0.10.2 — 2026-02-22 to 2026-02-23

### Overview

This release includes 6 changelog updates across 1 grouped workstreams, focused on Code Refactoring.

### Improvements
- Refactored multiple areas for maintainability.

---

## v0.10.1 — 2026-02-22

### Overview

This release includes 21 changelog updates across 5 grouped workstreams, focused on New Feature, Bug Fix, Code Refactoring.

### New Features
- Added new capabilities for changelog tooling.

### Bug Fixes
- Fixed issues in release process.

### Improvements
- Refactored changelog tooling and vkb-link lifecycle for maintainability.

---

## v0.9.2 — 2026-02-22

### Overview

This release includes 2 changelog updates across 2 grouped workstreams, focused on Bug Fix.

### Bug Fixes
- Fixed issues in changelog tooling and rule engine.

---

## v0.9.1 — 2026-02-22

### Overview

This release includes 17 changelog updates across 4 grouped workstreams, focused on Bug Fix.

### Bug Fixes
- Fixed issues in vkb-link lifecycle and release process.

---

## v0.9.0 — 2026-02-22

### Overview

This release includes 6 changelog updates across 3 grouped workstreams, focused on UI Improvement, Configuration Cleanup.

### UI Improvements
- Improved UI workflows for ui and preferences and rule engine.

### Improvements
- Cleaned up configuration for changelog tooling.

---

## v0.8.5 — 2026-02-22

### Overview

This release includes 2 changelog updates across 2 grouped workstreams, focused on Configuration Cleanup.

### Improvements
- Cleaned up configuration for configuration and release process.

---

## v0.8.4 — 2026-02-22

### Overview

This release includes 1 changelog updates across 1 grouped workstreams, focused on Bug Fix.

### Bug Fixes
- Fixed issues in release process and changelog tooling.

---

## v0.8.3 — 2026-02-22

### Overview

This release includes 4 changelog updates across 4 grouped workstreams, focused on Bug Fix, Build / Packaging.

### Bug Fixes
- Fixed issues in release process and changelog tooling.

### Build and Packaging
- Improved build and packaging for release process.

---

## v0.8.2 — 2026-02-22

### Overview

This release includes 1 changelog updates across 1 grouped workstreams, focused on Bug Fix.

### Bug Fixes
- Fixed issues in release process and changelog tooling.

---

## v0.8.1 — 2026-02-22

### Overview

This release includes 19 changelog updates across 19 grouped workstreams, focused on New Feature, Bug Fix, Configuration Cleanup.

### New Features
- Added new capabilities for changelog tooling and packaging.

### Bug Fixes
- Fixed issues in changelog tooling and release process.

### Improvements
- Cleaned up configuration for changelog tooling and configuration.

### Build and Packaging
- Improved build and packaging for release process and changelog tooling.

### Documentation
- Updated documentation for release-process documentation.

---

## v0.8.0 — 2026-02-21 to 2026-02-22

### Overview

This release includes 16 changelog updates across 10 grouped workstreams, focused on Bug Fix, Code Refactoring, Configuration Cleanup.

### Bug Fixes
- Fixed issues in release process.

### Improvements
- Refactored changelog tooling and vkb-link lifecycle for maintainability.

### Improvements
- Cleaned up configuration for vkb-link lifecycle and ui and preferences.

### Documentation
- Updated documentation for release-process documentation.

---

## v0.7.0 — 2026-02-21

### Overview

This release includes 1 changelog updates across 1 grouped workstreams, focused on Documentation Update.

### Documentation
- Updated documentation for release-process documentation.

---

## v0.5.1 — 2026-02-19 to 2026-02-21

### Overview

This release includes 85 changelog updates across 85 grouped workstreams, focused on New Feature, Bug Fix, UI Improvement.

### New Features
- Added new capabilities for vkb-link lifecycle and rule engine.

### Bug Fixes
- Fixed issues in vkb-link lifecycle and ui and preferences.

### UI Improvements
- Improved UI workflows for vkb-link lifecycle and ui and preferences.

### Performance Improvements
- Improved performance for multiple areas.

### Improvements
- Refactored vkb-link lifecycle and process reliability for maintainability.

### Improvements
- Cleaned up configuration for configuration and vkb-link lifecycle.

### Testing
- Expanded test coverage for vkb-link lifecycle and tests.

### Documentation
- Updated documentation for developer and release-process documentation.

---

## v0.5.0 — 2026-02-19

### Overview

This release includes 1 changelog updates across 1 grouped workstreams, focused on Bug Fix.

### Bug Fixes
- Fixed issues in packaging.

---

## v0.4.0 — 2026-02-19

### Overview

This release includes 7 changelog updates across 7 grouped workstreams, focused on Configuration Cleanup, Build / Packaging, Documentation Update.

### Improvements
- Cleaned up configuration for multiple areas.

### Build and Packaging
- Improved build and packaging for changelog tooling and release process.

### Documentation
- Updated documentation for release-process documentation.
