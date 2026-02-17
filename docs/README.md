# EDMCVKBConnector Documentation

Complete documentation for the EDMCVKBConnector plugin.

## Getting Started

New to the plugin? Start here:

1. **[Installation Guide](../INSTALLATION.md)** - Install and configure the plugin
2. **[Rule Editor Guide](RULE_EDITOR_GUIDE.md)** - Create rules using the visual editor
3. **[Signals Reference](../SIGNALS_CATALOG_REFERENCE.md)** - Browse all 195+ available signals

## User Documentation

### Installation & Setup
- **[Installation Guide](../INSTALLATION.md)** - Complete installation instructions for users
- **[VKB-Link Setup](REAL_SERVER_SETUP.md)** - Configuring VKB-Link to work with the plugin

### Creating Rules
- **[Rule Editor Guide](RULE_EDITOR_GUIDE.md)** - Using the visual rule editor (recommended)
- **[Rules Schema Reference](RULES_SCHEMA.md)** - Technical reference for manual JSON editing
- **[Signals Catalog](../SIGNALS_CATALOG_REFERENCE.md)** - Complete list of all signals and their sources

## Developer Documentation

Contributing or customizing the plugin? See these guides:

- **[Development Guide](../DEVELOPMENT.md)** - Setting up dev environment and contributing
- **[Architecture](ARCHITECTURE.md)** - How the plugin works internally
- **[Deployment Guide](DEPLOYMENT.md)** - Packaging and deploying the plugin
- **[Protocol Implementation](PROTOCOL_IMPLEMENTATION.md)** - VKB-Link protocol details

## Quick Reference

### For Users
```
Installation → Configuration → Create Rules → Test
     ↓              ↓              ↓            ↓
 INSTALL.md    VKB-Link     Rule Editor    In-game
               TCP setup    or JSON edit    testing
```

### For Developers
```
Bootstrap → Development → Testing → Package → Release
     ↓           ↓           ↓         ↓         ↓
 setup.py   run EDMC    pytest    package   GitHub
            from dev              script    Release
```

## Documentation Structure

```
EDMCVKBConnector/
├── README.md                     # Project overview
├── INSTALLATION.md               # User installation guide
├── DEVELOPMENT.md                # Developer setup guide
├── SIGNALS_CATALOG_REFERENCE.md # Complete signals reference
└── docs/
    ├── README.md                 # This file
    ├── RULE_EDITOR_GUIDE.md     # Visual rule editor guide
    ├── RULES_SCHEMA.md          # Technical schema reference
    ├── REAL_SERVER_SETUP.md     # VKB-Link configuration
    ├── ARCHITECTURE.md          # Internal architecture
    ├── DEPLOYMENT.md            # Deployment guide
    └── PROTOCOL_IMPLEMENTATION.md # VKB protocol details
```

## File Purposes

### Root Documentation
- **README.md**: First stop for anyone visiting the repository
- **INSTALLATION.md**: Complete installation and setup walkthrough
- **DEVELOPMENT.md**: Development environment setup and workflow
- **SIGNALS_CATALOG_REFERENCE.md**: Comprehensive signals reference (195+ signals)

### docs/ Folder
- **RULE_EDITOR_GUIDE.md**: How to use the visual rule editor UI
- **RULES_SCHEMA.md**: Technical JSON schema for manual rule editing
- **REAL_SERVER_SETUP.md**: VKB-Link TCP server configuration
- **ARCHITECTURE.md**: Plugin architecture and component overview
- **DEPLOYMENT.md**: Packaging and deployment instructions
- **PROTOCOL_IMPLEMENTATION.md**: VKB-Link protocol specification

## Need Help?

- **Installation Issues**: See [INSTALLATION.md](../INSTALLATION.md) troubleshooting section
- **Rule Creation**: Check [Rule Editor Guide](RULE_EDITOR_GUIDE.md) or [Rules Schema](RULES_SCHEMA.md)
- **Signal Questions**: Search [Signals Reference](../SIGNALS_CATALOG_REFERENCE.md)
- **Development Help**: Read [Development Guide](../DEVELOPMENT.md)
- **Bug Reports**: [GitHub Issues](https://github.com/Audumla/EDMCVKBConnector/issues)

## Contributing to Documentation

Found an error or want to improve the docs?

1. Documentation files are in Markdown format
2. Follow the existing style and structure
3. Update cross-references if adding new sections
4. Test all code examples before submitting
5. Submit a pull request with your changes

See [DEVELOPMENT.md](../DEVELOPMENT.md) for contribution guidelines.
