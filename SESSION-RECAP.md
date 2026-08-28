# Emptify Build — Session Recap (through S6)

This is a handoff doc for continuing this build in a fresh conversation without re-reading the whole prior thread. Point a new session at this repo and have it read this file plus `Backend-dev-plan.md` (which now includes an `S9` section) before continuing.

## Where things stand

Branch `main`, all work pushed. Sprints **S0–S6 are complete**, each committed and pushed individually:

```
17afbae Add Emptify frontend scaffold
9e85ada Add backend dev plan and S0 environment scaffold
6d33091 Add S1: role context, actor mapping, and audit log
0dc69cd Add S2: Gmail OAuth connect and first real send
8cedb91 Add S3: multi-account Connect screen and fix two live bugs
adee772 Add S4: voice profile builder from real 90-day sent mail
8ef5a8e Add S5: unified triage engine and real Board, fix account-label/filter bugs
9f5e9ad Add S6: voice-matched draft generation and real tone rewrite/revert
```

**Next up: S7 (Send/Archive/Skip)**, then S8 (Handoff Loop & EA Queue) — as originally scoped in `Backend-dev-plan.md`. Note: S2 proved the real Gmail send/undo pipeline via curl, but the frontend's Send/Archive/Skip/Handoff/Mark-ready buttons are still client-state-only stubs (`confirmSendNow`, `archiveEmail`, `skipEmail`, `submitHandoff`, `markReady` in `emptify-app.tsx`) — wiring those to the real backend endpoints (`send`, `undo`, and the not-yet-built `archive`/`skip`/`handoff`/`mark-ready`) is what S7/S8 actually do. A new `S9` section was added for post-MVP follow-ups (see below).

## Real integrations — all live and working

`backend/.env` is gitignored and already has real, working values for all three:

- **MongoDB Atlas** — connected, `/healthz` confirms it.
- **Google OAuth** — `GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET` configured, redirect URI registered. **3 real Gmail accounts are connected** with live data flowing: `kevmcg22@gmail.com` (slug `kevmcg22-gmail-com`), `kevin@ember.new` (slug `kevin-ember-new`), `kevin@ripplin.org` (slug `kevin-ripplin-org`). The user is non-technical — getting each of these three credentials required a plain-language, click-by-click walkthrough (Atlas cluster/user, Google Cloud OAuth client + consent screen + test users, Anthropic workspace-scoped API key). If any credential ever needs rotating, expect to walk through it the same way again.
- **Anthropic API** — `ANTHROPIC_API_KEY` is a **workspace-scoped** key (an early attempt with an identity-linked personal key failed with "anthropic-workspace-id is required"; the fix was creating the key from inside a specific Workspace in the Console, not the account-level identity page). `ANTHROPIC_MODEL=claude-sonnet-5`.

## What's built (S1–S5)

