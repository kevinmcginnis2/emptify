# Emptify — Build Brief (v2)

> EA and VA are used interchangeably throughout — both mean an assistant supporting an executive.

**Product in one sentence:** Emptify connects an executive's Gmail accounts, sorts everything into what needs them today, this week, or not at all, automatically learns how they write from their own last 90 days of sent mail, and lets them edit and send a reply — or hand the thread to their assistant — without leaving the app.

**Who it is for:** Executives who run several inboxes across roles or entities and already work with an executive assistant or virtual assistant. Both people are users: the exec triages, edits, and sends; the assistant works a queue of what the exec handed over and sends it back ready for signature.

**The problem it solves:** The exec opens whichever inbox is loudest, handles the top few fires, and closes it — everything else silts up. The assistant is copied on some of it, guesses at the rest, and interrupts the exec to ask what to take. Handoffs happen by forward, Slack, or hallway, with no context attached. Real threads go cold.

## Before and after

**Before:** Exec tab-switches between three inboxes, mentally triages a wall of mail, writes every reply from scratch, and forwards things to the assistant with "can you handle this?" and no context.

**After:** Exec opens one board covering all three accounts, sees three buckets with a reason on each, and either sends a draft that already sounds like them from the right account, or hands the thread to their assistant in one click from the board — which lands in the assistant's queue with the thread, draft, and a one-line note attached, and comes back to a "Ready to send" lane when it's done.

## Core workflow

- **Trigger:** Exec opens Emptify and lands on the unified triage board — all connected inboxes in one list, sorted Today / This Week / Can Wait, with a one-line reason and source-account badge on every email.
- **Action:** Exec either hands the thread off in one click from the card, or opens it. On open: Emptify shows why it was bucketed there and a drafted reply in the exec's voice, badged client or internal with a one-line note on why. The exec edits inline, or adjusts the register in one click with Shorter / Warmer / Firmer.
- **Result:** Exec hits Send — it goes out from the correct account, after a confirmation showing the FROM address, and lands in that account's Gmail Sent folder. Or Archive, or Skip, or Hand to EA with a one-line note.

### The handoff loop (the differentiator — protect it)

1. Exec clicks Hand to EA from the triage card or the detail screen, types one line, done. The thread moves out of the buckets and into With EA.
2. The assistant opens the queue, sees the thread, the exec's note, and the draft. They edit it and click Mark ready.
3. It lands in the exec's Ready to send lane. The exec reviews, hits Send, and the same confirmation and undo apply.
4. Every step is written to the audit log against a named human.

**Onboarding (automatic, once):** Exec connects each Gmail account and confirms which domains count as internal. Emptify pulls the last 90 days of Sent, filters out short replies, forwards, and auto-responses, splits the rest by recipient domain into client-facing and internal, and hands back two plain-English voice profiles with sample sizes — no typing, no pasting.

**Aha moment:** The exec connects three inboxes, waits about a minute, and gets back a description of how they write that is uncomfortably accurate — having typed nothing. Then the first draft it produces goes out with a two-word edit.

## Priority features (5)

1. **Multi-inbox Gmail connection** — OAuth for 3 accounts, token refresh, per-account sync, connection-health panel with one-click reconnect, and an internal-domains field per account.
2. **Automatic voice profile builder** — 90 days of Sent, noise-filtered, auto-split client vs. internal by recipient domain, two editable plain-English profiles with sample sizes.
3. **Unified triage engine** — one list across all inboxes, Today / This Week / Can Wait, reason and source badge per email, plus a suggested-handoff chip where Emptify thinks the assistant should own it.
4. **Draft → adjust → send** — voice-matched draft, inline editing, three one-click tone controls (Shorter / Warmer / Firmer) that rewrite within the active voice profile, and a real send from the correct account behind a confirmation showing the FROM address and a 10–15 second undo.
5. **Handoff loop** — one-click Hand to EA from the board with a note; assistant queue with edit and mark-ready; a Ready to send lane returning work to the exec; immutable audit log covering the full chain.

## Triage model (read this part carefully)

**Three buckets, one axis — urgency.** Today / This Week / Can Wait. Every email is in exactly one, with a one-line reason.

**Handoff is a flag, not a bucket.** Any email in any bucket can carry a Hand to EA chip on the card. Where Emptify thinks the assistant should own it, the chip is pre-highlighted with a short reason ("scheduling request — EA usually handles these"). One click tags it without opening the thread. Handoff is an ownership decision, not an urgency one, so it does not compete with the buckets for the same slot.

**Two status lanes**, shown as counts in the header, not as buckets:

- **With EA (n)** — handed over, in the assistant's queue, out of the exec's buckets.
- **Ready to send (n)** — assistant has edited and marked ready; waiting on the exec's send.

