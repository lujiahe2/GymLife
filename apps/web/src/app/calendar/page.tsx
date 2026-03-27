"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { useAuth } from "@/context/auth-context";
import {
  apiGetCalendarDay,
  apiGetCalendarMonth,
  apiPutCalendarDay,
} from "@/lib/calendarApi";

function toISODateParts(year: number, month: number, day: number): string {
  const m = String(month).padStart(2, "0");
  const d = String(day).padStart(2, "0");
  return `${year}-${m}-${d}`;
}

function localTodayISO(): string {
  const n = new Date();
  return toISODateParts(n.getFullYear(), n.getMonth() + 1, n.getDate());
}

function formatLongDate(iso: string): string {
  const [y, m, d] = iso.split("-").map(Number);
  const dt = new Date(y, m - 1, d);
  return dt.toLocaleDateString(undefined, {
    weekday: "long",
    month: "long",
    day: "numeric",
    year: "numeric",
  });
}

function shiftMonth(year: number, month: number, delta: number): [number, number] {
  const d = new Date(year, month - 1 + delta, 1);
  return [d.getFullYear(), d.getMonth() + 1];
}

type Cell = {
  kind: "prev" | "current" | "next";
  year: number;
  month: number;
  day: number;
};

function buildGrid(year: number, month: number): Cell[] {
  const jsMonth = month - 1;
  const first = new Date(year, jsMonth, 1);
  const last = new Date(year, jsMonth + 1, 0);
  const firstWeekday = first.getDay();
  const daysInMonth = last.getDate();
  const prevLast = new Date(year, jsMonth, 0);
  const daysInPrev = prevLast.getDate();

  const cells: Cell[] = [];

  for (let i = 0; i < firstWeekday; i++) {
    const dayNum = daysInPrev - firstWeekday + 1 + i;
    let py = year;
    let pm = month - 1;
    if (pm < 1) {
      pm = 12;
      py -= 1;
    }
    cells.push({ kind: "prev", year: py, month: pm, day: dayNum });
  }
  for (let d = 1; d <= daysInMonth; d++) {
    cells.push({ kind: "current", year, month, day: d });
  }
  let next = 1;
  let ny = year;
  let nm = month + 1;
  if (nm > 12) {
    nm = 1;
    ny += 1;
  }
  while (cells.length < 42) {
    cells.push({ kind: "next", year: ny, month: nm, day: next });
    next += 1;
  }
  return cells;
}

const WEEKDAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"] as const;

