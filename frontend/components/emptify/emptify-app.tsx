"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { NavBar } from "./nav-bar";
import { BoardScreen } from "./board-screen";
import { ConnectScreen } from "./connect-screen";
import { VoiceScreen } from "./voice-screen";
import { QueueScreen } from "./queue-screen";
import { ReadyScreen } from "./ready-screen";
import { DetailScreen } from "./detail-screen";
import { HandoffDialog } from "./handoff-dialog";
import { ConfirmSendDialog } from "./confirm-send-dialog";
import { EmptifyToast } from "./toast";
import * as api from "@/lib/emptify/api";
import {
  Account,
  AccountId,
  ConfirmDialogState,
  EmailThread,
  HandoffDialogState,
  Role,
  Screen,
  ToastState,
  Tone,
  ToneLoadingState,
  VoiceMode,
  VoiceState,
} from "@/lib/emptify/types";

const DOMAINS_DEBOUNCE_MS = 500;
const NOTES_DEBOUNCE_MS = 500;
const DRAFT_DEBOUNCE_MS = 500;
const VOICE_POLL_MS = 2000;
const RESTORABLE_SCREENS: Screen[] = ["board", "voice", "connect", "queue", "ready"];

const EMPTY_VOICE_PROFILE = { sampleSize: "Loading…", rebuilding: false, notes: "", traits: [] };
const EMPTY_VOICE_STATE: VoiceState = { client: EMPTY_VOICE_PROFILE, internal: EMPTY_VOICE_PROFILE };

