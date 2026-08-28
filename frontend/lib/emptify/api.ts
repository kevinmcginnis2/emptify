import { Account, EmailThread, Role, Tone, VoiceMode, VoiceProfile, VoiceState } from "./types";

export type ThreadListStatus = "board" | "withEA" | "readyToSend";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });

  if (!res.ok) {
    let message = res.statusText;
    try {
      const body = await res.json();
      if (body?.error) message = body.error;
    } catch {
      // response had no JSON body
    }
    throw new Error(message);
  }

  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

function roleHeaders(role: Role): HeadersInit {
  return { "X-Role": role };
}

export async function getAccounts(): Promise<Account[]> {
  return request<Account[]>("/api/v1/accounts");
}

export async function getConnectUrl(): Promise<string> {
  const { authUrl } = await request<{ authUrl: string }>("/api/v1/accounts/connect");
  return authUrl;
}

export async function patchAccountDomains(id: string, domains: string, role: Role): Promise<Account> {
  return request<Account>(`/api/v1/accounts/${id}`, {
    method: "PATCH",
    headers: roleHeaders(role),
    body: JSON.stringify({ internalDomains: domains }),
  });
}

export async function reconnectAccount(id: string, role: Role): Promise<string> {
  const { authUrl } = await request<{ authUrl: string }>(`/api/v1/accounts/${id}/reconnect`, {
    method: "POST",
    headers: roleHeaders(role),
  });
  return authUrl;
}

export async function getVoice(): Promise<VoiceState> {
  return request<VoiceState>("/api/v1/voice");
}

export async function patchVoiceNotes(mode: VoiceMode, notes: string, role: Role): Promise<VoiceProfile> {
  return request<VoiceProfile>(`/api/v1/voice/${mode}`, {
    method: "PATCH",
    headers: roleHeaders(role),
    body: JSON.stringify({ notes }),
  });
}

export async function rebuildVoice(mode: VoiceMode, role: Role): Promise<VoiceProfile> {
  return request<VoiceProfile>(`/api/v1/voice/${mode}/rebuild`, {
    method: "POST",
    headers: roleHeaders(role),
  });
}

export async function getThreads(status: ThreadListStatus, account?: string): Promise<EmailThread[]> {
  const params = new URLSearchParams({ status });
  if (account) params.set("account", account);
  return request<EmailThread[]>(`/api/v1/threads?${params.toString()}`);
}

export async function patchDraft(id: string, draft: string, role: Role): Promise<EmailThread> {
  return request<EmailThread>(`/api/v1/threads/${id}/draft`, {
    method: "PATCH",
    headers: roleHeaders(role),
    body: JSON.stringify({ draft }),
  });
}

export async function postTone(id: string, tone: Tone, role: Role): Promise<EmailThread> {
  return request<EmailThread>(`/api/v1/threads/${id}/tone`, {
    method: "POST",
    headers: roleHeaders(role),
    body: JSON.stringify({ tone }),
  });
}

export async function postRevert(id: string, role: Role): Promise<EmailThread> {
  return request<EmailThread>(`/api/v1/threads/${id}/revert`, {
    method: "POST",
    headers: roleHeaders(role),
  });
}

export async function sendThread(id: string, role: Role, cc: string[] = []): Promise<{ status: string }> {
  return request(`/api/v1/threads/${id}/send`, {
    method: "POST",
    headers: roleHeaders(role),
    body: JSON.stringify({ cc }),
  });
}

export async function archiveThread(id: string, role: Role): Promise<{ status: string }> {
  return request(`/api/v1/threads/${id}/archive`, {
    method: "POST",
    headers: roleHeaders(role),
  });
}

export async function skipThread(id: string, role: Role): Promise<{ status: string }> {
  return request(`/api/v1/threads/${id}/skip`, {
    method: "POST",
    headers: roleHeaders(role),
  });
}

export async function markReadThread(id: string, role: Role): Promise<EmailThread> {
  return request<EmailThread>(`/api/v1/threads/${id}/mark-read`, {
    method: "POST",
    headers: roleHeaders(role),
  });
}

export async function removeThread(id: string, role: Role): Promise<{ status: string }> {
  return request(`/api/v1/threads/${id}/remove`, {
    method: "POST",
    headers: roleHeaders(role),
  });
}

export async function deleteThread(id: string, role: Role): Promise<{ status: string }> {
  return request(`/api/v1/threads/${id}/delete`, {
    method: "POST",
    headers: roleHeaders(role),
  });
}

export async function unsubscribeThread(id: string, role: Role): Promise<{ mechanism: string }> {
  return request(`/api/v1/threads/${id}/unsubscribe`, {
    method: "POST",
    headers: roleHeaders(role),
  });
}

export async function undoThread(id: string, role: Role): Promise<{ status: string }> {
  return request(`/api/v1/threads/${id}/undo`, {
    method: "POST",
    headers: roleHeaders(role),
  });
}

export async function postHandoff(id: string, note: string, role: Role): Promise<EmailThread> {
  return request<EmailThread>(`/api/v1/threads/${id}/handoff`, {
    method: "POST",
    headers: roleHeaders(role),
    body: JSON.stringify({ note }),
  });
}

export async function postMarkReady(id: string, role: Role): Promise<EmailThread> {
  return request<EmailThread>(`/api/v1/threads/${id}/mark-ready`, {
    method: "POST",
    headers: roleHeaders(role),
  });
}
