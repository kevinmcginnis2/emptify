"use client";

import { cn } from "@/lib/utils";
import { BlueprintCorners } from "./blueprint-corners";
import { EmailThread } from "@/lib/emptify/types";

interface EmailCardProps {
  email: EmailThread;
  accountLabel: string;
  onOpen: () => void;
  onHandoffClick: (e: React.MouseEvent) => void;
}

export function EmailCard({ email, accountLabel, onOpen, onHandoffClick }: EmailCardProps) {
  return (
    <div
      className="blueprint card-emptify elev-sm cursor-pointer"
      role="button"
      tabIndex={0}
      onClick={onOpen}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") onOpen();
      }}
    >
      <BlueprintCorners />
      <div className="flex justify-between gap-[var(--space-2)]">
        <div className="card-title">{email.subject}</div>
        <span className="tag tag-neutral">{accountLabel}</span>
      </div>
      <div className="card-body">{email.from}</div>
      <div className="card-meta">{email.reason}</div>
      {email.handoffSuggested ? (
        <button
          type="button"
          className={cn("btn-emptify btn-emptify-secondary self-start")}
          style={{
            borderColor: "var(--color-accent)",
            color: "var(--color-accent-700)",
            fontSize: 12,
            padding: "4px 8px",
          }}
          onClick={onHandoffClick}
          title={email.handoffReason}
        >
          Hand to EA — {email.handoffReason}
        </button>
      ) : (
        <button
          type="button"
          className="btn-emptify btn-emptify-ghost self-start"
          style={{ fontSize: 12, padding: "4px 0" }}
          onClick={onHandoffClick}
        >
          Hand to EA
        </button>
      )}
    </div>
  );
}
