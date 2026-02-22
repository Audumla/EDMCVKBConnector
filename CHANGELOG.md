# Changelog

> Source of truth: `CHANGELOG.json` (unreleased) and `CHANGELOG.archive.json` (released history).

## [0.8.0](https://github.com/Audumla/EDMCVKBConnector/compare/v0.7.0...v0.8.0) (2026-02-22)


### Features

* add Windows-native PowerShell release script ([1572a09](https://github.com/Audumla/EDMCVKBConnector/commit/1572a0938299aebadd0b00fc134e23b171b9636d))


### Bug Fixes

* correct path resolution in release.ps1 ([df92cfe](https://github.com/Audumla/EDMCVKBConnector/commit/df92cfe76eb9ae7457b79d9a666601ee5da49b55))


### Documentation

* improve release notes formatting by removing meta-commentary ([3dbb20d](https://github.com/Audumla/EDMCVKBConnector/commit/3dbb20de911407254262c9eb8967874ebca14a39))
* update CHANGELOG.md with detailed per-version summaries ([55c6ba6](https://github.com/Audumla/EDMCVKBConnector/commit/55c6ba67f5e1b6cda80c435d2e931d6e9ff8f735))

## [Unreleased]

### Overview

This release introduces intelligent LLM-based changelog summarization and completes the changelog pipeline overhaul with enhanced release-note generation and VKB-Link recovery improvements.

### New Features
- **Intelligent LLM-based changelog summarization** — Created `summarize_changelog.py` with Claude/Codex backend support to generate human-readable release summaries grouped by logical categories
- **LLM release-notes mode** — Added `--summary-mode llm` to `generate_release_notes.py` for narrative-driven release notes
- **Configurable LLM backend** — Added `changelog_summarizer` config section supporting Claude API or Codex CLI

### Bug Fixes
- **VKB-Link crash recovery** — Fixed EventHandler recovery cooldown logic to bypass throttling for process-crash recovery while maintaining behavior for other recovery paths

### Build / Packaging
- **Intelligent grouped changelog workflow** — Implemented globally unique CHG IDs (branch-safe format) with `change_group` metadata for grouped release notes
- **Compact release-note generation** — Added `--max-groups-per-tag` limit (default 5) to `generate_release_notes.py` to prevent verbose output; validated on v0.5.1 reducing 85 detailed bullets to 42 compact bullets
- **Changelog summarization pipeline** — Integrated summarizer into `changelog_activity.py` pre-release workflow with `--skip-summarize` override
- **LLM-generated CHANGELOG.md** — Replaced table-based format with readable per-version narrative summaries that show Overview, Bug Fixes, New Features, Code Refactoring, Build/Packaging, and Documentation sections

### Code Refactoring
- **Intelligent release-note summaries** — Implemented topic inference using regex patterns and tag-specific summary templates so iterative updates collapse into concise, readable statements
- **Archive deduplication** — Added safe deduplication in release-note generation to prevent duplicate entries on repeated stamping
- **CHANGELOG.md simplification** — Refactored `build_changelog.py` to render aggregate workstream/release summaries instead of individual change rows, keeping detailed history in JSON source files

### Documentation Update
- **Release-process documentation** — Updated CLAUDE.md with changelog summarizer configuration and usage patterns
- **Agent instructions** — Enhanced AGENTS.md and copilot-instructions.md with new changelog workflow guidance
- **Script documentation** — Added inline docstrings and help text to new summarization scripts

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
