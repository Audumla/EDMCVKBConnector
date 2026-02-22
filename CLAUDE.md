# Agent Workspace Policy

All Claude execution artifacts must stay under `agent_artifacts/claude/`.

- Reports: `agent_artifacts/claude/reports/`
- Temporary scripts and scratch files: `agent_artifacts/claude/temp/`

Do not write Claude-generated reports or temp files anywhere else in this repository.

## Changelog Policy

### At the START of every session

Read `docs/changelog/CHANGELOG.json` to understand what every agent has already done. Use it to avoid duplicating work and to understand the current state of the codebase.

### After completing ANY task that modifies files

Before declaring the task done, you MUST record what was changed. Do not skip this step. Do not wait for the user to ask. Updating the changelog is the final step of every task.

Run this script — it handles all file updates automatically:

```bash
python scripts/log_change.py \
    --agent claude \
    --group "<WorkstreamSlug>" \
    --tags "<Tag1>" "<Tag2>" \
    --summary "One-sentence description" \
    --details "Bullet one" "Bullet two" "Bullet three"
```

`--group` is recommended and should stay stable for related iterative work that will ship together.

The script generates a short, globally unique `CHG-<commit-hash>` ID (merge-safe across branches), appends to `docs/changelog/CHANGELOG.json`, and rebuilds `CHANGELOG.md` from JSON sources. Do not edit those files manually.

### Release prep activity

Before pushing for release creation, run:

```bash
python scripts/changelog/changelog_activity.py --strict
```

This rebuilds `CHANGELOG.md` and writes compact unreleased release-note preview to `dist/RELEASE_NOTES.preview.md`.

### Approved `--tags` values

Use one or more of these exact strings:

`Bug Fix` · `New Feature` · `Code Refactoring` · `Configuration Cleanup` ·
`Documentation Update` · `Test Update` · `Dependency Update` ·
`Performance Improvement` · `UI Improvement` · `Build / Packaging`

## Codex Delegation — `/codex` label

When the user's prompt contains the label `/codex`, delegate the task to Codex via the wrapper script instead of implementing it directly. Follow these steps exactly:

1. **Write a plan file** to `agent_artifacts/claude/temp/<short-task-name>.md`.
   - Use clear markdown: Goal, Steps, Acceptance criteria, and any Out-of-scope notes.
   - Be specific enough that Codex can act without further clarification.

2. **Configure defaults (optional):**

   Edit `docs/changelog/changelog-config.json` to set project-wide defaults for `/codex` delegation:

   ```json
   {
     "codex_delegation": {
       "claude_model": "claude-sonnet-4-6",
       "thinking_budget": "none",
       "claude_input_tokens": 5000,
       "claude_output_tokens": 2000,
       "codex_model": "gpt-5"
     }
   }
   ```

   Supported `thinking_budget` values:
   - `"none"` (default) — standard Claude reasoning
   - `"low"` — minimal extended thinking (Codex effort level 2)
   - `"medium"` — moderate extended thinking (Codex effort level 3)
   - `"high"` — maximum extended thinking (Codex effort level 4)

3. **Run the wrapper script:**

   ```bash
   python scripts/claude_run_plan.py \
       --plan-file agent_artifacts/claude/temp/<short-task-name>.md \
       --claude-model claude-sonnet-4-6 \
       --thinking-budget medium \
       --task-summary "<one-line description>" \
       --run-name <short-task-name>
   ```

   All `claude_run_plan.py` arguments are loaded from `docs/changelog/changelog-config.json` if not specified on the command line.

   Optional overrides:

   ```bash
   # Token estimates (default: 5000 input / 2000 output)
   --claude-input-tokens 10000 --claude-output-tokens 5000

   # Codex model for cost estimation (default: gpt-5)
   --codex-model gpt-5-mini

   # Explicit cost rates (USD / million tokens)
   --codex-input-rate 0.25 --codex-cached-input-rate 0.025 --codex-output-rate 2.0
   ```

4. **Report the outcome** to the user:
   - State: succeeded / failed / dry_run
   - Duration, Codex token usage, and estimated cost (from `claude_report.json`)
   - Final message from Codex (the `final_message` field)

5. **Update the changelog** as normal after a successful run.

The run artifacts (plan, logs, events, report) are written under
`agent_artifacts/codex/reports/plan_runs/<run_id>/`.

`claude_run_plan.py` also writes a ready-to-share formatted summary:
`agent_artifacts/codex/reports/plan_runs/<run_id>/codex_results.md`.

## Codex Results — `/codex-results` label

When the user's prompt contains `/codex-results`, return a polished summary from
the latest Codex run (or a specific run if they provide one).

1. **Generate/print formatted output**:

   ```bash
   python scripts/codex_results.py
   ```

   Optional target run:

   ```bash
   python scripts/codex_results.py --run-id <run_id>
   ```

   Flags:
   - `--refresh`: Regenerate the summary from JSON artifacts and update the cached file
   - `--write`: When refreshing, ensure the file is written back to disk

2. **Return the script output to the user as-is** so it includes:
   - run metadata and state
   - token usage and cache hit
   - estimated Codex/Claude cost
   - full Codex final message

## Release Workflow

All changes are automatically tracked in `docs/changelog/CHANGELOG.json` and released via release-please.

**VSCode integration:** Press `Ctrl+Shift+B` (Build Tasks) and select:

- **"Release: Prepare changelog"** — Rebuild changelog and generate release notes preview
- **"Release: Trigger release-please workflow"** — Create/update the release PR on GitHub
- **"Release: Full workflow (prep + trigger)"** — Do both in one step

For complete release guide, including troubleshooting and customization, see [RELEASE.md](RELEASE.md).
