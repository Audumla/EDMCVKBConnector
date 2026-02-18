# Development Scripts

Maintained scripts in this directory:

- `bootstrap_dev_env.py`: bootstrap EDMC dev environment and link this plugin.
- `run_edmc_from_dev.py`: run EDMC from a local dev checkout.
- `package_plugin.py`: create release ZIP under `dist/`.
- `signal_catalog_editor.py`: interactive editor for `signals_catalog.json`.
- `validate_signal_catalog.py`: validate catalog structure/operators/event references.
- `verify_catalog_coverage.py`: check catalog coverage against known ED events.
- `dev_paths.py`: shared path resolution used by dev scripts.

One-off migration and agent-generated maintenance scripts were removed to keep this directory focused on repeatable workflows.
