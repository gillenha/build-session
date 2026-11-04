// The session id lives in localStorage so a page reload keeps the conversation's server-side memory.
const KEY = "build-session:session-id";

export function newSessionId(): string {
  const id = `web-${crypto.randomUUID()}`;
  try {
    localStorage.setItem(KEY, id);
  } catch {
    // Storage blocked (private mode): the id just won't survive a reload.
  }
  return id;
}

export function loadSessionId(): string {
  try {
    return localStorage.getItem(KEY) ?? newSessionId();
  } catch {
    return newSessionId();
  }
}
