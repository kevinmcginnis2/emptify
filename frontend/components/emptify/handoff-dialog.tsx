"use client";

import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";

interface HandoffDialogProps {
  open: boolean;
  note: string;
  onNoteChange: (value: string) => void;
  onCancel: () => void;
  onSubmit: () => void;
}

export function HandoffDialog({ open, note, onNoteChange, onCancel, onSubmit }: HandoffDialogProps) {
  return (
    <Dialog open={open} onOpenChange={(next) => !next && onCancel()}>
      <DialogContent className="dialog-emptify rounded-none border-none p-[var(--space-4)] gap-[var(--space-3)] max-w-[440px]">
        <DialogTitle className="dialog-emptify-title">Hand to EA</DialogTitle>
        <div>
          <label className="field-label">One-line note for Theo</label>
          <input
            className="input-emptify"
            value={note}
            onChange={(e) => onNoteChange(e.target.value)}
            placeholder="e.g. Just find a date that works, keep it simple"
          />
        </div>
        <div className="flex justify-end gap-[var(--space-2)] mt-[var(--space-2)]">
          <button type="button" className="btn-emptify btn-emptify-secondary" onClick={onCancel}>
            Cancel
          </button>
          <button type="button" className="btn-emptify btn-emptify-primary" onClick={onSubmit}>
            Hand off
          </button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
