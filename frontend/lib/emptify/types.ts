export type Role = "exec" | "ea";

export type Screen = "board" | "voice" | "connect" | "queue" | "ready" | "detail";

export type AccountId = string;

export type AccountStatus = "connected" | "expiring" | "reconnect";

export type Bucket = "today" | "week" | "wait";

export type VoiceMode = "client" | "internal";

export type EmailStatus =
  | "board"
  | "withEA"
  | "readyToSend"
  | "sent"
  | "archived"
  | "skipped";

export type DraftAuthor = "emptify" | "ea";

export type Tone = "shorter" | "warmer" | "firmer";

export interface Account {
  id: AccountId;
  name: string;
  type: string;
  email: string;
  status: AccountStatus;
  lastSync: string;
  internalDomains: string;
}

export interface Message {
  from: string;
  at: string;
  body: string;
}

export interface EmailThread {
  id: string;
  account: AccountId;
  accountLabel: string;
  accountEmail: string;
  from: string;
  fromEmail: string;
  subject: string;
  bucket: Bucket;
  reason: string;
  voiceMode: VoiceMode;
  voiceWhy: string;
  messages: Message[];
  draft: string;
  draftAuthor: DraftAuthor;
  versionStack: string[];
  handoffSuggested: boolean;
  handoffReason: string;
  status: EmailStatus;
  prevStatus?: EmailStatus;
  eaNote: string;
  eaChangeSummary: string;
  draftAtHandoff: string;
}

export interface VoiceTrait {
  label: string;
  value: string;
}

export interface VoiceProfile {
  sampleSize: string;
  rebuilding: boolean;
  notes: string;
  traits: VoiceTrait[];
}

export interface VoiceState {
  client: VoiceProfile;
  internal: VoiceProfile;
}

export type ToneData = Record<string, Record<Tone, string>>;

export interface ToastState {
  message: string;
  showUndo: boolean;
  undoFn?: () => void;
}

export interface HandoffDialogState {
  emailId: string;
  note: string;
}

export interface ConfirmDialogState {
  emailId: string;
}

export interface ToneLoadingState {
  id: string;
  tone: Tone;
}
