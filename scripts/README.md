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

One-off migration and agent-generated maintenance scripts were removed to keep this directory focused on repeatable workflows.
