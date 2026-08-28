"use client";

import { useState } from "react";
import { BlueprintCorners } from "./blueprint-corners";
import { Account, EaRelationshipStatus } from "@/lib/emptify/types";
import { STATUS_LABEL, STATUS_TAG_CLASS } from "@/lib/emptify/data";

interface ConnectScreenProps {
  accounts: Account[];
  onDomainsChange: (accountId: string, value: string) => void;
  onReconnect: (accountId: string) => void;
  onConnect: () => void;
  connecting: boolean;
  eaRelationship: EaRelationshipStatus;
  onInviteEa: (email: string) => void;
  onRevokeEa: () => void;
}

function EaCard({
  eaRelationship,
  onInviteEa,
  onRevokeEa,
}: {
  eaRelationship: EaRelationshipStatus;
  onInviteEa: (email: string) => void;
  onRevokeEa: () => void;
}) {
  const [email, setEmail] = useState("");

  return (
    <div className="blueprint card-emptify elev-sm mb-[var(--space-6)] max-w-[420px]">
      <BlueprintCorners />
      <div className="card-title">Your assistant</div>
      {eaRelationship.status === "linked" && (
        <>
          <div className="text-emptify-muted text-[13px]">
            {eaRelationship.ea.name} ({eaRelationship.ea.email})
          </div>
          <button type="button" className="btn-emptify btn-emptify-ghost mt-[var(--space-2)]" onClick={onRevokeEa}>
            Remove
          </button>
        </>
      )}
      {eaRelationship.status === "pending" && (
        <>
          <div className="text-emptify-muted text-[13px]">
            Invited {eaRelationship.eaEmail} — they&apos;ll get access once they sign in with Google.
          </div>
          <button type="button" className="btn-emptify btn-emptify-ghost mt-[var(--space-2)]" onClick={onRevokeEa}>
            Cancel invite
          </button>
        </>
      )}
      {eaRelationship.status === "none" && (
        <div className="flex gap-[var(--space-2)] mt-[var(--space-2)]">
          <input
            type="email"
            className="input-emptify flex-1"
            placeholder="assistant@example.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <button
            type="button"
            className="btn-emptify btn-emptify-secondary"
            onClick={() => email.trim() && onInviteEa(email.trim())}
          >
            Invite EA
          </button>
        </div>
      )}
    </div>
  );
}

export function ConnectScreen({
  accounts,
  onDomainsChange,
  onReconnect,
  onConnect,
  connecting,
  eaRelationship,
  onInviteEa,
  onRevokeEa,
}: ConnectScreenProps) {
  return (
    <div>
      <h2 className="mb-[var(--space-1)]">Connect inboxes</h2>
      <p className="text-emptify-muted max-w-[560px] mb-[var(--space-6)]">
        Every account Emptify triages, in one place. Reconnect a lapsed token or edit which domains count as internal
        for that account.
      </p>
      <EaCard eaRelationship={eaRelationship} onInviteEa={onInviteEa} onRevokeEa={onRevokeEa} />
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-[var(--space-4)]">
        {accounts.map((acc) => (
          <div key={acc.id} className="blueprint card-emptify elev-sm">
            <BlueprintCorners />
            <div className="card-kicker">{acc.type}</div>
            <div className="card-title">{acc.name}</div>
            <div className="text-emptify-muted text-[13px]">{acc.email}</div>
            <span className={`tag ${STATUS_TAG_CLASS[acc.status]} self-start`}>{STATUS_LABEL[acc.status]}</span>
            <div className="card-meta">Last sync: {acc.lastSync}</div>
            <div className="mt-[var(--space-2)]">
              <label className="field-label">Internal domains</label>
              <input
                className="input-emptify"
                value={acc.internalDomains}
                onChange={(e) => onDomainsChange(acc.id, e.target.value)}
                placeholder="e.g. company.com"
              />
            </div>
            {acc.status === "reconnect" && (
              <button
                type="button"
                className="btn-emptify btn-emptify-secondary w-full mt-[var(--space-2)]"
                onClick={() => onReconnect(acc.id)}
              >
                Reconnect
              </button>
            )}
          </div>
        ))}
      </div>
      <button
        type="button"
        className="btn-emptify btn-emptify-secondary mt-[var(--space-6)]"
        onClick={onConnect}
        disabled={connecting}
      >
        + Connect another account
      </button>
    </div>
  );
}
