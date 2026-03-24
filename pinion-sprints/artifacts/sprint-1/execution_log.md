# Synthetic execution timeline

Derived from work unit JSON in this sprint (state and latest merge record only); not a live agent log.

- **PIN-001** — state `released` — last merge `recorded_at` `2026-03-24T02:30:00Z`
  - Clerk configuration and API JWT verification: validate CLERK_* settings at startup, verify Clerk-issued session JWTs on protected FastAPI routes via JWKS or official Clerk backend SDK, and document required env vars for deployers.
- **PIN-002** — state `released` — last merge `recorded_at` `2026-03-24T03:00:00Z`
  - Clerk webhook endpoint: implement POST /webhooks/clerk (or agreed path) with Svix signature verification, handle user.created and user.updated (idempotent), return appropriate HTTP statuses, and reject invalid signatures.
- **PIN-003** — state `released` — last merge `recorded_at` `2026-03-24T02:38:27Z`
  - Local User sync from Clerk: map webhook payloads to User rows (clerk_user_id, email, display fields), upsert idempotently, implement first-authenticated-user admin rule (FR-AUTH-02), and keep fields aligned with product data model.
- **PIN-004** — state `released` — last merge `recorded_at` `2026-03-24T02:42:47Z`
  - Remove or fully gate legacy local username/password authentication; align GET /me and all route dependencies with Clerk JWT identity only; update any remaining auth helpers and deprecation notes for operators.
- **PIN-005** — state `released` — last merge `recorded_at` `2026-03-24T02:51:44Z`
  - Web app Clerk integration: add @clerk/clerk-react (or current package), replace custom login/register with Clerk UI, protect gallery/upload routes, inject session tokens into the Axios (or equivalent) API client.
- **PIN-006** — state `released` — last merge `recorded_at` `2026-03-24T03:15:24Z`
  - Mobile Clerk integration: add @clerk/clerk-expo, wire Google and Apple sign-in per PRD, pass session tokens to the existing sync API client, and verify background sync still runs under authenticated session.
- **PIN-007** — state `released` — last merge `recorded_at` `2026-03-24T12:11:43Z`
  - Enforce per-user storage_quota_bytes on upload: check storage_used_bytes vs quota before accepting new assets, return a clear 413/409 (or documented status), and increment usage consistently with deduplication rules.
- **PIN-008** — state `released` — last merge `recorded_at` `2026-03-24T00:00:00Z`
  - Hash album share-link passwords with bcrypt before persistence: migrate existing plaintext passwords if any, verify on share access, and keep API backward-compatible for clients except stronger security guarantees.
- **PIN-009** — state `released` — last merge `recorded_at` `2026-03-24T12:12:28Z`
  - Thumbnail and preview pipeline: Celery tasks generate WebP (or configured) previews after upload, store paths in metadata, and expose sizes required by the web gallery; handle failures with retries and idempotency.
- **PIN-010** — state `released` — last merge `recorded_at` `2026-03-24T12:33:52Z`
  - PostgreSQL full-text search: add pg_trgm (or agreed FTS) indexes and query paths for FR-SRCH-05; wire search endpoint to use trigram ranking; Alembic migration is reversible or documented.
