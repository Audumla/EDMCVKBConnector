# Agent Workspace Policy

All Claude execution artifacts must stay under `agent_artifacts/claude/`.

- Reports: `agent_artifacts/claude/reports/`
- Temporary scripts and scratch files: `agent_artifacts/claude/temp/`

Do not write Claude-generated reports or temp files anywhere else in this repository.

## Changelog Policy

### At the START of every session

Read `CHANGELOG.json` (repo root) to understand what every agent has already done. Use it to avoid duplicating work and to understand the current state of the codebase.

### After completing ANY task that modifies files

Before declaring the task done, you MUST record what was changed. Do not skip this step. Do not wait for the user to ask. Updating the changelog is the final step of every task.

Run this script — it handles all file updates automatically:

```bash
python scripts/log_change.py \
    --agent claude \
    --tags "<Tag1>" "<Tag2>" \
    --summary "One-sentence description" \
    --details "Bullet one" "Bullet two" "Bullet three"
```

The script auto-increments the CHG-NNN id, appends to `CHANGELOG.json`, and prepends the row and detail section to `CHANGELOG.md`. Do not edit those files manually.

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

2. **Run the wrapper script:**

   ```bash
   python scripts/claude_run_plan.py \
       --plan-file agent_artifacts/claude/temp/<short-task-name>.md \
       --claude-model claude-sonnet-4-6 \
       --task-summary "<one-line description>" \
       --run-name <short-task-name>
   ```

   Note: Token estimates default to 5000 input / 2000 output. Only override if your plan is unusually large:

   ```bash
   --claude-input-tokens 10000 --claude-output-tokens 5000
   ```

   Codex execution-cost estimation defaults to `gpt-5` rates. Override only if needed:

   ```bash
   --codex-model gpt-5-mini
   # or explicit rates (USD / million tokens)
   --codex-input-rate 0.25 --codex-cached-input-rate 0.025 --codex-output-rate 2.0
   ```

3. **Report the outcome** to the user:
   - State: succeeded / failed / dry_run
   - Duration, Codex token usage, and estimated cost (from `claude_report.json`)
   - Final message from Codex (the `final_message` field)

4. **Update the changelog** as normal after a successful run.

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
