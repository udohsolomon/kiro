# Kiro Labyrinth - Deployment Guide

This guide covers deploying Kiro Labyrinth in various environments.

## Table of Contents

1. [Local Development](#local-development)
2. [Docker Deployment](#docker-deployment)
3. [Production Deployment](#production-deployment)
4. [Environment Variables](#environment-variables)
5. [Database Setup](#database-setup)
6. [Monitoring & Logging](#monitoring--logging)

---

## Local Development

### Prerequisites

- Python 3.12+
- Docker & Docker Compose
- PostgreSQL 15+ (or use Docker)
- Redis 7+ (or use Docker)

### Quick Start

1. **Clone and setup:**

```bash
cd kiro-labyrinth/backend
cp .env.example .env
# Edit .env with your settings
```

2. **Start infrastructure:**

```bash
docker compose up -d postgres redis
```

3. **Install dependencies:**

```bash
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt
```

4. **Run migrations:**

```bash
alembic upgrade head
```

5. **Seed database:**

```bash
python -c "from app.db.seed import seed_mazes; import asyncio; asyncio.run(seed_mazes())"
```

6. **Start the API:**

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

7. **Access:**
   - API: http://localhost:8000
   - Docs: http://localhost:8000/docs
   - Frontend: Open `frontend/index.html` in browser

---

## Docker Deployment

### Development with Docker Compose

```bash
# Start all services
docker compose up -d

# View logs
docker compose logs -f api

# Run migrations
docker compose exec api alembic upgrade head

# Run tests
docker compose exec api pytest tests/ -v

# Stop services
docker compose down
```

### Build Production Image

```dockerfile
# backend/Dockerfile.prod
FROM python:3.12-slim AS builder

WORKDIR /app
COPY requirements.txt .
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /wheels -r requirements.txt

FROM python:3.12-slim

# Create non-root user
RUN useradd -m -s /bin/bash appuser

WORKDIR /app

# Install dependencies
COPY --from=builder /wheels /wheels
RUN pip install --no-cache /wheels/*

# Copy application
COPY --chown=appuser:appuser . .

USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Build and run:

```bash
docker build -f Dockerfile.prod -t kiro-labyrinth:latest .
docker run -p 8000:8000 --env-file .env kiro-labyrinth:latest
```

---

## Production Deployment

### Architecture Overview

```
                    ┌─────────────┐
                    │   Nginx     │
                    │  (Reverse   │
                    │   Proxy)    │
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
        ┌─────▼─────┐ ┌────▼────┐ ┌─────▼─────┐
        │   API     │ │   API   │ │   API     │
        │ Instance 1│ │Instance2│ │ Instance 3│
        └─────┬─────┘ └────┬────┘ └─────┬─────┘
              │            │            │
              └────────────┼────────────┘
                           │
              ┌────────────┴────────────┐
              │                         │
        ┌─────▼─────┐           ┌───────▼───────┐
        │ PostgreSQL│           │     Redis     │
        │ (Primary) │           │   (Cluster)   │
        └───────────┘           └───────────────┘
```

### Recommended Stack

| Component | Recommended Service |
|-----------|---------------------|
| Compute | AWS ECS, GCP Cloud Run, or Kubernetes |
| Database | AWS RDS PostgreSQL, GCP Cloud SQL |
| Cache | AWS ElastiCache, GCP Memorystore |
| Load Balancer | AWS ALB, GCP Load Balancer |
| CDN | CloudFront, Cloud CDN |
| Monitoring | DataDog, New Relic, or Prometheus |

### Security Checklist

- [ ] Set `DEBUG=false` in production
- [ ] Use strong `SECRET_KEY` (64+ characters)
- [ ] Configure `CORS_ORIGINS` with specific domains
- [ ] Enable HTTPS/TLS everywhere
- [ ] Use managed database with encryption at rest
- [ ] Set up WAF rules for DDoS protection
- [ ] Configure rate limiting appropriately
- [ ] Review and restrict sandbox resource limits
- [ ] Set up log aggregation and monitoring
- [ ] Enable database backups

### Health Checks

Configure your load balancer to check:

```
GET /health
Expected: {"status": "ok", "version": "X.X.X"}
```

### Nginx Configuration Example

```nginx
upstream kiro_api {
    server api1:8000;
    server api2:8000;
    server api3:8000;
}

server {
    listen 80;
    server_name api.kiro-labyrinth.dev;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.kiro-labyrinth.dev;

    ssl_certificate /etc/ssl/certs/kiro.crt;
    ssl_certificate_key /etc/ssl/private/kiro.key;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    location / {
        proxy_pass http://kiro_api;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket support for leaderboard
    location /v1/leaderboard/ws {
        proxy_pass http://kiro_api;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 86400;
    }
}
```

---

## Environment Variables

### Required

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+asyncpg://user:pass@host:5432/db` |
| `REDIS_URL` | Redis connection string | `redis://host:6379/0` |
| `SECRET_KEY` | JWT signing key (min 32 chars) | `your-secure-random-key-here` |
| `GOOGLE_CLIENT_ID` | Google OAuth client ID | `xxx.apps.googleusercontent.com` |

### Optional

| Variable | Default | Description |
|----------|---------|-------------|
| `DEBUG` | `false` | Enable debug mode |
| `CORS_ORIGINS` | (see .env.example) | Allowed CORS origins |
| `RATE_LIMIT_REQUESTS` | `100` | General rate limit per minute |
| `RATE_LIMIT_SUBMISSIONS` | `10` | Submission rate limit per minute |
| `SANDBOX_TIMEOUT_SECONDS` | `300` | Max execution time |
| `SANDBOX_MEMORY_LIMIT_MB` | `256` | Max memory per sandbox |
| `MAX_CONCURRENT_SANDBOXES` | `50` | Concurrent execution limit |

---

## Database Setup

### Initial Setup

```bash
# Create database
psql -U postgres -c "CREATE DATABASE kiro_labyrinth;"

# Run migrations
alembic upgrade head

# Seed initial data
python -c "from app.db.seed import seed_mazes; import asyncio; asyncio.run(seed_mazes())"
```

### Backup & Restore

```bash
# Backup
pg_dump -U postgres kiro_labyrinth > backup_$(date +%Y%m%d).sql

# Restore
psql -U postgres kiro_labyrinth < backup_20240101.sql
```

### Migration Commands

```bash
# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback one version
alembic downgrade -1

# View history
alembic history
```

---

## Monitoring & Logging

### Log Format

Logs are structured with correlation IDs:

```
2024-01-01 12:00:00 - kiro_labyrinth - INFO - [abc12345] --> POST /v1/submit from 192.168.1.1
2024-01-01 12:00:01 - kiro_labyrinth - INFO - [abc12345] <-- 201 (150.23ms)
```

### Key Metrics to Monitor

| Metric | Warning | Critical |
|--------|---------|----------|
| API Response Time | >500ms | >2000ms |
| Error Rate | >1% | >5% |
| Active Sandboxes | >40 | >48 |
| Database Connections | >80% | >95% |
| Redis Memory | >80% | >95% |
| CPU Usage | >70% | >90% |

### Prometheus Metrics Endpoint

Add to your monitoring:

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'kiro-api'
    static_configs:
      - targets: ['api:8000']
    metrics_path: /metrics
```

### Log Aggregation

For production, ship logs to a centralized system:

```python
# Example: Add to config.py for cloud logging
import logging
from pythonjsonlogger import jsonlogger

handler = logging.StreamHandler()
handler.setFormatter(jsonlogger.JsonFormatter())
logging.getLogger().addHandler(handler)
```

---

## Troubleshooting

### Common Issues

**1. Database connection errors:**
```bash
# Check database is running
docker compose ps postgres

# Test connection
docker compose exec postgres pg_isready -U postgres
```

**2. Redis connection errors:**
```bash
# Check Redis
docker compose exec redis redis-cli ping
```

**3. Sandbox execution fails:**
```bash
# Ensure sandbox image is built
docker build -t kiro-sandbox backend/sandbox/

# Check Docker socket permissions
ls -la /var/run/docker.sock
```

**4. CORS errors:**
- Check `CORS_ORIGINS` includes your frontend domain
- Ensure `DEBUG=true` for development (allows all origins)

**5. Rate limiting:**
- Adjust `RATE_LIMIT_*` settings if legitimate users are blocked
- Check logs for rate limit events

---

## Support

- Documentation: `/docs` endpoint
- Issues: GitHub Issues
- Email: support@kiro-labyrinth.dev
