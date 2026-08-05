// Shared UI pieces. Every render function returns an HTML string; events are
// wired by delegation on [data-act] in app.js.
import { icon } from "./icons.js";
import { t } from "./i18n.js";
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
      ${before ? "" : `<span class="mono">${esc(beforeCap || "")}</span>`}
    </div>
    <div class="${cls(after, true)}" data-ba-after
         style="${bg(after)};clip-path:inset(0 0 0 ${value}%)">
      ${after ? "" : `<span class="mono">${esc(afterCap || "")}</span>`}
    </div>
    <div class="divider" data-ba-div style="left:${value}%"></div>
    <div class="handle" data-ba-handle style="left:${value}%">«»</div>
    <span class="balbl" style="left:9px">${t("result.before")}</span>
    <span class="balbl" style="right:9px">${t("result.after")}</span>
    <input class="bacut" type="range" min="0" max="100" value="${value}" data-slider="${key}">
  </div>`;
}

/** The app header. Pure: everything it varies on is an argument, so it can be
 *  rendered for either environment without booting the app.
 *  Inside Telegram the client draws its own header (back, title, close), so all
 *  that survives here is the cart, and only when it has something in it. */
export function appHeader({ inTelegram, canBack, cartCount, title }) {
  const cartBtn = cartCount
    ? `<span class="cartwrap"><button class="iconbtn" data-act="openCart">${icon("cart", 19)}</button>
        <span class="cartbadge">${cartCount}</span></span>`
    : "";

  if (inTelegram) return cartBtn;

  const backBtn = canBack
    ? `<button class="iconbtn" data-act="back">${icon("back", 20)}</button>`
    : `<span style="width:8px"></span>`;

  return `${backBtn}
    <div class="hdr-title">${esc(title || "MyCar Vision AI")}</div>
    <span class="hdr-spacer"></span>
    ${cartBtn}
    <span class="iconbtn mut2">${icon("close", 19)}</span>`;
}

/** Thin lime progress bar under the header — replaces the step-dot indicator.
 *  A fraction of the funnel, from photo (early) to request (full). */
const PROGRESS = {
  upload: 25, car: 50, catalog: 65, config: 78,
  generating: 88, result: 94, request: 100,
};
export function progressBar(screen) {
  const pct = PROGRESS[screen];
  if (pct === undefined) return "";
  return `<div class="ptrack"><b style="width:${pct}%"></b></div>`;
}

export const stockPill = (stock) =>
  stock === "in"
    ? `<span class="pill in">${t("catalog.in_stock")}</span>`
    : `<span class="pill order">${t("catalog.on_order")}</span>`;

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
    <div class="total"><span class="micro">${t("cart.total")}</span>
      <span class="num">${esc(breakdown.total_formatted)} ${t("ui.currency")}</span></div></div>`;
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
        width:${hub}px;height:${hub}px;border-radius:14px;background:#22252a;
        border:1px solid var(--line)"></div>
      ${
        led
          ? `<div style="position:absolute;left:50%;top:26%;transform:translateX(-50%);
              width:44px;height:5px;border-radius:3px;background:var(--accent);
              box-shadow:0 0 14px 3px rgba(198,240,77,.7)"></div>`
          : ""
      }
    </div>
  </div>`;
}

/** Generic product preview for non-wheel categories. */
export const genericPreview = (label) => `
  <div class="ph" style="height:190px;margin:14px 0">
    <span class="mono">[ ${esc(label)} ]</span>
  </div>`;

/** The shop's own photo when it has one, the striped placeholder when it does not. */
const photoStyle = (photo) =>
  photo
    ? `background-image:url('/img/products/${esc(photo)}');background-size:cover;background-position:center`
    : "";

/** Catalog card — one tap opens the product. Image, name, subtitle, lime price. */
export function productCard(p, { action = "openProduct" } = {}) {
  const sub = [p.material, p.time].filter(Boolean).join(" · ");
  return `
  <div class="card" role="button" tabindex="0" style="padding:0;cursor:pointer;margin-bottom:11px"
    data-act="${action}" data-id="${esc(p.id)}">
    <div class="${p.photo ? "" : "ph"}" style="height:150px;position:relative;display:grid;place-items:center;border-radius:var(--r-lg) var(--r-lg) 0 0;${photoStyle(p.photo)}">
      ${p.photo ? "" : `<span class="mono">[ ${esc(p.name)} ]</span>`}
      <span style="position:absolute;top:8px;right:8px;width:34px;height:34px;border-radius:50%;
        background:rgba(16,17,19,.62);display:grid;place-items:center;color:var(--txt)">${icon("eye", 18)}</span>
    </div>
    <div style="padding:13px 14px 14px">
      <div class="row" style="align-items:flex-start;gap:11px">
        <div style="flex:1;min-width:0">
          <h3>${esc(p.name)}</h3>
          ${sub ? `<div class="mut2" style="font-size:12.5px;margin-top:3px">${esc(sub)}</div>` : ""}
        </div>
        <div class="num" style="font-size:19px;white-space:nowrap;color:var(--accent)">${fmt(p.base_price)}</div>
      </div>
    </div>
  </div>`;
}

/** Home zone tile — full-bleed category photo with a label. */
export const zoneCard = (c, wide = false) => `
  <button class="zonecard${wide ? " wide" : ""}" data-act="pickZone" data-id="${esc(c.id)}"
    style="${c.photo ? `background-image:url('/img/categories/${esc(c.photo)}')` : ""}">
    <span>${esc(c.label)}</span>
  </button>`;

export const optionGroup = (g, sel) => {
  const current = sel[g.id];
  if (g.type === "toggle") {
    const price = g.choices[0]?.price_delta || 0;
    return `<div class="optrow">
      <div>
        <div style="font-size:14.5px">${esc(g.label)}</div>
        ${price ? `<div class="mut2" style="font-size:12px;margin-top:2px">+${fmt(price)} ${t("ui.currency")}</div>` : ""}
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
    return `<div style="padding:13px 0;border-top:1px solid var(--line)">
      <div class="micro" style="margin-bottom:10px">${esc(g.label)}</div>
      <div class="swatches">${sw}</div></div>`;
  }
  // Short-labelled option sets (sizes, diagonals) read best as a segmented row;
  // longer ones fall back to wrapping chips.
  const short = g.choices.every((c) => String(c.label).length <= 4);
  if (short) {
    const seg = g.choices
      .map(
        (c) => `<button class="seg ${current === c.id ? "on" : ""}"
          data-act="setOption" data-group="${esc(g.id)}" data-id="${esc(c.id)}">${esc(c.label)}</button>`
      )
      .join("");
    return `<div style="padding:13px 0;border-top:1px solid var(--line)">
      <div class="micro" style="margin-bottom:10px">${esc(g.label)}</div>
      <div class="segrow">${seg}</div></div>`;
  }
  const chips = g.choices
    .map(
      (c) => `<button class="chip ${current === c.id ? "on" : ""}"
        data-act="setOption" data-group="${esc(g.id)}" data-id="${esc(c.id)}">
        ${esc(c.label)}${c.price_delta ? ` +${fmt(c.price_delta)}` : ""}</button>`
    )
    .join("");
  return `<div style="padding:13px 0;border-top:1px solid var(--line)">
    <div class="micro" style="margin-bottom:10px">${esc(g.label)}</div>
    <div class="chips">${chips}</div></div>`;
};
