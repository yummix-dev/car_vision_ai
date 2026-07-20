// Shared UI pieces. Every render function returns an HTML string; events are
// wired by delegation on [data-act] in app.js.
import { icon } from "./icons.js";
import { fmt } from "./money.js";

export const esc = (s) =>
  String(s ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
  );

/** Before/after comparison slider. `key` names the state field holding 0–100. */
export function ba({ key, value, height = 224, before, after, beforeCap, afterCap }) {
  const bg = (src) => (src ? `background-image:url('${esc(src)}')` : "");
  const cls = (src, isAfter) =>
    src ? "layer" : `layer ph${isAfter ? " after" : ""}`;
  return `
  <div class="ba" data-ba="${key}" style="height:${height}px">
    <div class="${cls(before, false)}" style="${bg(before)}">
      ${before ? "" : `<span class="mono">${esc(beforeCap || "[ до ]")}</span>`}
    </div>
    <div class="${cls(after, true)}" data-ba-after
         style="${bg(after)};clip-path:inset(0 ${100 - value}% 0 0)">
      ${after ? "" : `<span class="mono">${esc(afterCap || "[ после ]")}</span>`}
    </div>
    <div class="divider" data-ba-div style="left:${value}%"></div>
    <div class="handle" data-ba-handle style="left:${value}%">«»</div>
    <span class="balbl" style="left:9px">До</span>
    <span class="balbl" style="right:9px">После</span>
    <input class="bacut" type="range" min="0" max="100" value="${value}" data-slider="${key}">
  </div>`;
}

/** The app header. Pure: everything it varies on is an argument, so it can be
 *  rendered for either environment without booting the app. */
export function appHeader({ inTelegram, canBack, cartCount }) {
  // Inside Telegram the client draws its own back button (wired to back() via
  // tg.onBack), so drawing a second one duplicates the control.
  const backBtn =
    !inTelegram && canBack
      ? `<button class="iconbtn" data-act="back">${icon("back", 20)}</button>`
      : `<span style="width:8px"></span>`;

  const cartBtn = cartCount
    ? `<span class="cartwrap"><button class="iconbtn" data-act="openCart">${icon("cart", 19)}</button>
        <span class="cartbadge">${cartCount}</span></span>`
    : "";

  // Window controls: real inside Telegram (✕ closes the app; ⋮ has no menu to
  // open, so it is dropped), inert drawing in the browser mockup — spans, not
  // buttons, so they never pretend to be clickable.
  const controls = inTelegram
    ? `<button class="iconbtn mut2" data-act="closeApp">${icon("close", 19)}</button>`
    : `<span class="iconbtn mut2">${icon("kebab", 19)}</span>
       <span class="iconbtn mut2">${icon("close", 19)}</span>`;

  return `${backBtn}
    <div>
      <div class="hdr-title">MyCar Vision AI</div>
      <div class="hdr-sub">мини-приложение</div>
    </div>
    <span class="hdr-spacer"></span>
    ${cartBtn}
    ${controls}`;
}

export const stockPill = (stock) =>
  stock === "in"
    ? `<span class="pill in">В наличии</span>`
    : `<span class="pill order">Под заказ</span>`;

export function priceBlock(breakdown) {
  if (!breakdown) return "";
  const lines = breakdown.lines
    .map(
      (l) =>
        `<div class="pl"><span>${esc(l.label)}</span><span>${esc(
          l.amount_formatted
        )}</span></div>`
    )
    .join("");
  return `<div class="price">${lines}
    <div class="total"><span class="micro">Итого</span>
      <span class="num">${esc(breakdown.total_formatted)} сум</span></div></div>`;
}