export function EmptifyApp() {
  const [role, setRole] = useState<Role>("exec");
  const [screen, setScreen] = useState<Screen>("board");
  const [accountFilter, setAccountFilter] = useState<AccountId | "all">("all");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detailOrigin, setDetailOrigin] = useState<Screen>("board");

  const [accounts, setAccounts] = useState<Account[]>([]);
  const [connecting, setConnecting] = useState(false);
  const [emails, setEmails] = useState<EmailThread[]>([]);
  const [boardLoading, setBoardLoading] = useState(false);
  const [voice, setVoice] = useState<VoiceState>(EMPTY_VOICE_STATE);

  const [toast, setToast] = useState<ToastState | null>(null);
  const [confirmDialog, setConfirmDialog] = useState<ConfirmDialogState | null>(null);
  const [handoffDialog, setHandoffDialog] = useState<HandoffDialogState | null>(null);
  const [toneLoading, setToneLoading] = useState<ToneLoadingState | null>(null);

  const undoTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const domainsTimers = useRef<Record<string, ReturnType<typeof setTimeout>>>({});
  const notesTimers = useRef<Record<string, ReturnType<typeof setTimeout>>>({});
  const draftTimers = useRef<Record<string, ReturnType<typeof setTimeout>>>({});
  const voicePollIntervals = useRef<Record<string, ReturnType<typeof setInterval>>>({});

  useEffect(() => {
    return () => {
      if (undoTimer.current) clearTimeout(undoTimer.current);
      Object.values(domainsTimers.current).forEach(clearTimeout);
      Object.values(notesTimers.current).forEach(clearTimeout);
      Object.values(draftTimers.current).forEach(clearTimeout);
      Object.values(voicePollIntervals.current).forEach(clearInterval);
    };
  }, []);

  useEffect(() => {
    api.getAccounts().then(setAccounts).catch(() => {});
    api.getVoice().then(setVoice).catch(() => {});

    const params = new URLSearchParams(window.location.search);
    const requestedScreen = params.get("screen");
    if (requestedScreen && RESTORABLE_SCREENS.includes(requestedScreen as Screen)) {
      setScreen(requestedScreen as Screen);
    }
    const requestedAccount = params.get("account");
    if (requestedAccount) {
      setAccountFilter(requestedAccount);
    }
  }, []);

  // Keeps the current screen (and, on the board, the account filter) in the
  // URL — except "detail", which has no stable reference until threads come
  // from the backend — so a refresh, including the one after the OAuth
  // connect/reconnect redirect, lands back where the user was instead of
  // resetting to the board with no filter.
  useEffect(() => {
    if (screen === "detail") return;
    const params = new URLSearchParams();
    if (screen !== "board") params.set("screen", screen);
    if (screen === "board" && accountFilter !== "all") params.set("account", accountFilter);
    const query = params.toString();
    window.history.replaceState(null, "", query ? `${window.location.pathname}?${query}` : window.location.pathname);
  }, [screen, accountFilter]);

  // The board endpoint runs a real (incremental) Gmail sync server-side on
  // every call, so re-fetching whenever the board is visited — not just on
  // first mount — is what actually picks up newly-arrived mail. A sync with
  // a backlog of new mail can take a while (one real Gmail fetch + one real
  // Claude call per new message, processed one at a time), so boardLoading
  // gives the screen something to show instead of looking stuck.
  useEffect(() => {
    if (screen !== "board") return;
    setBoardLoading(true);
    api
      .getThreads("board", accountFilter === "all" ? undefined : accountFilter)
      .then((boardEmails) => {
        setEmails((prev) => [...prev.filter((e) => e.status !== "board"), ...boardEmails]);
      })
      .catch(() => {})
      .finally(() => setBoardLoading(false));
  }, [screen, accountFilter]);

  const getEmail = useCallback((id: string) => emails.find((e) => e.id === id), [emails]);

  const updateEmail = useCallback((id: string, patch: Partial<EmailThread>) => {
    setEmails((prev) => prev.map((e) => (e.id === id ? { ...e, ...patch } : e)));
  }, []);

  const showToast = useCallback((message: string, showUndo: boolean, undoFn?: () => void) => {
    if (undoTimer.current) clearTimeout(undoTimer.current);
    setToast({ message, showUndo, undoFn });
    undoTimer.current = setTimeout(() => setToast(null), 12000);
  }, []);

  const undoLast = useCallback(() => {
    if (toast?.undoFn) toast.undoFn();
    if (undoTimer.current) clearTimeout(undoTimer.current);
    setToast(null);
  }, [toast]);

  const go = useCallback((next: Screen) => setScreen(next), []);

  const setRoleExec = useCallback(() => {
    setRole("exec");
    setScreen("board");
  }, []);
  const setRoleEA = useCallback(() => {
    setRole("ea");
    setScreen("queue");
  }, []);

  const openEmail = useCallback((id: string, origin: Screen) => {
    setSelectedId(id);
    setDetailOrigin(origin);
    setScreen("detail");
  }, []);

  const onBack = useCallback(() => {
    setScreen(detailOrigin);
    setSelectedId(null);
  }, [detailOrigin]);

  const updateDraft = useCallback(
    (id: string, val: string) => {
      updateEmail(id, { draft: val });

      if (draftTimers.current[id]) clearTimeout(draftTimers.current[id]);
      draftTimers.current[id] = setTimeout(() => {
        delete draftTimers.current[id];
        api.patchDraft(id, val, role).catch(() => {
          showToast("Couldn't save draft — try again.", false);
        });
      }, DRAFT_DEBOUNCE_MS);
    },
    [role, showToast, updateEmail],
  );

  const updateNotes = useCallback(
    (which: VoiceMode, val: string) => {
      setVoice((prev) => ({ ...prev, [which]: { ...prev[which], notes: val } }));

      if (notesTimers.current[which]) clearTimeout(notesTimers.current[which]);
      notesTimers.current[which] = setTimeout(() => {
        delete notesTimers.current[which];
        api.patchVoiceNotes(which, val, role).catch(() => {
          showToast("Couldn't save notes — try again.", false);
        });
      }, NOTES_DEBOUNCE_MS);
    },
    [role, showToast],
  );

  const rebuildVoice = useCallback(
    (which: VoiceMode) => {
      api
        .rebuildVoice(which, role)
        .then((profile) => {
          setVoice((prev) => ({ ...prev, [which]: profile }));

          if (voicePollIntervals.current[which]) clearInterval(voicePollIntervals.current[which]);
          voicePollIntervals.current[which] = setInterval(() => {
            api
              .getVoice()
              .then((next) => {
                setVoice(next);
                if (!next[which].rebuilding) {
                  clearInterval(voicePollIntervals.current[which]);
                  delete voicePollIntervals.current[which];
                  showToast(
                    `Rebuilt the ${which === "client" ? "client-facing" : "internal"} voice profile from the last 90 days.`,
                    false,
                  );
                }
              })
              .catch(() => {
                clearInterval(voicePollIntervals.current[which]);
                delete voicePollIntervals.current[which];
              });
          }, VOICE_POLL_MS);
        })
        .catch(() => showToast("Couldn't start rebuilding — try again.", false));
    },
    [role, showToast],
  );

  const updateDomains = useCallback(
    (accId: string, val: string) => {
      setAccounts((prev) => prev.map((a) => (a.id === accId ? { ...a, internalDomains: val } : a)));

      if (domainsTimers.current[accId]) clearTimeout(domainsTimers.current[accId]);
      domainsTimers.current[accId] = setTimeout(() => {
        delete domainsTimers.current[accId];
        api.patchAccountDomains(accId, val, role).catch(() => {
          showToast("Couldn't save internal domains — try again.", false);
        });
      }, DOMAINS_DEBOUNCE_MS);
    },
    [role, showToast],
  );

  const reconnectAccount = useCallback(
    (accId: string) => {
      api
        .reconnectAccount(accId, role)
        .then((authUrl) => {
          window.location.href = authUrl;
        })
        .catch(() => showToast("Couldn't start reconnect — try again.", false));
    },
    [role, showToast],
  );

  const connectNewAccount = useCallback(() => {
    setConnecting(true);
    api
      .getConnectUrl()
      .then((authUrl) => {
        window.location.href = authUrl;
      })
      .catch(() => {
        setConnecting(false);
        showToast("Couldn't start connecting — try again.", false);
      });
  }, [showToast]);

  const openHandoffDialog = useCallback((id: string) => setHandoffDialog({ emailId: id, note: "" }), []);
  const cancelHandoff = useCallback(() => setHandoffDialog(null), []);
  const onHandoffNoteChange = useCallback(
    (value: string) => setHandoffDialog((prev) => (prev ? { ...prev, note: value } : prev)),
    [],
  );
  const submitHandoff = useCallback(() => {
    if (!handoffDialog) return;
    const { emailId, note } = handoffDialog;
    const em = getEmail(emailId);
    if (!em) return;
    updateEmail(emailId, {
      status: "withEA",
      eaNote: note || "Handed off from the board.",
      draftAtHandoff: em.draft,
    });
    setHandoffDialog(null);
    if (screen === "detail") {
      setScreen(detailOrigin);
      setSelectedId(null);
    }
    showToast("Handed to Theo Banks.", false);
  }, [handoffDialog, getEmail, updateEmail, screen, detailOrigin, showToast]);

  const openSendConfirm = useCallback((id: string) => setConfirmDialog({ emailId: id }), []);
  const cancelSend = useCallback(() => setConfirmDialog(null), []);

  const undoPendingAction = useCallback(
    (id: string) => {
      api
        .undoThread(id, role)
        .then((res) => updateEmail(id, { status: res.status as EmailThread["status"] }))
        .catch(() => showToast("Couldn't undo — try again.", false));
    },
    [role, showToast, updateEmail],
  );

  const confirmSendNow = useCallback(() => {
    if (!confirmDialog) return;
    const id = confirmDialog.emailId;
    const em = getEmail(id);
    if (!em) return;
    api
      .sendThread(id, role)
      .then(() => {
        updateEmail(id, { status: "sent" });
        setConfirmDialog(null);
        if (screen === "detail") {
          setScreen(detailOrigin);
          setSelectedId(null);
        }
        showToast(`Sent from ${em.accountEmail}.`, true, () => undoPendingAction(id));
      })
      .catch(() => showToast("Couldn't send — try again.", false));
  }, [confirmDialog, getEmail, role, screen, detailOrigin, showToast, undoPendingAction, updateEmail]);

  const archiveEmail = useCallback(
    (id: string) => {
      api
        .archiveThread(id, role)
        .then(() => {
          updateEmail(id, { status: "archived" });
          if (screen === "detail") {
            setScreen(detailOrigin);
            setSelectedId(null);
          }
          showToast("Archived.", true, () => undoPendingAction(id));
        })
        .catch(() => showToast("Couldn't archive — try again.", false));
    },
    [role, screen, detailOrigin, showToast, undoPendingAction, updateEmail],
  );

  const skipEmail = useCallback(
    (id: string) => {
      api
        .skipThread(id, role)
        .then(() => {
          updateEmail(id, { status: "skipped" });
          if (screen === "detail") {
            setScreen(detailOrigin);
            setSelectedId(null);
          }
          showToast("Skipped from the board.", false);
        })
        .catch(() => showToast("Couldn't skip — try again.", false));
    },
    [role, screen, detailOrigin, showToast, updateEmail],
  );

  const markReady = useCallback(
    (id: string) => {
      const em = getEmail(id);
      if (!em) return;
      const changed = em.draft !== em.draftAtHandoff;
      updateEmail(id, {
        status: "readyToSend",
        draftAuthor: "ea",
        eaChangeSummary: changed ? "Edited the wording before marking ready." : "Reviewed as-is — no changes.",
      });
      if (screen === "detail") {
        setScreen("queue");
        setSelectedId(null);
      }
      showToast("Marked ready — back to Mara's queue.", false);
    },
    [getEmail, updateEmail, screen, showToast],
  );

  const applyTone = useCallback(
    (id: string, tone: Tone) => {
      setToneLoading({ id, tone });
      api
        .postTone(id, tone, role)
        .then((updated) => updateEmail(id, updated))
        .catch(() => showToast("Couldn't rewrite — try again.", false))
        .finally(() => setToneLoading(null));
    },
    [role, showToast, updateEmail],
  );

  const revertTone = useCallback(
    (id: string) => {
      const em = getEmail(id);
      if (!em || em.versionStack.length === 0) return;
      api
        .postRevert(id, role)
        .then((updated) => updateEmail(id, updated))
        .catch(() => showToast("Couldn't revert — try again.", false));
    },
    [getEmail, role, showToast, updateEmail],
  );

  const boardEmails = useMemo(
    () => emails.filter((e) => e.status === "board" && (accountFilter === "all" || e.account === accountFilter)),
    [emails, accountFilter],
  );
  const todayList = useMemo(() => boardEmails.filter((e) => e.bucket === "today"), [boardEmails]);
  const weekList = useMemo(() => boardEmails.filter((e) => e.bucket === "week"), [boardEmails]);
  const waitList = useMemo(() => boardEmails.filter((e) => e.bucket === "wait"), [boardEmails]);

  const queueList = useMemo(() => emails.filter((e) => e.status === "withEA"), [emails]);
  const readyList = useMemo(() => emails.filter((e) => e.status === "readyToSend"), [emails]);

  const withEACount = queueList.length;
  const readyCount = readyList.length;

  const selectedEmail = selectedId ? getEmail(selectedId) : undefined;

  const confirmEmail = confirmDialog ? getEmail(confirmDialog.emailId) : undefined;

  return (
    <div className="min-h-screen bg-[var(--color-bg)] text-[var(--color-text)]">
      <NavBar
        role={role}
        screen={screen}
        withEACount={withEACount}
        readyCount={readyCount}
        onSetRole={(r) => (r === "exec" ? setRoleExec() : setRoleEA())}
        onGo={go}
      />

      <div className="max-w-[1180px] mx-auto p-[var(--space-6)]">
        {screen === "connect" && (
          <ConnectScreen
            accounts={accounts}
            onDomainsChange={updateDomains}
            onReconnect={reconnectAccount}
            onConnect={connectNewAccount}
            connecting={connecting}
          />
        )}

        {screen === "voice" && <VoiceScreen voice={voice} onNotesChange={updateNotes} onRebuild={rebuildVoice} />}

        {screen === "board" && (
          <BoardScreen
            accounts={accounts}
            loading={boardLoading}
            accountFilter={accountFilter}
            onAccountFilterChange={setAccountFilter}
            todayList={todayList}
            weekList={weekList}
            waitList={waitList}
            onOpen={(id) => openEmail(id, "board")}
            onHandoff={openHandoffDialog}
          />
        )}

        {screen === "queue" && <QueueScreen emails={queueList} onOpen={(id) => openEmail(id, "queue")} />}

        {screen === "ready" && <ReadyScreen emails={readyList} onOpen={(id) => openEmail(id, "ready")} />}

        {screen === "detail" && selectedEmail && (
          <DetailScreen
            email={selectedEmail}
            role={role}
            toneLoading={toneLoading}
            onBack={onBack}
            onDraftChange={(val) => updateDraft(selectedEmail.id, val)}
            onTone={(tone) => applyTone(selectedEmail.id, tone)}
            onRevert={() => revertTone(selectedEmail.id)}
            onSendClick={() => openSendConfirm(selectedEmail.id)}
            onHandoffClick={() => openHandoffDialog(selectedEmail.id)}
            onArchive={() => archiveEmail(selectedEmail.id)}
            onSkip={() => skipEmail(selectedEmail.id)}
            onMarkReady={() => markReady(selectedEmail.id)}
          />
        )}
      </div>

      <HandoffDialog
        open={!!handoffDialog}
        note={handoffDialog?.note ?? ""}
        onNoteChange={onHandoffNoteChange}
        onCancel={cancelHandoff}
        onSubmit={submitHandoff}
      />

      <ConfirmSendDialog
        open={!!confirmDialog}
        from={confirmEmail?.accountEmail ?? ""}
        to={confirmEmail?.replyToEmail ?? ""}
        onCancel={cancelSend}
        onConfirm={confirmSendNow}
      />

      {toast && <EmptifyToast message={toast.message} showUndo={toast.showUndo} onUndo={undoLast} />}
    </div>
  );
}
