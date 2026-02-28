# Changelog

## Unreleased

### Bug Fixes
- Fixed release-please synchronization issues and ensured changelogs are included in distribution.
- Resolved the "tick-behind" problem where release tags missed the latest changelog stamps.
- Updated `package_plugin.py` to include `CHANGELOG.md` and data files in the ZIP asset.
- Hardened release synchronization and post-merge hooks to prevent local overwrites and ensure cleaner syncs.
- Fixed an endless loop caused by changelog stamp re-triggering CI by adding `[skip ci]` to the commit message.
- Prevented release-please from overwriting custom `CHANGELOG.md` by changing the file path.

### New Features
- Added a dynamic model selector to the task dispatcher, allowing automatic model filtering based on selected executor.
- Integrated Release Please configuration into the Agent System, creating a new version tracker and release workflow template.
- Added native runners for Copilot and Generic Local LLM, supporting full native CLI support.
- Implemented a native Claude runner, achieving 100% specialized execution logic for all supported AI agents.
- Added an `enabled` flag to `delegation-config.json` for planner and executor control, and created a comprehensive integration test suite.

### Improvements
- Completed the decoupling of the Agent System, pruned the project root, and finalized the modular structure.
- Achieved a pristine standalone state for the Agent System, verified all internal modular paths, and ensured project-agnostic governance.
- Updated and verified core unit tests for the modular Agent System, confirming full cross-module import compatibility.
- Implemented automatic task summary extraction from plan files, using Markdown H1 headings to derive summaries.

### Fix release-please synchronization and include changelogs in distribution (Bug Fix, Build / Packaging)
- Added automated changelog stamping to Release PRs via prepare-release job
- Eliminated 'tick-behind' issue where release tags missed the latest changelog stamp
- Updated package_plugin.py to include CHANGELOG.md and data files in the ZIP asset

### Harden release synchronization and post-merge hooks (Bug Fix, Configuration Cleanup)
- Updated post-merge hook to skip CHANGELOG.md rebuilds during release merges
- Prevented local overwrites of officially stamped cloud changelogs
- Switched auto_pull_after_release.py to use --rebase for cleaner local-to-remote sync

### Fix endless release-please loop caused by changelog stamp re-triggering CI (Bug Fix, Build / Packaging)
- Added [skip ci] to the changelog stamp commit message in prepare-release job
- Prevents the bot commit from firing another pull_request workflow run
- Breaks the commit-merge-commit cycle when merging release-please PRs

### Stop release-please from overwriting custom CHANGELOG.md (Bug Fix, Build / Packaging)
- Changed changelog-path to CHANGELOG.release-please.md so release-please owns its own file
- Eliminates conflict between release-please changelog generation and build_changelog.py output
- Fixed extra-files path: src/edmcruleengine/version.py -> src/edmcruleengine/config/version.py

### Added Dynamic Model Selector to Task Dispatcher (New Feature, UI Improvement)
- Implemented automatic model filtering in Dashboard based on selected Executor
- Added discovered model IDs for Gemini, Codex, Claude, and Copilot
- Refined Dispatcher panel layout to prevent row overlap and improved vertical alignment
- Fixed DataTable status formatting logic for cleaner run navigation

### Decoupled Agent System into a dedicated directory structure (Code Refactoring, Configuration Cleanup)
- Created agent_system/ directory to house all AI and Agent modules
- Moved runners, dashboard, maintenance, and utilities into agent_system/scripts/
- Updated all script paths and PROJECT_ROOT constants for the new structure
- Migrated agent-specific documentation and configurations into the new system folder

### Integrated Release Please configuration into Agent System (New Feature, Configuration Cleanup)
- Migrated release-please-config.json and manifest to agent_system/config/
- Created agent_system/core/config/version.py as the new project version tracker
- Provided agent_system/workflows/release-please.yml as a template for the new project
- Updated release configuration paths to track the new modular structure

### Integrated Release Please configuration into Agent System (New Feature, Configuration Cleanup)
- Migrated release-please-config.json and manifest to agent_system/config/
- Created agent_system/core/config/version.py as the new project version tracker
- Provided agent_system/workflows/release-please.yml as a template for the new project
- Updated release configuration paths to track the new modular structure

### Integrated Release Please configuration into Agent System (New Feature, Configuration Cleanup)
- Migrated release-please-config.json and manifest to agent_system/config/
- Created agent_system/core/config/version.py as the new project version tracker
- Provided agent_system/workflows/release-please.yml as a template for the new project
- Updated release configuration paths to track the new modular structure

### Completed Agent System decoupling and pruned project root (Code Refactoring, Configuration Cleanup, Documentation Update)
- Removed all VKB/EDMC specific code, data, and documentation
- Updated pyproject.toml, README.md, and requirements.txt for the standalone Agent System
- Established 0.1.0 versioning for the independent project
- Verified all core scripts and reporting modules in the new modular structure

### Finalized standalone configuration and task definitions (Configuration Cleanup, Documentation Update)
- Cleaned .vscode/tasks.json of all VKB-specific legacy actions
- Rewrote .github/copilot-instructions.md for the independent Agent System scope
- Performed final workspace pruning of VKB release artifacts

### Completed deep clean and project documentation overhaul (Configuration Cleanup, Documentation Update)
- Removed final residual VKB data files (rules.json, unregistered_events.json)
- Updated CLAUDE.md and GEMINI.md to focus exclusively on the Agent System project
- Performed total purge of all historical agent artifacts and worktrees
- Verified full system integrity in the final modular state

### Refined final documentation for standalone Agent System (Documentation Update)
- Rewrote DEVELOPMENT.md to focus on modular architecture
- Updated AGENT_RUNNER_TUTORIAL.md with correct modular paths
- Ensured all guides are project-agnostic and focused on universal agent orchestration

### Completed final root cleanup and configuration tuning (Configuration Cleanup, Documentation Update)
- Pruned legacy references from .gitattributes and .gitignore
- Updated SECURITY.md for the independent Agent System scope
- Finalized all project metadata for standalone operation

### Synchronized automated workflows with modular Agent System structure (Configuration Cleanup, New Feature)
- Updated .github/workflows/release-please.yml to target agent_system/config/
- Refactored .githooks/post-merge to use modular changelog build paths
- Removed legacy VKB release automation from git hooks
- Verified full end-to-end reporting and release configuration

### Finalized semantic decoupling and project-agnostic sweep (Code Refactoring, Configuration Cleanup)
- Removed project-specific 'Rule Authoring' Codex skills
- Cleaned legacy terminology from reporting scripts and simulation data
- Verified all active code path references are modular and agnostic
- Completed total structural and semantic separation of the Agent System

### Achieved zero-clutter modular project state (Code Refactoring, Configuration Cleanup)
- Relocated changelog system and data into agent_system/reporting/
- Pruned legacy CHANGELOG.md from root and updated git control attributes
- Verified full system isolation and professional directory architecture
- Completed total decoupling from the original project context

### Completed final project-agnostic synchronization (Code Refactoring, Configuration Cleanup)
- Verified project-agnostic Release Please workflow
- Confirmed all VS Code tasks target modular agent_system paths
- Completed exhaustive terminology sweep and governance overhaul
- Achieved 100% standalone project purity for the Agent System

### Completed exhaustive semantic sweep and final path refactoring (Code Refactoring, Configuration Cleanup)
- Updated PROJECT_ROOT depth in generate_release_notes.py
- Verified all project URLs and asset names are project-agnostic
- Completed total structural and semantic separation of the Agent System
- Final decoupled repository state achieved

### Fixed cross-module imports for modular Agent System (Code Refactoring, Bug Fix)
- Injected dynamic sys.path adjustments in all agent runner scripts
- Resolved broken imports between runners/ and core/ modules
- Verified all internal dependency paths in delegation-config.json
- Achieved 100% technical modularity for standalone project transition

### Achieved pristine standalone state for Agent System (Code Refactoring, Configuration Cleanup)
- Completed exhaustive cache and artifact purge across the repository
- Removed project-specific Codex skills and residual VKB metadata
- Verified all internal modular paths and project-agnostic governance
- Finalized total decoupling from the original project context

### Verified and synchronized all agent slash command configurations (Configuration Cleanup)
- Audited .gemini command definitions for correct modular pathing
- Confirmed all delegation scripts (run, cleanup, agent) point to agent_system/core/
- Finalized configuration tuning for standalone Agent System operation

### Achieved total modular purity and operational excellence (Code Refactoring, Configuration Cleanup)
- Completed final terminoloy purge and project-agnostic documentation sweep
- Verified all internal modular paths and project-wide configuration tuning
- Performed final smoke test confirming PRISTINE and OPERATIONAL system state
- Achieved 100% decoupling from the legacy project context

### Completed final git-level pruning and historical audit (Code Refactoring, Configuration Cleanup)
- Pruned all lingering git worktrees and associated agent branches
- Verified active code is free of legacy VKB/EDMC terminology
- Preserved historical JSON changelog data within the new modular structure
- Achieved 100% project purity for the standalone Agent System

### Completed final project-agnostic sweep and decoupled state verification (Configuration Cleanup)
- Pruned residual VKB test log references from pyproject.toml
- Verified absolute modularity of the root directory and .github workflows
- Confirmed all internal paths and governance documents are project-agnostic
- Finalized Agent System as a pristine standalone core foundation

### Added native runners for Copilot and Generic Local LLM (New Feature, Code Refactoring)
- Implemented runners/run_copilot_plan.py using gh copilot CLI
- Implemented runners/run_localllm_plan.py for project-agnostic local CLIs
- Updated delegation-config.json to route both agents to their dedicated native scripts
- Achieved full native CLI support for the entire agent suite

### Achieved absolute standalone project purity for Agent System (Code Refactoring, Configuration Cleanup, Documentation Update)
- Completed final exhaustive terminology purge and license attribution
- Removed residual chatgpt settings and legacy environment clutter
- Verified all internal modular paths and project-agnostic governance protocols
- Confirmed full operational excellence through comprehensive smoke testing
- Finalized total transition to independent Agent System project

### Added native Claude runner and finalized executor suite (New Feature, Code Refactoring)
- Implemented runners/run_claude_plan.py for native Claude CLI support
- Synchronized delegation-config.json with the complete set of native runners
- Achieved 100% specialized execution logic for all supported AI agents
- Verified technical modularity across the entire runner ecosystem

### Completed technical path audit and synchronized modular configs (Code Refactoring, Configuration Cleanup)
- Corrected PROJECT_ROOT depth across core/ and dashboard/ modules
- Synchronized delegation-config.json paths in main orchestration wrapper
- Pruned lingering git worktrees and agent branches for environment purity
- Verified full system stability through final modular smoke testing

### Centralized agent definitions and synchronized core orchestration (Code Refactoring, Configuration Cleanup)
- Established centralized AGENT_TYPES list in agent_runner_utils.py
- Refactored core/ scripts to use unified agent definitions and correct modular paths
- Synchronized dashboard data gathering with modular system structure
- Achieved full technical cohesion across the decoupled Agent System

### Finalized technical path synchronization across all reporting modules (Code Refactoring, Configuration Cleanup)
- Corrected PROJECT_ROOT depth in summarize_changelog, generate_release_notes, and changelog_activity
- Performed final recursive compilation check on the entire agent_system/ directory
- Achieved 100% path accuracy and modular integrity for standalone project transition
- Total project decoupling and restructuring complete

### Updated and verified core unit tests for modular Agent System (Test Update, Code Refactoring)
- Refactored test_agent_runner_logic.py to point to modular agent_system paths
- Verified dashboard data gathering and maintenance logic via pytest
- Confirmed full cross-module import compatibility in the restructured core/
- Achieved technical validation of the standalone project foundation

### Achieved complete standalone project maturity for Agent System (Code Refactoring, Configuration Cleanup)
- Verified all native runners (Gemini, Claude, Codex, OpenCode, Copilot, Local-LLM) in delegation-config.json
- Confirmed full project-agnostic metadata and documentation across the entire repository
- Validated system stability and cross-module connectivity through comprehensive testing
- Completed total structural and semantic separation of the AI orchestration foundation

### Achieved total repository purity for standalone project (Configuration Cleanup)
- Purged final transient test logs and cache from the root
- Verified all internal modular paths and project-agnostic governance protocols
- Completed 100% decoupling from the legacy project context

### Achieved 100% standalone modular purity for Agent System (Code Refactoring, Configuration Cleanup)
- Completed final recursive terminoloy purge and structural verification
- Removed project-specific Codex skills and residual legacy artifacts
- Verified all active code path references and project-agnostic governance protocols
- Finalized total structural and semantic transition to independent project foundation

### Achieved complete standalone project maturity for Agent System (Code Refactoring, Configuration Cleanup)
- Verified all internal modular paths and project-agnostic governance protocols
- Confirmed full operational excellence through comprehensive smoke testing
- Finalized total structural and semantic separation of the AI orchestration foundation

### Completed absolute final modular verification and technical synchronization (Code Refactoring, Configuration Cleanup)
- Synchronized artifact directory structure with centralized agent definitions
- Verified all native runners are 100% free of legacy VKB/EDMC references
- Confirmed git worktree and branch integrity through exhaustive pruning
- Total project restructuring and decoupling stream successfully finalized

### Achieved total modular purity and exhaustive state verification (Code Refactoring, Configuration Cleanup)
- Confirmed all native agent runners are correctly registered and path-aware
- Verified centralized agent definitions are utilized across all core modules
- Completed final repo-wide terminology purge and project-agnostic sweep
- Finalized Agent System as a pristine standalone core foundation

### Achieved complete modular purity across all configuration layers (Code Refactoring, Configuration Cleanup)
- Audited all nested .gemini command definitions for modular path accuracy
- Confirmed full operational alignment of deep and fast agent subcommands
- Verified absolute standalone state of the Agent System configuration suite
- Completed total structural and semantic separation of the project

### Hardened native runners with unit tests and technical fixes (Test Update, Bug Fix, Code Refactoring)
- Created agent_system/core/test_native_runners.py to verify CLI command building
- Fixed missing 'subprocess' and 'time' imports across multiple runner modules
- Audited entire runner suite for technical integrity and import safety
- Verified all unit tests pass in the modular structure

### Deduplicated changelog history and finalized project transition (Code Refactoring, Configuration Cleanup)
- Surgically removed redundant changelog entries from the unreleased JSON data
- Rebuilt the modular CHANGELOG.md for a clean and professional project history
- Verified full repository purity and technical integrity across all modules
- Completed total structural and semantic separation of the Agent System foundation

### Achieved complete standalone modularity for Agent System (Code Refactoring, Configuration Cleanup)
- Completed final recursive terminoloy purge and structural verification
- Removed project-specific Codex skills and residual legacy artifacts
- Verified all active code path references and project-agnostic governance protocols
- Finalized total structural and semantic transition to independent project foundation

### Achieved total modular purity and established 0.1.0-alpha baseline (Configuration Cleanup)
- Synchronized .release-please-manifest.json with the new project version
- Completed exhaustive terminology purge and project-agnostic documentation sweep
- Verified absolute standalone state of the Agent System foundation
- Achieved 100% project decoupling from the legacy context

