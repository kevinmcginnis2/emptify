"use client";

import { Role, Screen } from "@/lib/emptify/types";

interface NavBarProps {
  role: Role;
  screen: Screen;
  withEACount: number;
  readyCount: number;
  onSetRole: (role: Role) => void;
  onGo: (screen: Screen) => void;
}

export function NavBar({ role, screen, withEACount, readyCount, onSetRole, onGo }: NavBarProps) {
  const isExec = role === "exec";
  const isEA = role === "ea";

  return (
    <div className="border-b border-[var(--color-divider)] sticky top-0 bg-[var(--color-bg)] z-20">
      <div className="nav max-w-[1180px] mx-auto px-[var(--space-6)] gap-[var(--space-6)] flex items-center py-[var(--space-3)]">
        <div className="nav-brand mr-auto">Emptify</div>

        <div className="flex items-center gap-[var(--space-1)]">
          {isExec && (
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
          {isEA && (
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
          {isExec && (
            <>
              <span className="tag tag-neutral">With EA ({withEACount})</span>
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
          {isEA && <span className="tag tag-neutral">In queue ({withEACount})</span>}

          <div className="seg">
            <label className="seg-opt" data-active={isExec}>
              <input
                type="radio"
                name="role"
                className="sr-only"
                checked={isExec}
                onChange={() => onSetRole("exec")}
              />
              Exec
            </label>
            <label className="seg-opt" data-active={isEA}>
              <input
                type="radio"
                name="role"
                className="sr-only"
                checked={isEA}
                onChange={() => onSetRole("ea")}
              />
              EA
            </label>
          </div>
        </div>
      </div>
    </div>
  );
}
