"use client";

import { ChevronDown } from "lucide-react";
import { EmailCard } from "./email-card";
import { InformationalCard } from "./informational-card";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
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
  informationalList: EmailThread[];
  onOpen: (id: string) => void;
  onHandoff: (id: string) => void;
  onMarkRead: (id: string) => void;
  onRemove: (id: string) => void;
  onArchive: (id: string) => void;
  onDelete: (id: string) => void;
  onUnsubscribe: (id: string) => void;
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

function InformationalSection({
  emails,
  onOpen,
  onMarkRead,
  onRemove,
  onArchive,
  onDelete,
  onUnsubscribe,
}: {
  emails: EmailThread[];
  onOpen: (id: string) => void;
  onMarkRead: (id: string) => void;
  onRemove: (id: string) => void;
  onArchive: (id: string) => void;
  onDelete: (id: string) => void;
  onUnsubscribe: (id: string) => void;
}) {
  return (
    <Collapsible defaultOpen={false} className="mt-[var(--space-8)]">
      <CollapsibleTrigger className="flex items-center gap-[var(--space-2)] w-full text-left group">
        <ChevronDown size={16} className="transition-transform group-data-[state=open]:rotate-180" />
        <h4 className="m-0">
          Informational / Subscriptions <span className="text-emptify-muted">({emails.length})</span>
        </h4>
      </CollapsibleTrigger>
      <CollapsibleContent>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-[var(--space-4)] mt-[var(--space-4)]">
          {emails.map((em) => (
            <InformationalCard
              key={em.id}
              email={em}
              accountLabel={em.accountLabel}
              onOpen={() => onOpen(em.id)}
              onMarkRead={(e) => {
                e.stopPropagation();
                onMarkRead(em.id);
              }}
              onRemove={(e) => {
                e.stopPropagation();
                onRemove(em.id);
              }}
              onArchive={(e) => {
                e.stopPropagation();
                onArchive(em.id);
              }}
              onDelete={(e) => {
                e.stopPropagation();
                onDelete(em.id);
              }}
              onUnsubscribe={(e) => {
                e.stopPropagation();
                onUnsubscribe(em.id);
              }}
            />
          ))}
        </div>
      </CollapsibleContent>
    </Collapsible>
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
  informationalList,
  onOpen,
  onHandoff,
  onMarkRead,
  onRemove,
  onArchive,
  onDelete,
  onUnsubscribe,
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
      <InformationalSection
        emails={informationalList}
        onOpen={onOpen}
        onMarkRead={onMarkRead}
        onRemove={onRemove}
        onArchive={onArchive}
        onDelete={onDelete}
        onUnsubscribe={onUnsubscribe}
      />
    </div>
  );
}
