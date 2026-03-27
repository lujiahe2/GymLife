"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { useAuth } from "@/context/auth-context";
import type { ChatMessageDTO } from "@/lib/chatApi";
import { clearChatHistory, fetchChatHistory, sendChatMessage } from "@/lib/chatApi";

const styles = {
  fab: {
    position: "fixed" as const,
    right: 20,
    bottom: 20,
    width: 56,
    height: 56,
    borderRadius: 999,
    border: "none",
    cursor: "pointer",
    background: "#c8ff00",
    color: "#0a0a0a",
    fontSize: 13,
    fontWeight: 700,
    boxShadow: "0 8px 24px rgba(0,0,0,0.35)",
    zIndex: 50,
  },
  panel: {
    position: "fixed" as const,
    right: 20,
    bottom: 88,
    width: "min(100vw - 40px, 380px)",
    height: 440,
    borderRadius: 16,
    background: "#141414",
    color: "#f2f2f2",
    boxShadow: "0 16px 48px rgba(0,0,0,0.45)",
    display: "flex",
    flexDirection: "column" as const,
    overflow: "hidden",
    zIndex: 50,
    border: "1px solid #2a2a2a",
  },
  header: {
    padding: "12px 16px",
    borderBottom: "1px solid #2a2a2a",
    fontWeight: 600,
    fontSize: 15,
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 8,
  },
  accent: { color: "#c8ff00" },
  messages: {
    flex: 1,
    overflowY: "auto" as const,
    padding: 12,
    display: "flex",
    flexDirection: "column" as const,
    gap: 10,
    fontSize: 14,
    lineHeight: 1.45,
  },
  bubbleUser: {
    alignSelf: "flex-end" as const,
    maxWidth: "88%",
    background: "#2d2d2d",
    padding: "10px 12px",
    borderRadius: "12px 12px 4px 12px",
  },
  bubbleBot: {
    alignSelf: "flex-start" as const,
    maxWidth: "88%",
    background: "#1f1f1f",
    padding: "10px 12px",
    borderRadius: "12px 12px 12px 4px",
    border: "1px solid #2f2f2f",
  },
  inputRow: {
    display: "flex",
    gap: 8,
    padding: 12,
    borderTop: "1px solid #2a2a2a",
    background: "#101010",
  },
  input: {
    flex: 1,
    borderRadius: 10,
    border: "1px solid #333",
    background: "#1a1a1a",
    color: "#f2f2f2",
    padding: "10px 12px",
    fontSize: 14,
    outline: "none",
  },
  send: {
    borderRadius: 10,
    border: "none",
    background: "#c8ff00",
    color: "#0a0a0a",
    fontWeight: 600,
    padding: "0 14px",
    cursor: "pointer",
  },
  muted: { fontSize: 12, color: "#888", padding: "4px 16px 8px" },
  link: { color: "#c8ff00", textDecoration: "underline" },
};

/** Only mount when logged in — see `ChatWidgetGate`. */
export function ChatWidget() {
  const { token } = useAuth();
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessageDTO[]>([]);
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(false);
  const [clearing, setClearing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement | null>(null);

  const loadHistory = useCallback(async () => {
    if (!token) return;
    setError(null);
    try {
      const rows = await fetchChatHistory();
      setMessages(rows);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load chat.");
    }
  }, [token]);

  useEffect(() => {
    if (open && token) void loadHistory();
  }, [open, token, loadHistory]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, open]);

  const displayMessages = useMemo(() => {
    const seen = new Set<number>();
    return messages.filter((m) => {
      if (seen.has(m.id)) return false;
      seen.add(m.id);
      return true;
    });
  }, [messages]);

  async function onSend() {
    const trimmed = text.trim();
    if (!trimmed || !token || loading || clearing) return;
    setLoading(true);
    setError(null);
    setText("");
    try {
      await sendChatMessage(trimmed);
      await loadHistory();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Send failed.");
    } finally {
      setLoading(false);
    }
  }

  async function onClearHistory() {
    if (!token || clearing || loading) return;
    if (displayMessages.length === 0) return;
    if (
      !window.confirm(
        "Clear all messages in this chat? This cannot be undone.",
      )
    ) {
      return;
    }
    setClearing(true);
    setError(null);
    try {
      await clearChatHistory();
      setMessages([]);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not clear chat.");
    } finally {
      setClearing(false);
    }
  }

  return (
    <>
      <button
        type="button"
        aria-label={open ? "Close chat" : "Open chat"}
        style={styles.fab}
        onClick={() => setOpen((o) => !o)}
      >
        {open ? "×" : "Chat"}
      </button>

      {open && (
        <div style={styles.panel} role="dialog" aria-label="GymLife coach chat">
          <div style={styles.header}>
            <span>
              Coach <span style={styles.accent}>chat</span>
            </span>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <button
                type="button"
                onClick={() => void onClearHistory()}
                disabled={clearing || loading || displayMessages.length === 0}
                style={{
                  background: "transparent",
                  border: "1px solid #444",
                  color: "#aaa",
                  borderRadius: 8,
                  padding: "4px 10px",
                  fontSize: 12,
                  cursor:
                    clearing || loading || displayMessages.length === 0
                      ? "not-allowed"
                      : "pointer",
                  opacity: displayMessages.length === 0 ? 0.45 : 1,
                }}
              >
                {clearing ? "Clearing…" : "Clear history"}
              </button>
              <button
                type="button"
                onClick={() => setOpen(false)}
                style={{
                  background: "transparent",
                  border: "none",
                  color: "#aaa",
                  cursor: "pointer",
                  fontSize: 18,
                }}
              >
                ×
              </button>
            </div>
          </div>

          <>
              <div style={styles.muted}>
                Logged in — messages and profile are stored only for your account.
                Edit basics on{" "}
                <Link href="/profile" style={styles.link}>
                  Profile
                </Link>
                .
              </div>
              <div style={styles.messages}>
                {displayMessages.length === 0 && !error && (
                  <p style={{ color: "#777", margin: 8 }}>
                    Say hi or ask about your plan — the coach uses your saved gym
                    profile when you set it.
                  </p>
                )}
                {displayMessages.map((m) => (
                  <div
                    key={`${m.id}-${m.role}`}
                    style={m.role === "user" ? styles.bubbleUser : styles.bubbleBot}
                  >
                    {m.content}
                  </div>
                ))}
                {loading && (
                  <p style={{ color: "#aaa", fontSize: 13, margin: "4px 0" }}>
                    Coach is thinking… (first reply with Ollama can take 30–60s)
                  </p>
                )}
                {error && (
                  <p style={{ color: "#f66", fontSize: 13 }}>{error}</p>
                )}
                <div ref={bottomRef} />
              </div>
              <div style={styles.inputRow}>
                <input
                  style={styles.input}
                  placeholder={
                    clearing ? "Clearing…" : loading ? "Sending…" : "Type a message…"
                  }
                  value={text}
                  disabled={loading || clearing}
                  onChange={(e) => setText(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      void onSend();
                    }
                  }}
                />
                <button
                  type="button"
                  style={styles.send}
                  disabled={loading || clearing || !text.trim()}
                  onClick={() => void onSend()}
                >
                  Send
                </button>
              </div>
          </>
        </div>
      )}
    </>
  );
}

/** Hides the coach chat FAB until the user is signed in. */
export function ChatWidgetGate() {
  const { token } = useAuth();
  if (!token) return null;
  return <ChatWidget />;
}
