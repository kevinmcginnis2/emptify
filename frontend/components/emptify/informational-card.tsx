"use client";

import { MailOpen, EyeOff, Archive, Trash2, Ban } from "lucide-react";
import { BlueprintCorners } from "./blueprint-corners";
import { EmailThread } from "@/lib/emptify/types";

interface InformationalCardProps {
  email: EmailThread;
  accountLabel: string;
  onOpen: () => void;
  onMarkRead: (e: React.MouseEvent) => void;
  onRemove: (e: React.MouseEvent) => void;
  onArchive: (e: React.MouseEvent) => void;
  onDelete: (e: React.MouseEvent) => void;
  onUnsubscribe: (e: React.MouseEvent) => void;
}

export function InformationalCard({
  email,
  accountLabel,
  onOpen,
  onMarkRead,
  onRemove,
  onArchive,
  onDelete,
  onUnsubscribe,
}: InformationalCardProps) {
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
        <div className="card-title">
          {!email.read && <span className="tag tag-outline mr-[var(--space-2)]">New</span>}
          {email.subject}
        </div>
        <span className="tag tag-neutral">{accountLabel}</span>
      </div>
      <div className="card-body">{email.from}</div>
      <div className="card-meta">{email.reason}</div>
      <div className="flex items-center gap-[var(--space-2)] mt-[var(--space-2)]">
        <button
          type="button"
          className="btn-emptify btn-emptify-ghost"
          style={{ padding: "4px 6px" }}
          onClick={onMarkRead}
          title="Mark read"
        >
          <MailOpen size={14} />
        </button>
        <button
          type="button"
          className="btn-emptify btn-emptify-ghost"
          style={{ padding: "4px 6px" }}
          onClick={onRemove}
          title="Remove from Emptify (keep in Gmail)"
        >
          <EyeOff size={14} />
        </button>
        <button
          type="button"
          className="btn-emptify btn-emptify-ghost"
          style={{ padding: "4px 6px" }}
          onClick={onArchive}
          title="Archive (Emptify + Gmail)"
        >
          <Archive size={14} />
        </button>
        <button
          type="button"
          className="btn-emptify btn-emptify-ghost"
          style={{ padding: "4px 6px" }}
          onClick={onDelete}
          title="Delete (Emptify + Gmail)"
        >
          <Trash2 size={14} />
        </button>
        <button
          type="button"
          className="btn-emptify btn-emptify-ghost"
          style={{ padding: "4px 6px" }}
          onClick={onUnsubscribe}
          title="Unsubscribe"
        >
          <Ban size={14} />
        </button>
      </div>
    </div>
  );
}
