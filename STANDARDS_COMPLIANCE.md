# EDMC Plugin Standards Compliance

This document certifies that EDMCVKBConnector complies with all standards as defined in the [EDMC Plugin Browser Standards](https://github.com/EDCD/EDMC-Plugin-Registry/blob/main/docs/STANDARDS.md).

## Versioning ✅

**Status**: Compliant

The plugin uses semantic versioning compatible with the format `MAJOR.MINOR.PATCH` (e.g., 0.1.0).

- **VERSION constant**: Defined in `load.py` as `VERSION = "0.1.0"`
- **__version__ dunder**: Defined in `src/edmcvkbconnector/__init__.py` as `__version__ = "0.1.0"`
- **Standard**: Follows [Semantic Versioning](https://semver.org/) specification

## Compatibility ✅

**Status**: Compliant

The plugin is responsible for maintaining compatibility with recent versions of EDMC and will be updated when EDMC adds or removes functionality.

- **Target EDMC Version**: 5.0 or higher
- **Entry Point**: Uses `plugin_start3()` for EDMC 5.0+ compatibility
- **Maintenance**: Plugin authors commit to updating on timely basis when EDMC changes

See `load.py` for minimum version specification in module docstring.

## Licensing ✅

**Status**: Compliant

The plugin is licensed under the MIT License, which is fully compatible with GNU GPL v2+ as required by EDMC's GPL v2 or later license.

- **License**: MIT
- **License File**: [LICENSE](../LICENSE) (included in repository)
- **SPDX Identifier**: `MIT`
- **GPL Compatibility**: MIT is compatible with GPL v2+ (MIT permits redistribution under compatible licenses)

## Respect for the Ecosystem ✅

**Status**: Compliant

The plugin is designed as a good steward of the Elite: Dangerous community's resources:

- **Plugin Name**: Descriptive and specific ("EDMC VKB Connector" clearly states purpose and target hardware)
- **No Namespace Manipulation**: Does not use tricks like prefixing with numbers or special characters
- **No Malicious Content**: Plugin contains no malicious functionality or content
- **EULA Compliance**: Does not violate Frontier's Elite Dangerous EULA
- **Resource Respectful**: Uses only direct TCP/IP communication to user's own hardware, no scraping of community resources

## Least Privilege ✅

**Status**: Compliant

The plugin requests only the necessary permissions and dependencies:

- **Dependencies**: Uses only Python 3.8+ standard library
  - `socket`: For TCP/IP communication
  - `threading`: For background reconnection management
  - `json`: For event serialization
  - `logging`: For logging
  - `pathlib`: For file path handling
  - `time`: For timeout management
  - `typing`: For type hints

- **No External Packages**: Zero external dependencies (pydantic was optional in requirements.txt but not used)
- **System Privileges**: Requests only network access to user-specified host/port
- **No Bundled Content**: No unnecessary files or resources included

## Coding Standards ✅

**Status**: Compliant

Code is written to a high standard with readability, documentation, and best practices:

### Code Style
- **PEP 8 Compliance**: Code follows Python Enhancement Proposal 8 style guidelines
- **Formatting**: Consistent indentation, spacing, and naming conventions
- **Type Hints**: Comprehensive type annotations throughout (Python 3.8+)

### Documentation
- **Module Docstrings**: All modules have descriptive docstrings
- **Function Docstrings**: All public functions include docstring with purpose, args, and return value
- **Class Docstrings**: All classes documented with behavior and usage
- **Inline Comments**: Clarifying comments for complex logic
- **README**: Comprehensive README with installation, configuration, and usage

### Code Quality
- **Error Handling**: Proper exception handling with specific exception types
- **Thread Safety**: Uses locks and thread-safe primitives for concurrent operations
- **Resource Management**: Context managers used appropriately (e.g., socket cleanup)
- **Logging**: Appropriate logging levels (debug, info, warning, error)

### Structure
- **Modularity**: Code organized into logical modules
  - `config.py`: Configuration management
  - `vkb_client.py`: TCP/IP socket client
  - `event_handler.py`: Event processing
  - `load.py`: EDMC plugin entry point
- **Single Responsibility**: Each class/function has a clear purpose
- **Reusability**: Components designed to be testable and reusable

## Registry Information

For submission to the EDMC Plugin Registry, see [PLUGIN_REGISTRY.py](../PLUGIN_REGISTRY.py) for the registry metadata.

### Required Fields
- ✅ `pluginName`: "EDMC VKB Connector"
- ✅ `pluginVer`: "0.1.0"
- ✅ `autoUpdateEnabled`: False (not yet available in EDMC)
- ✅ `autoInstallEnabled`: False (not yet available in EDMC)
- ✅ `pluginAuthors`: ["EDMC VKB Connector Contributors"]
- ✅ `pluginMainLink`: Project repository URL
- ✅ `pluginLastUpdate`: Update date
- ✅ `pluginDirName`: "EDMCVKBConnector"
- ✅ `pluginCategory`: ["Utility"]
- ✅ `pluginDesc`: Clear description of plugin purpose
- ✅ `pluginLastTestedEDMC`: "5.13.0"
- ✅ `pluginLicense`: "MIT"

### Recommended Fields
- ⏳ `pluginHash`: SHA256 hash of release archive (add when creating releases)
- ⏳ `pluginZip`: URL to release archive (add when creating releases)

### Optional Fields
- ✅ `pluginRequirements`: Empty list (no external dependencies)
- ⏳ `pluginIcon`: Icon URL (optional, can be added later)
- ⏳ `pluginVT`: VirusTotal link (optional, can be added later)

## Summary

EDMCVKBConnector fully meets all EDMC Plugin Browser Standards:

| Standard | Status |
|----------|--------|
| Versioning | ✅ Compliant |
| Compatibility | ✅ Compliant |
| Licensing | ✅ Compliant |
| Ecosystem Respect | ✅ Compliant |
| Least Privilege | ✅ Compliant |
| Coding Standards | ✅ Compliant |

The plugin is ready for submission to the EDMC Plugin Registry.

---

*Last Updated: 2025-02-10*
*EDMC Compatibility: 5.0+*
