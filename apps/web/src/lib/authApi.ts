import { getApiBaseUrl } from "./apiBase";
import { getStoredToken } from "./auth";

/** Avoid hanging forever when the API is down (stuck on “Loading…”). */
const AUTH_FETCH_TIMEOUT_MS = 12_000;

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
  const h: Record<string, string> = { "Content-Type": "application/json" };
  if (token) h.Authorization = `Bearer ${token}`;
  return h;
}

export type UserPublic = { id: number; email: string };

export type SexOption =
  | "female"
  | "male"
  | "non_binary"
  | "other"
  | "prefer_not_to_say";

export type GymProfileData = {
  name: string | null;
  sex: SexOption | null;
  age: number | null;
  height_cm: number | null;
  weight_kg: number | null;
  /** 1 = beginner … 5 = expert */
  experience_level_index: number | null;
  experience_level: string | null;
  goals: string | null;
  days_per_week: number | null;
  equipment: string | null;
  injuries_limitations: string | null;
};

export async function apiRegister(
  email: string,
  password: string,
): Promise<{ access_token: string; user: UserPublic }> {
  const res = await fetch(`${getApiBaseUrl()}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
    signal: AbortSignal.timeout(AUTH_FETCH_TIMEOUT_MS),
  });
  if (!res.ok) throw new Error(await readApiError(res));
  return res.json();
}

export async function apiLogin(
  email: string,
  password: string,
): Promise<{ access_token: string; user: UserPublic }> {
  const res = await fetch(`${getApiBaseUrl()}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
    signal: AbortSignal.timeout(AUTH_FETCH_TIMEOUT_MS),
  });
  if (!res.ok) throw new Error(await readApiError(res));
  return res.json();
}

export async function apiGetMe(): Promise<UserPublic> {
  const res = await fetch(`${getApiBaseUrl()}/auth/me`, {
    headers: authHeaders(),
    cache: "no-store",
    signal: AbortSignal.timeout(AUTH_FETCH_TIMEOUT_MS),
  });
  if (!res.ok) throw new Error(await readApiError(res));
  return res.json();
}

export async function apiGetProfile(): Promise<{
  email: string;
  profile: GymProfileData;
}> {
  const res = await fetch(`${getApiBaseUrl()}/profile`, {
    headers: authHeaders(),
    cache: "no-store",
    signal: AbortSignal.timeout(AUTH_FETCH_TIMEOUT_MS),
  });
  if (!res.ok) throw new Error(await readApiError(res));
  return res.json();
}

export async function apiPatchProfile(
  patch: Partial<GymProfileData>,
): Promise<{ email: string; profile: GymProfileData }> {
  const res = await fetch(`${getApiBaseUrl()}/profile`, {
    method: "PATCH",
    headers: authHeaders(),
    body: JSON.stringify(patch),
    signal: AbortSignal.timeout(AUTH_FETCH_TIMEOUT_MS),
  });
  if (!res.ok) throw new Error(await readApiError(res));
  return res.json();
}
