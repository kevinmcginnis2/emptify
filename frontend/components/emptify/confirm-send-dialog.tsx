"use client";

import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";

interface ConfirmSendDialogProps {
  open: boolean;
  from: string;
  to: string;
  onCancel: () => void;
  onConfirm: () => void;
}

export function ConfirmSendDialog({ open, from, to, onCancel, onConfirm }: ConfirmSendDialogProps) {
  return (
    <Dialog open={open} onOpenChange={(next) => !next && onCancel()}>
      <DialogContent className="dialog-emptify rounded-none border-none p-[var(--space-4)] gap-[var(--space-3)] max-w-[440px]">
        <DialogTitle className="dialog-emptify-title">Confirm send</DialogTitle>
        <div className="flex flex-col gap-1.5 text-[14px]">
          <div>
            <span className="text-muted">From:</span> {from}
          </div>
          <div>
            <span className="text-muted">To:</span> {to}
          </div>
        </div>
        <div className="flex justify-end gap-[var(--space-2)] mt-[var(--space-2)]">
          <button type="button" className="btn-emptify btn-emptify-secondary" onClick={onCancel}>
            Cancel
          </button>
          <button type="button" className="btn-emptify btn-emptify-primary" onClick={onConfirm}>
            Send
          </button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
