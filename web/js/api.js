import { sessionId } from "./analytics.js";
import { tg } from "./tg.js";

/** initData for identity, session id so server-side events join the funnel. */
function authHeaders() {
  return {
    ...(tg.initData ? { "X-Telegram-Init-Data": tg.initData } : {}),
    "X-Session-Id": sessionId,
  };
}

async function req(url, opts = {}) {
  const res = await fetch(url, {
    ...opts,
    // Merged, not spread over: a caller passing `headers` would otherwise
    // replace the whole object and silently drop the auth headers with it.
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
      ...(opts.headers || {}),
    },
  });
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      detail = (await res.json()).detail || detail;
    } catch {}
    throw new Error(detail);
  }
  return res.json();
}

export const api = {
  config: () => req("/api/config"),

  catalog: () => req("/api/catalog"),

  services: (category_id) =>
    req(`/api/catalog/${encodeURIComponent(category_id)}/services`),

  demoPhoto: () => req("/api/photos/demo"),

  rotatePhoto: (photo_id) =>
    req("/api/photos/rotate", {
      method: "POST",
      body: JSON.stringify({ photo_id }),
    }),

  uploadPhoto: async (file) => {
    const fd = new FormData();
    fd.append("file", file);
    // Its own fetch: FormData must set its own Content-Type boundary, so this
    // call cannot go through req() — the auth header is added by hand.
    const res = await fetch("/api/photos", {
      method: "POST",
      body: fd,
      headers: authHeaders(),
    });
    if (!res.ok) {
      let detail = `HTTP ${res.status}`;
      try {
        detail = (await res.json()).detail || detail;
      } catch {}
      throw new Error(detail);
    }
    return res.json();
  },

  recognize: (photo_id) =>
    req("/api/vehicle/recognize", {
      method: "POST",
      body: JSON.stringify({ photo_id }),
    }),

  correct: (make, model, year) =>
    req("/api/vehicle/correct", {
      method: "POST",
      body: JSON.stringify({ make, model, year }),
    }),

  // Accepting the recognised car. Recorded server-side: an invited person must
  // have a car of their own before a referral can qualify.
  confirmCar: (make, model, year) =>
    req("/api/vehicle/confirm", {
      method: "POST",
      body: JSON.stringify({ make, model, year }),
    }),

  quote: (product_id, selections, service_ids = []) =>
    req("/api/pricing/quote", {
      method: "POST",
      body: JSON.stringify({ product_id, selections, service_ids }),
    }),

  balance: (category_id) =>
    req(`/api/generation-balance${category_id ? `?category_id=${encodeURIComponent(category_id)}` : ""}`),

  transactions: () => req("/api/generation-transactions"),

  referral: () => req("/api/referral"),

  attribute: (start_param) =>
    req("/api/referral/attribute", {
      method: "POST",
      body: JSON.stringify({ start_param }),
    }),

  invitedBy: () => req("/api/referral/invited-by"),

  // Only the code goes up. What it is worth is decided on the server.
  activateCode: (code) =>
    req("/api/reward-codes/activate", {
      method: "POST",
      body: JSON.stringify({ code }),
    }),

  startGeneration: (photo_id, product_id, selections, idempotencyKey) =>
    req("/api/generation", {
      method: "POST",
      // One key per attempt, so a retry or a double tap costs a single try.
      headers: idempotencyKey ? { "Idempotency-Key": idempotencyKey } : {},
      body: JSON.stringify({ photo_id, product_id, selections }),
    }),

  pollGeneration: (job_id) => req(`/api/generation/${job_id}`),

  shareResult: (job_id, product_id, car_label) =>
    req("/api/generation/share", {
      method: "POST",
      body: JSON.stringify({ job_id, product_id, car_label }),
    }),

  booking: (payload) =>
    req("/api/booking", { method: "POST", body: JSON.stringify(payload) }),
};
