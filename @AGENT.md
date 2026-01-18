# Kiro Labyrinth - Agent Build Instructions

## Environment Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

## Dependencies (requirements.txt)

```
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
pydantic>=2.5.0
pydantic-settings>=2.1.0
sqlalchemy>=2.0.25
alembic>=1.13.0
asyncpg>=0.29.0
redis>=5.0.0
bcrypt>=4.1.0
python-jose[cryptography]>=3.3.0
python-multipart>=0.0.6
httpx>=0.26.0
pytest>=7.4.0
pytest-asyncio>=0.23.0
pytest-cov>=4.1.0
```

## Docker Compose Services

```bash
# Start all services (postgres, redis, api)
docker compose up -d

# Start only databases
docker compose up -d postgres redis

# View logs
docker compose logs -f api

# Stop all
docker compose down
```

## Run Tests

```bash
# All tests
pytest backend/tests/ -v

# Specific test file
pytest backend/tests/test_auth.py -v

# Single test
pytest backend/tests/test_auth.py::test_register -v

# With coverage
pytest backend/tests/ --cov=app --cov-report=term-missing

# Watch mode (requires pytest-watch)
ptw backend/tests/
```

## Linting & Formatting

```bash
# Type checking
mypy backend/app/

# Format code
black backend/app/

# Lint
ruff check backend/app/

# Fix lint issues
ruff check backend/app/ --fix
```

## Database Migrations (Alembic)

```bash
cd backend

# Create new migration
alembic revision --autogenerate -m "Add users table"

# Apply all migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# Show current revision
alembic current

# Show migration history
alembic history
```

## Run Development Server

```bash
cd backend

# With auto-reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production mode
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## API Testing

```bash
# Health check
curl http://localhost:8000/health

# Register user
curl -X POST http://localhost:8000/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "username": "testuser", "password": "SecurePass123!"}'

# Start maze session
curl -X POST http://localhost:8000/v1/maze/start \
  -H "X-API-Key: your_api_key" \
  -H "Content-Type: application/json" \
  -d '{"maze_id": "tutorial"}'
```

## Environment Variables

Create `.env` file in backend/:

```
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/kiro_labyrinth
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=your-secret-key-here
API_KEY_PREFIX=kiro_
DEBUG=true
```

## Common Issues

### Database connection failed
- Ensure PostgreSQL is running: `docker compose up -d postgres`
- Check connection string in .env

### Redis connection failed
- Ensure Redis is running: `docker compose up -d redis`
- Check REDIS_URL in .env

### Import errors
- Ensure you're in the venv: `source venv/bin/activate`
- Reinstall dependencies: `pip install -r requirements.txt`

### Migration errors
- Check if database exists: `docker compose exec postgres psql -U postgres -c '\l'`
- Create database if needed: `docker compose exec postgres createdb -U postgres kiro_labyrinth`
