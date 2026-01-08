# Documentation Index

This folder contains technical documentation for the Human Hunter project.

## Essential Documentation

| Document | Description |
|----------|-------------|
| [SYSTEM_ARCHITECTURE.md](SYSTEM_ARCHITECTURE.md) | Detailed system architecture, data flow diagrams, component interactions |
| [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) | LangGraph development patterns, adding features, testing strategies |
| [DEPLOYMENT.md](DEPLOYMENT.md) | Deployment guide: local backend + cloud frontend setup |
| [QUICK_START.md](QUICK_START.md) | Quick start for running the project |
| [TESTING_GUIDE.md](TESTING_GUIDE.md) | Testing strategies and how to run tests |

## Feature Documentation

| Document | Description |
|----------|-------------|
| [GEM_ECONOMY_IMPLEMENTATION.md](GEM_ECONOMY_IMPLEMENTATION.md) | Complete gem system guide: earning (single/multi-human), stakes, rewards, cashouts |
| [REDEMPTION_CODE_SYSTEM.md](REDEMPTION_CODE_SYSTEM.md) | Redemption codes for gem cashouts |
| [MTURK_WORKFLOW.md](MTURK_WORKFLOW.md) | Complete MTurk integration workflow |
| [WEBSOCKET_IMPLEMENTATION.md](WEBSOCKET_IMPLEMENTATION.md) | WebSocket protocol and message types |

## Operations & Configuration

| Document | Description |
|----------|-------------|
| [SQLITE_TO_POSTGRESQL.md](SQLITE_TO_POSTGRESQL.md) | Database migration guide for production |
| [PRODUCTION_DEPLOYMENT_SECURITY_CHECKLIST.md](PRODUCTION_DEPLOYMENT_SECURITY_CHECKLIST.md) | Security checklist for production deployment |
| [TUNNELING_OPTIONS.md](TUNNELING_OPTIONS.md) | Options for exposing local backend (ngrok, etc.) |
| [RULES.md](RULES.md) | Game rules, modes (single/multi-human), voting mechanics, gem rewards |

## Main Project Documentation

For getting started and project overview, see the root directory:

- **[../TUTORIAL.md](../TUTORIAL.md)** - Comprehensive project tutorial (start here!)
- **[../README.md](../README.md)** - Project overview
- **[../START_HERE.md](../START_HERE.md)** - Quick start guide
- **[../MTURK_SETUP.md](../MTURK_SETUP.md)** - MTurk integration and gem cashout system setup
- **[../ENVIRONMENT_REFERENCE.md](../ENVIRONMENT_REFERENCE.md)** - Complete environment variable reference with correct defaults
- **[../env.example](../env.example)** - Environment configuration template

## Archived Documentation

Historical documentation (bug fixes, implementation notes, etc.) has been moved to `archive/`:

```
archive/
├── bugfixes/        # Bug fix summaries and resolutions (60 files)
├── implementations/ # Feature implementation notes (39 files)
└── misc/            # Other historical documentation (90 files)
```

These files are preserved for reference but are not actively maintained.

