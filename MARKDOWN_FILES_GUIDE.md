# Markdown Files Guide

A comprehensive index of all documentation in the Human Hunter project, organized by topic to help you find what you need quickly.

## Quick Reference

| What You're Looking For | Go To |
|-------------------------|-------|
| First-time setup | [START_HERE.md](START_HERE.md), [markdowns/QUICK_START.md](markdowns/QUICK_START.md) |
| Complete project tutorial | [TUTORIAL.md](TUTORIAL.md) |
| Environment variables | [ENVIRONMENT_REFERENCE.md](ENVIRONMENT_REFERENCE.md), [env.example](env.example) |
| System architecture | [markdowns/SYSTEM_ARCHITECTURE.md](markdowns/SYSTEM_ARCHITECTURE.md) |
| Game rules and modes | [markdowns/RULES.md](markdowns/RULES.md) |
| Gem economy and rewards | [markdowns/GEM_ECONOMY_IMPLEMENTATION.md](markdowns/GEM_ECONOMY_IMPLEMENTATION.md) |
| MTurk integration | [MTURK_SETUP.md](MTURK_SETUP.md), [markdowns/MTURK_WORKFLOW.md](markdowns/MTURK_WORKFLOW.md) |
| WebSocket implementation | [markdowns/WEBSOCKET_IMPLEMENTATION.md](markdowns/WEBSOCKET_IMPLEMENTATION.md) |
| Deployment guide | [DEPLOYMENT_GUIDE_NGROK_NETLIFY.md](DEPLOYMENT_GUIDE_NGROK_NETLIFY.md), [markdowns/DEPLOYMENT.md](markdowns/DEPLOYMENT.md) |
| Database migration | [markdowns/SQLITE_TO_POSTGRESQL.md](markdowns/SQLITE_TO_POSTGRESQL.md) |
| Security checklist | [markdowns/PRODUCTION_DEPLOYMENT_SECURITY_CHECKLIST.md](markdowns/PRODUCTION_DEPLOYMENT_SECURITY_CHECKLIST.md) |
| Developer guide | [markdowns/DEVELOPER_GUIDE.md](markdowns/DEVELOPER_GUIDE.md) |
| Testing guide | [markdowns/TESTING_GUIDE.md](markdowns/TESTING_GUIDE.md) |
| AI delay system | [backend/DELAY_SYSTEM.md](backend/DELAY_SYSTEM.md) |

---

## 1. Getting Started

These documents help you set up and run the project for the first time.

| Document | Description |
|----------|-------------|
| [README.md](README.md) | Project overview, quick start commands, feature summary, and architecture diagram. The main entry point for understanding the project. |
| [START_HERE.md](START_HERE.md) | Step-by-step setup guide with prerequisites, common troubleshooting tips, and verification steps for your local development environment. |
| [TUTORIAL.md](TUTORIAL.md) | Comprehensive project tutorial covering architecture, codebase walkthrough, core concepts, key features, and deployment. The most complete learning resource for new developers. |
| [markdowns/QUICK_START.md](markdowns/QUICK_START.md) | Minimal setup instructions to get the backend and frontend running quickly. Includes environment configuration examples. |
| [ENVIRONMENT_REFERENCE.md](ENVIRONMENT_REFERENCE.md) | Complete reference for all environment variables including API keys, database configuration, game settings, JWT secrets, and MTurk configuration. |
| [env.example](env.example) | Template `.env` file with all configurable options and their default values. Copy this to create your own `.env` file. |

---

## 2. Architecture & Design

These documents explain how the system is built and how components interact.

| Document | Description |
|----------|-------------|
| [markdowns/SYSTEM_ARCHITECTURE.md](markdowns/SYSTEM_ARCHITECTURE.md) | Detailed system architecture with ASCII diagrams showing the React frontend, FastAPI backend, LangGraph AI layer, and database. Covers data flows, API endpoints, WebSocket communication, and room management. |
| [markdowns/WEBSOCKET_IMPLEMENTATION.md](markdowns/WEBSOCKET_IMPLEMENTATION.md) | WebSocket protocol documentation for real-time game updates. Describes the custom `useWebSocket` React hook, message types (phase, timer_sync, message, typing, vote, etc.), and reconnection handling. |
| [markdowns/DEVELOPER_GUIDE.md](markdowns/DEVELOPER_GUIDE.md) | LangGraph multi-agent development patterns including state-driven architecture, graph nodes, how to add new AI behaviors, and best practices for working with the game state. |