- **S1** — `X-Role: exec|ea` header dependency (`backend/app/api/v1/deps.py`) mapping to fixed actor names (`Mara Lindqvist` / `Theo Banks`) for audit attribution. Audit log write helper + verification-only `GET /api/v1/audit/{thread_id}`.
- **S2** — Real Google OAuth connect/callback (`backend/app/services/gmail.py`, `backend/app/api/v1/accounts.py`), delayed-dispatch `POST /threads/{id}/send` + `/undo` with a 12s undo window via `BackgroundTasks`. Verified with a real send landing in Gmail's Sent folder and a real undo that never dispatched.
- **S3** — Frontend's first real backend wiring: Connect screen, `frontend/lib/emptify/api.ts` (the fetch wrapper + `X-Role` attachment), all 3 accounts connecting/reconnecting through the real UI, debounced internal-domains PATCH.
- **S4** — Voice profile builder (`backend/app/services/voice.py`): pulls 90 days of Sent mail per account, noise-filters (forwards/auto-responses/short replies), splits by recipient domain into pooled client/internal profiles, extracts 6 traits + a default note via one forced-tool-use Anthropic call per mode. Rebuilding a profile only sets the default note the *first* time — later rebuilds never overwrite notes the user edited (explicit product decision, see S4 section in the dev plan).
- **S5** — Real inbound triage (`backend/app/services/triage.py`): incremental Gmail Inbox sync (capped at 20 new messages/account/call, dedup by Gmail `threadId`, `last_sync` only advances when the whole backlog was processed), one Anthropic call per new thread for bucket/reason/handoff, deterministic domain-matching (reused from S4) for voice_mode/voice_why. Board screen wired to real data for the first time.
- **S6** — Draft generation and tone controls. The triage Anthropic call (`triage.py`) now also emits a voice-matched `draft` in the same request (voice_mode is computed deterministically *before* the LLM call now, so its traits/notes can be folded into the same prompt — avoids a second sequential LLM call per synced message, which would have compounded the S9-flagged sync-latency concern). New `backend/app/services/tone.py` does the Shorter/Warmer/Firmer rewrite (forced tool-use, same pattern as `voice.py`/`triage.py`) — its prompt explicitly demands a rewrite "genuinely, noticeably different" from the input, because the model would otherwise sometimes return an already-warm draft unchanged on `warmer`. Three new routes on `threads.py`: `PATCH .../draft`, `POST .../tone` (409 if thread isn't `board`/`withEA`/`readyToSend`), `POST .../revert` (409 on an empty `version_stack`). Frontend's draft textarea/tone buttons/revert arrow — built ahead of the backend with a `setTimeout` + static `TONE_DATA` dummy map keyed by non-real seed IDs — are now wired to real calls; `TONE_DATA`/`toneData()`/`ToneData` deleted as dead code.

## Bugs found and fixed along the way

Worth knowing so they don't get re-discovered from scratch:

1. **Account slug collision** — account IDs were derived from just the email's local part; `kevin@ember.new` and `kevin@ripplin.org` both slugged to `kevin` and silently overwrote each other. Fixed: slug from the full address.
2. **PKCE `code_verifier` lost between requests** — `google-auth-oauthlib` generates a PKCE verifier tied to the `Flow` instance that built the authorize URL; a fresh `Flow` for the callback request didn't have it, causing `invalid_grant: Missing code verifier`. Fixed: stash the verifier server-side keyed by OAuth `state` between the two requests (`gmail.py`'s `_pending_verifiers`).
3. **CSS class name collision** — a custom `.text-muted` class silently lost to Tailwind's auto-generated `.text-muted` utility (from the theme's "muted" *surface* color, not meant for text) every time, since Tailwind's utility layer outranks `@layer components` regardless of source order. No amount of contrast tweaking had any visible effect until this was found. Fixed: renamed to `.text-emptify-muted` across all 19 usages.
4. **`ACCOUNT_LABELS` hardcoded demo map** — `board-screen.tsx`, `detail-screen.tsx`, `queue-screen.tsx`, `ready-screen.tsx` all looked up account display names from a static 3-entry map (`kestrel`/`northwind`/`personal`) instead of using `EmailThread.accountLabel`, which was already on the object. Real accounts would've shown `undefined`. Fixed across all 4 files; the map is deleted.
5. **Account filter not URL-persisted** — the board's account filter reset to "All accounts" on every refresh because only `screen` was synced to the URL, not `accountFilter`. Fixed: both now round-trip through the URL together.
6. **No loading feedback during sync** — `GET /threads?status=board` does a real, potentially slow (backlog-dependent) sync inline before responding; with zero loading indicator this looked broken/stuck. Fixed: a "Syncing…" label now shows on the board while the fetch is in flight.
7. Decorative "blueprint" corner registration marks on cards were removed per user feedback (pure CSS, `.blueprint > .corner { display: none; }`) — not a bug, but a design change worth knowing about if it looks like something's "missing" from the original SnapDev scaffold.

## Conventions established (follow these for S6+)

- **Workflow per sprint:** `EnterPlanMode` → explore relevant existing code → write context + design to the plan file → `AskUserQuestion` for any real product-behavior forks (there's usually at least one per sprint) → `ExitPlanMode` → implement → verify for real (curl the API directly, check Mongo state, hit real Gmail/Anthropic — don't just trust that code compiles) → hand off browser-only steps (OAuth consent, visual checks) to the user → fix anything that surfaces → `git status`/diff review → commit with a real explanatory message → push.
- **API response shape:** backend Mongo documents are snake_case; every response is hand-mapped to the frontend's camelCase `EmailThread`/`Account`/`VoiceProfile` shapes in the router (`_to_response`/`_thread_response` helper functions) — no Pydantic alias magic beyond request bodies.
- **Mutating routes** attach `X-Role` via `require_role`/`require_exec`/`require_ea` (`backend/app/api/v1/deps.py`); GET routes don't require it.
- **Blocking calls** (Gmail API via `googleapiclient`, Anthropic SDK) are always wrapped in `asyncio.to_thread` — see any `_*_sync` / async wrapper pair in `gmail.py`, `voice.py`, `triage.py`.
- **Frontend debounce pattern** for any user-typed field that triggers a PATCH: update local state immediately, debounce the network call via a per-key `setTimeout` ref (see `updateDomains`/`updateNotes` in `emptify-app.tsx`).
- **Manual test scripts** get written to the scratchpad, never committed — see how S2's seed-thread script and various one-off DB-inspection snippets were handled.
- Both dev servers: backend `cd backend && source .venv/bin/activate && uvicorn app.main:app --port 8000`; frontend `cd frontend && npm run dev`.

## S9 (new)

Added to the bottom of `Backend-dev-plan.md`: post-MVP hardening items not covered by any of S1–S8, headlined by the **Gmail → Emptify two-way sync gap** — currently sync only ever detects new incoming mail; a message deleted or replied-to directly in Gmail never reflects back onto the board. Fixing it properly means migrating from S5's date-based `after:` sync to Gmail's **History API**, plus deciding what a board card should actually do when its underlying message disappears or gets an out-of-band reply. Also lists the other known simplifications flagged during S2 (plaintext OAuth tokens, unvalidated OAuth `state`) and a performance note from S5 (sequential per-message classification during sync). None of it is scoped in detail yet — that's the first thing to do whenever S9 actually starts.
