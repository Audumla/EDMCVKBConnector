# Provider Fragments

Optional per-provider fragments can be added here to reduce merge conflicts when multiple agents edit provider settings in parallel.

Each `*.json` file is merged into `delegation-config.json` at load time.

Schema:

```json
{
  "name": "provider-name",
  "provider": {
    "provider_type": "cli",
    "bin": "provider-bin",
    "available_models": ["model-a"],
    "usage": {
      "quick_command": ["{bin}", "stats"],
      "quick_parser": "version",
      "quick_timeout_sec": 10,
      "detailed_command": ["{bin}", "stats"],
      "timeout_sec": 30
    }
  },
  "planner": {
    "enabled": true,
    "test_enabled": false,
    "model": "model-a",
    "thinking_budget": "none"
  },
  "executor": {
    "enabled": true,
    "test_enabled": false,
    "model": "model-a",
    "runner": "runners/run_openai_api_plan.py",
    "runner_args": ["--base-url", "https://api.openai.com/v1", "--api-key-env", "OPENAI_API_KEY"]
  }
}
```

Use `*.json.example` for templates that should not be auto-loaded.
