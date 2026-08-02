import { track } from "../analytics.js";
import { api } from "../api.js";
import { t } from "../i18n.js";
import { icon } from "../icons.js";
import { fmt } from "../money.js";
import {
  back,
  carLabelShort,
  currentCategory,
  currentProduct,
  defaultSelections,
  nav,
  setState,
  state,
} from "../state.js";
import { tg } from "../tg.js";
import { ba, esc, priceBlock, stockPill } from "../ui.js";

/** Browser fallback for saving: a synthetic <a download> click. */
function anchorDownload(url, fileName) {
  const a = document.createElement("a");
  a.href = url;
  a.download = fileName;
  document.body.appendChild(a);
  a.click();
  a.remove();
  return true;
}

export function body() {
  const product = currentProduct();
  const cat = currentCategory();
  const job = state.job || {};

  const tags = (product?.tags || [])
    .map((tag) => `<span class="tag">${esc(tag)}</span>`)
    .join(" ");

  const buttons = [
    ["another", "refresh", t("result.another")],
    ["edit", "rotate", t("result.edit")],
    ["save", "save", state.saved ? t("result.saved") : t("result.save")],
  ];
  // Compare only makes sense when the section has another product to try.
  if ((cat?.products?.length || 0) > 1) {
    buttons.push(["openCompare", "compare", t("result.compare")]);
  }
  // Sharing needs Telegram: the bot delivers the image into the user's own
  // chat. Nothing to fall back to in a browser, so the button is not offered.
  if (tg.canShare) {
    buttons.push([
      "share",
      "share",
      state.sharing ? t("result.sharing") : state.shared ? t("result.shared") : t("result.share"),
    ]);
  }

  const done = { save: state.saved, share: state.shared };
  const grid = buttons
    .map(
      ([act, ic, label]) => `<button class="ract${done[act] ? " done" : ""}" data-act="${act}"
        ${state.sharing && act === "share" ? "disabled" : ""}>${icon(ic, 16)}<span>${label}</span></button>`
    )
    .join("");

  return `
    ${ba({
      key: "resultSlider",
      value: state.resultSlider,
      height: 280,
      before: job.before_url,
      after: job.after_url,
      beforeCap: t("result.cap_before"),
      afterCap: t("result.cap_after"),
    })}
    <div class="row" style="margin-top:11px">
      <button class="btn ${state.resultSlider >= 100 ? "on" : ""}" style="flex:1" data-act="showBefore">${t("result.before")}</button>
      <button class="btn ${state.resultSlider <= 0 ? "on" : ""}" style="flex:1" data-act="showAfter">${t("result.after")}</button>
      <button class="iconbtn" style="border:1px solid var(--line)" data-act="zoom">${icon("zoom", 18)}</button>
    </div>

    <div class="card" style="margin-top:14px">
      <div class="row" style="align-items:flex-start">
        <div style="flex:1"><h3>${esc(product?.name || "")}</h3>
          <div class="mut2" style="font-size:12px;margin-top:2px">
            ${esc(product?.material || "")} · ${t("config.for")} ${esc(carLabelShort())}</div>
        </div>${stockPill(product?.stock || "in")}
      </div>
      <div class="chips" style="margin:10px 0 12px">${tags}</div>
      ${priceBlock(state.breakdown)}
    </div>

    <div class="racts">${grid}</div>
    ${
      state.resultError
        ? `<div class="note" style="color:var(--red)">${esc(state.resultError)}</div>`
        : ""
    }
    <div class="note">${t("result.note")}</div>`;
}

/** The bottom sheet for picking the second product to compare against. */
function comparePickSheet() {
  const cat = currentCategory();
  const rows = (cat?.products || [])
    .filter((p) => p.id !== state.productId)
    .map(
      (p) => `<button class="btn" data-act="pickCompare" data-id="${esc(p.id)}"
        style="width:100%;text-align:left;padding:10px;margin-top:8px;display:flex;align-items:center;gap:12px">
        <span style="width:56px;height:42px;border-radius:8px;flex:none;background:#131922 ${
          p.photo ? `center/cover url('/img/products/${esc(p.photo)}')` : ""
        }"></span>
        <span style="flex:1;min-width:0">
          <span style="display:block;font-size:14px;font-weight:600">${esc(p.name)}</span>
          <span class="mut2" style="font-size:12px">${fmt(p.base_price)} ${t("ui.currency")}</span>
        </span></button>`
    )
    .join("");
  return `
    <div class="sheet-back" data-act="closeCompare"></div>
    <div class="sheet">
      <div class="sheet-grip"></div>
      <h3 style="margin:0 0 2px">${t("compare.pick_title")}</h3>
      <div class="mut2" style="font-size:12.5px;margin-bottom:6px">${t("compare.pick_sub")}</div>
      ${rows}
      <button class="cta sec" data-act="closeCompare" style="margin-top:14px">${t("compare.cancel")}</button>
    </div>`;
}