---

## 3. Game Features

These documents explain the game mechanics and feature implementations.

| Document | Description |
|----------|-------------|
| [markdowns/RULES.md](markdowns/RULES.md) | Complete game rules covering single-human mode (1 human vs AI agents) and multi-human mode (2+ humans competing). Explains objectives, voting mechanics, winning conditions, and gem rewards for each mode. |
| [markdowns/GEM_ECONOMY_IMPLEMENTATION.md](markdowns/GEM_ECONOMY_IMPLEMENTATION.md) | Full gem system guide explaining how players earn gems (single-human: 50 gems, multi-human: 100 base + stakes), the stakes system mechanics, winner determination, and how gems are calculated and distributed. |
| [markdowns/REDEMPTION_CODE_SYSTEM.md](markdowns/REDEMPTION_CODE_SYSTEM.md) | Technical documentation for the redemption code system used in gem cashouts. Covers code generation, validation, and the cashout confirmation flow. |

---

## 4. MTurk Integration & Payments

These documents cover the Amazon Mechanical Turk integration for real-money payments.

| Document | Description |
|----------|-------------|
| [MTURK_SETUP.md](MTURK_SETUP.md) | Complete MTurk integration guide covering the gem-based economy overview, AWS credentials setup, worker-specific HIT configuration, cashout workflow, and troubleshooting common issues. |
| [markdowns/MTURK_WORKFLOW.md](markdowns/MTURK_WORKFLOW.md) | Detailed MTurk workflow documentation including HIT creation, qualification assignment, bonus payment processing, and the per-transaction HIT service architecture. |

---

## 5. Deployment & Operations

These documents help you deploy and maintain the application in production.

| Document | Description |
|----------|-------------|
| [DEPLOYMENT_GUIDE_NGROK_NETLIFY.md](DEPLOYMENT_GUIDE_NGROK_NETLIFY.md) | Beginner-friendly deployment guide using ngrok for backend tunneling and Netlify for frontend hosting. Includes step-by-step instructions, diagrams, and troubleshooting tips. |
| [markdowns/DEPLOYMENT.md](markdowns/DEPLOYMENT.md) | Alternative deployment strategies including different hosting options, production configuration, and environment setup for various cloud providers. |
| [markdowns/TUNNELING_OPTIONS.md](markdowns/TUNNELING_OPTIONS.md) | Comparison of tunneling services (ngrok, Cloudflare Tunnel, localtunnel, etc.) for exposing your local backend to the internet. |
| [markdowns/SQLITE_TO_POSTGRESQL.md](markdowns/SQLITE_TO_POSTGRESQL.md) | Step-by-step migration guide for moving from SQLite (development) to PostgreSQL (production). Covers Alembic migrations, connection pooling, and data migration strategies. |
| [markdowns/PRODUCTION_DEPLOYMENT_SECURITY_CHECKLIST.md](markdowns/PRODUCTION_DEPLOYMENT_SECURITY_CHECKLIST.md) | Security checklist for production deployment including JWT secret rotation, CORS configuration, HTTPS enforcement, rate limiting, and input validation. |

---

## 6. Testing & Quality Assurance

These documents help you test the application and ensure quality.

| Document | Description |
|----------|-------------|
| [markdowns/TESTING_GUIDE.md](markdowns/TESTING_GUIDE.md) | Testing guide covering test setup, test cases for room leave system, multi-player scenarios, and how to simulate different user sessions. |
| [backend/tests/README.md](backend/tests/README.md) | Backend test suite documentation including how to run tests, test file organization, and coverage requirements. |
| [backend/tests/MANUAL_PENETRATION_TESTING.md](backend/tests/MANUAL_PENETRATION_TESTING.md) | Manual security testing guide with penetration testing procedures for authentication, authorization, and API security validation. |

---

## 7. Backend-Specific Documentation

These documents are located in the `backend/` directory and cover backend-specific features.

