"use client";

import { BlueprintCorners } from "./blueprint-corners";
import { EmailThread } from "@/lib/emptify/types";
import { ACCOUNT_LABELS } from "@/lib/emptify/data";

interface QueueScreenProps {
  emails: EmailThread[];
  onOpen: (id: string) => void;
}

export function QueueScreen({ emails, onOpen }: QueueScreenProps) {
  return (
    <div>
      <h2 className="mb-[var(--space-1)]">EA queue</h2>
      <p className="text-muted mb-[var(--space-6)]">Threads handed off, with Mara&apos;s note and the draft as it stands.</p>
      <div className="flex flex-col gap-[var(--space-3)] max-w-[760px]">
        {emails.map((em) => {
          const preview = em.draft.length > 90 ? em.draft.slice(0, 90) + "…" : em.draft;
          return (
            <div
              key={em.id}
              className="blueprint card-emptify elev-sm cursor-pointer"
              role="button"
              tabIndex={0}
              onClick={() => onOpen(em.id)}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") onOpen(em.id);
              }}
            >
              <BlueprintCorners />
              <div className="flex justify-between gap-[var(--space-3)]">
                <div className="card-title">{em.subject}</div>
                <span className="tag tag-neutral">{ACCOUNT_LABELS[em.account]}</span>
              </div>
              <div className="card-body">From {em.from}</div>
              <div className="text-[13px] bg-[var(--color-surface)] p-[var(--space-2)]">
                <span className="text-muted">Mara&apos;s note: </span>
                {em.eaNote}
              </div>
              <div className="text-muted text-[12px]">Draft: {preview}</div>
            </div>
          );
        })}
        {emails.length === 0 && <p className="text-muted">Nothing in the queue right now.</p>}
      </div>
    </div>
  );
}
