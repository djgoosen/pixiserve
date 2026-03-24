# Sprint 1

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

## Retrospective

### Meta

- **Date / time**: 2026-03-24
- **Scope**: sprint-1 wrap

### Stats

- **PB-1 artifact bundle:** `pinion/sprints/artifacts/sprint-1/`

- **Lines added** (sum): 5250
- **Net lines** (sum): -55453
- **Estimated input tokens** (sum): 1273

| id | lines added | net lines | est. input tok. | recorded_at |
| --- | --- | --- | --- | --- |
| PIN-010 | 1043 | -11143 | 177 | 2026-03-24T12:33:52Z |
| PIN-009 | 1018 | -11193 | 185 | 2026-03-24T12:12:28Z |
| PIN-007 | 1018 | -11193 | 176 | 2026-03-24T12:11:43Z |
| PIN-006 | 1009 | -11213 | 176 | 2026-03-24T03:15:24Z |
| PIN-002 | — | — | — | 2026-03-24T03:00:00Z |
| PIN-005 | 432 | -3532 | 182 | 2026-03-24T02:51:44Z |
| PIN-004 | 383 | -3580 | 189 | 2026-03-24T02:42:47Z |
| PIN-003 | 347 | -3599 | 188 | 2026-03-24T02:38:27Z |
| PIN-001 | — | — | — | 2026-03-24T02:30:00Z |
| PIN-008 | — | — | — | 2026-03-24T00:00:00Z |

### What happened

Sprint 1 completed the full v0.2 auth and media/search foundation: Clerk is end-to-end on API/web/mobile, share-link passwords are bcrypt-hashed, upload quota enforcement is in place, thumbnail/preview processing is wired through Celery, and pg_trgm-based search ranking plus migration landed. We also closed all in-scope PINs (001-010) and generated retro artifacts/state updates.

### Notes

Next frontier target after sprint close is `PIN-010` follow-on work for search quality/perf hardening and migration operational polish. Keep Android usage/docs updates and auth flow guidance synced with future mobile releases.
