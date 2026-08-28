import { Account, EaRelationshipStatus, EmailThread, Me, Tone, VoiceMode, VoiceProfile, VoiceState } from "./types";

export type ThreadListStatus = "board" | "withEA" | "readyToSend";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class UnauthorizedError extends Error {}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });

  if (res.status === 401) {
    throw new UnauthorizedError("Not authenticated");
  }

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

export async function getMe(): Promise<Me> {
  return request<Me>("/api/v1/auth/me");
}

export async function getLoginUrl(): Promise<string> {
  const { authUrl } = await request<{ authUrl: string }>("/api/v1/auth/login");
  return authUrl;
}

export async function logout(): Promise<void> {
  await request("/api/v1/auth/logout", { method: "POST" });
}

export async function getEaRelationship(): Promise<EaRelationshipStatus> {
  return request<EaRelationshipStatus>("/api/v1/relationships");
}

export async function inviteEa(email: string): Promise<EaRelationshipStatus> {
  return request<EaRelationshipStatus>("/api/v1/relationships", {
    method: "POST",
    body: JSON.stringify({ eaEmail: email }),
  });
}

export async function deleteEaRelationship(): Promise<void> {
  await request("/api/v1/relationships", { method: "DELETE" });
}

export async function getAccounts(): Promise<Account[]> {
  return request<Account[]>("/api/v1/accounts");
}

export async function getConnectUrl(): Promise<string> {
  const { authUrl } = await request<{ authUrl: string }>("/api/v1/accounts/connect");
  return authUrl;
}

export async function patchAccountDomains(id: string, domains: string): Promise<Account> {
  return request<Account>(`/api/v1/accounts/${id}`, {
    method: "PATCH",
    body: JSON.stringify({ internalDomains: domains }),
  });
}

export async function reconnectAccount(id: string): Promise<string> {
  const { authUrl } = await request<{ authUrl: string }>(`/api/v1/accounts/${id}/reconnect`, {
    method: "POST",
  });
  return authUrl;
}

export async function getVoice(): Promise<VoiceState> {
  return request<VoiceState>("/api/v1/voice");
}

export async function patchVoiceNotes(mode: VoiceMode, notes: string): Promise<VoiceProfile> {
  return request<VoiceProfile>(`/api/v1/voice/${mode}`, {
    method: "PATCH",
    body: JSON.stringify({ notes }),
  });
}

export async function rebuildVoice(mode: VoiceMode): Promise<VoiceProfile> {
  return request<VoiceProfile>(`/api/v1/voice/${mode}/rebuild`, { method: "POST" });
}

export async function getThreads(
  status: ThreadListStatus,
  account?: string,
  asEa?: boolean,
): Promise<EmailThread[]> {
  const params = new URLSearchParams({ status });
  if (account) params.set("account", account);
  if (asEa) params.set("as_ea", "true");
  return request<EmailThread[]>(`/api/v1/threads?${params.toString()}`);
}

export async function patchDraft(id: string, draft: string): Promise<EmailThread> {
  return request<EmailThread>(`/api/v1/threads/${id}/draft`, {
    method: "PATCH",
    body: JSON.stringify({ draft }),
  });
}

export async function postTone(id: string, tone: Tone): Promise<EmailThread> {
  return request<EmailThread>(`/api/v1/threads/${id}/tone`, {
    method: "POST",
    body: JSON.stringify({ tone }),
  });
}

export async function postRevert(id: string): Promise<EmailThread> {
  return request<EmailThread>(`/api/v1/threads/${id}/revert`, { method: "POST" });
}

export async function sendThread(id: string, cc: string[] = []): Promise<{ status: string }> {
  return request(`/api/v1/threads/${id}/send`, {
    method: "POST",
    body: JSON.stringify({ cc }),
  });
}

export async function archiveThread(id: string): Promise<{ status: string }> {
  return request(`/api/v1/threads/${id}/archive`, { method: "POST" });
}

export async function skipThread(id: string): Promise<{ status: string }> {
  return request(`/api/v1/threads/${id}/skip`, { method: "POST" });
}

export async function markReadThread(id: string): Promise<EmailThread> {
  return request<EmailThread>(`/api/v1/threads/${id}/mark-read`, { method: "POST" });
}

export async function removeThread(id: string): Promise<{ status: string }> {
  return request(`/api/v1/threads/${id}/remove`, { method: "POST" });
}

export async function deleteThread(id: string): Promise<{ status: string }> {
  return request(`/api/v1/threads/${id}/delete`, { method: "POST" });
}

export async function unsubscribeThread(id: string): Promise<{ mechanism: string }> {
  return request(`/api/v1/threads/${id}/unsubscribe`, { method: "POST" });
}

export async function undoThread(id: string): Promise<{ status: string }> {
  return request(`/api/v1/threads/${id}/undo`, { method: "POST" });
}

export async function postHandoff(id: string, note: string): Promise<EmailThread> {
  return request<EmailThread>(`/api/v1/threads/${id}/handoff`, {
    method: "POST",
    body: JSON.stringify({ note }),
  });
}

export async function postMarkReady(id: string): Promise<EmailThread> {
  return request<EmailThread>(`/api/v1/threads/${id}/mark-ready`, { method: "POST" });
}
