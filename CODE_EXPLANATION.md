# Code Explanation Guide

A comprehensive guide explaining every code file in the Human Hunter project. Each entry provides a brief paragraph describing the file's purpose, key responsibilities, and relationships to other files.

---

## Table of Contents

1. [Backend Core](#1-backend-core)
2. [Backend Routers](#2-backend-routers)
3. [Backend Services](#3-backend-services)
4. [Backend MTurk & Payment](#4-backend-mturk--payment)
5. [Backend MTurk Utility Scripts](#5-backend-mturk-utility-scripts)
6. [Backend Other Utilities](#6-backend-other-utilities)
7. [Frontend Core](#7-frontend-core)
8. [Frontend Pages](#8-frontend-pages)
9. [Frontend Components](#9-frontend-components)
10. [Frontend Contexts](#10-frontend-contexts)
11. [Frontend Hooks](#11-frontend-hooks)
12. [Frontend Services](#12-frontend-services)
13. [Frontend Utilities](#13-frontend-utilities)
14. [Root Scripts](#14-root-scripts)
15. [Configuration Files](#15-configuration-files)

---

## 1. Backend Core

### `backend/main.py`

The FastAPI application entry point that initializes the entire backend server. Configures CORS middleware with production-safe origin validation (prevents wildcard origins in production), applies global rate limiting middleware to protect API endpoints, and includes global exception handling to ensure CORS headers are included even in error responses. Imports and registers all routers (auth, wallet, sessions, admin, rooms, websocket, general), and sets up application lifecycle events that initialize the database, MTurk client, cashout monitor background task, and periodic room cleanup/health monitoring tasks on startup.

### `backend/config.py`

Central configuration module that loads all game settings from environment variables. Defines core game parameters including `NUM_AI_PLAYERS`, `DISCUSSION_TIME`, `VOTING_TIME`, and `ROUNDS_TO_WIN`. Configures AI model settings (provider, model name, temperature) supporting OpenAI, Anthropic, and Groq providers. Contains AI personality definitions in both English and Korean, personality-based imperfection profiles for humanizing AI behavior, discussion topic lists, and MTurk payment configuration (gems per dollar, minimum cashout, base pay). Also handles multi-API key support via comma-separated `OPENAI_API_KEYS`.

### `backend/database.py`

SQLAlchemy async database setup with models for all persistent data. Defines the `User` model (with authentication, gems balance, gamification stats, MTurk integration), `Session` model (game session records), `SessionPlayer` (player participation in sessions), `CashoutTransaction` (payment tracking), `RoomStake` (multi-human stakes), and `AIAgentUsage` (API cost tracking). Supports both SQLite (development) and PostgreSQL (production) with appropriate connection pooling. Includes database initialization (`init_db`) and cleanup functions, plus the `get_async_session` dependency for FastAPI routes.

### `backend/langgraph_game.py`

The core LangGraph-based AI game orchestration engine. Implements the `GameGraph` class that manages AI agent behavior during gameplay. Contains the LLM integration for generating AI chat messages with human-like typing patterns (chunk-based delivery, typos, corrections), AI voting logic, and agent decision-making about when to respond. Uses the hybrid delay system combining statistical distributions with chunked typing. Handles personality-driven response generation, conversation context, and proper phase checking to prevent messages being sent outside discussion phase. This is the brain of the AI agents.

### `backend/langgraph_state.py`

Defines the TypedDict schema for the game state used throughout the LangGraph system. Contains the `Phase` enum (DISCUSSION, VOTING, ELIMINATION, GAME_OVER), `PlayerInfo` structure (id, role, eliminated status, personality), `ChatMessage` structure, and the main `GameState` TypedDict. The game state includes room metadata, players list, chat history with annotated append behavior, topic, votes dictionary (supporting multi-vote for multi-human games), pending AI operations, and result fields. This schema is passed through all game nodes and updated atomically.

### `backend/global_state.py`

In-memory state management for real-time game rooms. Maintains the `rooms` dictionary storing all active game rooms with their state, WebSocket connections, tasks, and metadata. Also manages `room_locks` for preventing race conditions during concurrent AI operations. Contains the thread pool executor (60 workers) for running blocking AI operations without blocking the async event loop. Initializes the `api_key_manager` for round-robin API key distribution and tracks global `user_activity` for online user counting.

### `backend/auth.py`

Authentication and authorization module using JWT tokens and Argon2 password hashing. Provides password hashing/verification functions, JWT token creation with configurable expiration, and token verification logic. Implements FastAPI dependencies: `get_current_user` (requires valid auth), `get_current_user_optional` (allows anonymous), and `require_admin` (admin-only access). Includes MTurk worker auto-registration logic and user lookup functions. Validates JWT secret strength on startup with security warnings.

### `backend/schemas.py`

Pydantic models for API request/response validation. Defines `RegisterRequest`, `LoginRequest`, `LoginResponse`, `UserResponse`, `MTurkRegisterRequest`, and `SessionResponse`. These schemas ensure type safety and automatic documentation for FastAPI endpoints, validating incoming data and serializing responses.

### `backend/env_config.py`

Robust environment configuration loader with validation. Ensures environment variables are properly loaded from the project root `.env` file regardless of the current working directory. Validates critical configuration like `CASHOUT_HIT_ID` for MTurk integration. Provides `get_config_status()` function for health checking configuration completeness at startup.

### `backend/middleware_utils.py`

Rate limiting utilities and middleware components. Implements `SimpleRateLimiter` class for in-memory rate limiting with configurable max requests and time windows. Creates pre-configured rate limiters for different endpoint types: MTurk registration, login, registration, cashout, WebSocket connections, and general API calls. Includes `periodic_rate_limiter_cleanup()` background task to prevent memory leaks from accumulated timestamps.

### `backend/api_key_manager.py`

Thread-safe round-robin API key distribution for multiple OpenAI keys. The `APIKeyManager` class prevents rate limiting by distributing requests across multiple API keys when running with 100+ concurrent users. Tracks key assignments, maintains health status for each key, handles rate-limited and erroring keys, and provides statistics about key usage. Raises `APIKeyManagerError` for configuration issues.

### `backend/security_monitor.py`

Real-time security monitoring and alerting system. Defines `SecurityEventType` enum (failed login, rate limit violation, unusual cashout, etc.) and `SeverityLevel` enum. The `SecurityMonitor` class tracks security events in memory, aggregates patterns, and can trigger alerts for suspicious activity. Provides logging functions like `log_rate_limit_violation()`, `log_failed_login()`, and `log_unusual_cashout()` used throughout the codebase.

### `backend/gamification.py`

Gamification system for player engagement. Defines `Achievement` dataclass and the `ACHIEVEMENTS` list with milestones for games played, wins, streaks, and accuracy. Implements `calculate_level()` using exponential scaling, `points_for_next_level()`, `calculate_game_points()`, `check_achievements()`, and `update_streak()` functions. Also provides `get_motivational_message()` and `get_next_close_achievements()` for UI encouragement.

### `backend/pricing.py`

AI API cost tracking and calculation utilities. Provides functions to calculate token costs for different models (GPT-4, GPT-4o-mini, Claude, etc.), format costs for display, and track usage per session. Used by the admin dashboard to show AI infrastructure costs.

### `backend/earnings.py`

Earnings tier calculation for player progression. Defines earning tiers based on total gems earned and provides `get_earnings_tier()` function to determine player status levels for display in the dashboard.

---

## 2. Backend Routers

### `backend/routers/auth.py`

Authentication API endpoints. Implements `/api/auth/register` for new user registration with rate limiting and duplicate checking, `/api/auth/login` for password authentication returning JWT tokens, `/api/auth/me` for fetching current user info, and MTurk-specific endpoints for worker registration and auto-login. Uses security monitor to log failed login attempts and rate limit violations.

### `backend/routers/wallet.py`

Wallet and cashout API endpoints. Implements `/api/wallet/balance` for checking gem balance and MTurk profile completeness, `/api/wallet/cashout` for initiating cashouts with validation, `/api/wallet/check-cashout-ready` to verify HIT availability, `/api/wallet/transactions` for transaction history, and `/api/wallet/cashout/{id}/cancel` for canceling pending cashouts. Integrates with the V2 per-transaction HIT system.

### `backend/routers/sessions.py`

Session and dashboard API endpoints. Implements `/api/sessions` for listing game sessions (users see own, admins see all with filtering), `/api/sessions/{id}` for session detail with full player stats and message history, `/api/dashboard` for user dashboard statistics (level, achievements, earnings, recent games), and `/api/leaderboard` for public leaderboard data. Contains complex aggregation queries for gamification stats.

### `backend/routers/admin.py`

Admin-only API endpoints protected by `require_admin` dependency. Implements `/api/admin/dashboard` for admin statistics (session counts, pending payments, user count), `/api/admin/sessions` for full session list with payment status, `/api/admin/process-payment/{id}` for manual MTurk payment processing, and `/api/admin/cleanup-hits` for garbage collecting old MTurk HITs. Includes AI cost tracking display.

### `backend/routers/rooms.py`

Room management API endpoints (largest router). Implements `/api/rooms/create` for creating new game rooms with validation of stakes and player configuration, `/api/rooms/list` for listing available rooms with real-time player counts, `/api/rooms/{code}/info` for room details, `/api/rooms/{code}/join` for joining rooms with stake collection for multi-human games, `/api/rooms/{code}/leave` for leaving rooms with stake refunds, `/api/rooms/{code}/start` for starting games, message/vote submission endpoints, and heartbeat tracking. Contains significant game logic for phase transitions.

### `backend/routers/websocket.py`

WebSocket endpoint for real-time game connections. Implements `/ws/{room_code}/{player_id}` that accepts WebSocket connections, authenticates users via JWT token query parameter, handles rate limiting, and manages the connection lifecycle. Processes incoming messages (chat, typing indicators, votes, pings), triggers AI agent responses via `trigger_agent_decisions()`, and broadcasts state changes to connected clients. Handles WebSocket disconnection and cleanup.

### `backend/routers/general.py`

General utility endpoints. Implements `/config` for retrieving game configuration (AI players, timings), `/health` for health check with API key manager status, and `/api/lobby/online-users` for getting count of currently active users based on heartbeat tracking.

---

## 3. Backend Services

### `backend/services/game_coordinator.py`

Central game phase management service (re-exports from langgraph_game.py for organizational purposes). Orchestrates discussion and voting phases, manages timers with monotonic clock for accuracy, broadcasts phase changes and timer synchronization messages every 5 seconds, triggers AI agent decisions during quiet periods (proactive engagement), handles phase transitions atomically with locking, and processes voting completion including winner determination for both single-human and multi-human game modes.

### `backend/services/messaging.py`

WebSocket message broadcasting service. Implements `broadcast_to_room()` for sending messages to all connected clients in a room, with automatic cleanup of failed/stale connections. Also provides `process_broadcast_queue()` for handling batched messages from game state updates.

### `backend/services/room_management.py`

Room lifecycle management utilities. Implements `create_room()` for initializing room data structures with unique codes, `generate_room_code()` for alphanumeric room codes, player slot management functions (`get_assigned_humans()`, `sync_assigned_and_current_humans()`), `get_api_key_for_room()` for round-robin key assignment, heartbeat/activity tracking, and `periodic_room_cleanup()` / `monitor_room_health()` background tasks that clean up abandoned rooms and detect stuck states.

### `backend/services/stats_service.py`

Game statistics and rewards service. The largest service file containing `save_session_stats()` for persisting game results to database with full player breakdown, `calculate_game_rewards()` for computing gem rewards based on game type (single-human: 50 gems, multi-human: 100 base + stakes), stake distribution logic for winners/losers, achievement checking, streak updates, and AI usage cost tracking. Includes retry logic with exponential backoff for database operations.

### `backend/services/user_activity.py`

User online status tracking. Simple service with `update_user_activity()` to record last activity timestamp and `get_online_users_count()` to count users active within the threshold (90 seconds by default), with automatic cleanup of stale entries older than 5 minutes.

---

## 4. Backend MTurk & Payment

### `backend/mturk_api.py`

AWS Mechanical Turk API wrapper. Implements `MTurkClient` class that handles all MTurk operations: HIT creation, qualification management (creating worker-specific qualifications), assignment approval, bonus payments, and HIT status checking. Supports both sandbox and production environments with automatic endpoint switching. Provides `get_mturk_client()` singleton factory and `process_payment()` for automatic assignment approval and bonus payment.

### `backend/cashout_service.py`

Core cashout business logic. Implements `create_cashout_transaction()` for initializing cashout requests with redemption codes, `redeem_cashout_code()` for processing worker confirmations, `get_user_cashout_history()` for transaction history, `check_cashout_status()` for status lookup, and currency conversion utilities (`gems_to_usd()`, `usd_to_gems()`). Includes `generate_redemption_code()` for unique 64-character hex codes. Raises `CashoutError` for validation failures.

### `backend/cashout_endpoint_v2.py`

Modern cashout endpoint using per-transaction HITs. Replaces the old standing HIT approach with worker-specific HITs for each cashout. The `request_cashout_v2()` function validates worker ID and gem balance, creates a cashout transaction, then calls `create_worker_specific_hit()` to generate a private HIT visible only to the requesting worker. Returns HIT URL and instructions.

### `backend/per_transaction_hit_service.py`

Per-transaction HIT creation service. Implements `create_worker_specific_hit()` that creates a unique qualification for the worker, creates a HIT requiring that qualification (making it worker-exclusive), and stores the HIT ID in the transaction record. Solves the "No HITs available" problem by ensuring each cashout has its own HIT with MaxAssignments=1. Includes `get_cashout_instructions()` for user guidance.

### `backend/cashout_monitor.py`

Background service for monitoring cashout transactions. Periodically checks pending cashouts, verifies HIT status, updates transaction states, and can trigger auto-approval. Provides `start_cashout_monitor()` and `stop_cashout_monitor()` for lifecycle management.

### `backend/cashout_cancel_service.py`

Cashout cancellation service. Implements `cancel_cashout_transaction()` for canceling pending cashouts and refunding gems to user balance. Also provides `garbage_collect_old_hits()` for cleaning up expired HITs that were never completed.

### `backend/direct_bonus_service.py`

Alternative payment service using direct MTurk bonuses. Allows paying workers via bonus payments on existing assignments rather than creating new HITs. Useful for administrative payouts or correcting payment issues.

---

## 5. Backend MTurk Utility Scripts

These are standalone Python scripts for MTurk administration and debugging. Run them directly with `python backend/<script>.py`.

### `backend/check_mturk_balance.py`

Checks the available MTurk account balance. Useful for verifying AWS credentials are configured correctly and ensuring sufficient funds for payments.

### `backend/check_hit_ready.py`

Verifies that a HIT is properly configured and available for workers. Checks qualification requirements, assignment availability, and HIT status.

### `backend/check_hit_status.py`

Retrieves detailed status information about a specific HIT including creation date, expiration, assignments completed, and pending assignments.

### `backend/check_hit_group.py`

Lists all HITs in a HIT group (HITs with the same HITTypeId). Useful for understanding how many HITs share the same configuration.

### `backend/check_hit_qualification.py`

Checks qualification type details and which workers have been assigned specific qualifications. Used for debugging worker-specific HIT visibility.

### `backend/check_worker_id.py`

Validates a worker ID format and looks up worker information from MTurk. Useful for verifying worker IDs before processing payments.

### `backend/check_worker_assignments.py`

Lists all assignments (completed, pending, rejected) for a specific worker. Helpful for debugging payment issues.

### `backend/check_recent_cashouts.py`

Queries the database for recent cashout transactions and their status. Provides quick overview of payment activity.

### `backend/create_standing_hit.py`

Creates a standing HIT for the legacy cashout system (before V2). Standing HITs have high MaxAssignments and are reused across cashouts.

### `backend/delete_all_hits.py`

Bulk deletes all HITs in the current MTurk environment. Use with caution! Primarily for sandbox cleanup during development.

### `backend/cancel_old_hits.py`

Cancels HITs that have expired or been abandoned. Cleans up the MTurk environment from orphaned HITs.

### `backend/approve_all_assignments.py`

Bulk approves all pending assignments. Use for administrative cleanup when auto-approval failed.

### `backend/extend_hit_assignments.py`

Extends the number of available assignments on an existing HIT. Used with standing HITs that run out of assignments.

### `backend/fix_hit_assignments.py`

Diagnostic and repair script for HIT assignment issues. Attempts to fix common problems with assignment availability.

### `backend/return_my_hits.py`

Returns (gives up) assignments that were accepted but not completed. Used during testing to reset state.

### `backend/verify_hit_exists.py`

Confirms a HIT ID exists in MTurk and retrieves its current configuration.

### `backend/verify_hit_reward.py`

Verifies the reward amount configured for a HIT matches expected values.

### `backend/verify_payment_math.py`

Validates that gem-to-USD calculations are correct across the system. Ensures no rounding errors in payment amounts.

### `backend/verify_cashout_integrity.py`

Checks database integrity for cashout transactions, looking for orphaned records, inconsistent states, or missing relationships.

### `backend/find_hit_transaction.py`

Looks up which cashout transaction is associated with a specific HIT ID.

### `backend/diagnose_cashout_system.py`

Comprehensive diagnostic script that checks all aspects of the cashout system: credentials, database, HIT configuration, and common failure points.

### `backend/test_cashout_creation.py`

Integration test for cashout creation flow. Creates a test transaction and HIT to verify the system works end-to-end.

---

## 6. Backend Other Utilities

### `backend/completion_keys.py`

Game completion key generation for MTurk integration. Creates unique completion tokens that workers can submit to prove game completion.

### `backend/ai_legacy.py`

Legacy AI implementation before LangGraph migration. Kept for reference and potential fallback. Contains older response generation logic.

### `backend/game_legacy.py`

Legacy game loop implementation before the current architecture. Preserved for historical reference.

### `backend/migrate_to_gems.py`

Database migration script for converting from an older points/payment system to the gems-based economy.

### `backend/reset_transactional_data.py`

Development utility to reset transactional database tables (sessions, cashouts, stakes) while preserving user accounts. Use for testing with clean state.

### `backend/fix_gem_duplication.py`

Repair script for fixing duplicate gem awards that may have occurred due to race conditions in earlier versions.

### `backend/test_env_config.py`

Tests that environment configuration is loading correctly. Validates all required variables are present.

### `backend/check_env.py`

Quick environment variable checker that displays current configuration (with secrets partially masked).

### `backend/__init__.py`

Python package marker for the backend module. Empty file required for Python imports.

---

## 7. Frontend Core

### `frontend/src/App.jsx`

Main React application component with routing configuration. Wraps the app in provider hierarchy: `AuthProvider` → `LanguageProvider` → `GameProvider` → `Router`. Defines all routes including public routes (lobby, leaderboard, gems-info, login, game pages), protected routes requiring authentication (dashboard, profile, wallet, sessions), and admin routes (admin dashboard, analytics). Configures `react-hot-toast` for notifications.

### `frontend/src/main.jsx`

React application entry point. Imports global CSS, renders the App component into the DOM root element, and sets up React strict mode.

### `frontend/src/index.css`

Global CSS styles using Tailwind CSS. Contains Tailwind directives (`@tailwind base`, `@tailwind components`, `@tailwind utilities`) plus any custom global styles and CSS variable definitions.

---

## 8. Frontend Pages

### `frontend/src/pages/LobbyPage.jsx`

Main lobby interface showing available game rooms. Displays room cards with player counts, allows filtering/sorting, shows online user count via API polling, and provides room creation modal. Handles room joining with stake validation for multi-human games.

### `frontend/src/pages/JoinPage.jsx`

Intermediate page after selecting a room but before entering the waiting room. Handles player slot assignment, displays room configuration, and manages the join process including stake payment for multi-human games.

### `frontend/src/pages/WaitingPage.jsx`

Waiting room interface before game starts. Shows current players, room configuration, handles WebSocket connection for real-time updates, displays countdown when all players have joined, and provides leave button with confirmation for stake refund.

### `frontend/src/pages/GamePage.jsx`

Main game interface with real-time WebSocket integration. The most complex page component managing: game state (phase, timer, players, chat), WebSocket connection via `useWebSocket` hook, chat message display and submission, typing indicators, voting interface (adapts for single-human vs multi-human modes), phase timer with server synchronization, and game over screen with results.

### `frontend/src/pages/LoginPage.jsx`

Authentication page with login and registration forms. Handles form validation, API calls via `authAPI`, token storage, and redirect to dashboard on success. Supports MTurk auto-login via query parameters.

### `frontend/src/pages/DashboardPage.jsx`

User dashboard with gamification statistics. Displays level progress, gem balance, achievement progress, recent game history, earnings chart, and motivational messages. Fetches data from `/api/dashboard` endpoint.

### `frontend/src/pages/ProfilePage.jsx`

User profile management page. Allows updating MTurk worker ID, demographic information (required for cashouts), and displays account statistics. Handles form submission and validation.

### `frontend/src/pages/SessionDetailPage.jsx`

Detailed view of a completed game session. Shows full chat history with player identities revealed, voting results, gem rewards, and player performance breakdown. Accessed via `/sessions/:sessionId`.

### `frontend/src/pages/LeaderboardPage.jsx`

Public leaderboard showing top players. Displays rankings by level, total games, win rate, and gems earned. Uses pagination and filtering options.

### `frontend/src/pages/GemsInfoPage.jsx`

Educational page explaining the gem economy. Details how gems are earned in different game modes, the stakes system, cashout process, and conversion rate to USD.

### `frontend/src/pages/AdminPage.jsx`

Admin dashboard with system statistics. Shows session counts, payment status, user metrics, and active rooms. Provides controls for processing payments and system administration.

### `frontend/src/pages/AdminAnalyticsPage.jsx`

Advanced analytics for administrators. Displays charts and metrics about game activity, player engagement, AI costs, and payment processing.

### `frontend/src/pages/CashoutConfirm.jsx`

Cashout confirmation page accessed from MTurk HIT. Workers land here to confirm their cashout, enter redemption code, and complete the payment flow.

---

## 9. Frontend Components

### `frontend/src/components/ChatWindow.jsx`

Real-time chat display component. Renders message list with player colors, handles auto-scroll to new messages, displays typing indicators, and shows system messages. Differentiates own messages from others.

### `frontend/src/components/MessageInput.jsx`

Chat input component with typing indicator integration. Handles message composition, Enter key submission, typing status broadcasts, and input validation. Disabled during voting phase.

### `frontend/src/components/PlayerList.jsx`

Player list sidebar showing all game participants. Displays player names with color coding, online/typing status indicators, vote counts during voting phase, and elimination status. Adapts display for single-human vs multi-human modes.

### `frontend/src/components/PhaseTimer.jsx`

Game phase timer with server synchronization. Displays countdown for discussion and voting phases, receives `timer_sync` WebSocket messages for drift correction, and provides visual warnings as time runs low.

### `frontend/src/components/GameOver.jsx`

Game results display component. Shows winner announcement, vote breakdown, player roles revealed, gem rewards with detailed breakdown (base gems, stake results), and navigation options.

### `frontend/src/components/ConnectionStatus.jsx`

WebSocket connection status indicator. Shows connected/disconnected/reconnecting states with visual badges and provides reconnection feedback.

### `frontend/src/components/ProtectedRoute.jsx`

Route wrapper for authentication. Checks for valid auth token, redirects to login if unauthenticated, and supports `requireAdmin` prop for admin-only routes.

### `frontend/src/components/ActiveSessionGuard.jsx`

Detects and handles active game sessions on page load. Checks localStorage for saved sessions, prompts user to rejoin or abandon, prevents duplicate sessions.

### `frontend/src/components/ErrorBoundary.jsx`

React error boundary for catching rendering errors. Displays fallback UI when components crash, logs errors, and provides recovery options.

### `frontend/src/components/Wallet.jsx`

Full-page wallet component for gem management. Displays current balance, USD equivalent, transaction history, cashout button with eligibility check, and pending cashout status.

### `frontend/src/components/CashoutModal.jsx`

Modal dialog for initiating cashouts. Shows gem balance, amount input with USD conversion, MTurk worker ID validation, and submission handling.

### `frontend/src/components/CompletionKeyModal.jsx`

Modal for displaying game completion keys for MTurk integration.

### `frontend/src/components/CreateRoomModal.jsx`

Room creation modal with configuration options. Allows setting max humans, total players, language, discussion/voting durations, and stake percentage. Validates settings before creation.

### `frontend/src/components/RoomCard.jsx`

Individual room card for lobby display. Shows room name, player count, stake level, language, and join button. Indicates if room is full or in progress.

### `frontend/src/components/ProgressBar.jsx`

Reusable progress bar component for level progress, achievement progress, and other percentage displays.

### `frontend/src/components/StatsCard.jsx`

Dashboard statistics card component. Displays stat value with label, icon, and optional trend indicator.

### `frontend/src/components/EarningsChart.jsx`

Chart component for visualizing earnings over time. Uses charting library to display gem earning history.

### `frontend/src/components/EarningsCounter.jsx`

Animated counter component that increments displayed gem value smoothly for visual feedback.

### `frontend/src/components/AchievementUnlock.jsx`

Toast/notification component for achievement unlocks. Displays achievement icon, name, and points earned with celebration animation.

### `frontend/src/components/PointsAnimation.jsx`

Floating points animation for gem awards. Shows "+X gems" with upward float animation.

### `frontend/src/components/MTurkAutoLogin.jsx`

Handles automatic login for MTurk workers. Parses URL parameters for worker ID and assignment ID, triggers auto-registration/login flow.

---

## 10. Frontend Contexts

### `frontend/src/contexts/AuthContext.jsx`

Global authentication state management. Provides `AuthProvider` wrapper and `useAuth()` hook. Manages user state, token storage, login/logout functions, loading states, and `clearAuthData()` for comprehensive logout. Persists auth to localStorage and validates tokens on mount.

### `frontend/src/contexts/GameContext.jsx`

Global game state for room and player management. Provides `GameProvider` wrapper and `useGame()` hook. Manages `roomCode`, `playerId`, `selectedRoom`, and active session persistence to localStorage for reconnection support. Includes `saveActiveSession()` and `clearActiveSession()` for session management.

### `frontend/src/contexts/LanguageContext.jsx`

Internationalization context for multi-language support. Provides `LanguageProvider` wrapper and `useLanguage()` hook. Manages current language selection (English/Korean) and provides translation functions.

---

## 11. Frontend Hooks

### `frontend/src/hooks/useWebSocket.js`

WebSocket connection management hook. Handles connection lifecycle, automatic reconnection with exponential backoff (up to 5 attempts), connection status tracking, and message dispatching. Accepts `roomCode`, `playerId`, `onMessage` callback, and `onReconnect` callback for state recovery after reconnection.

### `frontend/src/hooks/useHeartbeat.js`

Heartbeat hook for online status tracking. Sends periodic heartbeat requests to the backend to register user activity. Used by GamePage and other active pages to maintain online user counts.

### `frontend/src/hooks/useRoomPolling.js`

Polling hook for room list updates in the lobby. Periodically fetches room list from API, manages polling interval, and provides refresh function. Used when WebSocket isn't needed (lobby browsing).

---

## 12. Frontend Services

### `frontend/src/services/api.js`

Main API client using Axios. Configures base URL from environment, attaches JWT tokens via request interceptor, handles 401 responses with auto-logout. Exports `roomAPI` object with methods: `createRoom()`, `listRooms()`, `getRoomInfo()`, `joinRoom()`, `leaveRoom()`, `startGame()`, `sendMessage()`, `submitVote()`. Also exports `getWebSocketURL()` for WebSocket connections.

### `frontend/src/services/authAPI.js`

Authentication-specific API client. Exports `authAPI` object with methods: `register()`, `login()`, `getMe()`, `updateProfile()`. Handles token storage on successful login.

### `frontend/src/services/walletAPI.js`

Wallet and cashout API client. Exports `walletAPI` object with methods: `getBalance()`, `getTransactions()`, `requestCashout()`, `checkCashoutReady()`, `cancelCashout()`.

### `frontend/src/services/sessionsAPI.js`

Session history API client. Exports `sessionsAPI` object with methods: `listSessions()`, `getSession()`, `getDashboard()` for fetching game history and statistics.

### `frontend/src/services/leaderboardAPI.js`

Leaderboard API client. Exports `leaderboardAPI` object with methods for fetching leaderboard data with pagination and filtering.

### `frontend/src/services/mturkAPI.js`

MTurk-specific API client. Handles MTurk worker registration, auto-login flow, and completion key submission.

---

## 13. Frontend Utilities

### `frontend/src/utils/translations.js`

Translation strings for internationalization. Contains nested object with English and Korean translations for all UI text, organized by page/component. Used by `LanguageContext`.

### `frontend/src/utils/playerColors.js`

Player color assignment utilities. Provides consistent color mapping for player IDs, ensuring each player has a distinct, accessible color for chat messages and player lists.

---

## 14. Root Scripts

### `create_admin.py`

Utility script to create an admin user account. Prompts for user ID and password, creates user with admin role in database.

### `deploy.py`

Deployment helper script with functions for building frontend, starting backend, and environment validation.

### `run_backend_local.py`

Convenience script for running the backend locally. Sets up environment and launches uvicorn with appropriate settings.

### `QUICK_START.sh`

Shell script for quick project setup. Installs dependencies for both frontend and backend, copies example env file if needed.

### `RESTART_BACKEND.sh`

Shell script to restart the backend server. Kills existing uvicorn processes and starts fresh.

### `RESET_DATABASE.sh`

Shell script to reset the database. Deletes the SQLite file and reruns migrations for a clean state.

### `SETUP_GAMIFICATION.sh`

Shell script that initializes gamification tables and runs any required setup for the achievement system.

### `start_backend.sh`

Production-ready shell script for starting the backend with proper configurations.

### `QUICKSTART_AWS_CREDENTIALS.sh`

Helper script for setting up AWS credentials for MTurk integration.

### `scripts/setup_ngrok.sh`

Installs and configures ngrok for backend tunneling.

### `scripts/start_local.sh`

Starts both frontend and backend for local development.

### `scripts/test_backend.sh`

Runs backend test suite with pytest.

---

## 15. Configuration Files

### `env.example`

Template environment file with all configurable options documented. Copy to `.env` and fill in values.

### `backend/requirements.txt`

Python dependencies for the backend. Includes FastAPI, SQLAlchemy, LangGraph, OpenAI, boto3, and other required packages.

### `frontend/package.json`

Node.js dependencies and scripts for the frontend. Includes React, Vite, Tailwind CSS, Axios, and other packages.

### `frontend/vite.config.js`

Vite build configuration for the React frontend. Sets up development server, build options, and environment variable handling.

### `frontend/tailwind.config.js`

Tailwind CSS configuration. Defines content paths, theme extensions, and custom utility classes.

### `frontend/postcss.config.js`

PostCSS configuration for CSS processing. Configures Tailwind CSS and autoprefixer plugins.

### `frontend/netlify.toml`

Netlify deployment configuration. Sets up build command, publish directory, and redirect rules for SPA routing.

### `backend/alembic.ini`

Alembic database migration configuration. Points to the migrations directory and configures logging.

### `backend/alembic/` directory

Contains database migration scripts managed by Alembic. The `versions/` subdirectory holds individual migration files.

### `alembic.ini` and `alembic/` (root)

Root-level Alembic configuration (may duplicate backend configuration depending on project setup).

---

## File Relationship Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              Frontend                                     │
│  ┌─────────────┐   ┌──────────────┐   ┌─────────────────┐               │
│  │   Pages     │◄──│  Components  │◄──│    Contexts     │               │
│  │ (GamePage,  │   │ (ChatWindow, │   │ (Auth, Game,    │               │
│  │  Lobby...)  │   │  PlayerList) │   │  Language)      │               │
│  └──────┬──────┘   └──────────────┘   └────────┬────────┘               │
│         │                                       │                         │
│         ▼                                       ▼                         │
│  ┌─────────────┐   ┌──────────────┐   ┌─────────────────┐               │
│  │   Hooks     │   │   Services   │◄──│   Utils         │               │
│  │ (useWebSocket)│ │ (api.js,     │   │ (translations,  │               │
│  └──────┬──────┘   │  walletAPI)  │   │  playerColors)  │               │
│         │          └──────┬───────┘   └─────────────────┘               │
└─────────┼─────────────────┼─────────────────────────────────────────────┘
          │    WebSocket    │     REST API
          ▼                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                              Backend                                      │
│  ┌─────────────┐   ┌──────────────┐   ┌─────────────────┐               │
│  │   Routers   │──▶│   Services   │──▶│   Database      │               │
│  │ (websocket, │   │ (game_coord, │   │   (models,      │               │
│  │  rooms...)  │   │  messaging)  │   │   async session)│               │
│  └──────┬──────┘   └──────┬───────┘   └─────────────────┘               │
│         │                 │                                               │
│         ▼                 ▼                                               │
│  ┌─────────────┐   ┌──────────────┐   ┌─────────────────┐               │
│  │  LangGraph  │   │ Global State │   │   MTurk API     │               │
│  │ (AI agents, │   │ (rooms,locks)│   │ (payments, HITs)│               │
│  │  game logic)│   │              │   │                 │               │
│  └─────────────┘   └──────────────┘   └─────────────────┘               │
└─────────────────────────────────────────────────────────────────────────┘
```

