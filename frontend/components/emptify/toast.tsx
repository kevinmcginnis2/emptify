"use client";

interface EmptifyToastProps {
  message: string;
  showUndo: boolean;
  onUndo: () => void;
}

export function EmptifyToast({ message, showUndo, onUndo }: EmptifyToastProps) {
  return (
    <div
      className="fixed bottom-[var(--space-6)] left-1/2 -translate-x-1/2 flex items-center gap-[var(--space-4)] px-[var(--space-4)] py-[var(--space-3)] z-30"
      style={{
        background: "var(--color-neutral-900)",
        color: "var(--color-bg)",
        boxShadow: "var(--shadow-lg)",
      }}
    >
      <span className="text-[14px]">{message}</span>
      {showUndo && (
        <button
          type="button"
          className="btn-emptify btn-emptify-ghost"
          style={{ color: "var(--color-accent-300)" }}
          onClick={onUndo}
        >
          Undo
        </button>
      )}
    </div>
  );
}