| Document | Description |
|----------|-------------|
| [backend/DELAY_SYSTEM.md](backend/DELAY_SYSTEM.md) | Comprehensive documentation of the AI agent delay system. Explains the hybrid approach combining statistical rigor (Normal and Gamma distributions) with UX realism (chunked typing behavior). Includes the mathematical model and tuning parameters. |
| [backend/DELAY_QUICKSTART.md](backend/DELAY_QUICKSTART.md) | Quick start guide for understanding and modifying the AI delay system. Provides practical examples and common customization scenarios. |
| [backend/DELAY_VISUAL_GUIDE.md](backend/DELAY_VISUAL_GUIDE.md) | Visual diagrams and examples showing how the delay system works in practice, including timing breakdowns and comparison with human typing patterns. |

---

## 8. Archived Documentation

Historical documentation is preserved in `markdowns/archive/` for reference. These files document past implementations, bug fixes, and decisions.

```
markdowns/archive/
├── bugfixes/        # Bug fix summaries and resolutions (~60 files)
│                    # Examples: CORS_FIX_VOTING.md, TIMER_SYNC_FIX.md
├── implementations/ # Feature implementation notes (~39 files)
│                    # Examples: GEM_STAKES_IMPLEMENTATION_SUMMARY.md, SECURITY_AUDIT_SUMMARY.md
└── misc/            # Other historical documentation (~90 files)
                     # Examples: ENV_LOADING_GUIDE.md, API_KEY_ROUND_ROBIN.md
```

These files are not actively maintained but provide valuable historical context for understanding why certain decisions were made or how specific bugs were resolved.

---

## 9. Other Files

| File | Location | Description |
|------|----------|-------------|
| [frontend/README.md](frontend/README.md) | `frontend/` | Frontend-specific documentation including React component structure and build instructions. |
| [markdowns/README.md](markdowns/README.md) | `markdowns/` | Index file for the markdowns directory with quick links to essential documentation. |
| [LICENSE](LICENSE) | Root | Project license file. |

---

## Documentation by Role

### For New Developers
1. Start with [TUTORIAL.md](TUTORIAL.md) for a complete project overview
2. Set up your environment using [START_HERE.md](START_HERE.md)
3. Understand the architecture via [markdowns/SYSTEM_ARCHITECTURE.md](markdowns/SYSTEM_ARCHITECTURE.md)
4. Learn LangGraph patterns in [markdowns/DEVELOPER_GUIDE.md](markdowns/DEVELOPER_GUIDE.md)

### For DevOps/Deployment
1. Follow [DEPLOYMENT_GUIDE_NGROK_NETLIFY.md](DEPLOYMENT_GUIDE_NGROK_NETLIFY.md) for initial deployment
2. Review [markdowns/PRODUCTION_DEPLOYMENT_SECURITY_CHECKLIST.md](markdowns/PRODUCTION_DEPLOYMENT_SECURITY_CHECKLIST.md)
3. Migrate database using [markdowns/SQLITE_TO_POSTGRESQL.md](markdowns/SQLITE_TO_POSTGRESQL.md)
4. Configure environment with [ENVIRONMENT_REFERENCE.md](ENVIRONMENT_REFERENCE.md)

### For Game Designers/Researchers
1. Understand game mechanics in [markdowns/RULES.md](markdowns/RULES.md)
2. Learn the gem economy in [markdowns/GEM_ECONOMY_IMPLEMENTATION.md](markdowns/GEM_ECONOMY_IMPLEMENTATION.md)
3. Set up payments with [MTURK_SETUP.md](MTURK_SETUP.md)
4. Also look up the Gems info page in the app

### For Frontend Developers
1. Review [markdowns/WEBSOCKET_IMPLEMENTATION.md](markdowns/WEBSOCKET_IMPLEMENTATION.md) for real-time updates
2. Understand the game flow in [markdowns/RULES.md](markdowns/RULES.md)
3. Check [CODE_EXPLANATION.md](CODE_EXPLANATION.md) for frontend file descriptions

### For AI/ML Developers
1. Study [markdowns/DEVELOPER_GUIDE.md](markdowns/DEVELOPER_GUIDE.md) for LangGraph architecture
2. Review [backend/DELAY_SYSTEM.md](backend/DELAY_SYSTEM.md) for humanizing AI behavior
3. Check [ENVIRONMENT_REFERENCE.md](ENVIRONMENT_REFERENCE.md) for AI model configuration

