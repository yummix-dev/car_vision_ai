// The screen/history state machine, ported from the prototype.
// No router: `screen` is a string and `history` is a stack.

import { track } from "./analytics.js";

export const state = {
  screen: "flow",
  history: [],

  catalog: null,
  config: null, // public server settings: /api/config

  // vehicle
  brand: "Chevrolet",
  model: "Malibu",
  year: 2023,
  carLabel: "Chevrolet Malibu 2023",
  analyzing: false,
  carEditing: false,

  // photo
  photoSource: "", // camera | gallery | demo
  photoId: null,
  photoUrl: null,
  uploadError: "",
  rotating: false,

  // shopping
  category: null,
  filter: "pop",
  productId: null,
  selections: {}, // groupId -> choiceId
  breakdown: null,

  // generation
  jobId: null,
  job: null,
  generationKey: null, // one idempotency key per attempt

  // AI try-on balance, server-owned. The client only displays it.
  balance: null,
  balanceHistory: null,
  balanceOpen: false,
  exhaustedOpen: false,
  bonusConfirmOpen: false,

  // reward codes
  codeOpen: false,
  codeInput: "",
  codeError: "",
  codeBusy: false,
  codeResult: null,

  // referrals
  referral: null,
  referralCopied: false,
  invitedPending: false, // this user still owes their inviter a first try-on

  // result — `saved`/`shared` are set only after the action actually succeeded
  saved: false,
  shared: false,
  sharing: false,
  resultError: "",
  zoomOpen: false,

  // sliders
  homeSlider: 44,
  exSlider: 50,
  resultSlider: 50,
  zoomSlider: 50,

  cart: [],
  form: { name: "", phone: "", telegram: "", date: "", comment: "" },
  booking: null,
};

const listeners = new Set();

export function subscribe(fn) {
  listeners.add(fn);
}

export function render() {
  listeners.forEach((fn) => fn());
}

export function setState(patch) {
  Object.assign(state, patch);
  if (PERSISTED.some((k) => k in patch)) save();
  render();
}

// ── persistence ───────────────────────────────────────────────
//
// Only what a customer would be annoyed to retype. Deliberately NOT the photo,
// the job or the balance: photos expire with the media sweep, and a balance
// read from the browser would be a balance the customer can edit.

const STORE_KEY = "mcv_cart";
const PERSISTED = ["cart", "form", "brand", "model", "year", "carLabel"];

function save() {
  try {
    const data = {};
    for (const k of PERSISTED) data[k] = state[k];
    localStorage.setItem(STORE_KEY, JSON.stringify(data));
  } catch {
    // Private mode or a full store: losing persistence is not losing the app.
  }
}

/** Restore at boot, once the catalog is known so stale lines can be checked. */
export function restore(catalog) {
  let data;
  try {
    data = JSON.parse(localStorage.getItem(STORE_KEY) || "null");
  } catch {
    return;
  }
  if (!data) return;

  // A saved line whose product no longer exists would fail at checkout with an
  // error the customer cannot act on. Drop it here instead.
  const known = new Set(
    (catalog?.categories || []).flatMap((c) => c.products.map((p) => p.id))
  );
  const cart = Array.isArray(data.cart)
    ? data.cart.filter((i) => known.has(i.productId))
    : [];

  Object.assign(state, {
    cart,
    form: { ...state.form, ...(data.form || {}) },
    brand: data.brand || state.brand,
    model: data.model || state.model,
    year: data.year || state.year,
    carLabel: data.carLabel || state.carLabel,
  });

  if (cart.length !== (data.cart || []).length) save();
}

export function clearPersisted() {
  try {
    localStorage.removeItem(STORE_KEY);
  } catch {}
}

/** Mutate without re-rendering — for slider drags that update the DOM directly. */
export function setQuiet(patch) {
  Object.assign(state, patch);
}

export function nav(screen) {
  state.history.push(state.screen);
  state.screen = screen;
  // Every screen change reports here, so no screen can be forgotten when one is
  // added later.
  track("screen_view", { screen });
  render();
}

/** Navigate without leaving a history entry (used when generation auto-advances). */
export function replace(screen) {
  state.screen = screen;
  track("screen_view", { screen });
  render();
}

export function back() {
  if (!state.history.length) return;
  state.screen = state.history.pop();
  state.analyzing = false;
  state.carEditing = false;
  render();
}

export function canGoBack() {
  return state.history.length > 0 && state.screen !== "flow";
}

// ── derived helpers ───────────────────────────────────────────
export const currentCategory = () =>
  state.catalog?.categories.find((c) => c.id === state.category) || null;

export const currentProduct = () => {
  const cat = currentCategory();
  return cat?.products.find((p) => p.id === state.productId) || null;
};

export const carLabelShort = () => `${state.brand} ${state.model}`;

export const cartTotal = () => state.cart.reduce((s, i) => s + i.total, 0);

/** Seed selections from a product's default_config, falling back to group defaults. */
export function defaultSelections(cat, product) {
  const out = {};
  for (const g of cat.option_groups) {
    out[g.id] = product.default_config?.[g.id] ?? g.default;
  }
  return out;
}

export const selectionList = () =>
  Object.entries(state.selections).map(([group_id, choice_id]) => ({
    group_id,
    choice_id,
  }));
