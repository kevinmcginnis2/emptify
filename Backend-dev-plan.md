# Emptify — Backend Development Plan

## 1️⃣ Executive Summary

- Builds a FastAPI backend for the existing SnapDev-generated Emptify frontend (`frontend/`, Next.js, port 3000, dummy data in `frontend/lib/emptify/data.ts`)
- Backend: FastAPI, Python 3.14, fully async, lives in a new top-level `backend/` folder, sibling of `frontend/`
- Database: MongoDB Atlas only, accessed via Motor, all documents modeled with Pydantic v2
- No Docker, no Celery, no queues — background work (delayed send/archive with undo, voice-profile rebuild) uses FastAPI `BackgroundTasks` only where strictly necessary; everything else is synchronous
- Repo already exists with git history on branch `main` — no `git init`, no new root `.gitignore` or root `package.json`; only Python entries are appended to the existing root `.gitignore`
- API is served under `/api/v1/*`, backend on port `8000`, frontend stays on port `3000`
- Manual testing (via the running frontend UI) is required after every task, not just after every sprint
- **Deviation from the generic template, called out explicitly:** the PRD (`PRD.md`) states under "What to leave out for now" that v1 has *no real accounts, invites, or auth* — role selection between Exec and EA is a plain view toggle. The frontend has no signup/login screens. Building JWT signup/login per the generic template would add a feature the frontend never shows and the PRD explicitly excludes. Sprint S1 is therefore **Role Context & Actor Identity**, not JWT auth: no password, no token, no protected routes — just a header the frontend already-existing role toggle sends, used only to attribute audit-log entries to a named human ("Mara Lindqvist" for Exec, "Theo Banks" for EA), matching the names already hardcoded in the frontend copy
- Two real integrations are required because the PRD demands real behavior, not mocked behavior: **Gmail API** (OAuth, read, send, archive — "the first thing to build" per the PRD) and **an LLM provider (Anthropic Claude API)** for voice-profile analysis, triage classification, draft generation, and the three tone rewrites
- Dynamic sprint plan: S0 → S8, one sprint per major frontend feature area, each ending with a push to `main` after manual verification

---

## 2️⃣ In-Scope & Success Criteria

**In scope (all features visible in the frontend):**
- Connect inboxes: 3 Gmail accounts, connection status, last sync, editable internal domains, reconnect flow
- Voice profiles: client-facing and internal profiles, sample size, extracted traits, editable notes, rebuild-from-last-90-days
- Triage board: unified list across accounts, Today / This Week / Can Wait buckets with counts, one-line reason, source-account badge, account filter, suggested-handoff chip
- Email detail / compose: thread view, bucket + reason, voice badge + why, editable draft, Shorter / Warmer / Firmer tone controls with revert, Send / Hand to EA / Archive / Skip / Mark ready action bar (role- and status-gated)
- Confirm-send dialog (FROM/TO) and toast with 10–15s undo on Send and Archive
- Hand-to-EA dialog (one-line note)
- EA queue: handed-off threads with the exec's note and current draft
- Ready to send: exec's return lane showing the assistant's edited draft and what changed
- Nav bar: role toggle (Exec/EA), With EA count, Ready to send count
- Audit log (not a screen, but explicitly required by the PRD as an output covering the full handoff → edit → mark-ready → send chain)

**Explicitly out of scope (per PRD "What to leave out for now"):** autonomous sending (no AI ever sends without an explicit human click — see the S8 revision note below for why "assistant sending" specifically was later relaxed), permission tiers, delete/unsubscribe, freeform tone box, a 4th tone preset, Microsoft 365, real user accounts/invites/auth, learning from edits over time, calendar/scheduling/tasks/CRM, search/labels/attachments/snooze/scheduled send, more than 2 voice modes, mobile.

**Success Criteria:**
- All frontend features functional end-to-end against the real backend, dummy data fully replaced
- All task-level manual tests pass via the UI
- Each sprint's code pushed to `main` only after its manual tests pass

---

## 3️⃣ API Design

- Base path: `/api/v1`
- Actor header: every mutating request from the frontend sends `X-Role: exec` or `X-Role: ea` (no session, no token — this is the full extent of "auth" in v1, per PRD)
- Error envelope: `{ "error": "message" }` on all 4xx/5xx
- Filtering: `account` filter on the board list only (the only filter visible in the UI)
- No pagination anywhere (none of the frontend screens show pagination controls)

**Accounts**
- `GET /api/v1/accounts` — list connected accounts. Response: array of `{id, name, type, email, status, lastSync, internalDomains}`
- `GET /api/v1/accounts/connect` — returns `{authUrl}` to start Google OAuth for a new account
- `GET /api/v1/accounts/oauth/callback` — Google redirects here with `code`; backend exchanges it, stores tokens, upserts the account, redirects browser back to `frontend` Connect screen
- `PATCH /api/v1/accounts/{account_id}` — body `{internalDomains: string}`; validation: string, may be empty
- `POST /api/v1/accounts/{account_id}/reconnect` — returns `{authUrl}` to restart OAuth for a lapsed account

**Voice profiles**
- `GET /api/v1/voice` — returns `{client: VoiceProfile, internal: VoiceProfile}`
- `PATCH /api/v1/voice/{mode}` — `mode` is `client` or `internal`; body `{notes: string}`; validation: `mode` must be one of the two values
- `POST /api/v1/voice/{mode}/rebuild` — kicks off a `BackgroundTasks` rebuild (re-pulls last 90 days Sent, re-analyzes via LLM), immediately sets `rebuilding=true` and returns the profile; frontend polls `GET /api/v1/voice` until `rebuilding=false`

