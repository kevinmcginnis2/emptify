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
import { initialAccounts, initialEmails, initialVoice, toneData } from "@/lib/emptify/data";
import {
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
} from "@/lib/emptify/types";

const TONE_DATA = toneData();

export function EmptifyApp() {
  const [role, setRole] = useState<Role>("exec");
  const [screen, setScreen] = useState<Screen>("board");
  const [accountFilter, setAccountFilter] = useState<AccountId | "all">("all");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detailOrigin, setDetailOrigin] = useState<Screen>("board");

  const [accounts, setAccounts] = useState(initialAccounts);
  const [emails, setEmails] = useState(initialEmails);
  const [voice, setVoice] = useState(initialVoice);

  const [toast, setToast] = useState<ToastState | null>(null);
  const [confirmDialog, setConfirmDialog] = useState<ConfirmDialogState | null>(null);
  const [handoffDialog, setHandoffDialog] = useState<HandoffDialogState | null>(null);
  const [toneLoading, setToneLoading] = useState<ToneLoadingState | null>(null);

  const undoTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const toneTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    return () => {
      if (undoTimer.current) clearTimeout(undoTimer.current);
      if (toneTimer.current) clearTimeout(toneTimer.current);
    };
  }, []);

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
    (id: string, val: string) => updateEmail(id, { draft: val }),
    [updateEmail],
  );

  const updateNotes = useCallback((which: VoiceMode, val: string) => {
    setVoice((prev) => ({ ...prev, [which]: { ...prev[which], notes: val } }));
  }, []);

  const rebuildVoice = useCallback((which: VoiceMode) => {
    setVoice((prev) => ({ ...prev, [which]: { ...prev[which], rebuilding: true } }));
    setTimeout(() => {
      setVoice((prev) => ({ ...prev, [which]: { ...prev[which], rebuilding: false } }));
      showToast(
        `Rebuilt the ${which === "client" ? "client-facing" : "internal"} voice profile from the last 90 days.`,
        false,
      );
    }, 900);
  }, [showToast]);

  const updateDomains = useCallback((accId: string, val: string) => {
    setAccounts((prev) => prev.map((a) => (a.id === accId ? { ...a, internalDomains: val } : a)));
  }, []);

  const reconnectAccount = useCallback(
    (accId: string) => {
      setAccounts((prev) =>
        prev.map((a) => (a.id === accId ? { ...a, status: "connected" as const, lastSync: "Just now" } : a)),
      );
      showToast("Reconnected. Syncing now.", false);
    },
    [showToast],
  );

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
  const confirmSendNow = useCallback(() => {
    if (!confirmDialog) return;
    const id = confirmDialog.emailId;
    const em = getEmail(id);
    if (!em) return;
    const prevStatus = em.status;
    updateEmail(id, { status: "sent", prevStatus });
    setConfirmDialog(null);
    if (screen === "detail") {
      setScreen(detailOrigin);
      setSelectedId(null);
    }
    showToast(`Sent from ${em.accountEmail}.`, true, () => updateEmail(id, { status: prevStatus }));
  }, [confirmDialog, getEmail, updateEmail, screen, detailOrigin, showToast]);

  const archiveEmail = useCallback(
    (id: string) => {
      const em = getEmail(id);
      if (!em) return;
      const prevStatus = em.status;
      updateEmail(id, { status: "archived" });
      if (screen === "detail") {
        setScreen(detailOrigin);
        setSelectedId(null);
      }
      showToast("Archived.", true, () => updateEmail(id, { status: prevStatus }));
    },
    [getEmail, updateEmail, screen, detailOrigin, showToast],
  );

  const skipEmail = useCallback(
    (id: string) => {
      const em = getEmail(id);
      if (!em) return;
      const prevStatus = em.status;
      updateEmail(id, { status: "skipped" });
      if (screen === "detail") {
        setScreen(detailOrigin);
        setSelectedId(null);
      }
      showToast("Skipped from the board.", true, () => updateEmail(id, { status: prevStatus }));
    },
    [getEmail, updateEmail, screen, detailOrigin, showToast],
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
      if (toneTimer.current) clearTimeout(toneTimer.current);
      toneTimer.current = setTimeout(() => {
        const em = getEmail(id);
        if (em) {
          const variant = TONE_DATA[id]?.[tone] ?? em.draft;
          updateEmail(id, { draft: variant, versionStack: [...em.versionStack, em.draft] });
        }
        setToneLoading(null);
      }, 550);
    },
    [getEmail, updateEmail],
  );

  const revertTone = useCallback(
    (id: string) => {
      const em = getEmail(id);
      if (!em || em.versionStack.length === 0) return;
      const stack = em.versionStack.slice();
      const prev = stack.pop() as string;
      updateEmail(id, { draft: prev, versionStack: stack });
    },
    [getEmail, updateEmail],
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
          <ConnectScreen accounts={accounts} onDomainsChange={updateDomains} onReconnect={reconnectAccount} />
        )}

        {screen === "voice" && <VoiceScreen voice={voice} onNotesChange={updateNotes} onRebuild={rebuildVoice} />}

        {screen === "board" && (
          <BoardScreen
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
        to={confirmEmail?.fromEmail ?? ""}
        onCancel={cancelSend}
        onConfirm={confirmSendNow}
      />

      {toast && <EmptifyToast message={toast.message} showUndo={toast.showUndo} onUndo={undoLast} />}
    </div>
  );
}
