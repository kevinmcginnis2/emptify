"use client";

import { BlueprintCorners } from "./blueprint-corners";
import { EmailThread, Role, Tone, ToneLoadingState } from "@/lib/emptify/types";
import { BUCKET_LABELS } from "@/lib/emptify/data";

interface DetailScreenProps {
  email: EmailThread;
  role: Role;
  toneLoading: ToneLoadingState | null;
  onBack: () => void;
  onDraftChange: (value: string) => void;
  onTone: (tone: Tone) => void;
  onRevert: () => void;
  onSendClick: () => void;
  onHandoffClick: () => void;
  onArchive: () => void;
  onSkip: () => void;
  onMarkReady: () => void;
}

export function DetailScreen({
  email,
  role,
  toneLoading,
  onBack,
  onDraftChange,
  onTone,
  onRevert,
  onSendClick,
  onHandoffClick,
  onArchive,
  onSkip,
  onMarkReady,
}: DetailScreenProps) {
  const toneBusy = toneLoading?.id === email.id;
  const busyTone = toneBusy ? toneLoading.tone : null;
  const canRevert = email.versionStack.length > 0;

  const showSend =
    (role === "exec" && (email.status === "board" || email.status === "readyToSend")) ||
    (role === "ea" && email.status === "withEA");
  const showHandoff = role === "exec" && email.status === "board";
  const showArchiveSkip =
    (role === "exec" && email.status === "board") || (role === "ea" && email.status === "withEA");
  const showMarkReady = role === "ea" && email.status === "withEA";

  return (
    <div>
      <button type="button" className="btn-emptify btn-emptify-ghost mb-[var(--space-3)]" onClick={onBack}>
        ← Back
      </button>
      <div className="grid grid-cols-1 lg:grid-cols-[1fr_1.1fr] gap-[var(--space-6)] items-start">
        <div className="flex flex-col gap-[var(--space-3)]">
          <h3 className="mb-0">{email.subject}</h3>
          <span className="tag tag-neutral self-start">{email.accountLabel}</span>
          {email.messages.map((m, i) => (
            <div key={i} className="blueprint card-emptify elev-sm">
              <BlueprintCorners />
              <div className="flex justify-between text-[13px]">
                <strong>{m.from}</strong>
                <span className="text-emptify-muted">{m.at}</span>
              </div>
              <p className="m-0 text-[14px] whitespace-pre-wrap">{m.body}</p>
            </div>
          ))}
        </div>

        <div className="flex flex-col gap-[var(--space-3)]">
          <div className="flex gap-[var(--space-2)] flex-wrap">
            <span className="tag tag-outline">{BUCKET_LABELS[email.bucket] ?? "—"}</span>
          </div>
          <p className="text-emptify-muted text-[13px] m-0">{email.reason}</p>
          <div className="text-[13px] font-medium">
            {email.draftAuthor === "ea" ? "Edited by Theo" : "Drafted by Emptify"} — voice used:{" "}
            {email.voiceMode === "client" ? "Client voice" : "Internal voice"}
          </div>
          <p className="text-emptify-muted text-[13px] m-0">{email.voiceWhy}</p>

          {email.eaChangeSummary && (
            <div className="text-[13px] bg-[var(--color-surface)] p-[var(--space-2)]">
              <span className="text-emptify-muted">What Theo changed: </span>
              {email.eaChangeSummary}
            </div>
          )}

          <textarea
            className="input-emptify min-h-[180px] text-[14px]"
            value={email.draft}
            onChange={(e) => onDraftChange(e.target.value)}
          />

          <div className="flex items-center gap-[var(--space-2)] flex-wrap">
            <button type="button" className="btn-emptify btn-emptify-secondary" onClick={() => onTone("shorter")} disabled={toneBusy}>
              {busyTone === "shorter" ? "Shortening…" : "Shorter"}
            </button>
            <button type="button" className="btn-emptify btn-emptify-secondary" onClick={() => onTone("warmer")} disabled={toneBusy}>
              {busyTone === "warmer" ? "Warming…" : "Warmer"}
            </button>
            <button type="button" className="btn-emptify btn-emptify-secondary" onClick={() => onTone("firmer")} disabled={toneBusy}>
              {busyTone === "firmer" ? "Firming…" : "Firmer"}
            </button>
            {canRevert && (
              <button type="button" className="btn-emptify btn-emptify-ghost" onClick={onRevert} title="Revert last rewrite">
                ↶ Revert
              </button>
            )}
          </div>

          <div className="flex gap-[var(--space-2)] mt-[var(--space-3)] border-t border-[var(--color-divider)] pt-[var(--space-3)] flex-wrap">
            {showSend && (
              <button type="button" className="btn-emptify btn-emptify-primary blueprint" onClick={onSendClick}>
                <BlueprintCorners />
                Send
              </button>
            )}
            {showHandoff && (
              <button type="button" className="btn-emptify btn-emptify-secondary" onClick={onHandoffClick}>
                Hand to EA
              </button>
            )}
            {showArchiveSkip && (
              <>
                <button type="button" className="btn-emptify btn-emptify-secondary" onClick={onArchive}>
                  Archive
                </button>
                <button type="button" className="btn-emptify btn-emptify-secondary" onClick={onSkip}>
                  Skip
                </button>
              </>
            )}
            {showMarkReady && (
              <button type="button" className="btn-emptify btn-emptify-primary blueprint" onClick={onMarkReady}>
                <BlueprintCorners />
                Mark ready
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
