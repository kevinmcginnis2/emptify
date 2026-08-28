"use client";

import { useState } from "react";
import * as api from "@/lib/emptify/api";

export default function LoginPage() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const signIn = () => {
    setLoading(true);
    setError(null);
    api
      .getLoginUrl()
      .then((authUrl) => {
        window.location.href = authUrl;
      })
      .catch(() => {
        setLoading(false);
        setError("Couldn't start sign-in — try again.");
      });
  };

  return (
    <div className="min-h-screen bg-[var(--color-bg)] text-[var(--color-text)] flex items-center justify-center p-[var(--space-6)]">
      <div className="blueprint card-emptify elev-sm max-w-[380px] w-full flex flex-col gap-[var(--space-4)] items-center text-center p-[var(--space-6)]">
        <h2 className="m-0">Emptify</h2>
        <p className="text-emptify-muted text-[14px] m-0">
          Inbox triage for executives — drafted in your voice, one board for what needs you and what doesn&apos;t.
        </p>
        <button
          type="button"
          className="btn-emptify btn-emptify-primary blueprint w-full"
          onClick={signIn}
          disabled={loading}
        >
          {loading ? "Redirecting…" : "Sign in with Google"}
        </button>
        {error && <p className="text-[13px] m-0" style={{ color: "var(--color-danger, #b3261e)" }}>{error}</p>}
      </div>
    </div>
  );
}
