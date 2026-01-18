# Kiro Labyrinth - Project Context

## Overview

Kiro Labyrinth is a competitive maze-solving challenge platform inspired by AWS re:Invent 2025's "Kiro's Labyrinth" challenge. Developers write Python code to navigate from start (S) to exit (E) using the fewest turns possible.

## Challenge Mechanics

| Element | Description |
|---------|-------------|
| **Maze Format** | Text-based grid with symbols: S (start), E (exit), X (walls), # (mud) |
| **Actions** | `move(direction)` counts as 1 turn, `look()` is FREE |
| **Scoring** | Turn count (lower = better) |
| **Benchmark** | Winner Paul completed in 1,314 turns |

## Technology Stack

| Layer | Technology |
|-------|------------|
| **Backend** | FastAPI, Python 3.12, Uvicorn |
| **Database** | PostgreSQL 15 |
| **Cache** | Redis 7 |
| **Sandbox** | Docker with resource limits |
| **Frontend** | React 18, TypeScript, Vite |

## Code Conventions

- **Type hints**: Use everywhere
- **Schemas**: Pydantic for request/response validation
- **ORM**: SQLAlchemy 2.0 with async
- **Migrations**: Alembic
- **Testing**: pytest with pytest-asyncio
- **Formatting**: Black + Ruff

## API Design

- RESTful endpoints at `/v1/*`
- API key authentication via `X-API-Key` header
- JSON responses with Pydantic schemas
- Standard HTTP status codes

## Directory Structure

```
kiro-labyrinth/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI application
│   │   ├── config.py            # Pydantic settings
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── deps.py          # Dependencies (auth, db)
│   │   │   └── routes/
│   │   │       ├── auth.py      # /auth/* endpoints
│   │   │       ├── maze.py      # /maze/* endpoints
│   │   │       ├── submit.py    # /submit endpoint
│   │   │       └── leaderboard.py
│   │   ├── core/
│   │   │   ├── maze_engine.py   # Maze logic
│   │   │   ├── maze_parser.py   # Parse maze files
│   │   │   └── scoring.py       # Turn counting
│   │   ├── models/
│   │   │   ├── user.py
│   │   │   ├── maze.py
│   │   │   ├── submission.py
│   │   │   └── session.py
│   │   ├── schemas/
│   │   │   ├── user.py
│   │   │   ├── maze.py
│   │   │   └── submission.py
│   │   ├── services/
│   │   │   ├── auth_service.py
│   │   │   ├── maze_service.py
│   │   │   └── leaderboard_service.py
│   │   └── db/
│   │       ├── database.py      # Async engine
│   │       ├── redis.py         # Redis connection
│   │       └── seed.py          # Seed data
│   ├── tests/
│   │   ├── conftest.py          # Fixtures
│   │   ├── test_auth.py
│   │   ├── test_maze.py
│   │   └── test_leaderboard.py
│   ├── alembic/
│   │   └── versions/
│   ├── mazes/
│   │   ├── tutorial.txt
│   │   ├── intermediate.txt
│   │   └── challenge.txt
│   ├── requirements.txt
│   ├── alembic.ini
│   └── Dockerfile
├── frontend/                    # React frontend (existing)
├── starter-package/             # Python SDK (existing)
├── docker-compose.yml
└── (Ralph files)
```

## Database Schema

### Users
- `id` (UUID, PK)
- `email` (unique)
- `username` (unique, 3-20 chars)
- `password_hash`
- `api_key` (unique)
- `verified` (boolean)
- `created_at`

### Mazes
- `id` (UUID, PK)
- `name`
- `difficulty` (tutorial/intermediate/challenge)
- `grid_data` (text)
- `width`, `height`
- `start_x`, `start_y`
- `exit_x`, `exit_y`
- `is_active`

### Submissions
- `id` (UUID, PK)
- `user_id` (FK)
- `maze_id` (FK)
- `code_path`
- `status` (pending/running/completed/failed/timeout)
- `score`
- `error_message`
- `created_at`

### Sessions
- `id` (UUID, PK)
- `user_id` (FK)
- `maze_id` (FK)
- `current_x`, `current_y`
- `turn_count`
- `is_stuck` (boolean)
- `status` (active/completed/abandoned)

## API Endpoints (Phase 1)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/v1/auth/register` | Register new user |
| POST | `/v1/auth/verify` | Verify email |
| GET | `/health` | Health check |

## Testing Requirements

- Unit tests for all services
- Integration tests for API endpoints
- Async tests with `pytest-asyncio`
- Database fixtures with transaction rollback
- Minimum 80% coverage target

## Existing Code

The following already exists and should be preserved/extended:

- `backend/app/core/maze_engine.py` - Partial maze logic
- `backend/mazes/*.txt` - Maze files
- `starter-package/` - Complete Python SDK
- `frontend/` - Basic frontend structure

## Environment Variables

```
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/kiro_labyrinth
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=<random-secret>
API_KEY_PREFIX=kiro_
DEBUG=true
```
