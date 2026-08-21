"use client";

import { BlueprintCorners } from "./blueprint-corners";
import { EmailThread } from "@/lib/emptify/types";
import { ACCOUNT_LABELS } from "@/lib/emptify/data";

interface ReadyScreenProps {
  emails: EmailThread[];
  onOpen: (id: string) => void;
}

export function ReadyScreen({ emails, onOpen }: ReadyScreenProps) {
  return (
    <div>
      <h2 className="mb-[var(--space-1)]">Ready to send</h2>
      <p className="text-muted mb-[var(--space-6)]">Marked ready by Theo. Review and send from the right account.</p>
      <div className="flex flex-col gap-[var(--space-3)] max-w-[760px]">
        {emails.map((em) => (
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
              <span className="tag tag-accent">{ACCOUNT_LABELS[em.account]}</span>
            </div>
            <div className="card-body">To {em.from}</div>
            <div className="text-muted text-[12px]">Theo: {em.eaChangeSummary}</div>
          </div>
        ))}
        {emails.length === 0 && <p className="text-muted">Nothing waiting on your review.</p>}
      </div>
    </div>
  );
}
