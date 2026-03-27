"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { useAuth } from "@/context/auth-context";
import {
  apiGetProfile,
  apiPatchProfile,
  type SexOption,
} from "@/lib/authApi";

const SEX_OPTIONS: { value: SexOption | ""; label: string }[] = [
  { value: "", label: "Select…" },
  { value: "female", label: "Female" },
  { value: "male", label: "Male" },
  { value: "non_binary", label: "Non-binary" },
  { value: "other", label: "Other" },
  { value: "prefer_not_to_say", label: "Prefer not to say" },
];

const GOALS_MAX_LENGTH = 500;

/** Preset goals — stored as `Label · Label · …` plus optional extra text (API `goals` string). */
const GOAL_PRESETS = [
  { id: "fat_loss", label: "Fat loss" },
  { id: "muscle", label: "Build muscle" },
  { id: "strength", label: "Strength" },
  { id: "general", label: "General fitness" },
  { id: "cardio", label: "Cardio / endurance" },
  { id: "mobility", label: "Mobility / flexibility" },
  { id: "sport", label: "Sport performance" },
  { id: "rehab", label: "Rehab / careful training" },
] as const;

function parseGoalsString(raw: string): { presetIds: string[]; extra: string } {
  const t = raw.trim();
  if (!t) return { presetIds: [], extra: "" };
  const segments = (t.includes("·")
    ? t.split(/\s*·\s*/)
    : t.split(/[,;\n]+/)
  )
    .map((s) => s.trim())
    .filter(Boolean);
  const presetIds: string[] = [];
  const unmatched: string[] = [];
  for (const seg of segments) {
    const preset = GOAL_PRESETS.find((g) => g.label === seg);
    if (preset) presetIds.push(preset.id);
    else unmatched.push(seg);
  }
  return {
    presetIds: [...new Set(presetIds)],
    extra: unmatched.join(" · ").slice(0, GOALS_MAX_LENGTH),
  };
}

function buildGoalsString(presetIds: string[], extra: string): string {
  const labels = presetIds.flatMap((id) => {
    const g = GOAL_PRESETS.find((p) => p.id === id);
    return g ? [g.label] : [];
  });
  const parts: string[] = [...labels];
  const ex = extra.trim();
  if (ex) parts.push(ex);
  if (parts.length === 0) return "";
  return parts.join(" · ").slice(0, GOALS_MAX_LENGTH);
}

const EXPERIENCE_LABELS = [
  "Beginner",
  "Novice",
  "Intermediate",
  "Advanced",
  "Expert",
] as const;

function inferExperienceIndexFromLegacy(
  text: string | null | undefined,
): number | null {
  if (!text) return null;
  const t = text.toLowerCase();
  if (t.includes("expert")) return 5;
  if (t.includes("advanced")) return 4;
  if (t.includes("intermediate")) return 3;
  if (t.includes("novice")) return 2;
  if (t.includes("beginner")) return 1;
  return null;
}

