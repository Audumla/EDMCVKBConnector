# Gemini Workspace Policy

All Gemini execution artifacts must stay under `agent_artifacts/gemini/`.

- Reports: `agent_artifacts/gemini/reports/`
- Temporary scripts and scratch files: `agent_artifacts/gemini/temp/`

Do not write Gemini-generated reports or temp files anywhere else in this repository.

## Changelog Policy

### At the START of every session

Read `docs/changelog/CHANGELOG.json` to understand what every agent has already done. Use it to avoid duplicating work and to understand the current state of the codebase.

### After completing ANY task that modifies files

Before declaring the task done, you MUST record what was changed. Do not skip this step. Do not wait for the user to ask. Updating the changelog is the final step of every task.

Run this script — it handles all file updates automatically:

```bash
python scripts/changelog/log_change.py 
    --agent gemini 
    --group "<WorkstreamSlug>" 
    --tags "<Tag1>" "<Tag2>" 
    --summary "One-sentence description" 
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

## Post-Action Validation Mandate

EVERY task performed by Gemini MUST conclude with an explicit validation phase. A task is not considered complete until the following are satisfied:

1.  **Integrity Check**: Run static analysis (e.g., `ruff check`, `mypy`, `python -m py_compile`) to ensure no syntax or type errors were introduced.
2.  **Functional Verification**: Reproduce the original issue (for bug fixes) or demonstrate the new capability (for features) using a script or manual CLI command.
3.  **Test Coverage**: 
    - If modifying existing logic, run all related tests (`pytest test/test_*.py`).
    - If adding a new feature, a new test file or case MUST be added and shown to pass.
4.  **Zero-Regression**: Run the core smoke tests (`pytest test/test_integration.py`) to ensure existing functionality remains intact.

Never declare a task done based on "implied correctness." Always provide the output of the validation commands in your final response.

## Agent Delegation Protocol

This project uses a specific delegation protocol via `#agent:<budget>:<planner>` tags. When you see one:
1. Research the task.
2. Write a Markdown plan to `agent_artifacts/gemini/temp/plan.md`.
3. Execute: `python scripts/agent_runners/run_agent_plan.py --planner <planner> --thinking-budget <budget> --plan-file agent_artifacts/gemini/temp/plan.md --task-summary "Gemini: <task>"`
4. Output a Delegation Receipt:
   - **Planner:** Gemini
   - **Executor:** Codex
   - **Budget:** <budget>
   - **Monitor:** `python scripts/agent_runners/watch_run.py`

