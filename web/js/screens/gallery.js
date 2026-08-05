import { api } from "../api.js";
import { t } from "../i18n.js";
import { icon } from "../icons.js";
import { defaultSelections, nav, setState, state } from "../state.js";
import { tg } from "../tg.js";
import { ba, esc } from "../ui.js";
import { fmt } from "../money.js";

export const title = () => t("gallery.title");

/** created_at (unix seconds) → "DD.MM.YYYY". */
function fmtDate(sec) {
  const d = new Date((sec || 0) * 1000);
  const pad = (n) => String(n).padStart(2, "0");
  return `${pad(d.getDate())}.${pad(d.getMonth() + 1)}.${d.getFullYear()}`;
}

/** Locate a saved render's product (and its category) in the live catalog. */
function findProduct(productId) {
  for (const cat of state.catalog?.categories || []) {
    const product = cat.products.find((p) => p.id === productId);
    if (product) return { cat, product };
  }
  return null;
}

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

function card(item) {
  const sub = [item.car_label, fmtDate(item.created_at)].filter(Boolean).join(" · ");
  return `<button class="galcard" data-act="openItem" data-id="${item.id}">
    <div class="galthumb" style="background-image:url('${esc(item.after_url)}')"></div>
    <div class="galmeta">
      <div class="galname">${esc(item.product_name)}</div>
      <div class="galsub">${esc(sub)}</div>
    </div>
  </button>`;
}

export function body() {
  if (state.gallery === null) {
    return `<div style="display:grid;place-items:center;padding:64px 0"><div class="spinner"></div></div>`;
  }
  if (state.galleryError) {
    return `<h1>${t("gallery.title")}</h1>
      <div class="note" style="color:var(--red)">${esc(state.galleryError)}</div>`;
  }
  if (state.gallery.length === 0) {
    // The gallery is a Telegram-only feature — a browser visitor has no durable
    // profile, so their list is always empty. Say why rather than imply a bug.
    const hint = tg.available ? t("gallery.empty") : t("gallery.telegram_only");
    return `<h1>${t("gallery.title")}</h1>
      <div class="card" style="text-align:center;padding:32px 20px">
        <div style="color:var(--muted2);display:grid;place-items:center;margin-bottom:12px">
          ${icon("gallery", 40, 1.4)}</div>
        <p class="mut" style="margin:0">${hint}</p>
      </div>`;
  }
  return `<h1>${t("gallery.title")}</h1>
    <div class="galgrid">${state.gallery.map(card).join("")}</div>`;
}

/** Full-screen before/after of the tapped render, with follow-on actions. */
export function overlay() {
  const item = state.galleryView;
  if (!item) return "";

  const delOn = state.galleryConfirmDelete;
  const del = `<button class="ract" data-act="${delOn ? "doDelete" : "confirmDelete"}"
    style="${delOn ? "color:var(--red)" : ""}">${icon("trash", 16)}<span>${
    delOn ? t("gallery.confirm_delete") : t("gallery.delete")
  }</span></button>`;

  const save = `<button class="ract${state.gallerySaved ? " done" : ""}" data-act="saveImage">
    ${icon("save", 16)}<span>${state.gallerySaved ? t("result.saved") : t("result.save")}</span></button>`;

  const share = tg.canShare
    ? `<button class="ract${state.galleryShared ? " done" : ""}" data-act="shareImage"
        ${state.gallerySharing ? "disabled" : ""}>${icon("share", 16)}<span>${
        state.gallerySharing ? t("result.sharing") : state.galleryShared ? t("result.shared") : t("result.share")
      }</span></button>`
    : "";

  return `
    <div class="zoom">
      <button class="iconbtn zoom-close" data-act="closeItem">${icon("close", 22)}</button>
      <div class="zoom-inner">
        <div style="text-align:center">
          <div style="font-weight:650;font-size:15px">${esc(item.product_name)}</div>
          <div class="mut2" style="font-size:12.5px">${esc(item.car_label || item.category_label)}</div>
        </div>
        ${ba({
          key: "gallerySlider",
          value: state.gallerySlider,
          height: 360,
          before: item.before_url,
          after: item.after_url,
          beforeCap: t("result.cap_before"),
          afterCap: t("result.cap_after"),
        })}
        <div class="gal-actions">
          <button class="cta" data-act="addFromGallery" ${state.galleryAdding ? "disabled" : ""}>
            ${state.galleryAdding ? t("gallery.adding") : t("result.add_to_cart")}</button>
          <div class="racts">${save}${share}${del}</div>
        </div>
        ${
          state.galleryActionError
            ? `<div class="note" style="color:var(--red)">${esc(state.galleryActionError)}</div>`
            : ""
        }
      </div>
    </div>`;
}