/** Pure-CSS steering-wheel preview, coloured live from the current selections. */
export function wheelPreview(cat, sel, size = 168) {
  const hexOf = (gid, cid) =>
    cat.option_groups.find((g) => g.id === gid)?.choices.find((c) => c.id === cid)
      ?.hex || "#1c1c1e";
  const leather = hexOf("leather", sel.leather);
  const stitch = hexOf("stitch", sel.stitch);
  const led = sel.led === "on";
  const hub = Math.round(size * 0.31);
  return `
  <div style="display:grid;place-items:center;padding:18px 0">
    <div style="position:relative;width:${size}px;height:${size}px">
      <div style="position:absolute;inset:0;border-radius:50%;
        border:${Math.round(size * 0.14)}px solid ${leather};
        box-shadow:inset 0 0 0 3px ${stitch}, 0 10px 30px rgba(0,0,0,.5)"></div>
      <div style="position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);
        width:${hub}px;height:${hub}px;border-radius:14px;background:#1c232d;
        border:1px solid var(--line)"></div>
      ${
        led
          ? `<div style="position:absolute;left:50%;top:26%;transform:translateX(-50%);
              width:44px;height:5px;border-radius:3px;background:var(--blue);
              box-shadow:0 0 14px 3px rgba(59,130,246,.75)"></div>`
          : ""
      }
    </div>
  </div>`;
}

/** Generic product preview for non-wheel categories. */
export const genericPreview = (label) => `
  <div class="ph" style="height:168px;margin:14px 0">
    <span class="mono">[ ${esc(label)} ]</span>
  </div>`;

export function productCard(p, { action = "openProduct" } = {}) {
  const tags = p.tags.map((t) => `<span class="tag">${esc(t)}</span>`).join(" ");
  return `
  <div class="card">
    <div class="ph" style="height:150px;margin:-14px -14px 12px;border-radius:var(--r-lg) var(--r-lg) 0 0;position:relative">
      <span class="mono">[ ${esc(p.name)} ]</span>
      <span style="position:absolute;top:10px;right:10px">${stockPill(p.stock)}</span>
    </div>
    <div class="row" style="align-items:flex-start">
      <div style="flex:1">
        <h3>${esc(p.name)}</h3>
        <div class="mut2" style="font-size:12px;margin-top:2px">${esc(p.material || "")} · ${esc(p.time)}</div>
      </div>
      <div class="num" style="font-size:19px;white-space:nowrap">${fmt(p.base_price)}</div>
    </div>
    <div class="chips" style="margin:10px 0 12px">${tags}</div>
    <button class="cta" data-act="${action}" data-id="${esc(p.id)}">Настроить</button>
  </div>`;
}

export const categoryCard = (c) => `
  <button class="card" style="text-align:left;cursor:pointer" data-act="pickCategory" data-id="${esc(c.id)}">
    <div class="ph sm" style="height:78px;margin:-14px -14px 11px;border-radius:var(--r-lg) var(--r-lg) 0 0">
      <span class="mono">[ ${esc(c.label)} ]</span>
    </div>
    <h3>${esc(c.label)}</h3>
    <div class="mut2" style="font-size:12px;margin-top:3px">${esc(c.pick_sub)}</div>
  </button>`;

const STEP_MAP = {
  pick: 0, upload: 1, car: 2, catalog: 3,
  config: 3, generating: 3, result: 3, cart: 3, request: 3,
};
const STEP_LABELS = ["Раздел", "Фото", "Авто", "Выбор"];

export function stepIndicator(screen) {
  const active = STEP_MAP[screen];
  if (active === undefined) return "";
  const items = STEP_LABELS.map((label, i) => {
    const done = i < active;
    const on = i === active;
    const dot = done
      ? `<span class="stepdot done">${icon("check", 11, 2.6)}</span>`
      : `<span class="stepdot ${on ? "on" : ""}">${i + 1}</span>`;
    return `<div class="step">${dot}
      <span class="steplbl ${on || done ? "on" : ""}">${label}</span>
      ${i < STEP_LABELS.length - 1 ? '<span class="stepline"></span>' : ""}</div>`;
  }).join("");
  return `<div class="steps">${items}</div>`;
}

export const optionGroup = (g, sel) => {
  const current = sel[g.id];
  if (g.type === "toggle") {
    const price = g.choices[0]?.price_delta || 0;
    return `<div class="optrow">
      <div>
        <div style="font-size:14px">${esc(g.label)}</div>
        ${price ? `<div class="mut2" style="font-size:12px">+${fmt(price)} сум</div>` : ""}
      </div>
      <button class="sw-track ${current === "on" ? "on" : ""}"
        data-act="toggleOption" data-group="${esc(g.id)}"><b></b></button>
    </div>`;
  }
  if (g.ui === "swatch_square" || g.ui === "swatch_round") {
    const round = g.ui === "swatch_round" ? " round" : "";
    const sw = g.choices
      .map(
        (c) => `<button class="sw${round} ${current === c.id ? "on" : ""}"
          style="background:${esc(c.hex)}" title="${esc(c.label)}"
          data-act="setOption" data-group="${esc(g.id)}" data-id="${esc(c.id)}"></button>`
      )
      .join("");
    return `<div style="padding:11px 0;border-top:1px solid var(--line)">
      <div class="micro" style="margin-bottom:9px">${esc(g.label)}</div>
      <div class="swatches">${sw}</div></div>`;
  }
  const chips = g.choices
    .map(
      (c) => `<button class="chip ${current === c.id ? "on" : ""}"
        data-act="setOption" data-group="${esc(g.id)}" data-id="${esc(c.id)}">
        ${esc(c.label)}${c.price_delta ? ` +${fmt(c.price_delta)}` : ""}</button>`
    )
    .join("");
  return `<div style="padding:11px 0;border-top:1px solid var(--line)">
    <div class="micro" style="margin-bottom:9px">${esc(g.label)}</div>
    <div class="chips">${chips}</div></div>`;
};