export default function CalendarPage() {
  const { token, loading: authLoading } = useAuth();
  const router = useRouter();

  const now = useMemo(() => new Date(), []);
  const [viewYear, setViewYear] = useState(now.getFullYear());
  const [viewMonth, setViewMonth] = useState(now.getMonth() + 1);
  const [selectedISO, setSelectedISO] = useState(localTodayISO);

  const [markers, setMarkers] = useState<Set<string>>(new Set());
  const [training, setTraining] = useState("");
  const [diet, setDiet] = useState("");
  const [loadingDay, setLoadingDay] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [savedFlash, setSavedFlash] = useState(false);
  const touchStartX = useRef<number | null>(null);

  useEffect(() => {
    if (!authLoading && !token) router.replace("/login");
  }, [authLoading, token, router]);

  const loadMonth = useCallback(async () => {
    if (!token) return;
    try {
      const m = await apiGetCalendarMonth(viewYear, viewMonth);
      const s = new Set(m.days_with_plans.map((d) => d.slice(0, 10)));
      setMarkers(s);
    } catch {
      setMarkers(new Set());
    }
  }, [token, viewYear, viewMonth]);

  useEffect(() => {
    void loadMonth();
  }, [loadMonth]);

  const loadDay = useCallback(async () => {
    if (!token) return;
    setLoadingDay(true);
    setError(null);
    try {
      const d = await apiGetCalendarDay(selectedISO);
      setTraining(d.training_plan ?? "");
      setDiet(d.diet_plan ?? "");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load day");
    } finally {
      setLoadingDay(false);
    }
  }, [token, selectedISO]);

  useEffect(() => {
    void loadDay();
  }, [loadDay]);

  const grid = useMemo(
    () => buildGrid(viewYear, viewMonth),
    [viewYear, viewMonth],
  );

  const monthTitle = useMemo(() => {
    const d = new Date(viewYear, viewMonth - 1, 1);
    return d.toLocaleDateString(undefined, { month: "long", year: "numeric" });
  }, [viewYear, viewMonth]);

  async function onSave(e: React.FormEvent) {
    e.preventDefault();
    if (!token) return;
    setSaving(true);
    setError(null);
    setSavedFlash(false);
    try {
      await apiPutCalendarDay({
        date: selectedISO,
        training_plan: training,
        diet_plan: diet,
      });
      setSavedFlash(true);
      void loadMonth();
      setTimeout(() => setSavedFlash(false), 2000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  function selectCell(c: Cell) {
    setSelectedISO(toISODateParts(c.year, c.month, c.day));
    if (c.kind === "prev") {
      setViewYear(c.year);
      setViewMonth(c.month);
    } else if (c.kind === "next") {
      setViewYear(c.year);
      setViewMonth(c.month);
    }
  }

  if (!authLoading && !token) {
    return null;
  }
  if (authLoading) {
    return (
      <main className="cal-page">
        <p className="cal-muted" style={{ padding: "2rem" }}>
          Loading…
        </p>
      </main>
    );
  }

  const todayISO = localTodayISO();

  function goPrevMonth() {
    const [y, m] = shiftMonth(viewYear, viewMonth, -1);
    setViewYear(y);
    setViewMonth(m);
  }

  function goNextMonth() {
    const [y, m] = shiftMonth(viewYear, viewMonth, 1);
    setViewYear(y);
    setViewMonth(m);
  }

  return (
    <main className="cal-page">
      <div
        className="cal-shell"
        onTouchStart={(e) => {
          touchStartX.current = e.touches[0].clientX;
        }}
        onTouchEnd={(e) => {
          if (touchStartX.current === null) return;
          const dx = e.changedTouches[0].clientX - touchStartX.current;
          touchStartX.current = null;
          if (dx > 56) goPrevMonth();
          else if (dx < -56) goNextMonth();
        }}
      >
        <header className="cal-header">
          <Link href="/" className="cal-back">
            ← Home
          </Link>
          <h1 className="cal-title">Calendar</h1>
          <p className="cal-sub">Training & diet plans by day</p>
        </header>

        <div className="cal-month-nav">
          <button
            type="button"
            className="cal-nav-btn"
            aria-label="Previous month"
            onClick={goPrevMonth}
          >
            ‹
          </button>
          <span className="cal-month-label">{monthTitle}</span>
          <button
            type="button"
            className="cal-nav-btn"
            aria-label="Next month"
            onClick={goNextMonth}
          >
            ›
          </button>
        </div>

        <div className="cal-weekdays" role="row">
          {WEEKDAYS.map((w) => (
            <span key={w} className="cal-weekday">
              {w}
            </span>
          ))}
        </div>

        <div className="cal-grid" role="grid" aria-label="Month">
          {grid.map((c, idx) => {
            const iso = toISODateParts(c.year, c.month, c.day);
            const isToday = iso === todayISO;
            const isSelected = iso === selectedISO;
            const muted = c.kind !== "current";
            const hasPlan = markers.has(iso);
            return (
              <button
                key={`${idx}-${iso}`}
                type="button"
                role="gridcell"
                className={[
                  "cal-cell",
                  muted ? "cal-cell-muted" : "",
                  isToday ? "cal-cell-today" : "",
                  isSelected ? "cal-cell-selected" : "",
                ]
                  .filter(Boolean)
                  .join(" ")}
                onClick={() => selectCell(c)}
              >
                <span className="cal-cell-num">{c.day}</span>
                {hasPlan ? <span className="cal-dot" aria-hidden /> : null}
              </button>
            );
          })}
        </div>

        <section className="cal-detail">
          <h2 className="cal-detail-date">{formatLongDate(selectedISO)}</h2>
          {loadingDay ? (
            <p className="cal-muted">Loading plans…</p>
          ) : (
            <form onSubmit={onSave}>
              <div className="cal-plan-block">
                <label className="cal-plan-label" htmlFor="cal-training">
                  Training plan
                </label>
                <textarea
                  id="cal-training"
                  className="cal-textarea"
                  placeholder="Workout focus, exercises, sets/reps…"
                  value={training}
                  onChange={(e) => setTraining(e.target.value)}
                  rows={5}
                />
              </div>
              <div className="cal-plan-block">
                <label className="cal-plan-label" htmlFor="cal-diet">
                  Diet plan
                </label>
                <textarea
                  id="cal-diet"
                  className="cal-textarea"
                  placeholder="Meals, calories, protein targets…"
                  value={diet}
                  onChange={(e) => setDiet(e.target.value)}
                  rows={5}
                />
              </div>
              {error ? <p className="auth-error">{error}</p> : null}
              {savedFlash ? (
                <p className="cal-saved">Saved for this day.</p>
              ) : null}
              <button className="cal-save-btn" type="submit" disabled={saving}>
                {saving ? "Saving…" : "Save plans"}
              </button>
            </form>
          )}
        </section>
      </div>
    </main>
  );
}