export const bar = () => {
  if (state.gallery && state.gallery.length === 0 && !state.galleryError) {
    return `<button class="cta" data-act="toPick">${t("gallery.empty_cta")}</button>`;
  }
  return "";
};

export const actions = {
  openItem: (_ev, el) => {
    const item = (state.gallery || []).find((g) => String(g.id) === el.dataset.id);
    if (item)
      setState({
        galleryView: item, gallerySlider: 50, galleryConfirmDelete: false,
        galleryAdding: false, galleryActionError: "", gallerySaved: false,
        gallerySharing: false, galleryShared: false,
      });
  },
  closeItem: () => setState({ galleryView: null, galleryConfirmDelete: false }),
  confirmDelete: () => setState({ galleryConfirmDelete: true }),
  toPick: () => nav("home"),

  // Turn a saved render into a cart line. The original options and price were
  // never persisted, so this rebuilds from the product's defaults and re-quotes.
  addFromGallery: async () => {
    const item = state.galleryView;
    if (!item || state.galleryAdding) return;
    const found = findProduct(item.product_id);
    if (!found) {
      setState({ galleryActionError: t("gallery.unavailable") });
      return;
    }
    const { cat, product } = found;
    setState({ galleryAdding: true, galleryActionError: "" });

    const selections = defaultSelections(cat, product);
    let services = [];
    try {
      services = await api.services(cat.id);
    } catch {
      services = [];
    }
    const serviceIds = services.filter((s) => s.default_on).map((s) => s.id);

    let breakdown;
    try {
      breakdown = await api.quote(
        product.id,
        Object.entries(selections).map(([group_id, choice_id]) => ({ group_id, choice_id })),
        serviceIds
      );
    } catch (e) {
      setState({ galleryAdding: false, galleryActionError: e.message });
      return;
    }

    const chips = cat.option_groups
      .map((g) => {
        const cid = selections[g.id];
        if (!cid || cid === "off") return null;
        const choice = g.choices.find((c) => c.id === cid);
        return choice ? (g.type === "toggle" ? g.label : choice.label) : null;
      })
      .filter(Boolean);
    const serviceLines = services
      .filter((s) => serviceIds.includes(s.id))
      .map((s) => (s.price ? `${s.name} · ${fmt(s.price)}` : s.name));

    const cartItem = {
      uid: `${product.id}-${state.cart.length}-${Date.now()}`,
      productId: product.id,
      categoryLabel: cat.label,
      name: product.name,
      time: product.time,
      total: breakdown.total,
      selections: { ...selections },
      serviceIds,
      serviceLines,
      chips,
      image: item.after_url,
    };
    setState({
      cart: [...state.cart, cartItem],
      cartReturn: "home",
      carLabel: item.car_label || state.carLabel,
      galleryView: null,
      galleryAdding: false,
    });
    nav("cart");
  },

  saveImage: async () => {
    const url = state.galleryView?.after_url;
    if (!url) return;
    const absolute = new URL(url, location.origin).href;
    const fileName = `mycar-${state.galleryView.product_id || "result"}.jpg`;
    const accepted = tg.canDownload
      ? await tg.downloadFile({ url: absolute, file_name: fileName })
      : anchorDownload(absolute, fileName);
    if (accepted) setState({ gallerySaved: true, galleryActionError: "" });
  },

  shareImage: async () => {
    const item = state.galleryView;
    if (!item || state.gallerySharing || !item.job_id) return;
    const granted = await tg.requestWriteAccess();
    if (!granted) {
      setState({ galleryActionError: t("result.share_denied") });
      return;
    }
    setState({ gallerySharing: true, galleryActionError: "" });
    try {
      await api.shareResult(item.job_id, item.product_id, item.car_label);
      setState({ galleryShared: true, gallerySharing: false, galleryActionError: "" });
    } catch (e) {
      setState({ gallerySharing: false, galleryActionError: e.message });
    }
  },

  doDelete: async () => {
    const item = state.galleryView;
    if (!item) return;
    try {
      await api.deleteGalleryItem(item.id);
    } catch {
      // A failed delete leaves the render in place; closing is the safe outcome.
    }
    setState({
      gallery: (state.gallery || []).filter((g) => g.id !== item.id),
      galleryView: null,
      galleryConfirmDelete: false,
    });
  },
};

export async function onEnter() {
  setState({ gallery: null, galleryError: "", galleryView: null });
  try {
    const items = await api.gallery();
    setState({ gallery: items });
  } catch (e) {
    setState({ gallery: [], galleryError: t("gallery.load_error") });
  }
}