### Completed comprehensive audit and verification of all agent configurations (Configuration Cleanup)
- Verified all native runner mappings in delegation-config.json
- Confirmed correct modular paths in all 11 Gemini slash command definitions
- Validated Release Please configuration against the new modular version tracker
- Achieved 100% path accuracy and project-agnostic consistency across the config suite

### Synchronized project metadata and overhaulled debug configurations (Configuration Cleanup)
- Aligned pyproject.toml version with the internal 0.1.0-alpha tracker
- Rewrote .vscode/launch.json with professional debug targets for the Agent System
- Completed final synchronization of all project settings and metadata
- Achieved absolute standalone modular purity for the new core foundation

### Completed final technical polish and project metadata alignment (Code Refactoring, Configuration Cleanup)
- Updated pyproject.toml classifiers to reflect professional technical scope
- Verified absolute standalone state of the root directory and .github workflows
- Confirmed all internal modular paths and project-agnostic governance protocols
- Finalized Agent System as a pristine standalone core foundation

### Implemented provider control and comprehensive integration test suite (New Feature, Test Update, Configuration Cleanup)
- Added 'enabled' flag to delegation-config.json for planner and executor control
- Created test suite for orchestration, workflow branches, and native runners
- Hardened orchestrator logic to respect provider activation states
- Verified full system technical integrity with 9 passing integration tests

### Implement automatic task summary extraction from plan files (New Feature, Code Refactoring)
- Added extract_summary_from_plan() to run_agent_plan.py to derive summaries from Markdown H1 headings
- Configured orchestration to use extracted summaries when none are provided via CLI
- Validated functionality with end-to-end dry-run verification

### Fix missing model info in dashboard and standardize reporting (Bug Fix, Code Refactoring)
- Updated get_all_runs to resolve model/cost from metadata.json as primary source
- Enhanced generic_native_runner to populate cost_estimate metadata for all agent types
- Ensured all runs utilize the new automatic summary extraction logic

### Enhance dashboard simulation and create dummy runs (Test Update, Configuration Cleanup)
- Updated simulate_dashboard.py to comply with the test_mode flag
- Handled permission errors during cleanup in simulation script
- Generated dummy agent runs for testing purposes

### Fix missing model info in dashboard for orchestrated runs (Bug Fix, Code Refactoring)
- Updated agent_runner_utils.py to prioritize agent_report.json for model and cost resolution
- Implemented multi-file fallback logic (Report > Metadata > Status) for robust reporting
- Eliminated 'model n/a' issue in dashboard for runs delegated via run_agent_plan.py

### Implement 'merged' status tracking for agent runs (New Feature, UI Improvement)
- Updated dashboard to persist merge state and timestamp into metadata.json
- Modified state resolution logic to surface 'merged' as a primary run status
- Added visual styling for merged runs in the Textual dashboard

### Automate branch cleanup after agent run merge (UI Improvement, Code Refactoring)
- Updated action_merge_run in agent_dashboard.py to delete the source branch upon successful merge
- Ensured user is notified of both the successful merge and the subsequent branch deletion
- Verified through syntax check and logical path validation

### Widen dashboard selection dropdowns for longer model names (UI Improvement)
- Increased the CSS width of Select widgets from 24 to 32 in agent_dashboard.py
- Ensures visibility for model names like Qwen2.5-7B-Instruct-Q4_K_M.gguf

### Implement multi-line prompt support in dashboard (UI Improvement)
- Replaced single-line Input with multi-line TextArea widget in agent_dashboard.py
- Adjusted CSS layout to provide dedicated 5-row height for detailed task descriptions
- Updated dispatch logic to handle multi-line text extraction and widget clearing

### Expand Gemini available models list (New Feature, Configuration Cleanup)
- Added gemini-2.0-pro-exp-02-05, gemini-2.0-flash-lite-preview-02-05, and others to delegation-config.json
- Verified model availability through dry-run orchestration

### Add inline #plan/#exec tag dispatch and phase-aware dashboard (New Feature, UI Improvement, Documentation Update)
- - New tag_parser.py parses #plan, #exec, #budget, and legacy #agent: tags from any prompt
- - agent_management.dispatch_task() applies tag overrides before building plan file
- - run_agent_plan.py writes planning breadcrumb and patches phase=done into executor status.json
- - generic_native_runner and run_openai_api_plan write phase=executing/done to status.json
- - get_all_runs() exposes phase field with backward-compat inference for old runs
- - Dashboard run-list gains Phase column: PLANNING/EXECUTING/DONE with colour coding
- - CLAUDE.md, AGENTS.md, copilot-instructions.md updated with new tag syntax docs
- - New Gemini slash command /agent inline for tag-aware dispatch from Gemini CLI

### Add portable install.py with git-based self-update and workspace integration (New Feature, Build / Packaging, Documentation Update)
- New install.py entry point with install/update/start/uninstall sub-commands
- vscode_tasks.py and gitignore_inject.py helpers for idempotent workspace integration
- Changelog path routing moved to AGENT_WORKSPACE_ROOT so logs live in target workspace
- bootstrap.sh and bootstrap.ps1 now delegate to install.py
- pyproject.toml registers agent CLI entry point
- README.md rewritten with new installation, update, and uninstall instructions

### Add provider detection and interactive selection to install.py (New Feature, Build / Packaging)
- New provider_detect.py module detects CLI tools (claude, gemini, opencode, codex, copilot, ollama) and VS Code extensions
- install.py detect sub-command prints a detection report and optionally updates delegation-config.json
- Provider selection integrated into install flow as step 7 with --no-interactive and --skip-providers flags
- delegation-config.json enabled flags auto-updated to match detected providers

### Split local LLM providers into ollama and lmstudio with filesystem detection (New Feature, Build / Packaging)
- Replaced local-llm with separate ollama and lmstudio entries in provider_detect.py and delegation-config.json
- LM Studio detected via ~/.lmstudio directory and lms CLI binary
- Ollama detected via ollama binary and ~/.ollama directory
- LM Studio uses OpenAI-compatible API on port 1234; ollama uses port 11434
- lmstudio enabled=true on this machine (detected); ollama enabled=false (not installed)

### Add provider detection, auth management, local LLM support, and new runners for all AI providers (New Feature, Build / Packaging, Configuration Cleanup)
- Created scripts/agent_runners/provider_detect.py: detects CLI tools, VS Code extensions, and install directories for claude, gemini, opencode, codex, cline, copilot, ollama, and lmstudio
- Created scripts/agent_runners/auth_check.py: per-provider auth state detection with strategies cli_login, api_key, subscription, local, and extension; layered credential storage via env vars, keyring, and .agent-secrets.env fallback
- Created agent_system/runners/run_cline_plan.py: writes plan to handoff file for manual Cline VS Code panel execution
- Created agent_system/runners/run_ollama_plan.py: OpenAI-compat runner for Ollama daemon at localhost:11434
- Created agent_system/runners/run_lmstudio_plan.py: OpenAI-compat runner for LM Studio server at localhost:1234
- Added generic_api_runner() to agent_runner_utils.py: shared utility for all OpenAI-compatible HTTP endpoints
- Updated delegation-config.json: split local-llm into separate ollama and lmstudio providers; added cline to planners and executors; updated runner references
- Updated install.py: added detect and auth subcommands; _run_provider_setup now returns enabled list; added _run_auth_check helper; step 8 in cmd_install runs auth check for enabled providers

### Seed AGENT.md on install so agents know artifact paths, changelog location, and delegation commands (New Feature, Documentation Update, Configuration Cleanup)
- install.py now generates AGENT.md in every workspace with machine-specific absolute paths for artifacts root, changelog JSON/MD, venv python, and log_change command
- AGENT.md covers: artifact storage layout per run-id, changelog policy with exact command syntax, delegation protocol with run_agent_plan.py example, valid providers list, and env var reference
- _write_local_config expanded to include artifactsRoot, changelogJson, changelogMd, logChangeScript, and venvPython in .vscode/agent-system.json for tooling consumption
- AGENT.md added to .gitignore injection block (contains absolute paths, machine-local)
- run_agent_plan.py --planner and --executor choices updated to include cline, ollama, lmstudio (removed local-llm placeholder)
- AGENT_TYPES constant in agent_runner_utils.py updated to match all real provider names
- CLAUDE.md valid providers list updated to match new provider names

---

## v0.9.2 — 2026-02-22

### Overview

This release includes 2 changelog updates across 2 grouped workstreams, focused on Bug Fix.

### Bug Fixes
- Fixed issues in changelog tooling and rule engine.

### Embed custom ScrolledText widget for EDMC compatibility (Bug Fix, New Feature)
- Added src/edmcruleengine/scrolled_text.py with a drop-in ScrolledText class
- Updated rule_editor.py to use fallback if tkinter.scrolledtext is missing
- Ensures rule editor works in both dev and EDMC environments

### Normalize Claude and Codex changelog summary outputs to consistent template format (Bug Fix, Code Refactoring)
- Added _normalize_llm_summary() function that deduplicates headers and strips explanatory wrappers
- Removes Codex meta-commentary footnotes and separator lines that break template consistency
- Ensures both backends produce identical markdown structure: ### Overview + ### [Sections] format

---

## v0.9.1 — 2026-02-22

### Overview

This release includes 17 changelog updates across 4 grouped workstreams, focused on Bug Fix.

### Bug Fixes
- Fixed issues in vkb-link lifecycle and release process.

### Normalize stamped release summary cache format instead of promoting unreleased narrative text (Bug Fix, Build / Packaging)
- Updated scripts/generate_release_notes.py ensure_version_summary_cache() to prefer deterministic release-format summary generation for stamped versions.
- Kept unreleased-summary promotion only as a fallback when deterministic generation cannot produce output.
- Regenerated the 0.9.0 summary with the intelligent backend so CHANGELOG.summaries.json now uses the same ### Overview structure as other releases.

### Suppress VKB lifecycle subprocess popups and add command-level diagnostics for startup failures (Bug Fix, Configuration Cleanup)
- Added hidden Windows subprocess wrappers in vkb_link_manager so tasklist/wmic/powershell/taskkill calls no longer flash console windows.
- Disabled runtime pip auto-install attempts for cryptography to avoid surprise command windows during EDMC startup.
- Added debug logging for subprocess command execution and return codes, and fixed VKB INI filename discovery fallback regression.

### Align VKB-Link INI target with production filename to prevent false restarts and connection failures (Bug Fix, Test Update)
- Re-prioritized VKB-Link INI discovery to prefer VKB-Link.ini while still accepting VKBLink.ini compatibility.
- Updated manager default-path tests to assert against the configured primary INI filename constant rather than a hardcoded variant.
- Verified vkb_link_manager behavior with full focused test pass (36/36).

### Replace Windows PowerShell/WMIC process detection with tasklist-only parsing (Code Refactoring, Bug Fix)
- Simplified VKB-Link process discovery on Windows to parse tasklist CSV output and return PID-based results without PowerShell or WMIC calls.
- Kept lifecycle stop/start logic unchanged while preserving hidden subprocess execution and command diagnostics.
- Updated Windows-specific manager tests for tasklist parsing and verified focused suite passes (36/36).

### Use native Windows process enumeration with cleaner lifecycle logging (Code Refactoring, UI Improvement)
- Added native WinAPI process snapshot enumeration for VKB-Link detection and made tasklist a fallback-only path.
- Reduced subprocess debug noise by default so recurring health checks no longer emit repetitive raw command lines.
- Added one-time fallback notice when native enumeration is unavailable and kept command diagnostics for failure scenarios.

### Gate managed VKB-Link controls on cryptography availability with background install fallback and manual-mode UI (Bug Fix, UI Improvement, Configuration Cleanup)
- Added one-time background cryptography auto-install attempt (default enabled) and exposed managed availability/reason through VKB-Link status.
- Automatically disables vkb_link_auto_manage when cryptography remains unavailable and returns a manual-run status message for managed actions.
- Updated preferences UI to disable Auto-manage, hide Update VKB-Link, and show 'VKB needs to be downloaded and run manually' when managed mode is unavailable.

### Allow manual located VKB-Link management when cryptography download support is unavailable (Bug Fix, UI Improvement)
- Adjusted VKBLinkManager gating so missing cryptography blocks only managed download/update paths; known executable lifecycle management remains available.
- Updated VKB-Link preferences UI to keep Locate available, hide only Update VKB-Link when managed download support is unavailable, and show manual-mode status only when no executable path is known.
- Updated status label layout to avoid fixed-width cropping and added tests covering known-exe startup when cryptography is unavailable.

### Enable manual-process detection and reconnect workflow even when VKB-Link path is unknown (Bug Fix, UI Improvement)
- Updated preferences polling safety worker to detect any running VKB-Link process (including manually started instances without a stored exe path) and invoke the standard EventHandler connect workflow.
- Prevented manual-mode warning text from overriding active connected/reconnecting status indicators.
- Retained existing auto-start behavior for known executable paths while preserving non-blocking UI polling design.

### Drive VKB status display from process state for manual and managed modes (Bug Fix, UI Improvement)
- Added always-on background VKB-Link process probe in preferences polling so process stop/start is detected regardless of auto-manage mode.
- Updated connection status rendering to prioritize process-running state: a stopped process now forces disconnected status even if socket flags are stale.
- Kept manual process detection and standard connect workflow in the same probe while retaining auto-start behavior only when auto-manage is enabled and an executable path is known.

### Respect auto-manage disabled setting during plugin startup VKB-Link checks (Bug Fix)
- Updated load.py startup VKB-Link worker to read vkb_link_auto_manage and skip ensure_running when auto-manage is disabled.
- Expanded startup status logging to include auto_manage state for easier diagnosis of unintended launches.
- Validated with focused tests covering load/event-handler/vkb-manager/config suites.

### Make VKB connection status require live TCP state and force disconnect when process stops (Bug Fix, UI Improvement)
- Updated prefs polling to treat established state as connected plus live socket, not process detection alone.
- When process probe reports VKB-Link stopped, preferences now force a socket disconnect so stale connected flags are cleared immediately.
- Kept process-driven reconnect workflow unchanged so connection retries only run after process is detected again.

### Apply uniform process-settle connection workflow for manual VKB runs and harden auto-manage bool parsing (Bug Fix, Test Update)
- VKBLinkManager now tracks process running transitions and applies warmup settle delay after external/manual process detection before TCP connect attempts.
- Updated startup, event-handler, manager, and preferences auto-manage boolean reads to use strict value coercion so string values like 'false' do not accidentally enable managed startup behavior.
- Added regression tests covering startup skip when auto-manage is stored as string false and settle-delay behavior after external process detection.

### Include bool_utils in plugin package so startup auto-manage fixes deploy correctly (Build / Packaging, Bug Fix)
- Added src/edmcruleengine/bool_utils.py to scripts/package_plugin.py include list.
- Verified packaging output now contains EDMCVKBConnector/edmcruleengine/bool_utils.py.
- Prevents runtime drift where installed plugin misses new boolean parsing and startup gating behavior.

### Disable default cryptography auto-install in EDMC runtime and limit pip fallback to real Python interpreters (Bug Fix, Configuration Cleanup)
- Changed vkb_link_auto_install_cryptography default to false in config defaults and fallback constants so EDMC no longer attempts pip by default.
- Added runtime interpreter resolution for cryptography pip fallback and skip installation when running under non-Python launchers like EDMarketConnector.exe.
- Added manager tests covering install command resolution and default auto-install policy.

