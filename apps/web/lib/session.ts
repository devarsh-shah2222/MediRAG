const STORAGE_KEY = "medirag_client_session_id";

/** A per-browser anonymous id so chat history can be grouped without
 * requiring login. Falls back to an in-memory id if storage is unavailable
 * (private browsing, disabled storage). */
export function getClientSessionId(): string {
  if (typeof window === "undefined") return "server";
  try {
    const existing = window.localStorage.getItem(STORAGE_KEY);
    if (existing) return existing;
    const id = crypto.randomUUID();
    window.localStorage.setItem(STORAGE_KEY, id);
    return id;
  } catch {
    return crypto.randomUUID();
  }
}
