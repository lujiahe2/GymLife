import { getApiBaseUrl } from "./apiBase";
import { getStoredToken } from "./auth";

const CAL_FETCH_TIMEOUT_MS = 12_000;

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

export type CalendarDayDTO = {
  date: string;
  training_plan: string;
  diet_plan: string;
};

export type CalendarMonthDTO = {
  year: number;
  month: number;
  days_with_plans: string[];
};

export async function apiGetCalendarDay(isoDate: string): Promise<CalendarDayDTO> {
  const params = new URLSearchParams({ date: isoDate });
  const res = await fetch(`${getApiBaseUrl()}/calendar/day?${params}`, {
    headers: authHeaders(),
    cache: "no-store",
    signal: AbortSignal.timeout(CAL_FETCH_TIMEOUT_MS),
  });
  if (!res.ok) throw new Error(await readApiError(res));
  return res.json();
}

export async function apiPutCalendarDay(body: {
  date: string;
  training_plan: string;
  diet_plan: string;
}): Promise<CalendarDayDTO> {
  const res = await fetch(`${getApiBaseUrl()}/calendar/day`, {
    method: "PUT",
    headers: authHeaders(),
    body: JSON.stringify(body),
    signal: AbortSignal.timeout(CAL_FETCH_TIMEOUT_MS),
  });
  if (!res.ok) throw new Error(await readApiError(res));
  return res.json();
}

export async function apiGetCalendarMonth(
  year: number,
  month: number,
): Promise<CalendarMonthDTO> {
  const params = new URLSearchParams({
    year: String(year),
    month: String(month),
  });
  const res = await fetch(`${getApiBaseUrl()}/calendar/month?${params}`, {
    headers: authHeaders(),
    cache: "no-store",
    signal: AbortSignal.timeout(CAL_FETCH_TIMEOUT_MS),
  });
  if (!res.ok) throw new Error(await readApiError(res));
  return res.json();
}