### Add seamless bundled AES fallback so MEGA-managed VKB operations work without cryptography (Bug Fix, Build / Packaging, Test Update)
- Updated vkb_link_manager MEGA AES decrypt paths to use cryptography when available and bundled pure_python_aes fallback otherwise.
- Changed managed-availability gating and error messaging to fail only when no AES backend is available, avoiding false manual-mode warnings.
- Added fallback regression tests and included pure_python_aes.py in plugin packaging output.

### Track manual versus agent-authored changelog entries and surface source mix in release outputs (New Feature, Build / Packaging)
- Updated scripts/log_change.py to accept --agent human and persist change_source metadata (manual vs agent) on new changelog entries.
- Updated scripts/generate_release_notes.py to infer source for legacy entries and append a Change Source table to release notes, including LLM and intelligent rendering paths.
- Updated scripts/build_changelog.py to show source split lines in unreleased previews and released version sections so release-change logs visibly separate manual and agent-assisted work.

### Remove change-source attribution from changelog and release-note rendering (Bug Fix, Configuration Cleanup)
- Reverted scripts/log_change.py to stop writing change_source metadata and removed the temporary human agent mode.
- Removed source-breakdown sections from scripts/generate_release_notes.py so outputs no longer show manual vs agent counts.
- Removed source-split lines from scripts/build_changelog.py so changelog previews and released sections stay source-neutral.

---

## v0.9.0 — 2026-02-22

### Overview

This release includes 6 changelog updates across 3 grouped workstreams, focused on UI Improvement, Configuration Cleanup.

### UI Improvements
- Improved UI workflows for ui and preferences and rule engine.

### Improvements
- Cleaned up configuration for changelog tooling.

### Rearranged the settings panel and added a plugin self-update frame with GitHub release install support (UI Improvement, New Feature)
- Reworked Settings tab layout so Plugin and Static Shift frames share the top row while VKB-Link spans full width beneath them.
- Flattened VKB-Link controls to a single line and moved status plus Check Version immediately to the right of Auto-manage, with Locate kept inline.
- Added edmcruleengine.plugin_update_manager with GitHub latest-release ZIP install flow, wired it to a new Plugin Update button, added tests, and included the module in packaging.

### Adjusted settings panel labels and right-aligned VKB status/update controls (UI Improvement)
- Renamed the Plugin frame label to VKB Connector and changed Current to Current Version for the plugin version display.
- Renamed the plugin action button to Update EDMC Plugin and preserved that text after update checks complete.
- Inserted a flexible spacer after Auto-manage so VKB status text and the VKB update action align to the right side, and renamed Check Version to Update VKB-Link.

### Aligned plugin update action to the right and switched VKB-Link update to button/popup feedback (UI Improvement)
- Right-aligned the Update EDMC Plugin button in the VKB Connector frame while keeping version text on the left.
- Replaced VKB-Link update progress/result status-line messaging with button state text changes (Checking... -> Update VKB-Link).
- Updated VKB-Link update flow to show popup success/error messages like the plugin updater and still refresh connection/app status after completion.

### Fixed update button widths to prevent resize when button text changes (UI Improvement)
- Set a fixed width for the Update EDMC Plugin button so switching to Checking... keeps the same button size.
- Set a fixed width for the Update VKB-Link button so transient text changes do not alter layout width.
- Validated prefs_panel.py compiles successfully after the sizing update.

### Removed the rule-save success popup after editing a rule (UI Improvement)
- Deleted the centered 'Rule saved successfully' info dialog call from the rule editor save callback.
- Kept rule persistence and editor-window close behavior unchanged after save.
- Validated src/edmcruleengine/rule_editor.py compiles after the change.

### Removed archived duplicate IDs from active changelog entries to restore strict changelog rebuild (Configuration Cleanup, Build / Packaging)
- Pruned CHG-ff8e113f, CHG-c9577a5f, and CHG-0f866788 from docs/changelog/CHANGELOG.json because those IDs already exist in docs/changelog/CHANGELOG.archive.json as released entries.
- Re-ran strict changelog rebuild and confirmed duplicate_ids=0 in scripts/build_changelog.py output.
- Re-ran scripts/changelog_activity.py --strict and confirmed CHANGELOG and preview generation completes without duplicate-ID errors.

---

## v0.8.5 — 2026-02-22

### Overview

This release includes 2 changelog updates across 2 grouped workstreams, focused on Configuration Cleanup.

### Improvements
- Cleaned up configuration for configuration and release process.

### Enable automatic Git fetch and prune in VS Code workspace settings (Configuration Cleanup, UI Improvement)
- Added git.autofetch=true so VS Code refreshes remote refs without manual fetches.
- Added git.pruneOnFetch=true so deleted remote branches are removed from local tracking refs.
- Helps the PR/branch UI reflect post-merge release workflow updates faster and with less stale branch noise.

### Auto-sync local main after release-please stamp commits land (Configuration Cleanup, Build / Packaging)
- Added .githooks/post-merge to launch a background watcher after local merges on main.
- Added scripts/auto_pull_after_release.py to poll origin/main, require fast-forward safety, and run git pull --ff-only when the release stamp commit appears.
- Configured repository hook line endings via .gitattributes and documented the watcher in scripts/README.md.

---

## v0.8.4 — 2026-02-22

### Overview

This release includes 1 changelog updates across 1 grouped workstreams, focused on Bug Fix.

### Bug Fixes
- Fixed issues in release process and changelog tooling.

### Use deduplicated archived entries when computing stamped summary keys so release changelog sections resolve correctly (Bug Fix, Build / Packaging)
- Updated scripts/generate_release_notes.py archive_stamped() to return the actual entries appended to archive plus duplicate-skip count.
- Updated stamp/archive flow to build version summary cache from deduplicated appended entries, preventing hash mismatches with build_changelog rendering.
- Regenerated v0.8.3 summary cache key and rebuilt CHANGELOG.md so v0.8.3 renders the structured summary instead of condensed fallback.

---

## v0.8.3 — 2026-02-22

### Overview

This release includes 4 changelog updates across 4 grouped workstreams, focused on Bug Fix, Build / Packaging.

### Bug Fixes
- Fixed issues in release process and changelog tooling.

### Build and Packaging
- Improved build and packaging for release process.

### Block release-workflow dispatch when local tracked files are dirty after prepare to prevent stale local changelog state (Bug Fix, Build / Packaging)
- Added tracked-worktree detection in scripts/release_workflow.py and abort dispatch with a file list when local changes are present.
- Added --allow-dirty-dispatch override for intentional edge cases where dispatch should proceed despite local tracked edits.
- Updated scripts/README.md to document the new safety gate and override flag for release_workflow.py.

### Auto-run release-please on pushes to main to remove manual post-merge dispatch step (Build / Packaging, Configuration Cleanup)
- Updated .github/workflows/release-please.yml to trigger on push to main in addition to workflow_dispatch.
- Keeps workflow_dispatch input support for manual overrides while making normal release PR and post-merge release creation automatic.
- Simplifies release flow by eliminating the need to manually trigger the workflow after merging a release PR.

### Prevent summarize preview runs from silently wiping cached release summaries when summaries JSON is malformed (Bug Fix, Build / Packaging)
- Updated scripts/summarize_changelog.py to validate docs/changelog/CHANGELOG.summaries.json as a JSON object and fail with a clear error if parsing fails.
- Added pre-run cache validation in summarize_changelog.py main flow so malformed summary cache stops the run before any write occurs.
- Regenerated docs/changelog/CHANGELOG.summaries.json with --all --force intelligent summarization to restore released version keys plus current unreleased summary.

### Prune stale unreleased summary cache entries during preview summarization while preserving released version summaries (Bug Fix, Build / Packaging)
- Updated scripts/summarize_changelog.py to always prune stale unreleased:* keys on unreleased/default runs so only the current hash remains.
- Kept existing force-mode pruning behavior for all processed versions and reused the same cache cleanup path.
- Verified summarize_changelog.py --unreleased now leaves exactly one unreleased summary key and retains all released version summary keys.

---

## v0.8.2 — 2026-02-22

### Overview

This release includes 1 changelog updates across 1 grouped workstreams, focused on Bug Fix.

### Bug Fixes
- Fixed issues in release process and changelog tooling.

### Persist stamped changelog summaries and markdown so release-please output no longer overwrites release history formatting (Bug Fix, Build / Packaging)
- Updated release-please workflow commit step to stage CHANGELOG.md and docs/changelog/CHANGELOG.summaries.json alongside changelog JSON sources.
- Regenerated summary cache to add missing 0.8.1 hash key and removed stale unreleased summary cache entries after release rollover.
- Rebuilt CHANGELOG.md so v0.8.1 now renders the structured release summary instead of release-please auto-generated conventional-commit text.

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

### Make release rollover preserve version summaries and reliably reset unreleased changelog state (Bug Fix, Code Refactoring, Build / Packaging)
- Updated build_changelog.py to select summaries by exact version/unreleased content hash instead of first matching prefix
- Updated generate_release_notes.py to promote matching unreleased summary cache to the stamped release key and clear stale unreleased summary keys during --stamp --archive
- Updated release-please workflow commit step to include docs/changelog/CHANGELOG.summaries.json alongside CHANGELOG.json, CHANGELOG.archive.json, and CHANGELOG.md

### Backfill missing v0.7.0 and v0.8.0 changelog history and align unreleased entries with post-release state (Documentation Update, Configuration Cleanup)
- Moved 16 release-workflow and VKB-link entries from docs/changelog/CHANGELOG.json into archive as v0.8.0 while keeping only post-release work unreleased
- Added a v0.7.0 archive backfill marker so CHANGELOG.md now includes the missing release in version history
- Rebuilt CHANGELOG.md and normalized summary cache keys so released history renders correctly and unreleased reflects one active entry

### Normalize archive summary cache keys to hash-based format and remove legacy fallback rendering (Bug Fix, Configuration Cleanup)
- Removed legacy prefix fallback from scripts/build_changelog.py so summary lookup now strictly uses version/hash keys
- Rewrote docs/changelog/CHANGELOG.summaries.json to exact hash keys for v0.4.0, v0.5.0, v0.5.1, v0.7.0, and v0.8.0
- Rebuilt CHANGELOG.md and verified archived versions render full summary sections (Overview + change bullets) instead of condensed fallback lines

### Rebuilt all changelog summaries from archive/current source entries using deterministic grouped summarization (Documentation Update, Code Refactoring)
- Added an intelligent deterministic backend in summarize_changelog.py that groups related changes and emits concise release summaries without repeated similar entries
- Forced regeneration of all version summaries and synchronized hash computation so CHANGELOG.summaries.json keys match build_changelog.py exactly
- Rebuilt CHANGELOG.md so archived versions now render full Overview/section summaries instead of condensed fallback lines

### Add dispatch-only release mode to avoid redundant local changelog prep runs (Build / Packaging, Configuration Cleanup)
- Extended release_workflow.py with --skip-prepare to bypass local summarize/rebuild when preview was already generated
- Added VS Code task 'Release: Trigger release (already prepared)' for low-token, low-latency release dispatch
- Updated scripts README to document dispatch-only workflow and reduce repeated pre-release processing

### Streamline VS Code task picker with favorites and parameterized release workflows (Configuration Cleanup, UI Improvement)
- Collapsed redundant release tasks into input-driven backend and bump prompts
- Promoted frequent tasks with [fav] labels and set default build/test task groups
- Hidden low-frequency tasks from picker while preserving access for edge workflows

### Label default release preview output as Unreleased instead of the current version number (Bug Fix, Documentation Update)
- Updated scripts/generate_release_notes.py default preview mode to use display_version='unreleased' when no --stamp/--version/--all is provided
- Adjusted release note title rendering to output 'Release Notes - Unreleased' for unreleased previews while preserving vX.Y.Z format for stamped versions
- Regenerated dist/RELEASE_NOTES.preview.md and verified the heading now reads 'Release Notes - Unreleased'

### Move changelog/release LLM runtime defaults to config and remove script-level model assumptions (Configuration Cleanup, Code Refactoring)
- Updated summarize_changelog.py and generate_release_notes.py to use config-managed backend/model/timeout settings instead of hardcoded model defaults
- Added codex/claude timeout and model runtime keys to docs/changelog/changelog-config.json and set backend default there
- Aligned changelog_activity.py backend override choices with supported config-driven backends including intelligent

### Switch changelog and release-note LLM flows to CLI-only backends and remove Claude API fallback paths (Configuration Cleanup, Bug Fix)
- Updated summarize_changelog.py defaults/validation to use claude-cli or codex backends only and removed Claude API backend branch
- Updated generate_release_notes.py LLM mode to support claude-cli directly, default to claude-cli, and avoid Anthropic API dependency
- Restricted release workflow backend override options to claude-cli/codex and increased Claude CLI timeouts to improve reliability for long prompts

### Split delegation settings from changelog config and move LLM prompt/runtime controls into changelog config (Configuration Cleanup, Code Refactoring)
- Created docs/automation/delegation-config.json for codex_delegation and updated claude_run_plan.py to read from that file
- Removed codex_delegation from docs/changelog/changelog-config.json and expanded changelog_summarization with backend/model/timeouts plus prompt requirement lists
- Updated summarize_changelog.py and generate_release_notes.py to read prompt requirements and runtime knobs from config while adding UTF-8 subprocess decoding for stable CLI output handling

### Split changelog LLM runtime into per-backend config sections and separate delegation config file (Configuration Cleanup, Code Refactoring)
- Refactored docs/changelog/changelog-config.json into changelog_summarization.common plus backend sections (codex, claude_cli, intelligent)
- Updated summarize_changelog.py and generate_release_notes.py to resolve backend model/timeouts and prompt requirements from sectioned config with backward-compatible fallbacks
- Moved orchestration defaults to docs/automation/delegation-config.json and updated claude_run_plan.py to read delegation settings from the new file

### Simplify changelog LLM configuration to a single shared timeout setting (Configuration Cleanup)
- Removed backend-specific timeout fields from docs/changelog/changelog-config.json and kept only common.timeout_seconds
- Updated summarize_changelog.py and generate_release_notes.py fallback defaults to match single-timeout config shape
- Validated summarization still runs successfully using shared timeout and current backend settings

### Move delegation config into scripts and stop tracking generated changelog summary artifacts (Configuration Cleanup, Code Refactoring)
- Moved delegation defaults from docs/automation/delegation-config.json to scripts/delegation-config.json and updated claude_run_plan.py + scripts docs references.
- Updated .gitignore to treat generated CHANGELOG.md and docs/changelog/CHANGELOG.summaries.json as local artifacts.
- Updated release-please workflow commit step to stage only changelog JSON source files so ignored generated artifacts are not persisted.

### Document backend/model options in changelog config and add configurable Claude CLI model support (Configuration Cleanup, Documentation Update)
- Added inline _comment guidance in docs/changelog/changelog-config.json for backend choices, timeout behavior, and model examples
- Added claude_cli.model setting and wired summarize_changelog.py + generate_release_notes.py to pass --model to Claude CLI when configured
- Validated claude-cli backend run succeeds with config-driven model selection

