import { api } from "./api.js";
import { hasLang, t } from "./i18n.js";
import { back, canGoBack, nav, openScreen, render, restore, setQuiet, setState, state, subscribe } from "./state.js";
import { tg } from "./tg.js";
import { appHeader, stepIndicator } from "./ui.js";

import * as flow from "./screens/flow.js";
import * as home from "./screens/home.js";
import * as example from "./screens/example.js";
import * as pick from "./screens/pick.js";
import * as upload from "./screens/upload.js";
import * as car from "./screens/car.js";
import * as catalog from "./screens/catalog.js";
import * as config from "./screens/config.js";
import * as generating from "./screens/generating.js";
import * as result from "./screens/result.js";
import * as cart from "./screens/cart.js";
import * as request from "./screens/request.js";
import * as success from "./screens/success.js";
import * as referral from "./screens/referral.js";
import * as lang from "./screens/lang.js";
import * as gallery from "./screens/gallery.js";

const SCREENS = {
  lang, flow, home, example, pick, upload, car,
  catalog, config, generating, result, cart, request, success, referral, gallery,
};

const $hdr = document.getElementById("hdr");
const $steps = document.getElementById("steps");
const $scr = document.getElementById("scr");
const $bar = document.getElementById("bar");
const $overlay = document.getElementById("overlay");

let lastScreen = null;

// Telegram's native header back button, driven by the same history stack as the
// in-app one. No-op in a browser.
const setNativeBack = tg.onBack(() => back());

const header = () =>
  appHeader({
    inTelegram: tg.available,
    canBack: canGoBack(),
    cartCount: state.cart.length,
  });

function draw() {
  const screen = SCREENS[state.screen];
  if (!screen) return;

  setNativeBack(canGoBack());
  $hdr.innerHTML = header();
  $steps.innerHTML = stepIndicator(state.screen);
  $scr.innerHTML = screen.body ? screen.body() : "";
  $bar.innerHTML = screen.bar ? screen.bar() : "";
  $overlay.innerHTML = screen.overlay ? screen.overlay() : "";

  if (state.screen !== lastScreen) {
    $scr.scrollTop = 0;
    // Restart the fade-up animation on screen change.
    $scr.style.animation = "none";
    void $scr.offsetHeight;
    $scr.style.animation = "";
    lastScreen = state.screen;
    screen.onEnter?.();
  }
  screen.afterRender?.();
}

subscribe(draw);

// ── Global actions available on every screen ──────────────────
const GLOBAL = {
  back: () => back(),
  // Utility screens remember where they were opened from, so Back returns there.
  openCart: () => openScreen("cart", "cartReturn"),
  openReferral: () => {
    setState({ exhaustedOpen: false, balanceOpen: false });
    openScreen("referral", "referralReturn");
  },
};

document.addEventListener("click", (ev) => {
  const el = ev.target.closest("[data-act]");
  if (!el) return;
  const name = el.dataset.act;
  const handler = SCREENS[state.screen]?.actions?.[name] || GLOBAL[name];
  if (handler) handler(ev, el);
});

// Elements that act as buttons without being one get their keyboard activation
// back here — a native <button> gives this for free, a div with role=button
// does not.
document.addEventListener("keydown", (ev) => {
  if (ev.key !== "Enter" && ev.key !== " ") return;
  const el = ev.target.closest?.('[data-act][role="button"]');
  if (!el) return;
  ev.preventDefault();
  el.click();
});

document.addEventListener("input", (ev) => {
  const el = ev.target;

  // Before/after slider: update the DOM directly rather than re-rendering, so
  // the drag stays smooth and the range input keeps its grab.
  if (el.dataset.slider) {
    const key = el.dataset.slider;
    const v = Number(el.value);
    setQuiet({ [key]: v });
    const wrap = el.closest(".ba");
    if (wrap) {
      wrap.querySelector("[data-ba-after]").style.clipPath = `inset(0 ${100 - v}% 0 0)`;
      wrap.querySelector("[data-ba-div]").style.left = `${v}%`;
      wrap.querySelector("[data-ba-handle]").style.left = `${v}%`;
    }
    return;
  }

  if (el.dataset.field) SCREENS[state.screen]?.onInput?.(el);
});

// ── Boot ──────────────────────────────────────────────────────
(async function boot() {
  tg.ready();

  if (tg.available) {
    // One class swaps the desktop showcase frame for a real mini-app viewport;
    // the rest is CSS.
    document.body.classList.add("in-telegram");
    // Otherwise a drag on the before/after handle, or a scroll, closes the app.
    tg.disableVerticalSwipes();
    tg.setColors(
      getComputedStyle(document.documentElement).getPropertyValue("--bg").trim()
    );
  }

  // Prefill from the Telegram account before the request screen is ever drawn,
  // so the form is already filled rather than filling in under the user.
  if (tg.user) {
    setQuiet({
      form: {
        ...state.form,
        name: tg.user.fullName || state.form.name,
        telegram: tg.user.username ? `@${tg.user.username}` : state.form.telegram,
      },
    });
  }

  // Attribution happens once, on the first open, before anything else can
  // change the user's state. Failures are silent: an unattributed visit is a
  // missed bonus, never a broken app.
  if (tg.startParam) {
    try {
      await api.attribute(tg.startParam);
    } catch {}
  }
  api.invitedBy()
    .then((r) => setState({ invitedPending: Boolean(r.pending) }))
    .catch(() => {});

  try {
    const [data, cfg] = await Promise.all([api.catalog(), api.config()]);
    // Restore after the catalog arrives: saved lines are checked against it,
    // so a product the shop has dropped cannot reach checkout.
    restore(data);
    setState({ catalog: data, config: cfg });
  } catch (e) {
    $scr.innerHTML = `<div class="note" style="color:var(--red)">
      ${t("ui.catalog_error", { msg: e.message })}</div>`;
    return;
  }

  // No language chosen yet → the choice screen comes first.
  if (!hasLang()) state.screen = "lang";
  render();
})();

// Switching language refetches the catalog so its labels come back localized,
// then continues where the language screen was headed.
window.addEventListener("lang-changed", async (ev) => {
  try {
    setState({ catalog: await api.catalog() });
  } catch {}
  nav(ev.detail.dest);
});
