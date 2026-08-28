"use client";

import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";

interface ConfirmDeleteDialogProps {
  open: boolean;
  subject: string;
  onCancel: () => void;
  onConfirm: () => void;
}

export function ConfirmDeleteDialog({ open, subject, onCancel, onConfirm }: ConfirmDeleteDialogProps) {
  return (
    <Dialog open={open} onOpenChange={(next) => !next && onCancel()}>
      <DialogContent className="dialog-emptify rounded-none border-none p-[var(--space-4)] gap-[var(--space-3)] max-w-[440px]">
        <DialogTitle className="dialog-emptify-title">Confirm delete</DialogTitle>
        <div className="text-[14px]">
          This will permanently delete <strong>{subject}</strong> in both Emptify and Gmail. Continue?
        </div>
        <div className="flex justify-end gap-[var(--space-2)] mt-[var(--space-2)]">
          <button type="button" className="btn-emptify btn-emptify-secondary" onClick={onCancel}>
            Cancel
          </button>
          <button type="button" className="btn-emptify btn-emptify-primary" onClick={onConfirm}>
            Delete
          </button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
