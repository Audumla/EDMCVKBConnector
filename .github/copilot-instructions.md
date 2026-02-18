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