### Tone controls (three buttons, fixed, on every draft)

The voice profile is identity — how this person writes, generally. The tone controls are register — how this particular message should land. They are not a correction to the profile and should not be presented as one.

- **Shorter** — cuts length, keeps the point
- **Warmer** — softens the register
- **Firmer** — tightens and removes hedging

Warmer and Firmer are deliberate opposites, so the effect of each is legible without trying it. Rules:

- Every rewrite is instructed to apply the change while staying inside the active voice profile. A plain rewrite strips the characteristic phrasing the profile exists to capture.
- The buttons rewrite whatever is currently in the draft box, including hand edits.
- Every rewrite is revertible in one click. Keep a version stack for the session.
- Show an in-flight state on the button. Each click is a model round trip and silence reads as broken.
- No freeform tone box in v1. If a fourth preset is repeatedly wanted, that wish is the spec for the fourth preset.

### Button definitions, so nothing is a mystery

- **Send** — real send from the source account, behind confirmation and undo.
- **Hand to EA** — moves to With EA with a one-line note.
- **Archive** — archives in the source Gmail account, behind the same undo toast.
- **Skip** — dismisses from the board only. Nothing changes in Gmail. Returns to the board if the thread receives a new message.

## Inputs

- OAuth grants for 2 or more Gmail accounts (example configuration: 2 work, 1 personal)
- A list of internal domains per account, confirmed by the exec at connect time
- 90 days of sent mail per account, pulled automatically
- Incoming mail via sync
- Exec's inline draft edits
- Exec's one-line handoff note
- Assistant's edits and mark-ready action
- Role selection (Exec / EA) — a view toggle, since there is no real auth in v1

## Outputs

- Two auto-built voice profiles in plain English, with sample sizes, editable
- Unified triage board: three buckets with counts, reason and source badge per email, suggested-handoff chips
- Two status lanes with counts: With EA, Ready to send
- Per-email: bucket + reason, voice mode + why, drafted reply
- Real sent email from the correct account, landing in that account's Gmail Sent folder
- Assistant queue: tagged threads with exec note, draft, and status
- Immutable audit log covering the whole chain: who handed off, who edited, who marked ready, who sent, from which account, when

## Main screens

**Connect inboxes** — add account via Google sign-in; list of connected accounts with status (connected / expires in N days / reconnect needed), account type, last sync time, and an editable "internal domains" field per account. Permanent furniture, not onboarding-only.

**Voice profiles** — two profiles side by side, each with sample size, extracted traits (sentence length, greeting and sign-off habits, formality, hedging, characteristic phrases), editable notes, and a "rebuild from last 90 days" button.

**Triage board** — exec home. Header carries the role toggle, an account filter, and the two status-lane counts (With EA, Ready to send). Below that: Today / This Week / Can Wait with counts. Each card shows sender, subject, source-account badge, one-line reason, and a Hand to EA chip — highlighted with a short reason where handoff is suggested.

**Email detail / compose** — thread on the left; on the right: bucket + reason, voice badge + why, the editable draft, a tone row directly beneath it (Shorter / Warmer / Firmer, plus a revert arrow that appears once a rewrite has run), and the action bar: Send, Hand to EA, Archive, Skip. Send opens a confirmation showing FROM account, recipients, and voice used, with a 10–15 second undo.

**EA queue** — visible when the role toggle is set to EA. Tagged threads with the exec's note, the draft, and status. The assistant edits, has the same three tone controls, and clicks Mark ready. Send is not available to the assistant in v1.

**Ready to send** — the exec's return lane. Threads the assistant has marked ready, showing the assistant's version of the draft and what changed. Exec reviews and sends through the same confirmation and undo path.

## Look and feel

Calm, dense, and executive — closer to a well-kept desk than a productivity app. Quiet colour, generous type, no badges shouting for attention. Four things must be legible at a glance and never ambiguous: which account you're looking at, which voice a draft used, which account a send will go out from, and whether a draft in front of you was written by Emptify or edited by your assistant. Confident, not cute.

## What to leave out for now

- Autonomous sending — a human clicks send, every time
- Assistant sending — exec only in week one
- Permission tiers for the assistant — one model in v1: edit and mark ready, cannot send
- Delete and Unsubscribe — Archive only
- A freeform tone or prompt box — three fixed presets only
- More than three tone controls
- Microsoft 365
- Real accounts, invites, or auth — role toggle only
- Learning from the exec's edits over time
- Calendar, scheduling, tasks, CRM
- Search, labels, attachments, snooze, scheduled send
- More than two voice modes
- Mobile

## The first thing to build

One Gmail account connected, syncing, and able to send one real email. Not the UI, not the prompts — the connection. Everything else in this brief is worthless if that doesn't work, and everything else gets easier the moment it does.
