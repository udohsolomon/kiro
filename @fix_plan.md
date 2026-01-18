# Kiro Labyrinth - Development Plan

## Phase 1: Foundation (COMPLETE)

### T-01: Project Setup
- [x] **T-01.1**: Initialize FastAPI project structure
- [x] **T-01.2**: Set up PostgreSQL database with Docker
- [x] **T-01.3**: Configure Redis
- [x] **T-01.4**: Create Docker Compose for local dev
- [x] **T-01.5**: Set up pytest with fixtures

### T-02: User Authentication
- [x] **T-02.1**: Implement POST /auth/register endpoint
- [x] **T-02.2**: Add password hashing with bcrypt
- [x] **T-02.3**: Generate secure API keys
- [x] **T-02.4**: Create API key validation middleware
- [x] **T-02.5**: Add email verification flow

### T-03: Database Models
- [x] **T-03.1**: Create SQLAlchemy models
- [x] **T-03.2**: Set up Alembic migrations
- [x] **T-03.3**: Seed tutorial maze data

---

## Phase 2: Maze Engine (COMPLETE)

### T-04: Maze Parser
- [x] **T-04.1**: Create maze parser to load and validate maze files
- [x] **T-04.2**: Implement maze validation (check S and E exist, walls are valid)
- [x] **T-04.3**: Create GET /v1/maze endpoint to list available mazes
- [x] **T-04.4**: Create GET /v1/maze/{id} endpoint to get maze details

### T-05: Session Management
- [x] **T-05.1**: Create POST /v1/session endpoint to start a maze session
- [x] **T-05.2**: Track current position and turn count in session
- [x] **T-05.3**: Create GET /v1/session/{id} endpoint to get session state

### T-06: Movement Logic
- [x] **T-06.1**: Implement POST /v1/session/{id}/move endpoint for movement
- [x] **T-06.2**: Implement POST /v1/session/{id}/look endpoint (free action)
- [x] **T-06.3**: Handle wall collisions and mud tiles (# = slower)
- [x] **T-06.4**: Detect maze completion when reaching exit (E)

---

## Phase 3: Sandbox Execution (COMPLETE)

### T-07: Docker Sandbox
- [x] **T-07.1**: Create Docker sandbox container for code execution
- [x] **T-07.2**: Add resource limits (CPU, memory, timeout) to sandbox
- [x] **T-07.3**: Implement network isolation in sandbox

### T-08: Submission Pipeline
- [x] **T-08.1**: Create POST /v1/submit endpoint to accept code submissions
- [x] **T-08.2**: Queue submissions for async processing
- [x] **T-08.3**: Execute code in sandbox and capture results
- [x] **T-08.4**: Create GET /v1/submission/{id} endpoint to check status

### T-09: Security Hardening
- [x] **T-09.1**: Sanitize and validate submitted code
- [x] **T-09.2**: Prevent filesystem escape and malicious imports

---

## Phase 4: Leaderboard (COMPLETE)

### T-10: Leaderboard Service
- [x] **T-10.1**: Create GET /v1/leaderboard endpoint
- [x] **T-10.2**: Store leaderboard in Redis sorted set
- [x] **T-10.3**: Update leaderboard on successful submission

### T-11: Real-Time Updates
- [x] **T-11.1**: Implement WebSocket for real-time leaderboard updates
- [x] **T-11.2**: Broadcast updates when new high scores are set

---

## Phase 5: Production Readiness (NEW)

### T-12: Security & Configuration
- [x] **T-12.1**: Fix CORS configuration for production environments
- [x] **T-12.2**: Create .env.example file with documentation
- [x] **T-12.3**: Add secret key validation
- [x] **T-12.4**: Fix API key regeneration on Google login (preserve existing keys)
- [x] **T-12.5**: Remove sensitive data from public endpoints

### T-13: API Improvements
- [x] **T-13.1**: Add rate limiting to submission endpoint
- [x] **T-13.2**: Add structured request logging with correlation IDs
- [x] **T-13.3**: Add /auth/regenerate-key endpoint

### T-14: Frontend Integration
- [x] **T-14.1**: Connect frontend to backend API
- [x] **T-14.2**: Add mobile responsiveness
- [x] **T-14.3**: Handle Google Sign-In dynamically

### T-15: Documentation
- [x] **T-15.1**: Create deployment documentation
- [x] **T-15.2**: Update fix plan to reflect completed work

---

## Progress Summary

| Phase | Tasks | Completed | Status |
|-------|-------|-----------|--------|
| Foundation | 13 | 13 | ✅ COMPLETE |
| Maze Engine | 11 | 11 | ✅ COMPLETE |
| Sandbox Execution | 9 | 9 | ✅ COMPLETE |
| Leaderboard | 5 | 5 | ✅ COMPLETE |
| Production Readiness | 11 | 11 | ✅ COMPLETE |
| **Total** | **49** | **49** | **100%** |

## Completion Criteria

All phases are complete when:
- [x] All checkboxes in all phases are marked [x]
- [x] All verification commands in prd.json pass
- [x] All tests pass with `docker compose exec api pytest tests/ -v`
- [x] Production readiness improvements implemented

## Recent Changes (2026-01-18)

1. **Security Fixes:**
   - CORS now configurable via environment (not wildcard in production)
   - Secret key validation added (minimum 32 characters)
   - API keys preserved on Google re-login (no forced regeneration)
   - Google client ID removed from public root endpoint

2. **Rate Limiting:**
   - Added slowapi for rate limiting
   - Submit endpoint: 10 requests/minute per IP
   - Configurable via environment variables

3. **Logging:**
   - Structured logging with correlation IDs
   - Request/response logging middleware
   - Request timing metrics

4. **Frontend:**
   - Full API integration (mazes, sessions, leaderboard)
   - WebSocket support for real-time updates
   - Mobile responsive design
   - Fallback to offline mode when API unavailable

5. **Documentation:**
   - Created `.env.example` with all configuration options
   - Created `docs/DEPLOYMENT.md` with deployment guide
   - Updated this fix plan to reflect all work