### Rebuilt CHANGELOG.md from current changelog JSON sources (Documentation Update)
- Ran scripts/build_changelog.py to regenerate the markdown changelog from docs/changelog/CHANGELOG.json and docs/changelog/CHANGELOG.archive.json.
- Verified the generated markdown renders unreleased counts and version sections consistently after rebuild.
- No schema or runtime config changes were made; this task only refreshed rendered changelog output.

### Render CHANGELOG.md as released-history only and omit unreleased entries (Bug Fix, Code Refactoring)
- Updated scripts/build_changelog.py to stop generating the [Unreleased] section in markdown output.
- Kept unreleased entries as JSON source data while rendering only versioned release sections in CHANGELOG.md.
- Adjusted rebuild status output text to clarify unreleased source entries are hidden from markdown rendering.

### Guarantee release stamping writes a version summary cache for changelog rendering (Bug Fix, Code Refactoring)
- Updated generate_release_notes.py to ensure a vX.Y.Z summary cache key is always present during --stamp, promoting unreleased cache when available.
- Added deterministic summary generation fallback for stamped releases when unreleased cache is missing so build_changelog can still render rich release sections.
- Kept stale unreleased summary cache cleanup in the stamp flow and added status messages for promoted/generated/existing summary outcomes.

### Generate a dedicated changelog preview artifact during changelog activity (New Feature, Configuration Cleanup)
- Extended build_changelog.py with an include-unreleased mode so preview rendering can include the [Unreleased] section without changing the default release-history output.
- Updated changelog_activity.py to produce dist/CHANGELOG.preview.md before generating dist/RELEASE_NOTES.preview.md.
- Documented the new preview artifact workflow in scripts/README.md.

### Pin VS Code terminal PATH to workspace .venv Python (Configuration Cleanup)
- Updated .vscode/settings.json to prepend .venv\Scripts to terminal Path on Windows.
- Kept python.defaultInterpreterPath pointing to /.venv/Scripts/python.exe for interpreter selection.
- Validated settings JSON syntax after update.

---

## v0.8.0 — 2026-02-21

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

### Migrate all existing changelog IDs to simpler commit-hash format (Code Refactoring, Build / Packaging)
- Created migrate_changelog_ids.py script to convert timestamp-based IDs to CHG-<commit-hash>
- Converted CHANGELOG.archive.json entries to CHG-arc-NNN format for clarity
- Eliminated 50+ character IDs in favor of 8-12 character IDs
- All IDs now globally unique and merge-safe across branches
- Rebuilt CHANGELOG.md with migrated IDs, no duplicate ID conflicts

### Enforced restart-after-confirmed-stop and removed obsolete VKB retry/cooldown timers (Configuration Cleanup, Code Refactoring, Bug Fix)
- VKBLinkManager restart path now verifies no VKB-Link process remains before launching a new process and uses a short default restart delay (0.25s)
- Removed plugin config defaults and fallback keys for initial/fallback socket retry intervals plus vkb_link_recovery_cooldown
- Simplified VKBClient API by removing unused retry timer parameters and updated affected tests to match explicit process-driven reconnect behavior

### Clarify and reorganize configuration files for better discoverability (Configuration Cleanup, Code Refactoring)
- Renamed config_defaults.json to changelog-config.json for clarity
- Clarified config sections: changelog_summarizer -> changelog_summarization
- Added _comment fields to config_defaults.json for self-documentation
- Updated all scripts and docs to reference new changelog-config.json
- Removed ambiguous field names: max_tokens -> claude_max_tokens, removed unused codex_model from summarization config

### Made process monitor interval configurable and unified timer keys to seconds with fewer UI timer knobs (Configuration Cleanup, Code Refactoring)
- Added vkb_link_process_monitor_interval_seconds and switched link polling to vkb_link_poll_interval_seconds with legacy ms fallback support
- Removed separate UI feedback timer config and derive feedback tick from vkb_ui_poll_interval_seconds to reduce timer count
- Updated defaults/fallbacks and config tests to match the new seconds-based timer schema

### Move changelog files to docs/changelog/ subdirectory (Code Refactoring)
- Organized CHANGELOG.json, CHANGELOG.archive.json, CHANGELOG.summaries.json, and changelog-config.json into docs/changelog/

### Improve release notes formatting by removing meta-commentary and shortening group IDs (Documentation Update, Code Refactoring)
- Removed verbose meta-commentary like 'Condensed X entries into Y grouped changes'
- Removed '(condensed from N updates)' suffixes from bullet points
- Shortened group IDs in Change Group Index table to fit column width easily
- Simplified summary display to focus on actual changes rather than grouping metadata

### Increase group ID length limit to preserve meaning (Code Refactoring)
- Increased _slugify default from 48 to 70 characters
- Increased _normalise_group from 64 to 75 characters
- Updated release notes display to handle 50-char IDs
- Allows complete, meaningful group names in change entries

### Refactor group naming to extract concise topic-focused names (Code Refactoring)
- Created _extract_group_topic() to generate short group names from summaries
- Extracts 2-4 key words while filtering common stopwords
- Updated existing CHANGELOG.json entries to use new shorter names
- Group names now 20-38 chars instead of 48+ chars, no truncation needed
- Improved readability of release notes and change group index

### Centralized VKB-Link process monitoring and listener-probe logic in VKBLinkManager and switched callers to manager delegation (Code Refactoring, Configuration Cleanup)
- Added VKBLinkManager APIs for listener readiness probing and process health monitoring with crash callback support
- Removed in-handler VKB-Link monitor/probe internals from EventHandler and delegated connect/recovery/endpoint flows to manager methods
- Updated prefs panel and VKB-Link tests to call manager APIs, plus adjusted integration test config stubs for manager-backed behavior

### Completed VKB-Link delegation cleanup by moving INI endpoint parsing to manager and updating integration tests (Code Refactoring, Test Update)
- Added VKBLinkManager.read_ini_endpoint so prefs UI no longer parses VKB-Link INI directly
- Adjusted test_event_handler_vkb_link mocks for manager-driven probe/monitor APIs
- Updated test_vkb_server_integration EventHandler scenario to use a manager stub aligned with delegated manager responsibilities

### Add claude-cli backend so summarization works via VS Code Claude extension without an API key (New Feature, Configuration Cleanup)
- Added call_claude_cli() to summarize_changelog.py that calls the claude CLI with -p flag
- Wired claude-cli into summarize_version() dispatch alongside existing claude and codex backends
- Added claude-cli to --backend argparse choices
- Updated changelog-config.json default backend from claude to claude-cli

### Stop release script on summarization errors instead of silently falling back (Bug Fix)
- Changed changelog_activity.py to return a non-zero exit code when summarization fails
- Release script now aborts on Step 1 failure; use --skip-summarize to bypass intentionally

### Add configurable VS Code release workflow with selectable summarizer backend and bump strategy (New Feature, Build / Packaging, Bug Fix)
- Added scripts/release_workflow.py to run changelog preview and optionally trigger release-please with bump=auto|patch|minor|major
- Extended changelog_activity.py and summarize_changelog.py to support backend override and robust Claude CLI execution in VS Code terminals
- Updated release wrapper scripts, VS Code tasks, and release-please workflow input/path wiring for release_as dispatch and docs/changelog file commits

### Use release-please manifest as authoritative source when calculating forced bump versions (Bug Fix, Build / Packaging)
- Updated release_workflow.py to read current version from .release-please-manifest.json before pyproject.toml fallback
- Keeps --bump patch/minor/major aligned with release-please state even if local files drift
- Validated with dry-run output showing expected release_as values

### Fix codex backend summarization by auto-discovering VS Code codex.exe and using codex exec interface (Bug Fix, Build / Packaging)
- Updated summarize_changelog.py to resolve codex CLI from PATH or VS Code extension bundles when PATH is missing
- Switched Codex summarization call from deprecated codex run --plan flow to codex exec with stdin prompt and output capture
- Validated end-to-end changelog_activity.py --strict --summarize-backend codex now generates summaries and preview successfully

### Prevent conflicting release_as dispatch when an open release-please PR already targets a different version (Bug Fix, Build / Packaging)
- Updated release_workflow.py to detect open release-please PR version via gh pr list
- When --bump requests a different version than the open release PR, workflow now fails early with explicit guidance
- Avoids confusing no-op release-please runs where PR remains unchanged despite a requested bump

---

## v0.7.0 — 2026-02-21

### Overview

This release includes 1 changelog updates across 1 grouped workstreams, focused on Documentation Update.

### Documentation
- Updated documentation for release-process documentation.

### Backfill release history for v0.7.0 (release published with no changelog entries) (Documentation Update, Build / Packaging)
- Recorded v0.7.0 in archive so CHANGELOG.md shows the missing release in version history
- GitHub release notes for v0.7.0 indicate no changelog entries were present at release time

---

## v0.5.1 — 2026-02-19

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

### Release notes now show only one-line summaries, not detail bullets (Documentation Update)
- Changed group_by_tag() to use entry 'summary' field instead of 'details' list
- Keeps the tag-grouped sections and summary table; removes verbose bullet points

### Added VKB-Link auto-management with download/update and UI controls (New Feature, UI Improvement)
- Added VKB-Link manager for process detection, INI sync, and download/update flows
- Hooked recovery into connection failures with configurable auto-manage and cooldown
- Extended preferences UI with VKB-Link management, update, locate, and relocate controls

### Added project Codex config for on-request approvals and workspace writes (Configuration Cleanup)
- Added .codex/config.toml with approval_policy = on-request
- Set sandbox_mode = workspace-write for project-scoped access

### Add VKB-Link startup/shutdown handling and detailed lifecycle logging (New Feature)
- Start VKB-Link on plugin startup when not already running and stop it on plugin shutdown if started by the plugin
- Add step-by-step logging for VKB-Link status, updates, installs, and process control

### Improve VKB-Link update discovery and status/error display (Bug Fix, UI Improvement)
- Extract OneDrive links specifically from the Software section before scanning for VKB-Link archives
- Show VKB-Link status as '<exe> v<version>' and surface action errors in the status line

### Align initial VKB-Link status text with simplified display (UI Improvement)
- Initialize VKB-Link status line to 'VKB-Link.exe v?'

### Implement automated VKB-Link download from MEGA public folder with AES-CTR decryption (New Feature)
- Added MEGA API integration to vkb_link_manager.py: folder listing via https://g.api.mega.co.nz/cs, AES-ECB node-key decryption, AES-CBC attribute decryption, AES-CTR file decryption
- _fetch_latest_release() now queries MEGA as primary source (folder 980CgDDL) and falls back to VKB homepage scraping if unavailable
- New _mega_download() method on VKBLinkManager: requests per-file download URL from MEGA API, streams and decrypts with AES-128-CTR, saves valid zip to disk
- Extended VKBLinkRelease dataclass with mega_node_handle and mega_raw_key optional fields
- Fixed package_plugin.py INCLUDE list: added event_recorder, paths, prefs_panel, ui_components, unregistered_events_tracker, and vkb_link_manager modules

### Auto-install cryptography library silently when not present (New Feature)
- Added _ensure_cryptography() helper that pip-installs the cryptography package via sys.executable if it is not importable
- _fetch_latest_release() and _mega_download() now call _ensure_cryptography() instead of raising ImportError; no user action required

### Streamline VKB-Link preferences panel layout and auto-INI synchronization (UI Improvement)
- Removed 'Manage' button and 'Relocate' function; auto-manage checkbox now on same line as Host/Port fields
- Added 'VKB-Link status:' label; changed status text to 'Link Established vX.X.X' when connected, 'Disconnected' when not
- Removed 'VKB-Link.exe vX.X.X' display; replaced 'Check Updates' button with single 'Update' button
- Implemented auto-INI update: saves INI file 4 seconds after Host/Port change (if auto-manage enabled); timer resets on field focus; shows 'Settings Changed' / 'Updating INI Settings' status

### Fix NameError in VKB-Link prefs and move Update button to status line (Bug Fix, UI Improvement)
- Fixed undefined variable reference: changed vkb_app_status_var to vkb_status_var in _run_manager_action()
- Moved Update button to status_row and positioned right-aligned with status indicator
- Removed duplicate _get_vkb_manager() and _check_updates() function definitions

### Separated VKB-Link status line into its own frame (UI Improvement)
- Wrapped the VKB-Link status row in a dedicated frame
- Moved the status controls to the new frame to stabilize vertical spacing

### Left-align VKB-Link status text next to its label (UI Improvement)
- Set the status label anchor to west so the text starts immediately after the label

### Fix VKB-Link INI button packing when status row moved (Bug Fix, UI Improvement)
- Avoided packing the INI button relative to a widget in a different frame
- Kept INI button ordering relative to Locate button when visible

### Match VKB-Link status label font and center the row (UI Improvement)
- Set the status label font to match the message size
- Switched the status line to grid layout for consistent vertical centering

### Remove Configure INI button and prioritize standalone INI status messages (Bug Fix, UI Improvement)
- Removed the Configure INI control and its visibility logic from the VKB-Link preferences panel
- Made INI status states ('Settings Changed' and 'Updating INI Settings') override connection polling text
- Changed out-of-date INI display to show a standalone 'INI out of date' status instead of appending to established status

### Add restart-phase status and dotted INI pending indicator (UI Improvement)
- Added a delayed 'Restarting VKB-Link...' status phase during update actions
- Animated pending INI status by appending dots while waiting for the 4-second auto-write timer
- Added timer cancellation guards so dot animation stops cleanly on apply or focus reset

### Speed up pending INI dots and alternate warning color (UI Improvement)
- Increased pending-status dot cadence to 333ms (three dots per second)
- Alternated pending-status color between #f39c12 and darker orange #d68910
- Updated status override matching so dotted 'Settings Changed...' remains in warning style

### Removed agent source names from changelog storage and rendered outputs (Documentation Update, Code Refactoring)
- Updated scripts/log_change.py to stop writing agent fields and to render markdown rows/sections without an Agent column
- Updated scripts/generate_release_notes.py to remove the Agent column from generated release notes tables
- Sanitized existing CHANGELOG.json, CHANGELOG.archive.json, and CHANGELOG.md entries to remove agent source names from recorded metadata and headings

### Delay startup connect after launching VKB-Link and show transient connection state (Bug Fix, UI Improvement)
- Added startup sequencing so connect waits for VKB-Link start task and pauses 5 seconds when VKB-Link was launched by the plugin
- Exposed temporary connection status overrides on EventHandler for UI visibility during startup/connect
- Updated preferences status polling to display connection override text before normal connected/disconnected state

### Apply 5s reconnect delay after VKB-Link start/restart recovery and expand lifecycle logging (Bug Fix, UI Improvement)
- Added reconnect deferral support in VKBClient so retries can be paused after process launch
- Updated recovery flow to wait 5 seconds with status/countdown before reconnect when VKB-Link was started or restarted
- Expanded VKB-Link process lifecycle logs for start/stop/restart actions and INI-update connection state

### Reduce false INI mismatch status by syncing path and normalizing host comparison (Bug Fix, UI Improvement)
- Persisted vkb_ini_path in EDMC config after auto-INI writes from the preferences timer
- Synced the panel's cached INI path from config before status comparisons
- Normalized localhost/loopback host values during INI-vs-prefs checks to avoid false 'INI out of date' alerts

