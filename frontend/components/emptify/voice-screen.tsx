"use client";

import { BlueprintCorners } from "./blueprint-corners";
import { VoiceMode, VoiceState } from "@/lib/emptify/types";

interface VoiceScreenProps {
  voice: VoiceState;
  onNotesChange: (which: VoiceMode, value: string) => void;
  onRebuild: (which: VoiceMode) => void;
}

export function VoiceScreen({ voice, onNotesChange, onRebuild }: VoiceScreenProps) {
  const profiles: { key: VoiceMode; kicker: string; title: string }[] = [
    { key: "client", kicker: "Client-facing", title: "Client voice profile" },
    { key: "internal", kicker: "Internal", title: "Internal voice profile" },
  ];

  return (
    <div>
      <h2 className="mb-[var(--space-1)]">Voice profiles</h2>
      <p className="text-muted max-w-[560px] mb-[var(--space-6)]">
        Built once from 90 days of sent mail, split by recipient domain. Edit the notes to steer future drafts.
      </p>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-[var(--space-6)]">
        {profiles.map(({ key, kicker, title }) => {
          const vp = voice[key];
          return (
            <div key={key} className="blueprint card-emptify elev-sm gap-[var(--space-3)]">
              <BlueprintCorners />
              <div className="card-kicker">{kicker}</div>
              <div className="card-title">{title}</div>
              <div className="text-muted text-[13px]">{vp.sampleSize}</div>
              <div className="flex flex-col gap-[var(--space-1)] mt-[var(--space-2)]">
                {vp.traits.map((tr) => (
                  <div
                    key={tr.label}
                    className="grid grid-cols-[120px_1fr] gap-[var(--space-2)] text-[13px] py-1 border-b border-[var(--color-divider)]"
                  >
                    <span className="text-muted">{tr.label}</span>
                    <span>{tr.value}</span>
                  </div>
                ))}
              </div>
              <div className="mt-[var(--space-2)]">
                <label className="field-label">Notes</label>
                <textarea
                  className="input-emptify"
                  value={vp.notes}
                  onChange={(e) => onNotesChange(key, e.target.value)}
                />
              </div>
              <button
                type="button"
                className="btn-emptify btn-emptify-secondary"
                onClick={() => onRebuild(key)}
                disabled={vp.rebuilding}
              >
                {vp.rebuilding ? "Rebuilding…" : "Rebuild from last 90 days"}
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}