export default function ProfilePage() {
  const { token, user, loading: authLoading, logout } = useAuth();
  const router = useRouter();
  const [name, setName] = useState("");
  const [sex, setSex] = useState<SexOption | "">("");
  const [age, setAge] = useState("");
  const [heightCm, setHeightCm] = useState("");
  const [weightKg, setWeightKg] = useState("");
  const [experienceIndex, setExperienceIndex] = useState(3);
  const [goalPresetIds, setGoalPresetIds] = useState<string[]>([]);
  const [goalExtra, setGoalExtra] = useState("");
  const [days, setDays] = useState("");
  const [equipment, setEquipment] = useState("");
  const [injuries, setInjuries] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!authLoading && !token) router.replace("/login");
  }, [authLoading, token, router]);

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    (async () => {
      try {
        const { profile } = await apiGetProfile();
        if (cancelled) return;
        setName(profile.name ?? "");
        setSex((profile.sex as SexOption | null) ?? "");
        setAge(profile.age != null ? String(profile.age) : "");
        setHeightCm(profile.height_cm != null ? String(profile.height_cm) : "");
        setWeightKg(
          profile.weight_kg != null ? String(profile.weight_kg) : "",
        );
        if (profile.experience_level_index != null) {
          setExperienceIndex(profile.experience_level_index);
        } else {
          setExperienceIndex(
            inferExperienceIndexFromLegacy(profile.experience_level) ?? 3,
          );
        }
        {
          const parsed = parseGoalsString(profile.goals ?? "");
          setGoalPresetIds(parsed.presetIds);
          setGoalExtra(parsed.extra);
        }
        setDays(
          profile.days_per_week != null ? String(profile.days_per_week) : "",
        );
        setEquipment(profile.equipment ?? "");
        setInjuries(profile.injuries_limitations ?? "");
      } catch {
        /* network */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [token]);

  async function onSave(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSaved(false);
    setBusy(true);
    try {
      const daysNum = days.trim() === "" ? null : parseInt(days, 10);
      const ageNum = age.trim() === "" ? null : parseInt(age, 10);
      const hNum = heightCm.trim() === "" ? null : parseInt(heightCm, 10);
      const wNum = weightKg.trim() === "" ? null : parseFloat(weightKg);

      await apiPatchProfile({
        name: name.trim() || null,
        sex: sex === "" ? null : sex,
        age:
          ageNum != null && !Number.isNaN(ageNum) && ageNum >= 1 && ageNum <= 120
            ? ageNum
            : null,
        height_cm:
          hNum != null &&
          !Number.isNaN(hNum) &&
          hNum >= 50 &&
          hNum <= 250
            ? hNum
            : null,
        weight_kg:
          wNum != null &&
          !Number.isNaN(wNum) &&
          wNum >= 20 &&
          wNum <= 400
            ? Math.round(wNum * 10) / 10
            : null,
        experience_level_index: experienceIndex,
        experience_level: null,
        goals: buildGoalsString(goalPresetIds, goalExtra) || null,
        days_per_week:
          daysNum != null && !Number.isNaN(daysNum) ? daysNum : null,
        equipment: equipment.trim() || null,
        injuries_limitations: injuries.trim() || null,
      });
      setSaved(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save");
    } finally {
      setBusy(false);
    }
  }

  if (!authLoading && !token) {
    return null;
  }
  if (authLoading) {
    return (
      <main className="profile-page">
        <p style={{ color: "#888", padding: "2rem" }}>Loading…</p>
      </main>
    );
  }

  return (
    <main className="profile-page">
      <div className="profile-card">
        <p className="profile-brand">
          Gym<span style={{ color: "var(--gl-accent)" }}>Life</span>
        </p>
        <h1 className="profile-title">Gym profile</h1>
        <p className="profile-lede">
          Signed in as <strong style={{ color: "var(--gl-accent)" }}>{user?.email}</strong>.
          Name, metrics, and training info — saved only for your account.
        </p>

        <form onSubmit={onSave}>
          <p className="profile-section-title">About you</p>
          <div className="auth-field">
            <label className="auth-label" htmlFor="profile-name">
              Name
            </label>
            <input
              id="profile-name"
              className="auth-input"
              type="text"
              autoComplete="name"
              placeholder="What should we call you?"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>
          <div className="auth-field">
            <label className="auth-label" htmlFor="profile-sex">
              Sex
            </label>
            <select
              id="profile-sex"
              className="auth-input"
              value={sex}
              onChange={(e) =>
                setSex(e.target.value as SexOption | "")
              }
            >
              {SEX_OPTIONS.map((o) => (
                <option key={o.value || "empty"} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </div>
          <div className="auth-field">
            <label className="auth-label" htmlFor="profile-age">
              Age (years)
            </label>
            <input
              id="profile-age"
              className="auth-input"
              type="number"
              min={1}
              max={120}
              inputMode="numeric"
              placeholder="e.g. 28"
              value={age}
              onChange={(e) => setAge(e.target.value)}
            />
          </div>
          <div className="auth-field">
            <label className="auth-label" htmlFor="profile-height">
              Height (cm)
            </label>
            <input
              id="profile-height"
              className="auth-input"
              type="number"
              min={50}
              max={250}
              inputMode="numeric"
              placeholder="e.g. 175"
              value={heightCm}
              onChange={(e) => setHeightCm(e.target.value)}
            />
          </div>
          <div className="auth-field">
            <label className="auth-label" htmlFor="profile-weight">
              Weight (kg)
            </label>
            <input
              id="profile-weight"
              className="auth-input"
              type="number"
              min={20}
              max={400}
              step="0.1"
              inputMode="decimal"
              placeholder="e.g. 72.5"
              value={weightKg}
              onChange={(e) => setWeightKg(e.target.value)}
            />
          </div>

          <p className="profile-section-title">Training</p>
          <div className="auth-field">
            <label className="auth-label" htmlFor="profile-exp-slider">
              Experience level
            </label>
            <div className="profile-range-wrap">
              <input
                id="profile-exp-slider"
                className="auth-input profile-range"
                type="range"
                min={1}
                max={5}
                step={1}
                value={experienceIndex}
                onChange={(e) =>
                  setExperienceIndex(Number(e.target.value))
                }
              />
              <div className="profile-range-ticks">
                <span>1</span>
                <span>2</span>
                <span>3</span>
                <span>4</span>
                <span>5</span>
              </div>
              <p className="profile-range-value">
                {EXPERIENCE_LABELS[experienceIndex - 1]} ({experienceIndex}/5)
              </p>
            </div>
          </div>
          <div className="auth-field">
            <span className="auth-label" id="profile-goals-label">
              Goals
            </span>
            <p className="profile-goals-hint">Swipe sideways to pick one or more — add detail below.</p>
            <div
              className="profile-goals-scroll"
              role="group"
              aria-labelledby="profile-goals-label"
            >
              {GOAL_PRESETS.map((g) => {
                const pressed = goalPresetIds.includes(g.id);
                return (
                  <button
                    key={g.id}
                    type="button"
                    className="profile-goal-chip"
                    aria-pressed={pressed}
                    onClick={() => {
                      setGoalPresetIds((prev) =>
                        pressed
                          ? prev.filter((id) => id !== g.id)
                          : [...prev, g.id],
                      );
                    }}
                  >
                    {g.label}
                  </button>
                );
              })}
            </div>
            <label className="auth-label" htmlFor="profile-goals-extra" style={{ marginTop: 12 }}>
              Extra (optional)
            </label>
            <textarea
              id="profile-goals-extra"
              className="auth-input"
              style={{ minHeight: 64, resize: "vertical" }}
              placeholder="Anything else — e.g. race date, doctor limits…"
              maxLength={GOALS_MAX_LENGTH}
              value={goalExtra}
              onChange={(e) => setGoalExtra(e.target.value)}
            />
            <p
              style={{
                fontSize: 12,
                color: "#888",
                marginTop: 6,
                marginBottom: 0,
              }}
            >
              {buildGoalsString(goalPresetIds, goalExtra).length}/{GOALS_MAX_LENGTH}{" "}
              characters saved
            </p>
          </div>
          <div className="auth-field">
            <label className="auth-label" htmlFor="profile-days">
              Days per week (1–7)
            </label>
            <input
              id="profile-days"
              className="auth-input"
              type="number"
              min={1}
              max={7}
              placeholder="e.g. 3"
              value={days}
              onChange={(e) => setDays(e.target.value)}
            />
          </div>
          <div className="auth-field">
            <label className="auth-label" htmlFor="profile-equip">
              Equipment
            </label>
            <input
              id="profile-equip"
              className="auth-input"
              placeholder="Home, gym, dumbbells only…"
              value={equipment}
              onChange={(e) => setEquipment(e.target.value)}
            />
          </div>
          <div className="auth-field">
            <label className="auth-label" htmlFor="profile-inj">
              Injuries / limitations
            </label>
            <textarea
              id="profile-inj"
              className="auth-input"
              style={{ minHeight: 64, resize: "vertical" }}
              placeholder="Optional — we never diagnose; coach will be cautious"
              value={injuries}
              onChange={(e) => setInjuries(e.target.value)}
            />
          </div>

          {error ? <p className="auth-error">{error}</p> : null}
          {saved ? (
            <p style={{ color: "#8f8", fontSize: 14, marginBottom: 12 }}>Saved.</p>
          ) : null}

          <button
            className="auth-btn-primary"
            type="submit"
            disabled={busy}
            style={{ marginTop: "0.5rem" }}
          >
            {busy ? "Saving…" : "Save profile"}
          </button>
        </form>

        <p style={{ marginTop: 24 }}>
          <button
            type="button"
            onClick={() => {
              logout();
              router.push("/");
            }}
            style={{
              background: "transparent",
              border: "1px solid #555",
              color: "#aaa",
              padding: "8px 14px",
              borderRadius: 8,
              cursor: "pointer",
            }}
          >
            Log out
          </button>
        </p>
        <p style={{ marginTop: 16 }}>
          <Link href="/" className="auth-back" style={{ marginTop: 0 }}>
            ← Back to home
          </Link>
        </p>
      </div>
    </main>
  );
}