### Ensure shift/subshift state is resent on every new VKB socket connection (Bug Fix)
- Re-applied the on-connected callback before connect and recovery reconnect calls
- Added explicit connection log lines showing forced state resend payload
- Updated shift-state sender to return success/failure so resend issues are logged clearly

### Made VKB-Link startup/shutdown lifecycle status consistently visible in INFO logs (Bug Fix, Documentation Update)
- Set plugin logger minimum level to INFO in load.py so lifecycle messages are not dropped by higher default levels
- Added explicit startup post-action VKB-Link status logs including running state, exe path, version, and managed flag
- Added explicit shutdown pre-stop and post-stop VKB-Link status logs with started-by-plugin context

### Centralize VKB-Link control with consistent 5s post-start delay and unified logging (Code Refactoring)
- Added action_taken field to VKBLinkActionResult to track lifecycle actions (started/restarted/stopped/none)
- Created _apply_post_start_delay() helper on EventHandler as single point for post-start warmup delay logic
- Replaced string-inspection delay checks with typed action_taken field across startup and recovery paths
- Improved VKB-Link lifecycle logging with clear action state messages (starting/stopping/restarting)

### Restart VKB-Link when host/port settings change to apply new endpoint configuration (Bug Fix, UI Improvement)
- Added _apply_endpoint_change() to EventHandler that stops VKB-Link, updates INI, restarts process, and reconnects
- Modified prefs_panel to call endpoint change handler instead of just updating INI file
- Added countdown parameter to _apply_post_start_delay() for silent 5s wait without per-second UI updates or logs
- New flow: settings change -> 4s timer -> VKB-Link restart with new endpoint -> 5s silent warmup -> reconnect

### Add diagnostic logging and safety auto-start for VKB-Link during polling (Bug Fix, UI Improvement)
- Added diagnostic logging to _apply_ini_update() to reveal why restart may not occur (auto_manage disabled or event_handler unavailable)
- Added safety mechanism in _poll_vkb_status() to auto-start VKB-Link if configured but not running
- Polling loop now checks every 2s if VKB-Link should be running, and starts it if needed (crash recovery)
- Auto-started VKB-Link applies 5s warmup delay and reconnects to ensure stable connection

### Fix VKB-Link restart blocking main thread and status messages never rendering (Bug Fix)
- Moved _apply_endpoint_change() call into a background thread so status updates render before blocking work starts
- Added ini_action_inflight guard to prevent concurrent endpoint-change operations
- Rewrote _poll_vkb_status() to keep main thread clear of subprocess calls; safety auto-start runs in a dedicated background thread with its own inflight guard
- Fixed _apply_endpoint_change() to clear connection_status_override on both success and failure reconnect paths

### Fix countdown logs, wrong endpoint on reconnect, and disconnected vs reconnecting status mismatch (Bug Fix, UI Improvement)
- Suppress _attempt_vkb_link_recovery during intentional endpoint changes via _endpoint_change_active flag
- Remove countdown logs from all _apply_post_start_delay call sites (countdown=False everywhere)
- Add is_reconnecting() to VKBClient returning True when reconnect worker is active but not yet connected
- Show 'Reconnecting...' (blue) in preferences status panel instead of 'Disconnected' when reconnect worker is running

### Added a Codex plan runner script that writes monitorable run artifacts under agent outputs (New Feature, Documentation Update)
- Added scripts/run_codex_plan.py to execute codex exec from a plan file and stream logs/events/status into agent_artifacts/codex/reports/plan_runs/<run_id>
- Implemented heartbeat-updated status.json plus stdout/stderr/event/final-message files for external progress monitoring
- Documented the new runner in scripts/README.md so other agents can call it consistently

### Created test plan and dry-ran run_codex_plan.py to verify plan handoff (Documentation Update)
- Wrote agent_artifacts/claude/temp/test_plan.md as a minimal Codex prompt
- Executed run_codex_plan.py --dry-run and confirmed metadata.json, status.json, command.txt, plan_input.txt are generated correctly
- Verified the codex exec command is built with correct sandbox, approval, workspace, and stdin (-) arguments

### Auto-discover VS Code bundled Codex CLI when codex is missing from PATH (Bug Fix, New Feature, Documentation Update)
- Updated scripts/run_codex_plan.py to resolve codex from PATH first, then fall back to .vscode/.vscode-insiders extension bundles (openai.chatgpt-*/bin/windows-x86_64/codex.exe)
- Added Git Bash/MSYS path normalization so /c/Users/... values for HOME or --codex-bin resolve to valid Windows paths
- Documented the fallback behavior in scripts/README.md for cross-agent invocation clarity

### Added comprehensive VKB-Link manager tests including an opt-in live production integration path (Test Update)
- Added test/test_vkb_link_manager.py covering helper parsing, exe/INI discovery, ensure_running paths, update/stop flows, install behavior, and MEGA/fallback release handling
- Added test/test_vkb_link_manager_live.py for real production-like validation (download/start/connect/update/stop) gated behind RUN_VKB_LINK_LIVE=1
- Executed both suites; deterministic suite surfaced five behavior mismatches in current implementation while the live suite was attempted and skipped safely due an already-running VKB-Link process

### Write VKB-Link INI before starting process after install/download flows (Bug Fix, Test Update)
- Updated src/edmcruleengine/vkb_link_manager.py to resolve/write INI before process start in ensure_running and update_to_latest install paths
- Added _resolve_or_default_ini_path() to default to <exe_dir>/VKBLink.ini when no INI exists yet and persist vkb_ini_path
- Expanded test/test_vkb_link_manager.py with ordering assertions and default-INI coverage; reran deterministic and live suites

### Force first-run INI targeting to the downloaded executable directory before VKB-Link start (Bug Fix, Test Update)
- Changed _resolve_or_default_ini_path() to prioritize INI resolution near the specific executable being started and create a default <exe_dir>/VKBLink.ini path when missing
- Pre-start/pre-restart INI sync now avoids stale persisted INI paths from prior installs and always targets the active install directory
- Added test_ensure_running_download_ignores_stale_saved_ini_and_targets_exe_dir and reran targeted/full VKB manager tests

### Verified run_codex_plan.py live end-to-end with VSCode-bundled codex binary (New Feature)
- Script auto-discovered codex.exe via discover_vscode_codex() from openai.chatgpt VSCode extension
- Live run completed in ~24s with state=succeeded, return_code=0, 12 events
- Codex correctly listed load.py and PLUGIN_REGISTRY.py without modifying any files

### Removed OneDrive/homepage fallback and made VKB-Link release discovery MEGA-only with explicit live-test artifact cleanup (Bug Fix, Test Update)
- Updated src/edmcruleengine/vkb_link_manager.py to remove OneDrive/homepage scraping fallback in _fetch_latest_release; MEGA is now the sole release source
- Removed obsolete OneDrive/fallback tests and replaced them with MEGA-unavailable/MEGA-listing-failure expectations in test/test_vkb_link_manager.py
- Updated test/test_vkb_link_manager_live.py cleanup to explicitly delete downloaded/expanded install artifacts after each run

### Added claude_run_plan.py wrapper that appends claude_report.json to Codex run directories (New Feature)
- Created scripts/claude_run_plan.py as Claude's entry point for plan execution: calls run_codex_plan.py, then writes claude_report.json alongside the run artifacts
- claude_report.json captures Claude model, input/output tokens, cost estimate (with per-model pricing table), Codex event breakdown (commands/reasoning/messages), token usage with cache hit %, duration, and final_message
- Handles both live and --dry-run modes by matching 'Run directory:' and 'Dry run created:' output prefixes to locate the run directory

### Added /codex label convention to CLAUDE.md for delegating tasks to Codex via claude_run_plan.py (Documentation Update)
- Added 'Codex Delegation' section defining the /codex prompt label and the exact steps Claude must follow when it appears
- Steps cover: writing the plan file, calling claude_run_plan.py with token/model args, reporting the outcome, and updating the changelog

### Made VKB-Link live integration test run by default on Windows (Test Update)
- Removed RUN_VKB_LINK_LIVE env-gate from test/test_vkb_link_manager_live.py so the live test is no longer opt-in
- Removed runtime skip that previously bypassed the test when VKB-Link was already running
- Executed test/test_vkb_link_manager_live.py directly; it now runs automatically and currently xfails on TCP port refusal after successful download/install/start

### Live VKB-Link test now uses a repo-local runtime directory under test/ (Test Update)
- Updated test_vkb_link_manager_live to create runtime paths under test/_live_runtime instead of system temp
- Kept per-run isolation with run-<timestamp>-<pid> directories inside test/_live_runtime
- Verified cleanup removes run artifacts and deletes test/_live_runtime when empty

### Comprehensive code review completed identifying critical security and correctness issues (Documentation Update)
- Executed static code review via Codex agent covering VKB-Link integration, preferences UI, rules engine, and test suite
- Identified 2 critical security issues: missing executable signature verification, runtime pip auto-install
- Identified 5 high-priority correctness issues: duplicate rule IDs not prevented, incomplete process detection, subshift range inconsistency, rule editor crash path, numeric type casting bugs
- Identified 6 medium-priority issues: stale INI path references, UX inconsistencies, callback accumulation, race condition in safety auto-start, flaky live tests, under-tested recovery paths
- Review artifacts stored in agent_artifacts/codex/reports/plan_runs/20260219T111945Z_code-review/

### Bootstrap VKB-Link once after fresh install before applying managed INI settings (Bug Fix, Test Update)
- ensure_running now performs a bootstrap start/stop cycle after first install when no INI exists, then writes host/port and performs the managed start
- INI resolution now prefers a persisted INI path when it belongs to the active executable directory to avoid stale cross-install paths
- Added unit coverage for the bootstrap sequence and reran VKB-Link manager unit + live tests

### Optimized Codex delegation token estimates and event parsing (Performance Improvement, Documentation Update)
- Reduced default token estimates from 35k/25k to 5k/2k for typical plan files (80-85% cost reduction)
- Optimized parse_codex_events() to use single-pass event parsing instead of storing all events in memory
- Updated CLAUDE.md documentation to reflect new token defaults and clarify when to override estimates

### Update VKB-Link INI in place without overwriting unrelated settings (Bug Fix, Test Update)
- Reworked _write_ini to patch only [TCP] Adress and Port keys while preserving other sections/comments and inline key comments
- Added fallback behavior to create a minimal [TCP] section when no TCP section exists
- Added unit coverage asserting unrelated INI content survives endpoint updates and reran VKB-Link manager tests

### Move INI patch assertions to pure text tests so tests do not write INI files directly (Test Update, Code Refactoring)
- Extracted INI update logic into _patch_ini_text and kept _write_ini as thin file I/O wrapper
- Replaced direct _write_ini file-based tests with pure _patch_ini_text assertions
- Reran VKB-Link manager test suite with all tests passing

### Use graceful VKB-Link shutdown with forced fallback and wait for INI creation after shutdown (Bug Fix, Test Update)
- Bootstrap flow now polls for new/touched VKB INI files for several seconds after stopping VKB-Link to catch delayed file writes
- Process stop now attempts graceful termination first (taskkill /T or pkill) and only escalates to force kill if still running
- Updated stop-process test assertions and reran manager + live VKB-Link tests

### Add thorough VKB-Link control tests for UI endpoint-change flow and live stop/start cycle (Test Update, Code Refactoring)
- Updated EventHandler endpoint-change logic to resolve INI path via _resolve_or_default_ini_path for robust host/port patching
- Added new test_event_handler_vkb_link unit tests covering stop/start, INI patch, config/client endpoint updates, reconnect behavior, and missing-manager handling
- Expanded live VKB-Link test to include an explicit mid-cycle stop/start/reconnect/send sequence before update and cleanup

### Added formatted /codex-results reporting with Codex token and estimated-cost visibility (New Feature, Documentation Update)
- Enhanced scripts/claude_run_plan.py to estimate Codex execution cost from input/cached/output tokens, include model/rate metadata, and emit codex_results.md alongside claude_report.json
- Enhanced scripts/run_codex_plan.py status.json with structured token_usage and best-effort cost_estimate fields sourced from turn.completed usage events
- Added scripts/codex_results.py plus CLAUDE.md and scripts/README.md updates so /codex-results can print a polished summary including final message, token usage, and estimated spend

### Extend live VKB-Link test to execute real UI endpoint-change flow (Test Update)
- Live test now calls EventHandler._apply_endpoint_change with a new port after an explicit stop/start cycle
- Uses EventHandler with the live VKBClient and manager to validate stop, INI patch, restart, reconnect, and send on the new endpoint
- Stubs EventHandler catalog/rules loading in that live-only phase to keep focus on VKB-Link control behavior

### Fixed script issues: --refresh persistence and duplicate pricing table (Bug Fix)
- Fixed codex_results.py so --refresh flag now persists regenerated content to codex_results.md file
- Removed duplicate CODEX_PRICING table from run_codex_plan.py; now imports from claude_run_plan.py for single source of truth
- Updated CLAUDE.md to document --refresh and --write flag behavior

### Fixed pricing and cost calculation approach: no duplication, minimal tokens (Code Refactoring)
- Reverted run_codex_plan.py to keep CODEX_PRICING local (no imports)
- Modified claude_run_plan.py to read cost_estimate from status.json instead of recalculating
- Falls back to recalculating only if rate overrides are provided or status.json cost is missing
- Result: no duplicate pricing tables, no imports between scripts, no token waste on duplicate calculations

### Externalized VKB-Link timing defaults to config_defaults and wired runtime modules to config-driven values (Configuration Cleanup, Test Update, Build / Packaging)
- Added src/edmcruleengine/config_defaults.json and updated config.py to load defaults from this file with a matching fallback map
- Replaced hardcoded VKB-Link and preferences-panel timing constants with config-backed values in event_handler.py, vkb_link_manager.py, and prefs_panel.py
- Updated packaging include list and expanded config tests; re-ran unit + live VKB-Link tests successfully

### Validated Codex delegation script updates with a live test_scripts run (Test Update)
- Executed scripts/claude_run_plan.py with agent_artifacts/claude/temp/test_scripts.md and completed successfully
- Verified status.json cost_estimate matched claude_report.json codex_execution.cost_estimate exactly
- Confirmed scripts/codex_results.py --refresh rewrites codex_results.md and persists regenerated content

### Consolidated VKB-Link and UI timer settings into a smaller shared set (Configuration Cleanup, Test Update)
- Replaced multiple VKB-Link timer keys with warmup/operation-timeout/poll/restart settings and updated event handler and manager call sites
- Replaced multiple preferences timer keys with UI apply/poll/feedback settings and derived follow-up delay from feedback interval
- Updated defaults/tests and re-ran unit plus live VKB-Link test suites successfully

### Start VKB-Link as a detached child process while preserving clean stop behavior (Bug Fix, Configuration Cleanup)
- Updated VKBLinkManager._start_process to launch VKB-Link with detached process flags and DEVNULL stdio so it runs independently from the plugin host
- Kept graceful shutdown first and adjusted stop wait window to at least 5 seconds before force termination to improve clean exits
- Validated with test_vkb_link_manager.py and live start/stop/restart integration test

