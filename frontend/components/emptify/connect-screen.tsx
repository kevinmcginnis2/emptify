"use client";

import { BlueprintCorners } from "./blueprint-corners";
import { Account } from "@/lib/emptify/types";
import { STATUS_LABEL, STATUS_TAG_CLASS } from "@/lib/emptify/data";

interface ConnectScreenProps {
  accounts: Account[];
  onDomainsChange: (accountId: string, value: string) => void;
  onReconnect: (accountId: string) => void;
}

export function ConnectScreen({ accounts, onDomainsChange, onReconnect }: ConnectScreenProps) {
  return (
    <div>
      <h2 className="mb-[var(--space-1)]">Connect inboxes</h2>
      <p className="text-muted max-w-[560px] mb-[var(--space-6)]">
        Every account Emptify triages, in one place. Reconnect a lapsed token or edit which domains count as internal
        for that account.
      </p>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-[var(--space-4)]">
        {accounts.map((acc) => (
          <div key={acc.id} className="blueprint card-emptify elev-sm">
            <BlueprintCorners />
            <div className="card-kicker">{acc.type}</div>
            <div className="card-title">{acc.name}</div>
            <div className="text-muted text-[13px]">{acc.email}</div>
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
      <button type="button" className="btn-emptify btn-emptify-secondary mt-[var(--space-6)]" disabled>
        + Connect another account (3 of 3 connected in this demo)
      </button>
    </div>
  );
}
