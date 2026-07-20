// Funnel events.
//
// The whole point of this file is the event that never gets sent by a naive
// implementation: the last one before the user leaves. A drop-off IS the
// absence of anything further, so the queue must survive the page going away —
// hence sendBeacon on pagehide, which the browser delivers even as it tears the
// page down. A plain fetch() there is cancelled.

const KEY = "mcv_session";
const ENDPOINT = "/api/events";
const FLUSH_MS = 4000;

function newId() {
  // randomUUID needs a secure context; a plain-http dev server is not one.
  if (globalThis.crypto?.randomUUID) return crypto.randomUUID();
  return `s-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
}

function readSession() {
  try {
    const existing = localStorage.getItem(KEY);
    if (existing) return existing;
    const fresh = newId();
    localStorage.setItem(KEY, fresh);
    return fresh;
  } catch {
    // Private mode or a blocked store: analytics degrades to per-load sessions
    // rather than breaking the app.
    return newId();
  }
}

export const sessionId = readSession();

let queue = [];
let timer = null;

/** Best-effort send. Beacon during teardown, fetch otherwise. */
function flush(useBeacon = false) {
  if (!queue.length) return;
  const body = JSON.stringify({ session_id: sessionId, events: queue });
  queue = [];

  if (useBeacon && navigator.sendBeacon) {
    navigator.sendBeacon(ENDPOINT, new Blob([body], { type: "application/json" }));
    return;
  }
  // Analytics must never surface an error to the user or block anything.
  fetch(ENDPOINT, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body,
    keepalive: true,
  }).catch(() => {});
}

export function track(name, props = {}) {
  queue.push({ name, ...props });
  // Batched: a screen change fires several events and one request is plenty.
  if (!timer) {
    timer = setTimeout(() => {
      timer = null;
      flush();
    }, FLUSH_MS);
  }
}

if (typeof document !== "undefined") {
  // pagehide covers navigation and tab close; visibilitychange covers a phone
  // being locked or the mini-app being swiped away, which never fires pagehide
  // on iOS.
  addEventListener("pagehide", () => flush(true));
  addEventListener("visibilitychange", () => {
    if (document.visibilityState === "hidden") flush(true);
  });
}