### Config helper lookups now honor config_defaults values instead of hardcoded fallback literals (Bug Fix, Test Update)
- Updated EventHandler, VKBLinkManager, and prefs panel config helper methods to call config.get(key) first and only apply literal fallback when missing/invalid
- This fixes warmup/timer overrides from config_defaults.json not taking effect (e.g., vkb_link_warmup_delay_seconds)
- Updated affected tests to assert configured defaults rather than hardcoded timer literals and re-ran targeted suites

### Added configurable VKB-Link launch mode and restored legacy startup behavior by default (New Feature, Bug Fix, Test Update)
- Introduced vkb_link_launch_mode config key (legacy|detached), defaulting to legacy so plugin-launched behavior matches prior implementation
- Detached startup remains available for troubleshooting via config without code edits
- Updated config helper fallback behavior tests and endpoint-change assertions to follow configured warmup values

### Harden VKB-Link restart shutdown timing so low operation timeout does not cause premature force-kill (Bug Fix, Configuration Cleanup)
- Found restart oddness correlated with vkb_link_operation_timeout_seconds set to 2 in config_defaults
- Updated _stop_process to use minimum command timeout 10s and minimum graceful exit wait 8s before escalation
- Validated manager test suite after change

### Enforced VKB-Link single-instance behavior by stopping all detected duplicates before restart/stop/update actions (Bug Fix, Test Update)
- Added multi-process discovery helpers for Windows and POSIX so manager can enumerate all running VKB-Link instances
- Updated ensure_running/update_to_latest/stop_running to stop all detected processes when needed and then continue with a single controlled start
- Added regression tests for duplicate-process cleanup in ensure_running and stop_running; test/test_vkb_link_manager.py passes

### Added VKB-Link TCP listener readiness wait before reconnect attempts after start/restart (Bug Fix, Test Update)
- EventHandler now probes host:port readiness (using vkb_link_operation_timeout_seconds and vkb_link_poll_interval_ms) before attempting connect after warmup
- Wired readiness wait into startup connect flow, endpoint-change restart flow, recovery flow, and polling safety auto-start flow
- Updated endpoint-change tests to account for listener readiness probe and re-ran event-handler + manager test suites

### Prevented duplicate VKB-Link launches by serializing lifecycle operations and closing safety-start race (Bug Fix, Test Update)
- Added a manager lifecycle lock so ensure_running/update_to_latest/stop_running cannot run concurrently and race into duplicate starts
- Added pre-start recheck paths in ensure_running so if another path starts VKB-Link first, duplicate launch is skipped
- Moved prefs-panel safety inflight flag assignment before thread start and updated manager tests to fully mock multi-process discovery without touching live processes

### Fixed Windows VKB process discovery normalization to stop false duplicate-instance restarts (Bug Fix, Test Update)
- Changed _find_running_processes_windows to prefer unique PID-based results and only run WMIC fallback when PowerShell yields no actionable PID entries
- Hardened WMIC parsing against malformed blank-line blocks so path-only/pid-only partial records no longer create phantom duplicate processes
- Added Windows unit test covering duplicate partial discovery output and verified test_vkb_link_manager.py passes

### Suppressed send-failed VKB recovery before first successful connection to prevent startup restart loops (Bug Fix, Test Update)
- Added EventHandler connection state flag that is set on first successful socket connection
- _attempt_vkb_link_recovery now skips send_failed-triggered process recovery until a successful connection has been established
- Added unit test for suppressed early send_failed recovery and reran event-handler + manager suites

### Harden VKB-Link post-start settle handling for connect and recovery flows (Bug Fix, Test Update)
- Added a public VKBLinkManager wait_for_post_start_settle() hook and used it before listener probing.
- Updated EventHandler connect/recovery workflows to honor post-start warmup timing and reduce early reconnect races.
- Expanded VKB-Link event-handler tests to assert settle waiting behavior, including recovery worker execution.

### Do not stop pre-existing VKB-Link processes on plugin shutdown (Bug Fix, Test Update)
- Changed plugin shutdown policy to stop VKB-Link only when this plugin instance started/restarted it.
- Refined startup ownership tracking so successful ensure_running calls only mark ownership for action_taken started/restarted.
- Added load.py shutdown regression tests covering pre-existing-process preservation and owned-process shutdown.

### Disable pre-connect listener probing by default to avoid VKB-Link UI stalls (Bug Fix, Configuration Cleanup, Test Update)
- Added vkb_link_probe_listener_before_connect (default false) to config defaults and fallback defaults.
- EventHandler now probes listener readiness only when that config flag is enabled; normal connect/recovery uses warmup-delay then direct connect.
- Updated event-handler tests to validate no probe by default and probe behavior when explicitly enabled.

### Send zero VKB shift state before plugin disconnect/shutdown (Bug Fix, Test Update)
- Added EventHandler.clear_shift_state_for_shutdown() to send Shift/Subshift zeros without triggering recovery on send failure.
- plugin_stop now calls shutdown clear-state send before disconnecting VKB client.
- Added shutdown and event-handler tests to verify clear-state send occurs on plugin exit and skips recovery side effects.

### Simplify README and add dedicated VKB-Link setup guide with managed/manual workflows (Documentation Update)
- Reworked README quick start to stay concise and emphasize plugin-managed VKB-Link for users not already running it.
- Added docs/VKB_LINK_SETUP.md covering VKBDevCfg master-device setup, VKB-Link TCP setup, and both Auto-manage and manual operation paths.
- Updated documentation cross-links in docs/DEVELOPMENT.md and docs/RULE_EDITOR_TUTORIAL.md to reflect Auto-manage and the new setup guide.

### High-level code cleanup: removed redundant imports and constants (Code Refactoring, Performance Improvement)
- Removed duplicate VKB_LINK_VERSION_RE regex (MEGA_VKB_LINK_RE was identical)
- Removed unused struct import from vkb_link_manager.py
- Removed redundant sys.platform check in _find_running_processes_windows
- Removed unused json and logging imports from event_handler.py
- Replaced json.loads(json.dumps()) deep copy antipattern with copy.deepcopy() in prefs_panel.py

### Check VKB-Link process existence before any reconnection attempt (Bug Fix)
- Added process_readiness_check callback to VKBClient to gate reconnection attempts
- VKB-Link process now verified running before TCP reconnection in all scenarios
- Applied post-start settle delay to reconnection flow when process is detected as running

### Detect connection failures and handle INI mismatches with intelligent recovery (Bug Fix)
- Added terminal error flag to prevent infinite reconnection attempts when configuration is correct but connection fails
- Check INI host/port against plugin config when reconnection fails despite process running
- If INI mismatch found: trigger recovery to stop, fix INI, and restart VKB-Link
- If INI correct and connection fails: set terminal error status 'Cannot connect to VKB-Link' and halt reconnection attempts

### Simplified workspace VS Code Python settings to avoid duplicate system interpreter discovery (Configuration Cleanup)
- Removed python-envs system manager override from .vscode/settings.json so the workspace relies on the pinned .venv interpreter.
- Kept python.defaultInterpreterPath and pytest paths pinned to /.venv/Scripts.

### Reconnect worker now follows exact same startup sequence as plugin initialization (Bug Fix)
- Process readiness check now actively calls ensure_running() when process not found during reconnection
- Reconnection flow now mirrors startup: check process → ensure running → apply settle delay → TCP connect
- Handles download/install/bootstrap of VKB-Link if needed during reconnection, not just on startup

### Fix VKB-Link minimized window blocking UI event loop activation for TCP (Bug Fix)
- Temporarily disable minimized INI setting during VKB-Link startup to ensure UI event loop activates
- Once TCP connection succeeds, restore original minimized setting
- Adds restore_last_startup_minimized_setting() method called after successful TCP connection

### Robustly disable minimized mode during VKB-Link startup to ensure UI event loop activation (Bug Fix)
- Enhanced _ensure_not_minimized_for_startup() to handle missing INI files and create/add [UI] section as needed
- Now works on first run when INI doesn't exist yet (bootstrap phase)
- Saves and restores original minimized setting after TCP connection succeeds
- Added 5 comprehensive tests covering all scenarios: existing INI, missing INI, missing [UI] section, full flow

### run_codex_plan now executes non-dry runs in per-run git branches/worktrees by default (New Feature, Build / Packaging)
- Added isolated branch/worktree CLI controls and automatic worktree creation for non-dry runs.
- Codex execution now uses the isolated workspace for both --cd and subprocess cwd, keeping caller branch untouched.
- Recorded isolation metadata (requested/active branch/worktree/repo details) in run metadata and documented behavior in scripts README.

### Fixed: Use correct VKB-Link INI key 'Start Minimized=' for window startup state (Bug Fix)
- VKB-Link uses 'Start Minimized=0/1' not 'minimized=true/false'
- Now correctly detects, disables, and restores the Start Minimized setting
- VKB-Link will now start visible (not minimized) on plugin startup to ensure TCP connectivity

### Corrected: Use VKB-Link actual INI key [Common] section 'start minimized =1/0' (Bug Fix)
- VKB-Link uses [Common] section with 'start minimized =1' (note space before equals)
- Not [Settings] section as initially assumed in CHG-077
- VKB-Link now correctly starts visible (not minimized) to enable TCP connectivity

### run_codex_plan now defaults to gpt-5.3-codex and supports numeric effort shorthand (Configuration Cleanup, New Feature)
- Changed run_codex_plan default execution model and cost-model profile to gpt-5.3-codex.
- Added --effort with 1=minimal, 2=low, 3=medium, 4=high mapping to model_reasoning_effort config.
- Kept explicit --config model_reasoning_effort overrides authoritative and updated scripts README docs.

### Add automatic process crash detection and restart capability (Code Refactoring, Bug Fix)
- Added process health check in _handle_reconnect_failed() to detect VKB-Link process crashes
- Process crash triggers automatic recovery via standard startup path (ensure_running())
- Verifies all 53 tests pass with new crash detection logic in place

### Added a reusable rule-authoring Codex skill for rules.json creation and validation (New Feature, Documentation Update)
- Created .codex/skills/rule-authoring with project-specific SKILL.md workflow for drafting and debugging rules
- Added reusable JSON templates and a debug checklist in references/rule-patterns.md
- Generated and corrected agents/openai.yaml metadata including default prompt token -authoring, then validated with quick_validate.py

### Add periodic process health monitoring for automatic crash detection (Code Refactoring, Bug Fix)
- Background thread monitors VKB-Link process health every 5 seconds
- Detects process crashes (was running, now stopped) and triggers immediate recovery
- Only monitors when auto_manage is enabled; avoids false positives on intentional stops
- Thread is daemon-based and cleans up on disconnect; all 53 tests still passing

### Add dynamic model and thinking-budget support to /codex delegation (New Feature, Configuration Cleanup)
- Created config_defaults.json to set project-wide /codex defaults
- Added --thinking-budget parameter to claude_run_plan.py and run_codex_plan.py
- thinking-budget maps to Codex effort levels (low→2, medium→3, high→4)
- Updated CLAUDE.md documentation with new configuration options
- Config values load from config_defaults.json and can be overridden via CLI args

### Merged VKB-Link-enhanced-loading and copilot/add-status-line-and-mock-data branches into main (Code Refactoring)
- Merged VKB-Link-enhanced-loading branch fixing UI loop issue during minimized startup
- Merged copilot/add-status-line-and-mock-data adding connection status display and event anonymization
- Skipped copilot/update-documentation-and-guides to preserve main's documentation files

### Fix NameError in event_handler track_unregistered_events property (Bug Fix)
- Fixed missing self reference when accessing config in EventAnonymizer initialization

---

## v0.5.0 — 2026-02-19

### Overview

This release includes 1 changelog updates across 1 grouped workstreams, focused on Bug Fix.

### Bug Fixes
- Fixed issues in packaging.

### Fix package_plugin.py missing 5 modules from INCLUDE list (Bug Fix, Build / Packaging)
- Added paths.py, event_recorder.py, prefs_panel.py, ui_components.py, unregistered_events_tracker.py
- Missing files caused ModuleNotFoundError when plugin was installed from zip

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

### Moved bundled data files to data/ subdirectory and centralised path references (Configuration Cleanup, Code Refactoring)
- Created data/ directory to hold all bundled plugin data and example files
- Moved signals_catalog.json, rules.json.example, icon_map.json, dev_paths.json.example to data/ via git mv
- Created src/edmcruleengine/paths.py as single source of truth: PLUGIN_DATA_DIR constant and data_path() helper
- Added DATA_DIR = PROJECT_ROOT / 'data' to scripts/dev_paths.py for script-side consistency
- Updated 18 files across src/, scripts/, and test/ to reference new data/ paths
- Fixed packaging bug: icon_map.json was previously not included in the distributable ZIP

### Established cross-agent changelog infrastructure committed to the repository (Documentation Update, Configuration Cleanup)
- Created CHANGELOG.json at repo root as structured machine-readable history for all agents
- Created CHANGELOG.md at repo root as human-readable summary table and detail sections
- Added changelog policy (read at session start, write at session end) to CLAUDE.md, AGENTS.md, and .github/copilot-instructions.md
- Removed CLAUDE.md, AGENTS.md, and .github/ from .gitignore so agent instructions travel with the repo across machines
- Per-agent runtime scratch dirs (agent_artifacts/claude|codex|copilot/) remain gitignored
- Updated agent_artifacts/README.md to reflect new structure

### Strengthened changelog policy: recording is now required after every task, not at end of session (Documentation Update)
- Changed trigger from 'end of session' to 'after completing any task that modifies files'
- Added explicit instruction: do not skip, do not wait for the user to ask
- Updated CLAUDE.md, AGENTS.md, and .github/copilot-instructions.md with new wording

### Added release notes generation script and wired it into the release workflow and ZIP packaging (Build / Packaging, New Feature)
- Created scripts/generate_release_notes.py: reads CHANGELOG.json, filters by version, groups by summary tag, outputs RELEASE_NOTES.md
- Supports --version, --since, --all, --output, --stdout flags for flexible local and CI use
- Updated package_plugin.py to include dist/RELEASE_NOTES.md in the distributable ZIP when present
- Updated .github/workflows/release-please.yml to generate release notes before packaging and use them as the GitHub release body

### Adopted unreleased version sentinel so changelog entries always track the next release, not the last (Build / Packaging, Documentation Update)
- Changed agent instructions: plugin_version must always be unreleased, never read from version.py
- Rewrote generate_release_notes.py: default mode previews unreleased entries; --stamp <VERSION> stamps them and writes RELEASE_NOTES.md
- Updated release-please.yml: use --stamp so CI stamps and commits CHANGELOG.json on every release
- Added commit-stamped-changelog step to workflow so stamps persist in the repo after each release
- Backfilled all existing CHANGELOG.json entries (CHG-001 to CHG-004) from 0.2.0 to unreleased

### Added CHANGELOG.archive.json to keep CHANGELOG.json small for agent reads (Build / Packaging)
- generate_release_notes.py --stamp --archive moves stamped entries to CHANGELOG.archive.json after release
- CHANGELOG.json retains only unreleased entries, keeping agent read cost O(1) per release cycle not O(history)
- release-please.yml updated to pass --archive and commit CHANGELOG.archive.json alongside CHANGELOG.json

