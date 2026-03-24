# Sprint excerpt

## 1. Sprint Goal

Ship the **v0.2 foundation**: Clerk-backed authentication end-to-end on API, web, and mobile (JWT verification, verified webhooks, local user sync, first-user admin), harden **album share-link passwords** with bcrypt, **enforce storage quotas** on upload, and land **thumbnail generation** plus **PostgreSQL trigram full-text search** so the stack matches the v0.2 roadmap in `pinion/product/product.md`.

## 2. In-Scope Chains

| Chain | Targets | Outcome |
| --- | --- | --- |
| Clerk auth (API → web → mobile) | PIN-001 → PIN-006 | FR-AUTH-01,03,06,09,10 and aligned `/me` + clients |
| Storage & media | PIN-007, PIN-009, PIN-010 | FR-AUTH-07 enforcement; FR-ASSET-03; FR-SRCH-05 |
| Security hardening (parallel root) | PIN-008 | NFR: bcrypt share passwords before broader release |

## 3. Deferred Work

- OCR (FR-ML-10), family library mode (FR-ALB-07), hierarchical tag taxonomy UI (FR-ML-09), encryption at rest, pgvector migration, Kubernetes Helm — later phases per roadmap.
- Clerk JWKS caching / outage degradation — document or thin follow-up unless blocking MVP sign-in.

## 4. Critical Path

`PIN-001` → `PIN-002` → `PIN-003` → `PIN-004` → `PIN-005` → `PIN-006` (full Clerk vertical slice).

Secondary path for search quality: `PIN-004` → `PIN-009` → `PIN-010`.

## 5. Root Targets

- **PIN-001** — Clerk configuration and API JWT verification (JWKS / Clerk SDK).
- **PIN-008** — Bcrypt hashing for album share-link passwords (independent security track).

## 6. Risks

| Risk | Mitigation |
| --- | --- |
| Clerk outage / JWKS fetch failures | Short TTL cache in follow-up; document required env vars and health expectations |
| Breaking existing local-auth users during cutover | Feature-flag or staged removal; migration notes in target proofs |
| Thumbnail pipeline load | Celery concurrency and idempotent jobs; reuse existing worker patterns |
| FTS migration on large DB | Alembic migration with concurrent index strategy if needed |

## 7. Owner-Class Summary

All sprint targets use **`owner_class`: `default`** (single full-stack executor per repo config). Split backend vs frontend `owner_class` later if the team adds agents.

## Target index

| ID | Depends on | Summary |
| --- | --- | --- |
| PIN-001 | — | Clerk env/settings + API JWT verification |
| PIN-002 | PIN-001 | Clerk webhook + Svix signature verification |
| PIN-003 | PIN-002 | Local `User` sync + first-user admin |
| PIN-004 | PIN-003 | Remove legacy local auth; Clerk-only `/me` and guards |
| PIN-005 | PIN-004 | Web: `@clerk/clerk-react` + API token injection |
| PIN-006 | PIN-005 | Mobile: `@clerk/clerk-expo` + Google/Apple |
| PIN-007 | PIN-004 | Enforce `storage_quota_bytes` on upload |
| PIN-008 | — | Bcrypt album share-link passwords |
| PIN-009 | PIN-004 | Thumbnail/preview pipeline (Celery, WebP) |
| PIN-010 | PIN-009 | Full-text search (pg_trgm) |