**Threads (triage board / queue / ready lane / detail, one resource)**
- `GET /api/v1/threads?status=board&account=kestrel` — board list; `status` required (`board`, `withEA`, `readyToSend`); `account` optional filter; performs a lightweight incremental Gmail sync for the caller's connected accounts before returning
- `GET /api/v1/threads/{id}` — full thread detail (messages, draft, bucket, reason, voice info, status)
- `PATCH /api/v1/threads/{id}/draft` — body `{draft: string}`; inline edit, no side effects
- `POST /api/v1/threads/{id}/tone` — body `{tone: "shorter"|"warmer"|"firmer"}`; calls the LLM with the active voice profile, pushes the prior draft onto `versionStack`, returns the new draft; validation: thread must be in a status where editing is allowed (`board`, `withEA`, `readyToSend`)
- `POST /api/v1/threads/{id}/revert` — pops `versionStack`, restores the prior draft; 409 if the stack is empty
- `POST /api/v1/threads/{id}/handoff` — body `{note: string}`; requires `X-Role: exec`; sets `status=withEA`, `eaNote`, `draftAtHandoff`; writes an audit entry
- `POST /api/v1/threads/{id}/send` — requires `X-Role: exec`; thread must be `board` or `readyToSend`; optimistically sets `status=sent` and schedules the real Gmail send via `BackgroundTasks` after a 12s undo window; writes an audit entry when the real send fires
- `POST /api/v1/threads/{id}/archive` — requires `X-Role: exec`; thread must be `board`; same delayed-dispatch/undo pattern as send, calling Gmail archive instead
- `POST /api/v1/threads/{id}/skip` — requires `X-Role: exec`; thread must be `board`; immediate `status=skipped`, no Gmail call
- `POST /api/v1/threads/{id}/undo` — cancels a pending send/archive dispatch if it hasn't fired yet and restores `prevStatus`; 409 if the action already dispatched
- `POST /api/v1/threads/{id}/mark-ready` — requires `X-Role: ea`; thread must be `withEA`; sets `status=readyToSend`, `draftAuthor=ea`, computes `eaChangeSummary` by diffing `draft` against `draftAtHandoff`; writes an audit entry

**Audit log (verification-only — no frontend screen consumes this; included because the PRD requires the log as an output)**
- `GET /api/v1/audit/{thread_id}` — returns the ordered list of audit entries for one thread, for manual verification by opening the URL directly in the browser

---

## 4️⃣ Data Model (MongoDB Atlas)

**`accounts` collection** — one document per connected Gmail account
- `_id` (str, slug, e.g. `"kestrel"`)
- `name` (str, required)
- `type` (str, required, e.g. `"Work"`)
- `email` (str, required)
- `status` (str, required: `connected` | `expiring` | `reconnect`)
- `last_sync` (datetime, required)
- `internal_domains` (str, default `""`)
- `oauth_refresh_token` (str, required, never returned to the frontend)
- `oauth_access_token` (str, required, never returned to the frontend)
- `oauth_expires_at` (datetime, required)

Example:
```json
{"_id": "kestrel", "name": "Kestrel Partners", "type": "Work", "email": "mara@kestrelpartners.com", "status": "connected", "last_sync": "2026-08-21T14:02:00Z", "internal_domains": "kestrelpartners.com"}
```

