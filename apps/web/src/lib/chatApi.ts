import { getApiBaseUrl } from "./apiBase";
import { getStoredToken } from "./auth";

async function readApiError(res: Response): Promise<string> {
  const text = await res.text();
  try {
    const data = JSON.parse(text) as { detail?: unknown };
    const d = data.detail;
    if (typeof d === "string") return d;
    if (Array.isArray(d) && d[0] && typeof d[0] === "object" && "msg" in d[0]) {
      return String((d[0] as { msg: string }).msg);
    }
  } catch {
    /* ignore */
  }
  return text || `${res.status} ${res.statusText}`;
}

function authHeaders(): HeadersInit {
  const token = getStoredToken();
  if (!token) throw new Error("Not logged in");
  return {
    "Content-Type": "application/json",
    Authorization: `Bearer ${token}`,
  };
}

export type ChatMessageDTO = {
  id: number;
  role: "user" | "assistant";
  content: string;
  created_at: string;
};

export async function fetchChatHistory(): Promise<ChatMessageDTO[]> {
  const res = await fetch(`${getApiBaseUrl()}/chat/messages`, {
    cache: "no-store",
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(await readApiError(res));
  return res.json();
}

export async function sendChatMessage(
  content: string,
): Promise<{ user_message: ChatMessageDTO; assistant_message: ChatMessageDTO }> {
  const tz =
    typeof Intl !== "undefined"
      ? Intl.DateTimeFormat().resolvedOptions().timeZone
      : undefined;
  const res = await fetch(`${getApiBaseUrl()}/chat/messages`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify({
      content,
      ...(tz ? { client_timezone: tz } : {}),
    }),
  });
  if (!res.ok) throw new Error(await readApiError(res));
  return res.json();
}

export async function clearChatHistory(): Promise<void> {
  const res = await fetch(`${getApiBaseUrl()}/chat/messages`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(await readApiError(res));
}
