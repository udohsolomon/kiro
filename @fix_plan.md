# Kiro Labyrinth - Development Plan

## Phase 1: Foundation (Current Focus)

### T-01: Project Setup

- [ ] **T-01.1**: Initialize FastAPI project structure
  - Create main.py with FastAPI app
  - Create config.py with Pydantic settings
  - Set up directory layout (api/, core/, models/, etc.)

- [ ] **T-01.2**: Set up PostgreSQL database with Docker
  - Add postgres service to docker-compose.yml
  - Configure connection string

- [ ] **T-01.3**: Configure Redis
  - Add redis service to docker-compose.yml
  - Set up Redis connection

- [ ] **T-01.4**: Create Docker Compose for local dev
  - Complete docker-compose.yml with api, postgres, redis
  - Add health endpoint

- [ ] **T-01.5**: Set up pytest with fixtures
  - Create tests/conftest.py
  - Add database fixtures
  - Add test client fixtures

### T-02: User Authentication

- [ ] **T-02.1**: Implement POST /auth/register endpoint
  - Accept email, username, password
  - Validate input
  - Create user in database

- [ ] **T-02.2**: Add password hashing with bcrypt
  - Hash passwords before storing
  - Verify passwords on login

- [ ] **T-02.3**: Generate secure API keys
  - Create unique API keys on registration
  - Store hashed API keys

- [ ] **T-02.4**: Create API key validation middleware
  - Validate X-API-Key header
  - Inject user into request state

- [ ] **T-02.5**: Add email verification flow
  - Generate verification tokens
  - Mock email service (log to console)
  - Verify endpoint

### T-03: Database Models

- [ ] **T-03.1**: Create SQLAlchemy models
  - User model
  - Maze model
  - Submission model
  - Session model

- [ ] **T-03.2**: Set up Alembic migrations
  - Initialize Alembic
  - Create initial migration

- [ ] **T-03.3**: Seed tutorial maze data
  - Create seed script
  - Load mazes from backend/mazes/

## Completion Criteria

Phase 1 is complete when:
- All checkboxes above are marked [x]
- All verification commands in prd.json pass
- All tests pass with `pytest backend/tests/ -v`

## Next Phases (Not Yet Started)

### Phase 2: Maze Engine
- T-04: Maze Parser
- T-05: Session Management
- T-06: Movement Logic

### Phase 3: Sandbox Execution
- T-07: Docker Sandbox
- T-08: Submission Pipeline
- T-09: Security Hardening

### Phase 4: Leaderboard
- T-10: Leaderboard Service
- T-11: Real-Time Updates

See `../KIRO_LABYRINTH_PRD.md` for full task details.
