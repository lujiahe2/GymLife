"use client";

import Link from "next/link";

import { useAuth } from "@/context/auth-context";

export default function Home() {
  const { user, loading, logout } = useAuth();

  return (
    <div className="landing-page">
      <header className="landing-shell landing-nav">
        <Link href="/" className="landing-logo">
          Gym<span>Life</span>
        </Link>
        <div className="landing-nav-actions">
          {loading ? (
            <span className="landing-loading">Checking session…</span>
          ) : user ? (
            <>
              <span className="landing-user-pill">
                Signed in as <strong>{user.email}</strong>
              </span>
              <Link className="landing-btn landing-btn--secondary" href="/calendar">
                Calendar
              </Link>
              <Link className="landing-btn landing-btn--secondary" href="/profile">
                Gym profile
              </Link>
              <button
                type="button"
                className="landing-btn landing-btn--ghost"
                onClick={() => logout()}
              >
                Log out
              </button>
            </>
          ) : (
            <>
              <Link className="landing-btn landing-btn--secondary" href="/login">
                Log in
              </Link>
              <Link className="landing-btn landing-btn--primary" href="/register">
                Create account
              </Link>
            </>
          )}
        </div>
      </header>

      <main className="landing-shell landing-main">
        <section className="landing-hero" aria-labelledby="landing-heading">
          <p className="landing-eyebrow">Fitness coaching</p>
          <h1 id="landing-heading" className="landing-hero-title">
            Train smarter with a coach that knows your plan.
          </h1>
          <p className="landing-hero-sub">
            Calendar-based training and diet notes, a conversational coach you can run
            locally with Ollama, and a structured gym profile — built for people getting
            started in the gym.
          </p>

          <div className="landing-cta-row">
            {!loading && user ? (
              <>
                <Link className="landing-btn landing-btn--primary" href="/calendar">
                  Open calendar
                </Link>
                <Link className="landing-btn landing-btn--secondary" href="/profile">
                  Edit gym profile
                </Link>
              </>
            ) : !loading ? (
              <>
                <Link className="landing-btn landing-btn--primary" href="/register">
                  Get started
                </Link>
                <Link className="landing-btn landing-btn--secondary" href="/login">
                  I have an account
                </Link>
              </>
            ) : null}
          </div>

          <p className="landing-hint">
            After you sign in, use the <strong>Chat</strong> control (bottom-right) to
            talk to the coach. Complete your profile so replies stay relevant — your data
            stays on your account only.
          </p>
        </section>

        <section className="landing-features" aria-label="Product features">
          <article className="landing-card">
            <div className="landing-card-icon" aria-hidden>
              📅
            </div>
            <h2 className="landing-card-title">Day-by-day planning</h2>
            <p className="landing-card-text">
              Save training and diet notes per date. Review the month at a glance and
              adjust plans as your schedule changes.
            </p>
          </article>
          <article className="landing-card">
            <div className="landing-card-icon" aria-hidden>
              💬
            </div>
            <h2 className="landing-card-title">Coach chat</h2>
            <p className="landing-card-text">
              Ask questions, update your calendar, and refine your profile through natural
              conversation — powered by your chosen LLM backend.
            </p>
          </article>
          <article className="landing-card">
            <div className="landing-card-icon" aria-hidden>
              🏋️
            </div>
            <h2 className="landing-card-title">Structured profile</h2>
            <p className="landing-card-text">
              Goals, experience, equipment, and limitations in one place so guidance stays
              consistent and safe for beginners.
            </p>
          </article>
        </section>
      </main>

      <footer className="landing-shell landing-footer">
        GymLife — local-first coaching workflow. Run the API and web app on your machine
        for development.
      </footer>
    </div>
  );
}
