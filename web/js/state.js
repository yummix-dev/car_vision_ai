// The screen/history state machine. No router: `screen` is a string and back
// navigation is a per-screen target, not a free-form stack.

import { track } from "./analytics.js";
import { getLang } from "./i18n.js";

export const state = {
  screen: "home",
  lang: getLang(), // null until chosen — boot routes to the language screen then
  cartReturn: null, // where the cart returns to when closed

  catalog: null,
  config: null, // public server settings: /api/config

  // vehicle
  brand: "Chevrolet",
  model: "Malibu",
  year: 2023,
  carLabel: "Chevrolet Malibu 2023",
  carField: null, // which of brand/model/year has its picker open (null = none)

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
  services: [], // paid services offered for the current category
  selectedServices: [], // ids of chosen services
  breakdown: null,

  // generation
  jobId: null,
  job: null,
  generationKey: null, // one idempotency key per attempt

  // result — `saved`/`shared` are set only after the action actually succeeded
  saved: false,
  shared: false,
  sharing: false,
  resultError: "",
  zoomOpen: false,

  // sliders
  resultSlider: 50,
  zoomSlider: 50,

  cart: [],
  // A single required field (phone); name/telegram prefill from Telegram, date
  // and comment are optional behind the "add details" disclosure.
  form: { name: "", phone: "", telegram: "", date: "", comment: "" },
  reqExtra: false, // is the optional date/comment section expanded
  paymentMethod: "cash", // settled with the master on site; sent for the booking record
  formError: "",
  booking: null,

  // gallery ("Мои примерки")
  gallery: null,
  galleryError: "",
  galleryView: null,
  gallerySlider: 50,
  galleryConfirmDelete: false,

  // showcase ("Наши работы") — the shop's public feed
  showcase: null,
  showcaseError: "",
  showcaseFilter: "",
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
// the job or the balance.

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

// Where "back" goes from each screen — the logical parent, not the literal path
// that led here. The shopping screens back out to a single anchor (cart if the
// build has lines, otherwise home) rather than stepping back down through setup.
// null = terminal.
const anchor = () => (state.cart.length ? "cart" : "home");

const BACK_TARGET = {
  lang: () => null,
  home: () => null,
  upload: () => "home",
  car: () => "upload",
  catalog: anchor,
  config: () => "catalog",
  generating: () => "config",
  result: () => "config",
  cart: () => state.cartReturn || "home",
  request: () => "cart",
  success: () => null, // a submitted booking is done — no way back into it
  gallery: () => "home",
  showcase: () => "home",
};

export function nav(screen) {
  state.screen = screen;
  track("screen_view", { screen });
  render();
}

/** Kept as an alias: call sites read clearer when an auto-advance says `replace`. */
export const replace = nav;

/** Open a utility screen that should return to wherever it was opened from. */
export function openScreen(screen, returnKey) {
  if (returnKey) state[returnKey] = state.screen;
  nav(screen);
}

/** Leave the funnel entirely — a fresh root with nothing behind it. */
export function reset(screen) {
  state.cartReturn = null;
  nav(screen);
}

export function back() {
  const target = BACK_TARGET[state.screen]?.();
  if (!target) return;
  state.carField = null;
  nav(target);
}

export function canGoBack() {
  return Boolean(BACK_TARGET[state.screen]?.());
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
