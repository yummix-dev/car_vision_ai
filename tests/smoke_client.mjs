// Client render smoke test — executes every screen's render functions under
// Node with minimal browser shims, and fails on any thrown error.
//
// pytest cannot see client JS: a dangling reference like `STEP_LABELS` (renamed
// but missed on one line), or a screen using t() without importing it, throws
// only at render time and silently breaks the funnel past `home`. This runs the
// real render code so that class of bug fails a test instead of shipping.
//
// It is a smoke test, not a DOM test: it calls body()/bar()/overlay()/title()
// and the shared ui helpers with a realistic mid-funnel state and asserts none
// of them throw. It does not simulate clicks.

// ── browser-global shims (must run before importing the client modules) ──
const makeStore = () => {
  const m = new Map();
  return {
    getItem: (k) => (m.has(k) ? m.get(k) : null),
    setItem: (k, v) => m.set(k, String(v)),
    removeItem: (k) => m.delete(k),
    clear: () => m.clear(),
  };
};
globalThis.localStorage = makeStore();
globalThis.sessionStorage = makeStore();
globalThis.window = globalThis; // tg.js reads window.Telegram?.WebApp → undefined
// Deliberately no `document`: analytics.js guards on it and skips its listeners.

const base = new URL("../web/js/", import.meta.url);
const load = (p) => import(new URL(p, base).href);

const ui = await load("ui.js");
const { state, defaultSelections } = await load("state.js");
const { setLang } = await load("i18n.js");

// The v2 architecture: entry is the zone grid; photo and manual car selection
// are two screens; payments/quota/referrals/compare are gone.
const SCREEN_NAMES = [
  "lang", "home", "upload", "car", "catalog", "config",
  "generating", "result", "cart", "request", "success", "gallery", "showcase",
];
const screens = {};
for (const n of SCREEN_NAMES) screens[n] = await load(`screens/${n}.js`);

// ── a structurally complete mock catalog ──
const rul = {
  id: "rul", label: "Руль", noun_cap: "Руль", acc: "руль", title: "Рули",
  sub: "Кожа, карбон.", shoot_title: "Сфотографируйте руль", pick_sub: "Кожа, карбон",
  is_wheel: true, photo: "rul.jpg", gen_steps: ["Шаг 1", "Шаг 2", "Шаг 3"],
  option_groups: [
    { id: "leather", label: "Цвет кожи", type: "segment", default: "black", ui: "swatch_square",
      choices: [
        { id: "black", label: "Чёрный", hex: "#1c1c1e", price_delta: 0 },
        { id: "red", label: "Красный", hex: "#7a2530", price_delta: 0 },
      ] },
    { id: "insert", label: "Вставка", type: "segment", default: "leather",
      choices: [
        { id: "leather", label: "Кожа", price_delta: 0 },
        { id: "carbon", label: "Карбон", price_delta: 300000 },
      ] },
    { id: "led", label: "LED-подсветка", type: "toggle", default: "on", ui: "switch",
      choices: [{ id: "on", label: "LED-подсветка", price_delta: 250000 }] },
  ],
  products: [
    { id: "amg", category: "rul", name: "Mercedes-AMG Performance", base_price: 6200000,
      material: "Кожа + перфорация", tags: ["AMG", "LED"], time: "2–3 часа", stock: "in",
      popular: true, photo: "amg.jpg", flags: { carbon: false, has_led: true, has_paddles: true },
      default_config: { leather: "black", insert: "leather", led: "on" } },
    { id: "rs", category: "rul", name: "Carbon RS", base_price: 6900000, material: "Карбон",
      tags: ["Карбон"], time: "2–3 часа", stock: "order", popular: false, photo: null,
      flags: { carbon: true }, default_config: {} },
  ],
};
const audio = {
  id: "audio", label: "Магнитола", noun_cap: "Магнитола", acc: "магнитолу", title: "Магнитолы",
  sub: "Android-экраны.", shoot_title: "Сфотографируйте магнитолу", pick_sub: "Android",
  is_wheel: false, photo: "audio.jpg", gen_steps: ["A", "B"],
  option_groups: [
    { id: "size", label: "Диагональ", type: "segment", default: "s9",
      choices: [{ id: "s9", label: "9\"", price_delta: 0 }, { id: "s10", label: "10\"", price_delta: 400000 }] },
  ],
  products: [
    { id: "au1", category: "audio", name: "Teyes CC3", base_price: 3200000, material: "IPS",
      tags: ["Android"], time: "3 часа", stock: "in", popular: true, photo: null,
      flags: {}, default_config: {} },
  ],
};
const catalog = { categories: [rul, audio], car_options: { brands: ["Chevrolet", "BMW"], models: ["Malibu", "X5"], years: [2022, 2023] } };

