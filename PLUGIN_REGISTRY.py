"""
EDMC Plugin Registry Metadata

This file documents the plugin registration information for EDMC Plugin Registry listing.
When submitting to the official registry, this information will be used.

Reference: https://github.com/EDCD/EDMC-Plugin-Registry
"""

PLUGIN_REGISTRY_INFO = {
    # Required Fields
    "pluginName": "EDMC VKB Connector",
    "pluginVer": "0.1.0",
    "autoUpdateEnabled": False,  # Not yet supported by EDMC
    "autoInstallEnabled": False,  # Not yet supported by EDMC
    "pluginAuthors": [
        "EDMC VKB Connector Contributors"
    ],
    "pluginMainLink": "https://github.com/Audumla/EDMCVKBConnector",
    "pluginLastUpdate": "2025-02-10",
    "pluginDirName": "EDMCVKBConnector",
    "pluginCategory": [
        "Utility"
    ],
    "pluginDesc": "Forward Elite Dangerous game events to VKB HOTAS/HOSAS hardware via TCP/IP socket connection",
    "pluginLastTestedEDMC": "5.13.0",
    "pluginLicense": "MIT",
    
    # Recommended Fields
    "pluginHash": None,  # SHA256 hash of release archive - fill when creating release
    "pluginZip": None,  # URL to release archive - fill when creating release
    
    # Optional Fields
    "pluginRequirements": [],  # No external Python dependencies required
    "pluginIcon": None,  # Icon URL if available
    "pluginVT": None,  # VirusTotal link if available
}

# Standards Compliance Checklist
STANDARDS_COMPLIANCE = {
    "versioning": {
        "compliant": True,
        "notes": "Uses semantic versioning (0.1.0) as required by EDMC standards"
    },
    "compatibility": {
        "compliant": True,
        "notes": "Targets EDMC 5.0+ with proper plugin_start3 entry point. "
                "Responsible for maintaining compatibility with newer EDMC versions"
    },
    "licensing": {
        "compliant": True,
        "notes": "Licensed under MIT, which is GPL v2+ compatible as required"
    },
    "ecosystem_respect": {
        "compliant": True,
        "notes": "Plugin name is descriptive and specific. Uses no namespacing tricks. "
                "Respects Elite Dangerous community EULA"
    },
    "least_privilege": {
        "compliant": True,
        "notes": "Uses only standard library modules (socket, threading, json, logging). "
                "Requests only network access for TCP/IP communication"
    },
    "coding_standards": {
        "compliant": True,
        "notes": "Code follows PEP8 standards, includes comprehensive docstrings, "
                "uses type hints, and is well-documented"
    },
}