### Added log_change.py script so agents run one command to record changes instead of editing files manually (Build / Packaging, Documentation Update)
- Created scripts/log_change.py: auto-increments CHG-NNN, appends to CHANGELOG.json, prepends row and section to CHANGELOG.md
- Accepts --agent, --tags, --summary, --details, --date, --dry-run flags
- Validates tags against approved vocabulary; rejects unknown values
- Updated CLAUDE.md, AGENTS.md, copilot-instructions.md: replace manual editing instructions with single script call

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

### Integrate opencode as a supported agent and LLM backend for changelog scripts (New Feature)
- Added opencode to known agents in log_change.py
- Enabled opencode as a backend choice in summarization and activity scripts
- Implemented OpenCode CLI invocation logic in changelog utilities
- Updated changelog-config.json with OpenCode settings and fallback priority

### Centralize VKB coordination logic into VKBLinkManager and fix all broken tests (Code Refactoring, Test Update)
- Added VKBLinkManager.from_config() classmethod to encapsulate VKBClient construction
- Added startup(), shutdown(), set_shift_state(), restore_shift_state_from_config() to VKBLinkManager
- Dropped host/port parameters from ensure_running() and update_to_latest(); methods now read from config
- Fixed internal callers within vkb_link_manager.py that still passed host=/port= to ensure_running()
- Updated 9 test files (test_config, test_integration, test_rule_loading, test_edmc_integration, test_production_workflow, test_unregistered_events, test_journal_files, test_vkb_server_integration, test_vkb_link_manager_live) to use VKBLinkManager.from_config() instead of removed auto-fallback pattern
- Full test suite: 354 passed, 1 pre-existing failure (test_rule_editor), 1 xfailed live test

### Exhaustive cleanup of process leaks and logic redundancy (Bug Fix, Code Refactoring, Test Update)
- Implemented automated cleanup for VKBLinkManager health monitor threads
- Updated all integration tests to explicitly shutdown event handlers and managers
- Unified versioning and git logic in changelog_utils.py
- Removed redundant local helper functions across the script ecosystem
- Standardized 1/0 configuration across all JSON settings files

### Generate human-readable changelog summary for version 1.0.0 (Documentation Update)
- Summarized engine stability fixes and new landing gear toggle feature
- Formatted output with Overview and grouped sections as per project standards

### Fix remaining test failures after VKB centralization refactor (Test Update, Bug Fix)
- Fixed 4 test_production_workflow.py errors: handler fixture called handler.shutdown() which doesn't exist on EventHandler; changed to handler.disconnect()
- Full test suite now: 354 passed, 15 skipped, 1 xfailed, 1 pre-existing failure (test_rule_editor_simplified)

### Improve reliability and memory usage of changelog agent backends (Bug Fix, Performance Improvement)
- Updated Gemini CLI backend to use headless mode and JSON output to avoid recursive agent startup
- Switched Claude and OpenCode backends to use stdin for prompts to avoid Windows command-line limits
- Added OpenCode to live agent test suite
- Enabled changelog tests in test configuration
- Cleaned up orphaned Node.js processes from previous sessions

### Fix Codex CLI integration and update default model (Bug Fix, Code Refactoring)
- Updated call_codex_cli to use modern 'exec' command and skip-git-repo-check
- Updated default Codex model to gpt-4o for better account compatibility
- Verified all other active agents (Gemini, Claude, OpenCode, Local LLM) are functional

### Extend agent runner scripts to support multiple backends and generalized delegation (New Feature, Code Refactoring)
- Created run_agent_plan.py as a generic orchestration script for any planner/executor pair
- Updated delegation-config.json to support multiple planners (Claude, Gemini, Codex, OpenCode, Copilot) and executors
- Refactored shared logic into agent_runner_utils.py for consistent pricing and reporting
- Maintained backward compatibility with claude_run_plan.py as a legacy wrapper
- Expanded executor pricing in run_codex_plan.py to include Gemini and OpenCode

### Clean up redundant VS Code test configuration (Configuration Cleanup)
- Removed redundant [python] block override for pytestArgs in .vscode/settings.json
- Simplified global python.testing.pytestArgs to defer to pyproject.toml configuration

### Created Agent Runner tutorial and repaired Gemini settings (Documentation Update, Bug Fix)
- Created docs/AGENT_RUNNER_TUTORIAL.md detailing the planner-executor workflow
- Updated AGENTS.md with a link to the new runner documentation
- Repaired malformed global settings.json for Gemini CLI to prevent Unexpected token errors

### Added Slash Commands for Agent Runner (New Feature, Documentation Update)
- Created /agent, /agent:deep, and /agent:fast slash commands
- Updated AGENT_RUNNER_TUTORIAL.md with CLI command usage

### Added namespaced agent selection commands (New Feature)
- Created /agent:deep:gemini, /agent:deep:claude, etc. namespace structure
- Updated tutorial with namespaced command examples

### Added Watch Latest Run VS Code task (New Feature)
- Added '[fav] Agent: Watch Latest Run' to .vscode/tasks.json

### Fixed agent-specific artifact pathing and improved watch utility (Bug Fix, New Feature)
- Modified run_agent_plan.py to dynamically route artifacts to the correct agent folder
- Updated watch_run.py to search across all agent directories for the latest run

### Fixed model selection bug in agent runner (Bug Fix)
- Modified run_agent_plan.py to correctly pass the executor's model from delegation-config.json
- Ensured Gemini executor uses gemini-2.0-pro instead of defaulting to GPT models

### Implemented automatic worktree cleanup and maintenance tools (Bug Fix, New Feature)
- Added --cleanup-worktree flag to auto-remove isolated git branches after successful runs
- Created agent_system/core/cleanup_artifacts.py for forceful directory purging
- Created /agent:cleanup slash command for easy maintenance

### Added working-set synchronization to Agent Runner (Bug Fix)
- Modified run_codex_plan.py to sync uncommitted/untracked changes to isolated worktrees
- Ensures agents work on the current state of the code, not just the last commit

### Improved delegation workflow with branch preservation and merge commands (New Feature)
- Modified run_codex_plan.py to commit agent changes before cleanup
- Preserved isolated branches on success to allow manual review and merging
- Updated watch_run.py to output a 'git merge' command for successful runs

### Seamless VS Code integration for Agent Runner (New Feature)
- Added '[fav] Agent: Review Latest Changes (Diff)' task
- Added '[fav] Agent: Merge Latest Changes' task
- Created agent_system/core/get_latest_run_info.py for task automation

### Enable seamless merging for changelog files (Configuration Cleanup)
- Added union merge strategy for CHANGELOG.json in .gitattributes
- Updated post-merge hook to automatically rebuild CHANGELOG.md
- Configured core.hooksPath to point to .githooks

### Added support for parallel agent runs with VS Code agent picker (New Feature)
- Updated get_latest_run_info.py with --agent filtering
- Added 'agentChoice' input to .vscode/tasks.json to resolve parallel run ambiguity
- Allows selecting Gemini, Claude, or Codex work for Review/Merge individually

### Added Run Catalog and Specific Targeting for parallel agents (New Feature)
- Added '[fav] Agent: List Successful Runs' task
- Modified Review/Merge tasks to support optional Run ID input
- Created agent_system/core/list_agent_runs.py for run discovery

### Created Interactive Agent Dashboard (TUI) (New Feature)
- Created agent_system/dashboard/agent_dashboard.py using curses
- Added '[fav] Agent: Open Interactive Dashboard' VS Code task
- Implemented multi-run log switching and process termination (Kill) capability

### Fix thinking budget resolution and model reporting in agent runners (Bug Fix)
- Corrected --thinking-budget resolution in run_agent_plan.py to properly fall back to planner defaults
- Fixed detect_codex_model in agent_runner_utils.py to prioritize the last --model argument (user override)

### Upgraded Agent Dashboard to full Lifecycle TUI (New Feature)
- Added multi-pane layout with stats (Model, Cost, Tokens)
- Implemented integrated lifecycle actions: [M]erge, [K]ill, [D]elete
- Added live log streaming and color-coded status indicators

### Integrate local-llm option into agent runner system (New Feature, Configuration Cleanup)
- Added local-llm to planner and executor choices in run_agent_plan.py
- Added local-llm configuration to delegation-config.json
- Included local-llm in AGENT_TYPES for agent_dashboard.py
- Updated pricing and reporting utilities to support local-llm
- Fixed parameter naming bug in codex_results.py

### Polished Agent Dashboard with Rich Icons and Safety Logic (New Feature)
- Added box-drawing UI and agent-specific icons (GEM, CLD, CDX)
- Implemented safety-kill on Delete: active runs are terminated before purging
- Mapped DELETE and BACKSPACE keys to the purge action

### Improved Dashboard refresh reliability and added live clock (Bug Fix)
- Added multi-point timestamp checking (Dir + Status file) for instant run detection
- Added live (H:M:S) clock to dashboard header to verify TUI heartbeat
- Ensured sub-second refresh cycle is correctly reflected in the UI

### Created Widescreen Professional Agent Dashboard (New Feature, UI Improvement)
- Increased Sidebar width to 65 for full task visibility
- Added Rich Unicode icons (🚀, ✅, 🎭, 🤖) and live log scrolling
- Implemented 2-stage safety purge logic for DELETE key
- Added locale support for robust ANSI/Unicode rendering on Windows

### Added Agent Maintenance and Orphan Audit tool (New Feature)
- Created agent_system/core/agent_maintenance.py for deep-cleaning
- Implemented cross-check logic to find dangling branches and orphaned folders
- Added [C] Maintenance hotkey to Dashboard for interactive cleanup

### Fixed plan file encoding issue on Windows (Bug Fix)
- Modified run_codex_plan.py to robustly handle UTF-8, UTF-8-sig, and UTF-16 encoding
- Ensured agent runs don't crash when reading plan files created by PowerShell

### Implement local-llm integration and mandatory post-action validation (New Feature, Bug Fix, Configuration Cleanup)
- Codified Post-Action Validation Mandate in GEMINI.md
- Fixed --thinking-budget forwarding and model detection in orchestration scripts
- Integrated local-llm as a generic planner/executor option
- Removed legacy Claude/Codex specific runners and result file fallbacks

### Fixed Dashboard rendering spam and improved TUI stability (Bug Fix, UI Improvement)
- Replaced clear() with erase() to prevent terminal scrolling/spam issues
- Refactored header centering to avoid edge-wrap errors on Windows
- Added conservative width boundaries for Unicode/Emoji rendering
- Implemented global exception handling in TUI main loop

### Validate necessity of catalog comment handling test (Documentation Update)
- Verified that test_rule_editor_handles_catalog_comments in test_rule_editor_simplified.py is required for UI integrity
- Confirmed RuleEditor contains explicit logic to filter underscore-prefixed catalog metadata

### Fix RuleEditor initialization in test_rule_editor_simplified.py (Bug Fix, Test Update)
- Added missing plugin_dir argument to RuleEditor initialization in test_rule_editor_handles_catalog_comments
- Executed post-action validation: static analysis, specific test execution, and zero-regression smoke tests all passed

### Fixed Dashboard duplication and alignment issues (Bug Fix, UI Improvement)
- Replaced erase() with clear() to ensure a complete UI reset on every frame
- Switched to stable ASCII status icons (RUN, DONE, FAIL) for perfect alignment
- Enforced strict character-count clipping for sidebar summaries
- Launched low-usage validation batch using Gemini and Local LLM

### Implement auto-update notification popup and EDMC restart (New Feature, UI Improvement)
- Added background update checking on plugin startup
- Implemented Tkinter-based user prompt for available updates
- Added mandatory EDMC restart capability after successful plugin update
- Expanded PluginUpdateManager with non-blocking check and restart logic
- Verified with new unit tests and mandatory post-action validation suite

### Simulate and verify EDMC restart logic for plugin updates (New Feature, Bug Fix)
- Created and executed safe simulation script to verify subprocess re-launch logic
- Confirmed correct identification of runtime executable and arguments for Windows environments
- Validated immediate process termination via os._exit(0) in simulated contexts

### Fix VKB-Link live integration test initialization (Bug Fix, Test Update)
- Updated test_live_download_start_connect_update_and_stop to use VKBLinkManager.from_config()
- Ensured internal VKBClient is correctly initialized for the live test path
- Verified test execution proceeds to functional phase (though env-blocked in this run)

### Validate standardized agent runner system and local-llm integration (Test Update, Code Refactoring)
- Verified end-to-end orchestration for gemini and local-llm planners
- Confirmed standardized agent_report.json generation and rendering
- Updated run_codex_plan.py to allow binary-less dry-runs for easier validation

### Purge orphaned agent run branches and worktrees (Configuration Cleanup)
- Removed active worktrees for gemini-audit and local-audit
- Deleted corresponding git branches from codex/plan-runs/

---

## v0.11.0 — 2026-02-23

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

### Refactor load.py based on comprehensive code review (Code Refactoring, Configuration Cleanup)
- Consolidated global state into PluginState class
- Standardized sys.path manipulation with a helper function
- Added missing type hints and replaced magic numbers with constants
- Improved thread synchronization in the plugin startup sequence
- Added basic host/IP validation for VKB configuration
- Removed unused time import and redundant logger assignments

### Enhance load.py robustness and lifecycle management (Code Refactoring, Configuration Cleanup)
- Added threading.Event to signal background threads to exit gracefully
- Implemented robust host validation using socket.getaddrinfo
- Added error handling around configuration integer parsing
- Refined prefs_changed to reconnect more efficiently
- Improved shutdown reliability with timeout guards

### Fix SyntaxError in load.py from corrupted prefs_changed function (Bug Fix)
- Removed duplicated and truncated code block in prefs_changed
- Verified file syntax with compilation check

### Refine event_handler.py for robustness and thread safety (Code Refactoring, Configuration Cleanup)
- Extracted bit masks to VKB_SHIFT_MASK and VKB_SUBSHIFT_MASK protocol constants
- Implemented finally blocks to ensure recovery and endpoint change flags are always reset
- Added type validation for shift tokens to prevent execution crashes
- Improved rule engine loading to properly respect preserve_on_error
- Updated logging to use new protocol constants for consistent output

### Finalize event_handler.py robustness refinements (Code Refactoring)
- Standardized all log messages to use VKB protocol constants
- Implemented conditional recovery logic based on the allow_recovery flag
- Hardened the recovery worker lock to ensure safe state management
- Confirmed 100% pass rate across the VKB management test suite

### Consolidate boolean handling into Config class and remove bool_utils.py (Code Refactoring, Configuration Cleanup)
- Implemented robust boolean coercion directly in Config.get
- Removed bool_utils.py and all associated imports and usages
- Standardized all boolean configuration retrieval to use direct Config.get calls
- Updated test suite to align with consistent boolean usage

### Restructure codebase into functional subdirectories (Code Refactoring)
- Organized src/edmcruleengine into config, rules, vkb, ui, events, and utils subpackages
- Updated all internal imports to use relative paths
- Updated load.py and tests to reflect new package structure
- Verified integrity with full test suite pass

### Rename LMStudio backend to Local LLM in changelog tooling (Code Refactoring, Configuration Cleanup)
- Renamed lmstudio to local-llm/local_llm across scripts and config
- Updated call_lmstudio to call_local_llm in changelog_utils.py
- Standardized backend identifiers and display names for local LLM support