// ── mid-funnel state, everything populated so conditional paths render ──
function seedState() {
  const product = rul.products[0];
  Object.assign(state, {
    catalog,
    config: { bot_username: "bot", app_name: "app", currency: "сум", telegram_bot_username: "bot" },
    brand: "Chevrolet", model: "Malibu", year: 2023, carLabel: "Chevrolet Malibu 2023",
    carField: null,
    category: "rul", filter: "pop", productId: "amg",
    selections: defaultSelections(rul, product),
    services: [{ id: 1, name: "Установка", price: 500000, default_on: true }],
    selectedServices: [1],
    breakdown: {
      product_name: product.name, total: 6650000, total_formatted: "6 650 000",
      lines: [
        { label: product.name, amount: 6200000, amount_formatted: "6 200 000" },
        { label: "LED-подсветка", amount: 250000, amount_formatted: "250 000" },
      ],
    },
    photoSource: "demo", photoId: "p1", photoUrl: "/media/p1.jpg",
    jobId: "j1",
    job: { job_id: "j1", status: "done", progress: 100, step_index: 2,
      steps: ["Шаг 1", "Шаг 2", "Шаг 3"], sub: "Меняем только руль.",
      before_url: "/media/b.jpg", after_url: "/media/a.jpg", after_photo_id: "a" },
    gallery: [{ id: 1, job_id: "j1", product_id: "amg", product_name: product.name, category_label: "Руль",
      car_label: "Chevrolet Malibu 2023", before_url: "/media/b.jpg", after_url: "/media/a.jpg", created_at: 1000 }],
    galleryView: null, galleryConfirmDelete: false,
    showcase: [{ id: 1, car_model: "Malibu", car_label: "Chevrolet Malibu 2023", category_id: "rul",
      category_label: "Руль", title: "Руль Mercedes-AMG", before_url: "/media/b.jpg", after_url: "/media/a.jpg" }],
    showcaseFilter: "",
    cart: [{ uid: "x1", productId: "amg", categoryLabel: "Руль", name: product.name, time: "2–3 часа",
      total: 6650000, selections: { leather: "black" }, serviceIds: [1], serviceLines: ["Установка"],
      chips: ["LED-подсветка"], image: "/media/a.jpg" }],
    form: { name: "Иван", phone: "+998900000000", telegram: "@ivan", date: "", comment: "" },
    reqExtra: false, paymentMethod: "cash",
    booking: { booking_id: 214, status: "received", positions: 1, total: 6650000,
      total_formatted: "6 650 000", car_label: "Chevrolet Malibu 2023", payment_method: "cash" },
    saved: true, shared: false, sharing: false, resultError: "",
    zoomOpen: false, resultSlider: 50, zoomSlider: 50, gallerySlider: 50,
  });
}

// ── run every render path, collecting any thrown error ──
const failures = [];
function run(desc, fn) {
  try { fn(); } catch (e) { failures.push(`[${lang}] ${desc}: ${e.name}: ${e.message}`); }
}

let lang;
for (lang of ["ru", "uz"]) {
  setLang(lang);
  seedState();

  // Progress bar for every screen — where the step-indicator refactor lived.
  for (const n of SCREEN_NAMES) run(`progressBar(${n})`, () => ui.progressBar(n));

  // Each screen's render functions.
  for (const n of SCREEN_NAMES) {
    const s = screens[n];
    state.screen = n;
    if (s.title) run(`${n}.title`, () => s.title());
    if (s.body) run(`${n}.body`, () => s.body());
    if (s.bar) run(`${n}.bar`, () => s.bar());
    if (s.overlay) run(`${n}.overlay`, () => s.overlay());
  }

  // Car screen: each of the three field-pickers open.
  for (const key of ["brand", "model", "year"]) {
    state.carField = key;
    run(`car.body(field=${key})`, () => screens.car.body());
  }
  state.carField = null;

  // Gated overlays and alternate states.
  state.zoomOpen = true; run("result.overlay(zoom open)", () => screens.result.overlay());
  state.zoomOpen = false;
  state.galleryView = state.gallery[0];
  run("gallery.overlay(view)", () => screens.gallery.overlay());
  state.galleryConfirmDelete = true;
  run("gallery.overlay(confirm delete)", () => screens.gallery.overlay());
  state.galleryView = null; state.galleryConfirmDelete = false;
  state.job = { ...state.job, status: "error", error: "boom", progress: 0, step_index: 0 };
  run("generating.body(error)", () => screens.generating.body());
  run("generating.bar(error)", () => screens.generating.bar());

  // The optional details section on the request screen, expanded.
  state.reqExtra = true; run("request.body(details open)", () => screens.request.body());
  state.reqExtra = false;

  // Empty-cart path.
  const savedCart = state.cart; state.cart = [];
  run("cart.body(empty)", () => screens.cart.body());
  run("cart.bar(empty)", () => screens.cart.bar());
  state.cart = savedCart;

  // Non-wheel catalog path.
  state.category = "audio"; state.productId = "au1"; state.filter = "pop";
  run("catalog.body(non-wheel)", () => screens.catalog.body());
  run("config.body(non-wheel)", () => screens.config.body());

  // A few ui helpers directly.
  run("ui.productCard", () => ui.productCard(rul.products[0]));
  run("ui.zoneCard", () => { ui.zoneCard(rul); ui.zoneCard(audio, true); });
  run("ui.priceBlock", () => ui.priceBlock(state.breakdown));
  run("ui.stockPill", () => { ui.stockPill("in"); ui.stockPill("order"); });
  run("ui.appHeader", () => ui.appHeader({ inTelegram: false, canBack: true, cartCount: 1, title: "Руль" }));
  run("ui.appHeader(telegram)", () => ui.appHeader({ inTelegram: true, canBack: true, cartCount: 0, title: "Руль" }));
}

if (failures.length) {
  console.error("CLIENT SMOKE FAILURES:\n" + failures.join("\n"));
  process.exit(1);
}
console.log(`client smoke ok: ${SCREEN_NAMES.length} screens × 2 languages rendered clean`);
process.exit(0);
