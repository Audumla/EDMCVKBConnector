# Changelog

> Source of truth: `CHANGELOG.json` (unreleased) and `CHANGELOG.archive.json` (released history).

## [Unreleased]

_No unreleased entries._

---

## v0.8.0 — 2026-02-21 to 2026-02-22

_Condensed 16 entries across 10 workstreams._
_Primary areas: Code Refactoring, Bug Fix, Configuration Cleanup_

---

## v0.5.1 — 2026-02-19 to 2026-02-21

### Overview

This major release adds intelligent VKB-Link auto-management, extensive UI improvements, and comprehensive test coverage. Over 44 bug fixes address stability and behavior issues.

### New Features
- **VKB-Link auto-management** — Added automatic VKB-Link download, update detection, and startup/shutdown handling with detailed lifecycle logging
- **VKB-Link UI controls** — Introduced UI panel controls for auto-management settings, status display, and error reporting
- **Codex workspace integration** — Added project Codex configuration for on-request approvals and automated workspace modifications
- **Enhanced release notes** — Improved release-note generation to show one-line summaries instead of verbose detail bullets

### Bug Fixes
- **VKB-Link status handling** — Fixed VKB-Link update discovery, status display, and error handling across multiple scenarios
- **UI stability** — Addressed UI rendering issues, panel layout problems, and font/button behavior
- **Configuration correctness** — Fixed default settings, configuration file parsing, and INI file handling
- **Process reliability** — Improved crash recovery, timeout handling, and single-instance enforcement

### UI Improvements
- **Status panels** — Enhanced status display, error messaging, and user feedback throughout the plugin UI
- **Controls and preferences** — Improved button behavior, font rendering, and preference settings layout

### Test Updates
- **Comprehensive test coverage** — Expanded pytest test suite with 26+ new test cases covering changelog operations, configuration handling, and core plugin functionality

---

## v0.5.0 — 2026-02-19

### Overview

This maintenance release fixes a critical packaging issue affecting module inclusion in plugin distributions.

### Bug Fixes
- **Package build** — Fixed missing 5 critical modules in INCLUDE list of `package_plugin.py`, ensuring complete plugin distribution

---

## v0.4.0 — 2026-02-19

### Overview

This foundational release establishes the core plugin architecture, data management, and development infrastructure.

### New Features
- **Changelog infrastructure** — Established cross-agent changelog system committed to the repository with structured entry tracking and archival
- **Data file centralization** — Moved bundled data files to `/data` subdirectory with centralized path references for easier maintenance

### Documentation Update
- **Changelog policy enforcement** — Strengthened changelog policy making entry recording mandatory after every task, not just session end
- **Development setup guides** — Created comprehensive documentation for changelog operations and project structure

### Build / Packaging
- **Initial plugin packaging** — Set up plugin build and packaging infrastructure with artifact management
