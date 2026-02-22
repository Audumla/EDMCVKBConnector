# Development Scripts

Maintained scripts in this directory:

- `bootstrap_dev_env.py`: bootstrap EDMC dev environment and link this plugin.
- `run_edmc_from_dev.py`: run EDMC from a local dev checkout.
- `package_plugin.py`: create release ZIP under `dist/`.
- `signal_catalog_editor.py`: interactive editor for `signals_catalog.json`.
- `validate_signal_catalog.py`: validate catalog structure/operators/event references.
- `verify_catalog_coverage.py`: check catalog coverage against known ED events.
- `dev_paths.py`: shared path resolution used by dev scripts.
- `run_codex_plan.py`: run `codex exec` from a plan file and write monitorable run artifacts under `agent_artifacts/codex/reports/plan_runs/`; non-dry runs execute in a new isolated git worktree branch by default, default model is `gpt-5.3-codex`, and `--effort 1..4` maps to reasoning effort (auto-discovers VS Code bundled `codex.exe` if `codex` is not on `PATH`).
- `claude_run_plan.py`: Claude wrapper around `run_codex_plan.py` that writes `claude_report.json` and a formatted `codex_results.md` summary (tokens, estimated cost, final message).
- `codex_results.py`: print a clean, user-facing `/codex-results` summary from the latest or specified Codex run.
- `release_workflow.py`: prepare changelog/release preview and optionally trigger release-please with configurable summarizer backend and bump strategy (`auto`, `patch`, `minor`, `major`); supports `--skip-prepare` for dispatch-only runs after an earlier preview/prep pass, and blocks dispatch when tracked files changed during prepare unless `--allow-dirty-dispatch` is set.
- `changelog_activity.py`: run pre-release changelog activity, including release-history rebuild (`CHANGELOG.md`), unreleased changelog preview (`dist/CHANGELOG.preview.md`), and unreleased release-notes preview (`dist/RELEASE_NOTES.preview.md`).

One-off migration and agent-generated maintenance scripts were removed to keep this directory focused on repeatable workflows.

Configuration files:
- `docs/changelog/changelog-config.json`: changelog + release-notes summarization runtime; includes `common` settings plus per-backend sections (`codex`, `claude_cli`, `intelligent`).
- `scripts/delegation-config.json`: Claude/Codex delegation defaults used by `claude_run_plan.py`.