/** Full-screen before/after, reusing the same slider component as the card. */
export function overlay() {
  if (state.comparePickOpen) return comparePickSheet();
  if (!state.zoomOpen) return "";
  const job = state.job || {};
  return `
    <div class="zoom" data-act="closeZoom">
      <button class="iconbtn zoom-close" data-act="closeZoom">${icon("close", 22)}</button>
      <div class="zoom-inner">
        ${ba({
          key: "zoomSlider",
          value: state.zoomSlider,
          height: 460,
          before: job.before_url,
          after: job.after_url,
          beforeCap: t("result.cap_before"),
          afterCap: t("result.cap_after"),
        })}
      </div>
    </div>`;
}

export const bar = () => `
  <button class="cta" data-act="addToCart" style="display:flex;align-items:center;justify-content:center;gap:10px">
    ${icon("cart", 18)}<span>${t("result.add_to_cart")}</span></button>`;

export const actions = {
  showBefore: () => setState({ resultSlider: 100 }),
  showAfter: () => setState({ resultSlider: 0 }),
  zoom: () => setState({ zoomOpen: true, zoomSlider: state.resultSlider }),
  closeZoom: () => setState({ zoomOpen: false }),
  another: () => nav("pick"),
  edit: () => back(),

  openCompare: () => setState({ comparePickOpen: true }),
  closeCompare: () => setState({ comparePickOpen: false }),

  // Pick a second product and render it on the SAME photo, then land on the
  // compare screen. A snapshot of the current result is kept as the baseline.
  pickCompare: (_ev, el) => {
    const cat = currentCategory();
    const b = cat?.products.find((p) => p.id === el.dataset.id);
    if (!b) return;
    track("compare_started", { category_id: cat.id, product_id: b.id });
    setState({
      compareBase: {
        productId: state.productId,
        selections: { ...state.selections },
        job: state.job,
        breakdown: state.breakdown,
      },
      comparePickOpen: false,
      comparing: true,
      productId: b.id,
      selections: defaultSelections(cat, b),
      breakdown: null,
      jobId: null,
      job: null,
      // A fresh idempotency key, or the server would return the first render.
      generationKey: `cmp-${b.id}-${Date.now()}`,
      saved: false,
      shared: false,
      resultError: "",
    });
    nav("generating");
  },

  save: async () => {
    const url = state.job?.after_url;
    if (!url) return;
    const absolute = new URL(url, location.origin).href;
    const fileName = `mycar-${state.productId || "result"}.jpg`;

    // Telegram's own download prompt when it exists; an anchor in a browser or
    // on a client older than Bot API 8.0.
    const accepted = tg.canDownload
      ? await tg.downloadFile({ url: absolute, file_name: fileName })
      : anchorDownload(absolute, fileName);

    // Only now is the green "Сохранено" true. A declined prompt leaves the
    // button as it was rather than claiming success.
    if (accepted) {
      track("result_saved", { product_id: state.productId });
      setState({ saved: true, resultError: "" });
    }
  },

  share: async () => {
    if (state.sharing || !state.jobId) return;

    // The bot cannot message a user who has not allowed it — asking first is
    // what turns the later sendPhoto from a guaranteed 403 into a delivery.
    const granted = await tg.requestWriteAccess();
    if (!granted) {
      setState({ resultError: t("result.share_denied") });
      return;
    }

    setState({ sharing: true, resultError: "" });
    try {
      await api.shareResult(state.jobId, state.productId, state.carLabel);
      track("result_shared", { product_id: state.productId });
      setState({ shared: true, sharing: false, resultError: "" });
    } catch (e) {
      setState({ sharing: false, resultError: e.message });
    }
  },

  addToCart: () => {
    const product = currentProduct();
    const cat = currentCategory();
    if (!product || !state.breakdown) return;
    const chips = cat.option_groups
      .map((g) => {
        const cid = state.selections[g.id];
        if (!cid || cid === "off") return null;
        const choice = g.choices.find((c) => c.id === cid);
        return choice ? (g.type === "toggle" ? g.label : choice.label) : null;
      })
      .filter(Boolean);

    // Services chosen on the configurator, carried onto the cart line so the
    // booking recomputes with them and the customer sees what they cover.
    const serviceIds = [...(state.selectedServices || [])];
    const serviceLines = (state.services || [])
      .filter((s) => serviceIds.includes(s.id))
      .map((s) => (s.price ? `${s.name} · ${fmt(s.price)}` : s.name));

    const item = {
      uid: `${product.id}-${state.cart.length}-${Date.now()}`,
      productId: product.id,
      categoryLabel: cat.label,
      name: product.name,
      time: product.time,
      total: state.breakdown.total,
      selections: { ...state.selections },
      serviceIds,
      serviceLines,
      chips,
      // The render this line was chosen from — the cart showed a blank square
      // where the customer's own result belonged.
      image: state.job?.after_url || null,
    };
    track("cart_add", {
      category_id: cat.id,
      product_id: product.id,
      payload: { total: state.breakdown.total },
    });
    // Landed on the cart with the item added; Back from there returns home, not
    // to the result of an item already in the cart.
    setState({ cart: [...state.cart, item], cartReturn: "home" });
    nav("cart");
  },
};