**`threads` collection** — one document per triaged email thread; messages embedded (always read together with the thread, never queried independently)
- `_id` (str)
- `account_id` (str, required, references `accounts._id`)
- `account_label` (str, required)
- `account_email` (str, required)
- `from_name` (str, required)
- `from_email` (str, required)
- `subject` (str, required)
- `bucket` (str, required: `today` | `week` | `wait`)
- `reason` (str, required)
- `voice_mode` (str, required: `client` | `internal`)
- `voice_why` (str, required)
- `messages` (array of `{from: str, at: str, body: str}`, required, embedded)
- `draft` (str, required)
- `draft_author` (str, required: `emptify` | `ea`)
- `version_stack` (array of str, default `[]`)
- `handoff_suggested` (bool, default `false`)
- `handoff_reason` (str, default `""`)
- `status` (str, required: `board` | `withEA` | `readyToSend` | `sent` | `archived` | `skipped`)
- `prev_status` (str, optional — set while a send/archive/skip undo window is open)
- `ea_note` (str, default `""`)
- `ea_change_summary` (str, default `""`)
- `draft_at_handoff` (str, default `""`)
- `gmail_thread_id` (str, required, Gmail's own thread id)
- `pending_action` (str, optional: `send` | `archive`, cleared once dispatched or undone)
- `pending_dispatch_at` (datetime, optional — when the background task will actually call Gmail)

Example:
```json
{"_id": "e1", "account_id": "kestrel", "subject": "Term sheet redline — need this back today", "bucket": "today", "reason": "Counterparty needs the signed redline by 5pm today.", "voice_mode": "client", "draft": "Priya — thanks for the quick turnaround...", "draft_author": "emptify", "status": "board", "gmail_thread_id": "18c9f2a1b3d4e5f6"}
```

**`voice_profiles` collection** — exactly 2 documents, one per mode
- `_id` (str: `client` | `internal`)
- `sample_size` (str, required, display string e.g. `"58 of 214 sent emails (last 90 days)"`)
- `rebuilding` (bool, default `false`)
- `notes` (str, default `""`)
- `traits` (array of `{label: str, value: str}`, required)

Example:
```json
{"_id": "client", "sample_size": "58 of 214 sent emails (last 90 days)", "rebuilding": false, "notes": "Keep replies to clients short.", "traits": [{"label": "Sentence length", "value": "Short — averages 14 words per sentence"}]}
```

**`audit_log` collection** — append-only, one entry per action in the handoff/send chain
- `_id` (ObjectId)
- `thread_id` (str, required)
- `actor` (str, required: `"Mara Lindqvist"` | `"Theo Banks"`)
- `action` (str, required: `handoff` | `edit` | `mark_ready` | `send` | `archive` | `skip`)
- `account_email` (str, optional — the FROM account for send)
- `detail` (str, default `""`)
- `at` (datetime, required)

Example:
```json
{"thread_id": "e7", "actor": "Mara Lindqvist", "action": "handoff", "detail": "Just find a date that works for most people, keep it simple.", "at": "2026-08-21T09:15:00Z"}
```

---

## 5️⃣ Frontend Audit & Feature Map

- **`ConnectScreen` (`connect`)** — lists Gmail accounts with status/last sync/internal domains, reconnect button → `GET/PATCH/POST /api/v1/accounts*`, `accounts` collection. No auth requirement beyond `X-Role: exec` (nav only shows this to Exec)
- **`VoiceScreen` (`voice`)** — 2 profiles, notes edit, rebuild button → `GET/PATCH /api/v1/voice*`, `voice_profiles` collection. Exec only
- **`BoardScreen` + `EmailCard` (`board`)** — 3 bucket columns, account filter, handoff chip → `GET /api/v1/threads?status=board`, `threads` collection. Exec only
- **`DetailScreen` (`detail`)** — thread + draft + tone controls + action bar → `GET /threads/{id}`, `PATCH .../draft`, `POST .../tone`, `.../revert`, `.../send`, `.../handoff`, `.../archive`, `.../skip`, `.../mark-ready`. Action-bar buttons are gated by `role` + `status`, mirrored server-side by the `X-Role` check
- **`QueueScreen` (`queue`)** — withEA threads with exec's note and draft preview → `GET /api/v1/threads?status=withEA`, `X-Role: ea` view
- **`ReadyScreen` (`ready`)** — readyToSend threads with EA's change summary → `GET /api/v1/threads?status=readyToSend`, Exec view
- **`ConfirmSendDialog`** — reads `account_email` (FROM) and `from_email` (TO) already on the thread object, no separate endpoint
- **`HandoffDialog`** — posts the one-line note via `POST .../handoff`
- **`NavBar`** — `withEACount`/`readyCount` are just `len()` of the two list responses above, computed client-side same as today; role toggle is pure client state plus the `X-Role` header on subsequent calls
- **`EmptifyToast`** — undo button calls `POST /api/v1/threads/{id}/undo` for send/archive; for skip, undo can just re-PATCH status since nothing was dispatched to Gmail

---

## 6️⃣ Configuration & ENV Vars

Backend — `backend/.env` (gitignored, never committed):
- `APP_ENV` — `development` | `production`
- `PORT` — `8000`
- `MONGODB_URI` — MongoDB Atlas connection string
- `CORS_ORIGINS` — must include `http://localhost:3000`
- `GOOGLE_CLIENT_ID` — Gmail OAuth client id
- `GOOGLE_CLIENT_SECRET` — Gmail OAuth client secret
- `GOOGLE_REDIRECT_URI` — `http://localhost:8000/api/v1/accounts/oauth/callback`
- `ANTHROPIC_API_KEY` — LLM provider key for voice/triage/draft/tone
- `ANTHROPIC_MODEL` — pinned model id, default `claude-sonnet-5`

Frontend — `frontend/.env.local`:
- `NEXT_PUBLIC_API_URL` — `http://localhost:8000`

Note: `JWT_SECRET` / `JWT_EXPIRES_IN` from the generic template are intentionally omitted — there is no JWT in this build (see the Executive Summary deviation note).

---

## 7️⃣ Background Work

- **Delayed send/archive dispatch (`BackgroundTasks`)** — triggered by `POST /threads/{id}/send` or `.../archive`. Purpose: match the frontend's existing 12-second undo toast without needing a real "unsend" from Gmail. The task sleeps until `pending_dispatch_at`, then re-reads the thread; if `pending_action` is still set (i.e., not cancelled by `/undo`), it calls the real Gmail API (send or archive) and writes the audit entry; if cleared, it's a no-op. Idempotent by construction — it only acts if `pending_action` is still present, so a duplicate task run does nothing
- **Voice profile rebuild (`BackgroundTasks`)** — triggered by `POST /voice/{mode}/rebuild`. Purpose: re-pull last 90 days of Sent for the relevant domains and re-run the LLM analysis without blocking the request. Sets `rebuilding=true` immediately, flips it back to `false` (with new `notes`/`traits`/`sample_size`) when the task completes. UI checks completion by polling `GET /api/v1/voice` (same pattern the frontend already uses for a spinner state, just backed by a real flag instead of a fixed timeout)
- Everything else (draft edits, tone rewrites, handoff, mark-ready, skip, board sync) is synchronous — each is a single user-triggered request/response with no reason to defer

---

## 8️⃣ Integrations

**Gmail API** (OAuth 2.0, scopes: `gmail.readonly`, `gmail.send`, `gmail.modify`)
- Connect flow: `GET /accounts/connect` → Google consent screen → `GET /accounts/oauth/callback` exchanges the code, stores refresh/access tokens, upserts the account doc
- Sync: on each `GET /threads?status=board` call, do an incremental fetch (Gmail History API since the account's last stored `historyId`, or a simple `INBOX` list scoped to messages after `last_sync` if history tracking isn't set up yet) for any account with `status=connected`; new messages are classified (see below) and inserted as new `threads` docs with `status=board`
- Send: real `users.messages.send` from the thread's `account_email`, only fired by the background dispatch task after the undo window
- Archive: real `users.messages.modify` removing `INBOX` label, same delayed-dispatch pattern

**Anthropic Claude API** (`ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL`)
- Voice profile builder: summarizes up to 90 days of a Sent-mail sample (noise-filtered: drop short replies, forwards, auto-responses; split by recipient domain using each account's `internal_domains`) into the `sample_size`, `traits`, and default `notes` fields
- Triage classification: for each newly synced message, produces `bucket`, `reason`, `voice_mode`, `voice_why`, `handoff_suggested`, `handoff_reason`, and an initial `draft` written in the matching voice profile
- Tone rewrites: given the current `draft` and the active voice profile, rewrites for `shorter` / `warmer` / `firmer` while staying inside that profile — mirrors the fixed three-preset rule in the PRD exactly, no freeform prompt

---

## 9️⃣ Testing Strategy (Manual via Frontend)

- All verification happens by using the running frontend at `http://localhost:3000` (or, for the one verification-only audit endpoint, by opening its URL directly)
- Every task below carries its own **Manual Test Step** and **User Test Prompt**
- Once every task in a sprint passes, commit and push to `main`
- If any task fails, fix and retest before pushing — never push a sprint with a failing task

---

## 🔟 Dynamic Sprint Plan & Backlog (S0 → S8)

### 🧱 S0 — Environment Setup & Frontend Connection

**Objectives:**
- Create `backend/` as a sibling of `frontend/`
- Pin and verify Python 3.14 (`backend/.python-version`), create `backend/.venv`
- FastAPI skeleton (`backend/app/main.py`) with `/api/v1` router mount and `/healthz`
- Connect to MongoDB Atlas via Motor; `/healthz` pings the DB and reports status
- CORS enabled for `http://localhost:3000`
- `frontend/.env.local` created with `NEXT_PUBLIC_API_URL=http://localhost:8000`
- Append `__pycache__/`, `*.pyc`, `.env`, `.venv/` to the existing root `.gitignore` (do not recreate it)
- Confirm branch is `main`, push

**Tasks:**
- Create `backend/app/{api/v1,models,schemas,services}` folders, `.python-version` = `3.14`
  - Manual Test Step: n/a (structural) — verified by the next task actually running
  - User Test Prompt: "Confirm the `backend/` folder exists next to `frontend/` with the app/api/v1, app/models, app/schemas, app/services subfolders."
- Create venv, pin `requirements.txt` with `==`, verifying each package has a Python 3.14 wheel
  - Manual Test Step: run `pip install -r backend/requirements.txt` inside `backend/.venv` with no errors
  - User Test Prompt: "Install backend dependencies and confirm there are no version/wheel errors."
- Build `backend/app/main.py`: FastAPI app, `/api/v1` router, `/healthz` (pings Mongo), CORS middleware for `http://localhost:3000`
  - Manual Test Step: start backend (`cwd: backend`), open `http://localhost:8000/healthz` in a browser tab → JSON `{"status": "ok", "db": "connected"}`
  - User Test Prompt: "Start the backend and open http://localhost:8000/healthz. Confirm it returns a JSON success status with the database connected."
- Create `frontend/.env.local`; start frontend, confirm it still boots unchanged on port 3000
  - Manual Test Step: run frontend (`cwd: frontend`), open `http://localhost:3000`, confirm the app renders exactly as before (dummy data still showing at this point — wiring happens per-sprint below)
  - User Test Prompt: "Start the frontend and confirm it loads on port 3000 with no console errors."
- Append Python entries to the existing root `.gitignore`; confirm on `main`; push
  - Manual Test Step: `git status` shows no `.venv`/`__pycache__`/`.env` as trackable, then push succeeds
  - User Test Prompt: "Confirm `.venv` and `.env` don't show up in `git status`, then confirm the push to main succeeded."

**Definition of Done:** backend runs on 8000 under Python 3.14, connects to MongoDB Atlas, `/healthz` succeeds, frontend unchanged on 3000, pushed to `main`.

---

### 🧩 S1 — Role Context & Actor Identity (No Real Auth — PRD Descope)

**Objectives:**
- No signup/login pages, no JWT, no password storage — the PRD explicitly excludes real auth for v1
- Backend accepts `X-Role: exec` or `X-Role: ea` on every mutating request and maps it to a fixed actor name (`Mara Lindqvist` / `Theo Banks`) for audit-log attribution only
- Frontend's existing role toggle (already in `NavBar`) is wired to send that header — no new UI

**Tasks:**
- Add an `X-Role` dependency in `backend/app/api/v1` that 400s if missing/invalid on any mutating route
  - Manual Test Step: in the browser devtools console, call a mutating endpoint (e.g. skip a card) with the toggle on Exec, then flip to EA and try `mark-ready` on a card not in `withEA` — confirm the exec-only/ea-only actions are rejected for the wrong role
  - User Test Prompt: "Toggle to EA in the nav bar, open a board card, and confirm Send/Handoff/Archive/Skip are not available — only Mark ready is, and only for withEA threads."
- Update the frontend's fetch wrapper to send `X-Role` on every mutating call based on the current role toggle
  - Manual Test Step: hand off a card as Exec, then switch to EA and mark it ready — confirm the audit log (via `GET /api/v1/audit/{id}`) shows `Mara Lindqvist` then `Theo Banks` as actors
  - User Test Prompt: "Hand a card to EA, switch roles, mark it ready, then open http://localhost:8000/api/v1/audit/<that-thread-id> and confirm both actions are attributed to the right person."

**Definition of Done:** every mutating call carries the correct actor; wrong-role calls are rejected; audit entries show the correct human name. Push to `main`.

---

### 🔌 S2 — Gmail OAuth Connection & First Real Send

**Objectives:** the PRD's stated first priority — one Gmail account connected, syncing, and able to send one real email, before anything else is built on top.

**Tasks:**
- Implement `GET /accounts/connect` and `GET /accounts/oauth/callback`, storing tokens in `accounts`
  - Manual Test Step: from the Connect screen, click a (temporary, single-account) connect button, complete Google consent, land back on the Connect screen showing status `Connected`
  - User Test Prompt: "Connect your first Gmail account through the real Google sign-in screen and confirm it shows as Connected with a recent last-sync time."
- Implement the delayed-send background task against this one real account (`POST /threads/{id}/send`, `BackgroundTasks`, 12s window, `/undo`)
  - Manual Test Step: open any thread on the connected account, hit Send, confirm the dialog, wait past 12 seconds without clicking Undo, then check that account's real Gmail Sent folder for the message
  - User Test Prompt: "Send a test email from the app, wait 15 seconds, and confirm it actually appears in that Gmail account's Sent folder."
- Implement `/undo` cancelling a pending send
  - Manual Test Step: send another test thread, click Undo within the 12-second window, confirm the Gmail account's Sent folder does NOT receive it and the thread returns to its prior status
  - User Test Prompt: "Send another test email but click Undo immediately. Confirm nothing arrives in Sent and the card returns to the board."

**Definition of Done:** one real Gmail account connects, and a real send (undoable within the window) lands in that account's Sent folder. Push to `main`.

---

### 🔗 S3 — Multi-Account Connect Inboxes Screen

**Objectives:** full Connect screen — 3 accounts, status panel, reconnect, editable internal domains.

**Tasks:**
- Extend accounts flow to support connecting all 3 accounts (Kestrel, Northwind, Personal), each showing real `status`/`lastSync`
  - Manual Test Step: connect the remaining 2 Gmail accounts through the Connect screen; confirm all 3 show with correct status and last-sync
  - User Test Prompt: "Connect all three accounts and confirm each card shows the right status and a recent sync time."
- Implement `PATCH /accounts/{id}` for internal domains
  - Manual Test Step: edit the internal domains field for one account, refresh the page, confirm the value persisted
  - User Test Prompt: "Change the internal domains field on one account, refresh the page, and confirm your edit is still there."
- Implement `POST /accounts/{id}/reconnect` for an expired/lapsed token
  - Manual Test Step: force one account's token to expire (or simulate via the account doc), click Reconnect, complete consent, confirm status flips back to Connected
  - User Test Prompt: "Click Reconnect on an account showing 'Reconnect needed' and confirm it flips to Connected after you sign in again."

**Definition of Done:** all 3 accounts connect and display live status; domains editable and persisted; reconnect flow works. Push to `main`.

---

### 🗣️ S4 — Voice Profile Builder

**Objectives:** real 90-day Sent analysis producing the two editable voice profiles.

**Tasks:**
- Implement the Sent-mail pull + noise filter (drop short replies/forwards/auto-responses) + domain split using each account's `internal_domains`
  - Manual Test Step: open Voice profiles screen after the accounts are connected; confirm both profiles show a real (non-placeholder) sample size
  - User Test Prompt: "Open Voice profiles and confirm the sample sizes reflect your real sent mail, not the old demo numbers."
- Implement the LLM trait extraction into `traits` + default `notes`
  - Manual Test Step: confirm each profile shows 6 populated traits (sentence length, greeting, sign-off, formality, hedging, characteristic phrases) that plausibly match your actual sent mail
  - User Test Prompt: "Read the extracted traits on both profiles and confirm they sound like a real description of how you write."
- Implement `PATCH /voice/{mode}` for notes editing
  - Manual Test Step: edit the notes field, refresh, confirm it persisted
  - User Test Prompt: "Edit the notes on one profile, refresh, and confirm your edit stuck."
- Implement `POST /voice/{mode}/rebuild` as a background task with polling
  - Manual Test Step: click Rebuild, confirm the button shows "Rebuilding…" and the profile refreshes with new data once the background task completes
  - User Test Prompt: "Click 'Rebuild from last 90 days' and confirm the button shows a loading state, then updates with fresh data."

**Definition of Done:** both profiles reflect real Sent mail, are editable, and rebuild correctly in the background. Push to `main`.

---

### 📋 S5 — Unified Triage Engine & Board

**Objectives:** real incoming-mail sync and LLM-driven bucketing across all 3 accounts.

**Tasks:**
- Implement incremental incoming-mail sync on `GET /threads?status=board`, inserting new `threads` docs
  - Manual Test Step: send yourself a test email into one connected account from another mailbox, refresh the board, confirm the new thread appears
  - User Test Prompt: "Send a real test email into one of your connected inboxes, refresh the board, and confirm the new card shows up."
- Implement LLM bucket/reason/voice classification + handoff suggestion on new messages
  - Manual Test Step: confirm the new card lands in a sensible bucket (Today/This Week/Can Wait) with a one-line reason, and a Hand to EA chip that's pre-highlighted when the content looks like a scheduling request
  - User Test Prompt: "Confirm the new email landed in the right-looking bucket with a reason that makes sense, and check the handoff chip behaves as expected."
- Implement the account filter on `GET /threads?status=board&account=`
  - Manual Test Step: use the Account dropdown on the board, confirm the list narrows to only that account's threads
  - User Test Prompt: "Filter the board to a single account and confirm only that account's cards remain."

**Definition of Done:** real mail syncs in, gets bucketed with a reason, and the account filter works. Push to `main`.

---

### ✍️ S6 — Draft Generation & Tone Controls

**Objectives:** voice-matched drafts and the three tone rewrites on the Detail screen.

**Tasks:**
- Generate the initial `draft` at triage time in the classified `voice_mode`
  - Manual Test Step: open a newly-synced thread, confirm a draft reply is already present and reads in a voice consistent with the badge shown
  - User Test Prompt: "Open a new thread's detail view and confirm there's already a draft reply that sounds appropriate for the voice badge shown."
- Implement `PATCH /threads/{id}/draft` for inline edits
  - Manual Test Step: edit the draft textarea, navigate away and back, confirm the edit persisted
  - User Test Prompt: "Edit a draft, leave the screen, come back, and confirm your edit is still there."
- Implement `POST /threads/{id}/tone` for Shorter/Warmer/Firmer
  - Manual Test Step: click each of the three tone buttons in turn on the same draft, confirm each produces a visibly different rewrite that stays recognizably in the same voice
  - User Test Prompt: "Try Shorter, then Warmer, then Firmer on the same draft and confirm each one changes the tone as expected without losing the voice."
- Implement `POST /threads/{id}/revert` and the version stack
  - Manual Test Step: after 2 tone rewrites, click Revert twice, confirm the draft steps back through history correctly and the Revert arrow disappears once the stack is empty
  - User Test Prompt: "After trying two tone buttons, click Revert twice and confirm the draft goes back through your history correctly."

**Definition of Done:** drafts are voice-matched, editable, tone-rewritable, and revertible. Push to `main`.

---

### 📨 S7 — Send / Archive / Skip Actions

**Objectives:** the full action bar with real Gmail effects and the confirm/undo pattern, generalized from S2's single-account proof to all threads.

**Tasks:**
- Wire `POST /threads/{id}/send` + confirm dialog + undo to every board/readyToSend thread (builds on S2)
  - Manual Test Step: send a thread from each of the 3 accounts, confirm the dialog shows the correct FROM address each time, and each lands in the right account's Sent folder
  - User Test Prompt: "Send one email from each of your three connected accounts and confirm each one lands in the correct Gmail account's Sent folder."
- Implement `POST /threads/{id}/archive` with the same delayed-dispatch/undo pattern
  - Manual Test Step: archive a board thread, wait past the undo window, confirm the message is archived in that Gmail account (no longer in Inbox)
  - User Test Prompt: "Archive a card, wait 15 seconds, and confirm the message left the Inbox in Gmail."
- Implement `POST /threads/{id}/skip` (immediate, no Gmail call)
  - Manual Test Step: skip a card, confirm it disappears from the board and Gmail is untouched (message still in Inbox)
  - User Test Prompt: "Skip a card and confirm it's gone from the board but still sitting untouched in your Gmail inbox."
- Write audit entries for send/archive/skip once dispatched
  - Manual Test Step: after each action above, open `GET /api/v1/audit/{thread_id}` and confirm an entry with the right actor/action/timestamp exists
  - User Test Prompt: "After sending, archiving, and skipping a thread, check the audit endpoint for each thread id and confirm all three actions are logged."

**Definition of Done:** Send/Archive/Skip all work end-to-end with correct Gmail effects, undo works within the window, and every action is logged. Push to `main`.

---

### 🤝 S8 — Handoff Loop & EA Queue

**Objectives:** the PRD's differentiator — hand off, EA edits and marks ready, exec sends from the return lane. **Expanded mid-sprint** after a real product conversation while building it: the original PRD's "no assistant sending" descope (see Executive Summary / Section 2) turned out to be too strict for how an EA relationship actually works — an EA often just finishes the job rather than always looping back. Decided: once a thread is `withEA`, the EA gets *both* paths, their judgment per thread — Mark ready (loop back to exec) **or** Send/Archive/Skip it directly, using the exact same connected-account Gmail machinery already built (no separate EA-owned mailbox/identity — the EA operates the same account the exec always has). Also added: mutual read-only monitoring — the exec can see the EA's queue (no Mark Ready button), the EA can see "Ready to send" (no Send button), neither gaining new authority, just visibility. Reply-all/CC support was raised in the same conversation and explicitly deferred — noted in the S9 section below.

**Tasks:**
- Implement `POST /threads/{id}/handoff` + `HandoffDialog` wiring (exec-only, unchanged from original scope)
  - Manual Test Step: as Exec, hand off a board card with a note, confirm it disappears from the board and the With EA count in the nav bar increments
  - User Test Prompt: "Hand a card to EA with a note and confirm it leaves the board and the 'With EA' count goes up by one."
- Implement `GET /threads?status=withEA` for `QueueScreen`, now visible (read-only for Exec, actionable for EA) to both roles via a clickable nav link
  - Manual Test Step: switch role to EA, open the queue, confirm the handed-off card shows the exec's note and current draft; switch back to Exec, confirm "With EA" is now a clickable link into the same queue, read-only (no Mark Ready button)
  - User Test Prompt: "Switch to the EA role, open the queue, and confirm you see the note and draft for the card you just handed off. Then switch back to Exec and confirm you can click into the same queue to check on it, without being able to act on it."
- Implement `POST /threads/{id}/mark-ready` with a **real Anthropic-generated** `eaChangeSummary` (diffing `draftAtHandoff` against the final draft; short-circuits to "Reviewed as-is — no changes." with no LLM call when nothing changed)
  - Manual Test Step: as EA, edit the draft and click Mark ready, confirm it leaves the queue and the summary shown to the exec is specific, not generic
  - User Test Prompt: "As EA, tweak the draft and click Mark ready, and confirm it disappears from your queue."
- Implement `GET /threads?status=readyToSend` for `ReadyScreen`, now visible (actionable for Exec, read-only for EA) to both roles via a clickable nav link (new for EA — didn't exist before this sprint)
  - Manual Test Step: switch back to Exec, open Ready to send, confirm the card appears with a sensible change summary, then send it through the normal confirm/undo flow; switch to EA, confirm a new "Ready to send" link exists and shows the same card read-only (no Send button)
  - User Test Prompt: "Switch back to Exec, open Ready to send, confirm the card is there with a summary of what changed, then send it and confirm it lands in Sent. Then switch to EA and confirm you can now check whether it's been sent."
- **New:** relax `send`/`archive`/`skip` to also accept `X-Role: ea` when the thread is `withEA` (additive — exec's existing permissions on `board`/`readyToSend` are unchanged; EA still can't act on a `board` thread, exec still can't act on a `withEA` one)
  - Manual Test Step: hand a card to EA, then as EA send/archive/skip it directly without ever clicking Mark ready; confirm the real Gmail effect happens and the audit log attributes it to Theo Banks, not Mara Lindqvist
  - User Test Prompt: "Hand a card to EA, then as EA send it directly instead of marking it ready. Confirm it actually sends and the audit log shows Theo did it."

**Definition of Done:** the full handoff → (edit → mark-ready → send) **or** (EA sends/archives/skips directly) loop works end-to-end across both roles, both roles can monitor the other's queue read-only, and every step is reflected in the audit log with the correct actor. Push to `main`.

---

### 🔁 S9 — Two-Way Gmail Sync & Reply-All/CC

**Objectives:** of the 5 post-MVP candidates identified at the end of S8, a scoping conversation picked two to build now: two-way Gmail sync (the headline gap — sync was one-directional through S8) and reply-all/CC support. The other 3 (plaintext OAuth tokens, no CSRF `state` verification, sequential per-message sync) were carried forward to S10, along with a wildcard CORS change made outside this sprint (see below).

**Product decisions made before implementation:** a message deleted/trashed directly in Gmail → archive it in Emptify too (recoverable, consistent with the in-app Archive action). A reply landing directly in Gmail on a tracked thread → re-classify from scratch (append the message, re-run the triage LLM call), and — extending that decision — regardless of the thread's current status, not just "mid-triage" ones, since silently dropping a genuine new reply on a terminal thread would be worse than reopening it. Reply-all defaults on; the confirm-send dialog pre-fills Cc and lets it be edited/cleared before sending.

**What was built:**
- `backend/app/services/gmail.py` gained `get_current_history_id` (wraps `getProfile`) and `get_history` (wraps `users().history().list`, paginated, catches an expired-cursor `HttpError 404` and signals the caller to fall back). `send_message` gained an optional `cc_emails` param and now returns the Gmail API response (was `None`) so callers can read the sent message's id.
- `backend/app/services/triage.py`'s `sync_account_board` was restructured into three phases: `_bootstrap_sync` (the original date-based `after:` logic, unchanged, except it now mints a `history_id` on the account once a full pass completes without hitting the cap — this is how the 3 already-connected accounts migrated automatically, with no manual step), `_ingest_new_thread` (unchanged behavior, extracted for reuse), and two new paths driven by History API records: `_resync_existing_thread` (re-triages a known thread when a genuinely new message shows up on it) and `_mark_deleted_in_gmail` (archives a known thread on a real trash/delete). `_extract_messages` now also captures `messageId`, `to`, and `cc` per message (via `email.utils.getaddresses`, not regex), and a new thread-level `cc_emails` field holds the reply-all default.
- **Anti-loop fix required for correctness:** `dispatch_send` (`threads.py`) now appends the message it just sent into the thread's own `messages` array (tagged with its Gmail message id). Without this, Emptify's own sends would show up in the next History fetch as "genuinely new" and falsely reopen the thread it just sent. `_resync_existing_thread` treats a touched thread as having nothing new when every fresh message id is already present locally.
- Reply-all/CC: `send_thread` takes a `SendBody { cc: string[] }`, stored as `pending_cc` on the thread through the same undo-window lifecycle as `pending_action`. `_thread_response` exposes `ccEmails`. Frontend: `ConfirmSendDialog` gained an editable Cc field pre-filled from the thread's `ccEmails`; `detail-screen.tsx` shows a Cc line per message.
- `backend/app/models/audit.py`'s `Actor`/`Action` literals widened to include `"Emptify Sync"` and `sync_archive`/`sync_reclassify`, for attributing sync-triggered changes distinctly from human actions.
- **One real bug found during verification** (commit `521ae71`, after the main S9 commit): Gmail's own compose-then-send flow creates a transient `DRAFT` message object that gets deleted once the reply actually sends — the initial history-walk treated *any* `messagesDeleted` event as a real deletion, so every direct-Gmail reply was incorrectly archiving the thread instead of re-triaging it. Fixed by skipping `messagesDeleted` events where the message still carries the `DRAFT` label.
- Verified live end-to-end using self-directed test threads on `kevmcg22@gmail.com`: a direct-Gmail reply correctly re-triages (fresh bucket/reason/draft, `sync_reclassify` audit entry); a real `users().threads().trash()` call correctly archives (`sync_archive` audit entry); sending through Emptify does not falsely reopen its own thread on the next sync; a Cc'd test recipient round-tripped through `ccEmails` → the confirm dialog → a real sent Gmail message independently confirmed to carry the `Cc` header. Regression spot-check confirmed archive/skip/handoff/mark-ready/send all still work unchanged.

**Note on a concurrent, unrelated change:** mid-sprint, a second concurrent session (a different collaborating engineer working in the same repo) committed `cffd9db` "Allow CORS from all origins" (`allow_origin_regex=".*"` instead of the `cors_origins` allowlist) — intentional, done for that engineer's own access/review, not part of S9. Kept as-is per explicit direction; tracked in S10 as something to tighten back up later.

**Definition of Done:** two-way sync detects both external replies and external deletes/trashes without manual intervention, reply-all/CC works end-to-end with real Gmail confirmation, and all pre-existing flows (S1–S8) are unaffected. Pushed to `main`.

---

### 🔒 S10 — User Accounts & Login (+ Hardening Candidates)

**Objectives:** the app went live for testing after S9, and its complete absence of app-level authentication became an immediate real problem, not a theoretical one — anyone with the URL gets full read/write access to the real connected Gmail inboxes with no login screen in front of it. This is now the top-priority item in S10, ahead of the hardening candidates carried forward from the S9 scoping conversation. Not scoped in code-level detail yet — needs its own product conversation, same as every sprint before it.

**🔴 Top priority — unique user accounts & login (multi-tenancy).** Today there is no concept of a "user" anywhere in the system. `X-Role: exec|ea` (`backend/app/api/v1/deps.py`) is the *only* signal on any request — it's a plain header, trivially spoofable, and maps to two hardcoded actor names (`ACTOR_NAMES = {"exec": "Mara Lindqvist", "ea": "Theo Banks"}`) shared by literally anyone who loads the page. None of the Mongo collections (`accounts`, `threads`, `voice_profiles`, `audit_log`) have an owner/`user_id` field at all — they're global to the one database. Real scope, once a product conversation settles the open questions below:
- A `users` collection with real credentials — needs a decision: email/password (with proper hashing, e.g. `passlib`/`bcrypt`) vs. reusing "Sign in with Google" (the OAuth machinery for Gmail connect already exists, but conflates "who's logged into Emptify" with "which Gmail account is connected" — needs careful scope separation if chosen).
- A real session/auth layer (signed JWT or server-side session cookie) protecting every API route, replacing the current header-only `require_role`/`require_exec`/`require_ea` chain in `deps.py` with real verified identity.
- `user_id` added to every tenant-scoped collection and every single query in `backend/app/api/v1/` and `backend/app/services/` scoped to the authenticated user — this touches nearly the whole backend.
- The hardcoded `Mara Lindqvist`/`Theo Banks` actor names become per-tenant (each user picks their own exec/EA display names at setup) instead of fixed constants.
- Frontend: real signup/login screens gating everything ahead of the Connect screen, with session persistence.
- Open product questions for that conversation: password vs. Google-identity login; whether "exec" and "EA" become two separate logins sharing one company's board, or stay one login with the existing role-switcher; and what happens to the 3 already-connected Gmail accounts and their existing thread/audit history when this ships (a one-time migration assigning them to Kevin's own new account is the obvious default, but worth confirming).
- Depends on knowing the actual hosting setup (cookie domain, HTTPS, same-origin vs. cross-origin frontend/backend) — this session doesn't have visibility into how the live deployment is configured; confirm that at the start of this work.

**Other hardening candidates (carried forward from S9 scoping, lower priority than the above):**
- **Plaintext OAuth tokens** stored in Mongo (`backend/app/models/account.py`) — known simplification since S2. More relevant now that this is a live, hosted, multi-user-bound app rather than a local dev tool.
- **No CSRF `state` verification** on the OAuth callback (`backend/app/api/v1/accounts.py`) — same motivation as above.
- **CORS wide open** (`backend/app/main.py`'s `allow_origin_regex=".*"`, commit `cffd9db`) — intentionally loosened mid-S9 to give a collaborating engineer access/review (likely because the frontend and backend are hosted on different origins); worth tightening back to an explicit allowlist once that access is no longer needed.
- **Sequential per-message sync classification** (`triage.py` — one Gmail fetch + one Claude call per new/touched thread, in a loop). Only worth parallelizing if backlogs turn out to be common in practice.
- **Dev-server hygiene** — nothing currently detects or warns about a stale `uvicorn` process already squatting on port 8000; a fresh session can silently verify against stale code with no error beyond a log line (this cost real debugging time during S9 verification). Worth a lightweight fix — a startup port check, or just a documented restart step.

---

### 💳 S11+ — Trial Access & Stripe Billing (early look-ahead, not scoped)

**Objectives:** once S10's user accounts exist, add a timed trial period per user, gate access once it expires, and eventually require payment via Stripe to continue — explicitly a "couple of months out" item, tied to when Stripe gets connected, not something to start now. Captured here only so it isn't lost; needs its own real scoping conversation when it's actually time to build it.

**Rough shape (not yet a task list):**
- A trial clock per user (e.g. `users.trial_started_at`, length TBD — 14/30 days is typical but undecided) — depends entirely on S10's user accounts existing first.
- Access gating once the trial expires: some form of middleware/check blocking app functionality (or redirecting to an upgrade/access page) for a user with no active trial and no paid subscription.
- Stripe integration once connected: checkout flow for starting a subscription, webhook handling to keep subscription status in sync, and a customer portal for managing/canceling — none of this can start until the Stripe account itself is set up, which is explicitly deferred.
- An "access page" experience for trial-ended / not-yet-subscribed users, distinct from the login screen.

**Definition of Done:** TBD — this section exists to hold the idea, not to commit to an approach yet.
