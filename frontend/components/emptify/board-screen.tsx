"use client";

import { EmailCard } from "./email-card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Account, AccountId, EmailThread } from "@/lib/emptify/types";

interface BoardScreenProps {
  accounts: Account[];
  loading: boolean;
  accountFilter: AccountId | "all";
  onAccountFilterChange: (value: AccountId | "all") => void;
  todayList: EmailThread[];
  weekList: EmailThread[];
  waitList: EmailThread[];
  onOpen: (id: string) => void;
  onHandoff: (id: string) => void;
}

function Column({
  title,
  emails,
  onOpen,
  onHandoff,
}: {
  title: string;
  emails: EmailThread[];
  onOpen: (id: string) => void;
  onHandoff: (id: string) => void;
}) {
  return (
    <div>
      <h4 className="mb-[var(--space-4)]">
        {title} <span className="text-emptify-muted">({emails.length})</span>
      </h4>
      <div className="flex flex-col gap-[var(--space-4)]">
        {emails.map((em) => (
          <EmailCard
            key={em.id}
            email={em}
            accountLabel={em.accountLabel}
            onOpen={() => onOpen(em.id)}
            onHandoffClick={(e) => {
              e.stopPropagation();
              onHandoff(em.id);
            }}
          />
        ))}
      </div>
    </div>
  );
}

export function BoardScreen({
  accounts,
  loading,
  accountFilter,
  onAccountFilterChange,
  todayList,
  weekList,
  waitList,
  onOpen,
  onHandoff,
}: BoardScreenProps) {
  const filterOptions: { value: AccountId | "all"; label: string }[] = [
    { value: "all", label: "All accounts" },
    ...accounts.map((acc) => ({ value: acc.id, label: acc.name })),
  ];

  return (
    <div>
      <div className="flex items-baseline justify-between mb-[var(--space-4)] flex-wrap gap-[var(--space-3)]">
        <div className="flex items-baseline gap-[var(--space-3)]">
          <h2 className="m-0">Triage board</h2>
          {loading && <span className="text-emptify-muted text-[13px]">Syncing…</span>}
        </div>
        <div className="w-[220px]">
          <label className="field-label">Account</label>
          <Select value={accountFilter} onValueChange={(v) => onAccountFilterChange(v as AccountId | "all")}>
            <SelectTrigger className="input-emptify w-full rounded-none">
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="rounded-none">
              {filterOptions.map((opt) => (
                <SelectItem key={opt.value} value={opt.value}>
                  {opt.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-[var(--space-8)] items-start">
        <Column title="Today" emails={todayList} onOpen={onOpen} onHandoff={onHandoff} />
        <Column title="This Week" emails={weekList} onOpen={onOpen} onHandoff={onHandoff} />
        <Column title="Can Wait" emails={waitList} onOpen={onOpen} onHandoff={onHandoff} />
      </div>
    </div>
  );
}