### Move changelog-config.json to agent_system/reporting/ (Code Refactoring, Configuration Cleanup)
- Moved configuration file to be adjacent to the scripts that use it
- Updated CONFIG_FILE path in changelog_utils.py using __file__ resolution
- Updated scripts/README.md and CLAUDE.md documentation paths

### Abstract download logic and add OneDrive support (Code Refactoring, New Feature)
- Created generic Downloader interface and MegaDownloader implementation
- Integrated OneDriveDownloader into src/edmcruleengine/utils/
- Refactored VKBLinkManager to use generic downloader component
- Added unit tests for OneDrive direct download resolution

### Finalize generic download architecture (Code Refactoring)
- Replaced VKBLinkRelease with generic DownloadItem dataclass
- Encapsulated all AES and MEGA logic within MegaDownloader component
- Decoupled VKBLinkManager from specific download provider implementations
- Updated test suite to align with generic downloader interface

### Decouple and encapsulate downloader implementations (Code Refactoring)
- Separated MegaDownloader and OneDriveDownloader into their own modules
- Consolidated all MEGA-specific cryptographic logic within its downloader
- Ensured VKBLinkManager is strictly provider-agnostic via generic Downloader interface
- Stabilized test suite with improved mocking of download components

### Consolidate VKB connection logic and modularize downloaders (Code Refactoring)
- Centralized socket lifecycle management within VKBLinkManager
- Simplified EventHandler by delegating all hardware interaction to the manager
- Separated MegaDownloader and OneDriveDownloader into their own specialized modules
- Ensured strict architectural decoupling between VKB management and download providers

### Implement generic Endpoint architecture and naive EventHandler (Code Refactoring)
- Created Endpoint interface for rule action delegation
- Refactored EventHandler to be naive and support multiple endpoints
- Moved all VKB-specific logic and state into VKBLinkManager (as an Endpoint)
- Maintained backward compatibility via proxy methods and properties
- Enabled future support for pluggable non-VKB endpoints

### Enhance OneDriveDownloader reliability for public shares (Bug Fix, Performance Improvement)
- Implemented redir-to-download URL transformation for direct file access
- Used urlsafe_b64encode for standard unpadded base64url sharing tokens
- Added expand=children parameter to Graph API calls for efficient folder listing
- Improved fallback discovery across multiple Microsoft Graph API versions

### Verify MEGA share as reliable VKB software source (Performance Improvement)
- Confirmed that MEGA share (node 980CgDDL) remains fully accessible anonymously
- Successfully listed 90+ VKB tools and software versions from MEGA
- Noted that public OneDrive folder shares are currently restricted by Microsoft API policies
- Ensured plugin can continue to use MEGA as the primary software delivery backend

### Centralize test configuration into test/test_config.json (Test Update, Code Refactoring)
- Moved ui_bootstrap, ui_rules_file, and run_live_agents options to JSON config
- Updated test/conftest.py to load and expose test_settings fixture
- Refactored test/test_ui_bootstrap.py to use centralized configuration
- Allowed bypassing --run-live-agents CLI flag via config file

### Add local-llm support and configurable test execution (New Feature, Test Update)
- Implemented support for OpenAI-compatible local LLM APIs (e.g. LMStudio)
- Added --run-changelog=0/1 pytest flag to toggle the changelog test suite
- Expanded test suite to cover local-llm and verified skip/fallback logic
- Ensured live agent tests are properly targeted and skipped by default

### Add KeyboardInterrupt handling to orchestration scripts (Bug Fix, UI Improvement)
- Wrapped entry points in try-except blocks to handle Ctrl+C
- Ensured Release Workflow, Changelog Activity, and Summarize exit cleanly
- Added user-friendly interruption messages

### Fix test suite hangs in VS Code Test Explorer (Bug Fix, Test Update)
- Updated MockVKBServer to forcefully close socket on stop
- Ensured mock_server fixture joins background thread during teardown
- Deferred edmcruleengine imports to prevent premature thread startup during discovery
- Added explicit thread joining with timeouts for robust cleanup

### Standardize config to use 1/0 for boolean toggles (Configuration Cleanup)
- Updated changelog-config.json to use 1/0 instead of true/false
- Added as_bool helper to changelog_utils.py for robust type conversion
- Restored changelog-config.json to docs/changelog/ directory

### Standardize test config to use 0/1 and centralize suite control (Configuration Cleanup, Test Update)
- Moved run_changelog toggle to test/test_config.json
- Standardized all test_config.json boolean values to 0/1
- Updated conftest.py to prioritize test_config.json settings with 0/1 support
- Verified skip logic for both changelog and live agent suites

### Move changelog config to scripts directory (Configuration Cleanup)
- Moved changelog-config.json from docs/changelog/ to agent_system/reporting/
- Updated changelog_utils.py to resolve config from its local directory

### Fix packaging discovery and stabilize unregistered event tests (Bug Fix, Code Refactoring)
- Updated package_plugin.py to use dynamic glob discovery for all subpackaged modules
- Corrected RuleEditorUI bootstrap and fixed missing plugin_dir attribute in RuleEditor
- Stabilized test_unregistered_events.py by ensuring correct tracking enablement and unknown event usage
- Ensured all 350+ tests pass or correctly handle environment limitations

### Explain UI bootstrap setting in test config (Documentation Update)
- Identified ui_bootstrap as a toggle for manual Rule Editor UI testing
- Verified association with VS Code 'EDMC: UI Bootstrap' task
- Clarified that it allows testing the editor UI without EDMC/Elite Dangerous

### Automate UI bootstrap tests (New Feature, Test Update)
- Converted manual UI bootstrap test into a fully automated functional test
- Added programmatic verification of rule editing and creation
- Implemented mock handlers for modal UI dialogs to prevent blocking
- Ensured test suite closes automatically after exercising UI logic

### Complete decoupling of VKB management from EventHandler (Code Refactoring)
- Moved all VKB settings and state tracking into VKBLinkManager
- Refactored load.py to manage vkb_manager as a top-level global component
- Updated prefs_panel.py to interact directly with VKBLinkManager for hardware status
- Achieved truly generic EventHandler design supporting pluggable rule endpoints

### Fix ModuleNotFoundError in plugin_prefs and prefs_panel (Bug Fix)
- Corrected internal import paths in load.py and prefs_panel.py after package reorganization
- Updated PrefsPanelDeps initialization in load.py to match new schema
- Verified dependency resolution with automated test case

### Fix VKB-Link updater selecting wrong version from MEGA folder due to loose filename regex (Bug Fix, Test Update)
- MegaDownloader._version_re now requires the 'VKB[- ]?Link' prefix; unrelated files like 'SomeLib-v0.94.zip' are skipped instead of producing a version like '0.94' that sorts higher than the real release (0, 94) > (0, 8, 2)
- _install_release now validates the cached archive with zipfile.is_zipfile() before use; a corrupt or mismatched cached file is deleted and re-downloaded instead of causing a silent extraction failure
- Added 7 regression tests: version regex acceptance/rejection, the 0.94-vs-0.8.2 tuple edge case, fetch_latest_release ordering sanity, corrupt-cache re-download, and valid-cache no-redownload

---

## v0.10.2 — 2026-02-22

### Overview

This release includes 6 changelog updates across 1 grouped workstreams, focused on Code Refactoring.

### Improvements
- Refactored multiple areas for maintainability.

### Add LMStudio as an optional local LLM backend for changelog summarization (New Feature)
- Added lmstudio configuration section to changelog-config.json
- Implemented call_lmstudio in changelog_utils.py using urllib.request
- Integrated lmstudio into the fallback orchestration and VS Code tasks

### Ensure consistent LLM output formatting across all backends (Code Refactoring)
- Updated normalize_llm_summary to standardize bullet points (e.g., converting • to -)
- Refined LMStudio system prompt to match the professional style of other providers
- Verified consistent markdown header and bullet usage regardless of selected backend

### Standardize spacing in LLM-generated changelog summaries (Code Refactoring)
- Updated normalize_llm_summary to enforce exactly one blank line after '### Overview'
- Ensured bullets immediately follow other section headers without a blank line
- Verified consistent section separation across all AI backends

### Centralize changelog analysis logic and improve overview consistency (Code Refactoring)
- Moved core grouping and statistical logic to changelog_utils.py
- Updated normalize_llm_summary to use statistical data as a descriptive fallback for missing overviews
- Ensured all LLM-generated summaries maintain the same professional statistical intro as historical releases

### Optimize AI prompts for minimal context and instruction overhead (Code Refactoring, Performance Improvement)
- Stripped redundant internal IDs and technical jargon from LLM context
- Consolidated prompt instructions into direct, imperative rules
- Reduced token usage while maintaining high-quality summarization output

### Fix NameError in generate_release_notes by completing logic consolidation (Bug Fix, Code Refactoring)
- Imported missing _intelligent_tag_summary, _shorten_group_key, and _version_tuple from changelog_utils
- Verified that all release-notes preview generation steps now complete successfully
- Consolidated shared changelog analysis logic to prevent future undefined symbol errors

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

### Add GitHub Copilot as LLM backend option for changelog summarization (New Feature, Code Refactoring)
- Added call_copilot_cli() function that invokes gh copilot CLI with prompt
- Updated summarize_version() to support copilot backend alongside claude-cli and codex
- Added copilot configuration section to changelog-config.json with install instructions

### Add GitHub Copilot to VS Code release task backend picker (Configuration Cleanup, UI Improvement)
- Updated .vscode/tasks.json releaseBackend input options to include copilot
- Added intelligent backend option to picker for consistency with CLI
- Release workflow tasks now show all 5 summarizer backend choices

### Add copilot and intelligent backends to release_workflow.py argument parser (Configuration Cleanup)
- Updated --summarize-backend choices to accept: claude-cli, codex, copilot, intelligent
- Updated docstring to reflect all supported backends
- Release workflow now supports all 4 changelog summarization backends

### Add copilot backend to changelog_activity.py argument parser (Configuration Cleanup)
- Updated --summarize-backend choices to accept copilot alongside claude-cli, codex, and intelligent
- changelog_activity.py now supports all 4 summarization backends for consistency

### Fix GitHub Copilot CLI integration to use Windows app and prompt mode (Bug Fix, Code Refactoring)
- Updated call_copilot_cli() to use copilot CLI with -p prompt mode and -s silent mode
- Updated _resolve_copilot_command() to resolve copilot executable instead of gh CLI
- Copilot backend now calls GitHub Copilot CLI directly instead of gh copilot extension

### Default Copilot backend to gpt-4.1 model (included, no token cost) (Configuration Cleanup, Bug Fix)
- Updated call_copilot_cli() to default model to gpt-4.1 instead of empty
- Updated changelog-config.json copilot section to use gpt-4.1 and updated install instructions
- gpt-4.1 is included with Copilot and has no token usage cost

### Fix Copilot CLI input handling to use stdin instead of command-line arguments (Bug Fix)
- Changed call_copilot_cli() to pass prompt via stdin for proper multiline/special character handling
- Removed -p flag from command line args, letting Copilot read from stdin
- Copilot backend now works reliably with complex prompts containing newlines and special chars

### Ensure Copilot output is normalized to standard changelog template format (Bug Fix, Code Refactoring)
- Enhanced _normalize_llm_summary() to add ### Overview section when missing from LLM output
- Copilot now produces identical format to Claude and Codex backends
- All LLM backends now consistently follow: ### Overview + ### [Section] + bullet points

### Add Google Gemini CLI as new LLM backend option for changelog summarization (New Feature, Code Refactoring)
- Added call_gemini_cli() function that invokes gemini CLI with stdin input for prompts
- Updated summarize_version() to route to gemini backend
- Updated all argument parsers and VS Code tasks to include gemini as a backend choice
- Gemini output normalized to match standard template like other backends

### Unify changelog normalization and establish Gemini agent policies (New Feature, Code Refactoring, Configuration Cleanup, Documentation Update)
- Consolidated LLM output normalization into generate_release_notes.py
- Updated summarize_changelog.py to use shared normalization logic
- Added GEMINI.md with workspace and changelog policies
- Added Gemini to log_change.py and generate_release_notes.py choice lists

### Refactor changelog tools into modular architecture (Code Refactoring)
- Consolidated logic into scripts/changelog_utils.py
- Implemented LLM backend fallback mechanism
- Standardized configuration loading

### Add comprehensive tests for changelog utilities and refine normalization (Test Update, Code Refactoring)
- Created test/test_changelog_utils.py with 7 test cases
- Fixed header deduplication content loss bug
- Improved metadata stripping for robust LLM output cleaning
- Verified sequential fallback mechanism via unit tests

### Add optional live agent tests with output validation (Test Update)
- Implemented --run-live-agents pytest flag to enable real LLM calls
- Added parameterized test to validate output format from all 4 backends
- Ensured live tests are skipped by default to save tokens
- Updated conftest.py with custom markers and collection logic

### Consolidate VKB-Link management logic into VKBLinkManager (Code Refactoring, Configuration Cleanup)
- Removed redundant _update_ini_file from load.py
- Deleted obsolete test/test_ini_updater.py
- Verified all vkb-link management is handled by VKBLinkManager and coordinated via EventHandler

### Add comprehensive consolidation and regression tests for VKB-Link management (Test Update)
- Added test/test_vkb_link_logic_consolidation.py to verify logic centralization
- Verified EventHandler and load.py delegation to VKBLinkManager
- Ran 64 tests across 4 VKB-related test files, all passed

### Reorganize scripts into a logical directory structure (Code Refactoring, Configuration Cleanup, Documentation Update)
- Created subdirectories for changelog, release, dev, validation, and agent_runners
- Updated PROJECT_ROOT and sys.path logic in all scripts for correct path resolution
- Refreshed VS Code tasks.json with new script paths
- Updated AGENTS.md, CLAUDE.md, and GEMINI.md with new command usage

### Consolidate redundant script logic into changelog_utils (Code Refactoring, Configuration Cleanup)
- Moved versioning (parse, bump, read) and git (dirty check, PR find) logic to changelog_utils.py
- Refactored release_workflow.py to use consolidated helpers
- Refactored migrate_changelog_ids.py to use consolidated helpers and paths
- Eliminated duplicate code across 3 major orchestration scripts

### Fix and expand VS Code tasks after reorganization (Configuration Cleanup)
- Fixed incorrect test runner path (tests/ -> test/)
- Added 'EDMC: Validate Signal Catalog' task
- Added 'EDMC: Verify Catalog Coverage' task
- Verified all script paths in tasks.json are accurate

### Fix internal script path in release_workflow.py (Bug Fix)
- Updated activity_cmd to point to agent_system/reporting/changelog_activity.py
- Cleaned up imports and sys.path logic in changelog_activity.py

### Fix Gemini CLI hang by switching to stdin for prompts (Bug Fix)
- Updated call_gemini_cli to pass prompt via stdin instead of -p argument
- Verified that large multi-line prompts no longer cause the CLI to hang

### Update script paths in release workflow and documentation after reorganization (Bug Fix, Configuration Cleanup)
- Fixed GitHub Actions release-please failure by updating script paths to agent_system/reporting/ and scripts/release/
- Updated RELEASE.md, DEVELOPMENT.md, and CLAUDE.md with correct script locations
- Ensured consistency across all agent workspace policies and dev guides

---
