# EDMCVKBConnector - Copilot Instructions

Python extension for Elite Dangerous Market Connector (EDMC) that forwards game events to VKB HOTAS/HOSAS hardware via TCP/IP socket connection.

## Project Setup Progress

- [x] Verify copilot-instructions.md exists
- [x] Project requirements: Python EDMC extension with TCP/IP socket client for VKB hardware
- [ ] Scaffold the project
- [ ] Customize for VKB connector implementation
- [ ] Install required dependencies
- [ ] Compile & verify no errors
- [ ] Create run tasks
- [ ] Documentation complete

## Project Details

- **Language:** Python 3.8+
- **Type:** EDMC Plugin/Extension
- **Purpose:** Forward Elite Dangerous game events to VKB hardware via TCP/IP
- **Key Features:**
  - EDMC event listener integration
  - TCP/IP socket client for VKB communication
  - Event forwarding and serialization
  - Configuration management

## Agent Workspace Policy

All GitHub Copilot execution artifacts must stay under `agent_artifacts/copilot/`.

- Reports: `agent_artifacts/copilot/reports/`
- Temporary scripts and scratch files: `agent_artifacts/copilot/temp/`

Do not write Copilot-generated reports or temp files anywhere else in this repository.

## Changelog Policy

### At the START of every session

Read `CHANGELOG.json` (repo root) to understand what every agent has already done. Use it to avoid duplicating work and to understand the current state of the codebase.

### At the END of every session

Record what was done by updating two files:

### 1. `CHANGELOG.json` (repo root)

Append a new JSON object to the array:

```json
{
  "id": "CHG-NNN",
  "plugin_version": "<read from src/edmcruleengine/version.py>",
  "date": "<YYYY-MM-DD>",
  "agent": "copilot",
  "summary_tags": ["<tag1>", "<tag2>"],
  "summary": "<one sentence>",
  "details": [
    "<bullet 1>",
    "<bullet 2>"
  ]
}
```

Increment `NNN` from the last entry in the file (e.g. if last is CHG-003, use CHG-004).

### 2. `CHANGELOG.md`

- Insert a new row at the **top** of the summary table (below the header).
- Insert a new `### CHG-NNN` detail section **above** the first existing detail section.

### Approved Summary Tags

Use one or more of these exact strings:

`Bug Fix` · `New Feature` · `Code Refactoring` · `Configuration Cleanup` ·
`Documentation Update` · `Test Update` · `Dependency Update` ·
`Performance Improvement` · `UI Improvement` · `Build / Packaging`
