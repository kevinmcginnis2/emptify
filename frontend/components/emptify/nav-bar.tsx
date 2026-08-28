"use client";

import { Screen } from "@/lib/emptify/types";

interface NavBarProps {
  screen: Screen;
  withEACount: number;
  readyCount: number;
  isEaMode: boolean;
  userName: string;
  onGo: (screen: Screen) => void;
  onSignOut: () => void;
}

export function NavBar({ screen, withEACount, readyCount, isEaMode, userName, onGo, onSignOut }: NavBarProps) {
  return (
    <div className="border-b border-[var(--color-divider)] sticky top-0 bg-[var(--color-bg)] z-20">
      <div className="nav max-w-[1180px] mx-auto px-[var(--space-6)] gap-[var(--space-6)] flex items-center py-[var(--space-3)]">
        <div className="nav-brand mr-auto">Emptify</div>

        <div className="flex items-center gap-[var(--space-1)]">
          {!isEaMode && (
            <>
              <a
                href="#"
                className="nav-item"
                aria-current={screen === "board" ? "page" : undefined}
                onClick={(e) => {
                  e.preventDefault();
                  onGo("board");
                }}
              >
                Board
              </a>
              <a
                href="#"
                className="nav-item"
                aria-current={screen === "voice" ? "page" : undefined}
                onClick={(e) => {
                  e.preventDefault();
                  onGo("voice");
                }}
              >
                Voice profiles
              </a>
              <a
                href="#"
                className="nav-item"
                aria-current={screen === "connect" ? "page" : undefined}
                onClick={(e) => {
                  e.preventDefault();
                  onGo("connect");
                }}
              >
                Connect inboxes
              </a>
            </>
          )}
          {isEaMode && (
            <a
              href="#"
              className="nav-item"
              aria-current={screen === "queue" ? "page" : undefined}
              onClick={(e) => {
                e.preventDefault();
                onGo("queue");
              }}
            >
              EA queue
            </a>
          )}
        </div>

        <div className="flex items-center gap-[var(--space-4)] ml-auto">
          {!isEaMode && (
            <>
              <a
                href="#"
                aria-current={screen === "queue" ? "page" : undefined}
                className="inline-flex"
                onClick={(e) => {
                  e.preventDefault();
                  onGo("queue");
                }}
              >
                <span className="tag tag-neutral">With EA ({withEACount})</span>
              </a>
              <a
                href="#"
                aria-current={screen === "ready" ? "page" : undefined}
                className="inline-flex"
                onClick={(e) => {
                  e.preventDefault();
                  onGo("ready");
                }}
              >
                <span className="tag tag-accent">Ready to send ({readyCount})</span>
              </a>
            </>
          )}
          {isEaMode && (
            <>
              <span className="tag tag-neutral">In queue ({withEACount})</span>
              <a
                href="#"
                aria-current={screen === "ready" ? "page" : undefined}
                className="inline-flex"
                onClick={(e) => {
                  e.preventDefault();
                  onGo("ready");
                }}
              >
                <span className="tag tag-accent">Ready to send ({readyCount})</span>
              </a>
            </>
          )}

          <span className="text-emptify-muted text-[13px]">{userName}</span>
          <button type="button" className="btn-emptify btn-emptify-ghost" onClick={onSignOut}>
            Sign out
          </button>
        </div>
      </div>
    </div>
  );
}
