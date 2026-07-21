import { track } from "../analytics.js";
import { api } from "../api.js";
import { icon } from "../icons.js";
import {
  back,
  carLabelShort,
  currentCategory,
  currentProduct,
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
    .map((t) => `<span class="tag">${esc(t)}</span>`)
    .join(" ");

  const buttons = [
    ["another", "refresh", "Другой товар"],
    ["edit", "rotate", "Изменить"],
    ["save", "save", state.saved ? "Сохранено" : "Сохранить"],
  ];
  // Sharing needs Telegram: the bot delivers the image into the user's own
  // chat. Nothing to fall back to in a browser, so the button is not offered.
  if (tg.canShare) {
    buttons.push([
      "share",
      "share",
      state.sharing ? "Отправляем…" : state.shared ? "Отправлено" : "Поделиться",
    ]);
  }

  const done = { save: state.saved, share: state.shared };
  const grid = buttons
    .map(
      ([act, ic, label]) => `<button class="btn" data-act="${act}"
        ${state.sharing && act === "share" ? "disabled" : ""}
        style="display:flex;align-items:center;justify-content:center;gap:8px;padding:12px${
          done[act] ? ";color:var(--green);border-color:rgba(34,197,94,.4)" : ""
        }">${icon(ic, 16)}<span>${label}</span></button>`
    )
    .join("");

  return `
    ${ba({
      key: "resultSlider",
      value: state.resultSlider,
      height: 280,
      before: job.before_url,
      after: job.after_url,
      beforeCap: "[ фото пользователя ]",
      afterCap: "[ AI-результат ]",
    })}
    <div class="row" style="margin-top:11px">
      <button class="btn ${state.resultSlider >= 100 ? "on" : ""}" style="flex:1" data-act="showBefore">До</button>
      <button class="btn ${state.resultSlider <= 0 ? "on" : ""}" style="flex:1" data-act="showAfter">После</button>
      <button class="iconbtn" style="border:1px solid var(--line)" data-act="zoom">${icon("zoom", 18)}</button>
    </div>

    <div class="card" style="margin-top:14px">
      <div class="row" style="align-items:flex-start">
        <div style="flex:1"><h3>${esc(product?.name || "")}</h3>
          <div class="mut2" style="font-size:12px;margin-top:2px">
            ${esc(product?.material || "")} · для ${esc(carLabelShort())}</div>
        </div>${stockPill(product?.stock || "in")}
      </div>
      <div class="chips" style="margin:10px 0 12px">${tags}</div>
      ${priceBlock(state.breakdown)}
    </div>

    <div class="grid2" style="margin-top:12px">${grid}</div>
    ${
      state.resultError
        ? `<div class="note" style="color:var(--red)">${esc(state.resultError)}</div>`
        : ""
    }
    <div class="note">AI-визуализация является предварительной. Итоговый вид может немного отличаться из-за освещения, ракурса и особенностей автомобиля.</div>`;
}

/** Full-screen before/after, reusing the same slider component as the card. */
export function overlay() {
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
          beforeCap: "[ фото пользователя ]",
          afterCap: "[ AI-результат ]",
        })}
      </div>
    </div>`;
}

export const bar = () => `
  <button class="cta" data-act="addToCart" style="display:flex;align-items:center;justify-content:center;gap:10px">
    ${icon("cart", 18)}<span>Добавить в корзину</span></button>`;

export const actions = {
  showBefore: () => setState({ resultSlider: 100 }),
  showAfter: () => setState({ resultSlider: 0 }),
  zoom: () => setState({ zoomOpen: true, zoomSlider: state.resultSlider }),
  closeZoom: () => setState({ zoomOpen: false }),
  another: () => nav("pick"),
  edit: () => back(),

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
      setState({ resultError: "Без разрешения бот не сможет прислать изображение." });
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
      .map((s) => s.name);

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
