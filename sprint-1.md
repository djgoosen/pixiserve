# Sprint 1: Android app v1 (foundation)

**Timebox:** (set dates)  
**Sprint goal:** Ship a credible **Android-first** Pixiserve companion: sign in, browse server library, and run **reliable manual backup** from device photos/videos toward PRD §11.2 / roadmap path to v0.3 Mobile GA.

**Product context:** [product.md](../product/product.md) — v0.1 foundation on server; mobile’s v1 role is background-oriented sync; risks call out **resumable uploads** and **correct hashing**.

---

## Current state (codebase snapshot)

- **Tabs:** Photos (server gallery), Settings (account + backup/sync controls).
- **Auth / API:** JWT + configurable `serverUrl` (`mobile/src/services/api.ts`, `authStore`).
- **Sync:** `syncService.ts` scans MediaLibrary, batches hash check via `POST /sync/check`, uploads via `POST /assets`; WiFi-only and video toggles in `syncStore`; **hashing reads whole file as base64** (memory risk, noted in code comments).
- **Gaps:** `registerDevice()` uses placeholders for device name / id / platform; no true background task scheduling documented in-sprint; failed uploads are logged but not retried as a queue; PRD risk on interrupted uploads still open.

---

## In scope

1. **Android v1 usability:** Polish login → server URL → gallery → settings flow for daily dogfooding on a physical device or emulator.
2. **Backup correctness:** Replace or constrain hashing so large photos/videos do not load entirely into memory; align with server dedup (SHA256) semantics.
3. **Device identity:** Real Android device id / name / `device_type` for `POST /sync/devices` so sync metadata is traceable.
4. **Failure handling (minimal):** Surface upload failures in UI; persist a small “failed items” or retry hint so one flaky upload does not look like success.

## Out of scope (defer)

- Play Store / internal track release mechanics (track under “release prep” spike if needed).
- iOS parity (Expo project supports it; treat as follow-up sprint unless capacity appears).
- True OS-level background sync / foreground service (Expo constraints — spike only if sprint goal shifts).
- Offline gallery of **local** thumbnails only (PRD v0.3 “offline gallery view”).

---

## User stories

| ID | Story | Acceptance criteria (high level) |
|----|--------|-----------------------------------|
| S1-01 | As a user, I connect to my server and sign in. | Valid server URL, login/register, token stored, errors shown clearly. |
| S1-02 | As a user, I see my server library on Android. | Grid loads, pull-to-refresh, pagination; thumbnail URLs work with auth if required by API. |
| S1-03 | As a user, I back up new photos to Pixiserve. | Grant media permission; “Sync now” uploads only **missing** hashes per server; progress and completion state visible. |
| S1-04 | As a user, I control when backup runs. | WiFi-only toggle respected; optional video sync toggle respected. |
| S1-05 | As an operator, I can identify the device on the server. | Device registration sends stable id + real model/name + `android` platform. |

---

## Technical tasks (suggested order)

1. **Hashing:** Implement chunked SHA256 (or documented native approach) in `syncService.ts`; verify against backend dedup expectations.
2. **Device registration:** Wire `expo-application` / `expo-device` (or platform APIs) in `registerDevice()`; call from post-login path if API requires it.
3. **Upload reliability (v1):** After failed `POST /assets`, increment visible error state; optional: queue retries for N attempts or expose “retry failed” in Settings.
4. **UX hardening:** Loading/empty/error states on Photos tab; confirm thumbnail auth headers if 401s appear on image URLs.
5. **QA checklist:** Large library (500+ items), video on/off, WiFi-only toggle, airplane mode mid-sync, server unreachable.

---

## Definition of Done

- Stories S1-01–S1-05 satisfied on **Android** with a running stack from `deploy/docker-compose.dev.yml` (or equivalent).
- No known crashers on sync path for common image sizes; memory use acceptable during hash phase (document test device if possible).
- Sprint retro notes captured (what to carry to Sprint 2: background tasks, resumable uploads, iOS).

---

## Risks & dependencies

| Risk | Mitigation |
|------|------------|
| Large-file hash memory | Chunked reads + streaming digest; cap concurrent hashing if needed. |
| Expo background limits | Keep “manual sync” as primary v1 path; document follow-up for `expo-task-manager` / native module. |
| Server API drift | Reconcile `mobile/src/services/api.ts` with `backend/app/api/v1/sync.py` and assets upload contract before locking AC. |

---

## Sprint backlog hygiene

- Move concrete feature ideas from [ideas.md](../backlog/ideas.md) only when they map to a sprint goal.
- Update [system.md](../architecture/system.md) when mobile sync flow stabilizes (sequence: client ↔ API ↔ worker).
