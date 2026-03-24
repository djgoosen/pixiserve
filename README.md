# Pixiserve

Self-hosted Google Photos replacement with ML-powered organization.

## Features (Planned)

- Clerk authentication (session JWTs verified on the API via JWKS)
- Photo & video upload with SHA256 deduplication
- Face recognition and clustering
- Object and scene detection
- Offline-first mobile sync
- Family library sharing

## Quick Start

### Prerequisites

- Docker & Docker Compose

### Setup

1. Clone the repository

2. Copy environment file and configure:
   ```bash
   cd deploy
   cp .env.example .env
   # Edit .env — set SECRET_KEY, POSTGRES_PASSWORD, CLERK_SECRET_KEY, CLERK_PUBLISHABLE_KEY
   ```

3. Start services:
   ```bash
   docker compose up -d
   ```

4. Run database migrations:
   ```bash
   docker compose exec api alembic upgrade head
   ```

5. After [Clerk](https://clerk.com) is configured, sign in via the web or mobile app. The API expects a **Clerk session JWT** on protected routes. Each user row must have `clerk_user_id` set (via Clerk webhook sync — see sprint backlog) before `/api/v1/auth/me` and other protected endpoints succeed.

6. Legacy `POST /api/v1/auth/register` and `/login` may still exist for migration tooling but **protected routes** authenticate with Clerk only.

## API authentication (Clerk)

- **CLERK_SECRET_KEY** — Backend API secret from the Clerk dashboard (required at API startup).
- **CLERK_PUBLISHABLE_KEY** — Publishable key for the React / Expo Clerk SDKs (required at startup so deploys are documented consistently; not used to verify Bearer tokens).
- **Bearer tokens** — The API validates `Authorization: Bearer <session_jwt>` with **RS256** using Clerk’s JWKS URL derived from the JWT `iss` claim: `{iss}/.well-known/jwks.json`.
- **Local user** — The JWT `sub` (Clerk user id) must match `users.clerk_user_id` in the database.

Health checks **`/health`**, **`/api/v1/health`**, and **`/api/v1/health/ready`** stay unauthenticated.

## Development

### Backend (Python/FastAPI)

```bash
cd backend
poetry install
cp .env.example .env
# Edit .env with your settings

# Start dependencies
docker compose -f ../deploy/docker-compose.yml up db redis -d

# Run migrations
alembic upgrade head

# Start dev server
uvicorn app.main:app --reload
```

### API Documentation

Once running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Architecture

See `/architecture` for detailed system design:
- `ml-pipeline.md` - Hardware-agnostic ML processing
- `sync-protocol.md` - Offline-first sync protocol
- `security.md` - Security model

## Tech Stack

- **Backend:** Python, FastAPI, SQLAlchemy, Celery
- **Database:** PostgreSQL, Redis
- **Auth:** Clerk session JWTs (JWKS), bcrypt for share-link passwords
- **Storage:** Local filesystem or S3-compatible

## License

MIT
