import { api } from "../api.js";
import { t } from "../i18n.js";
import { icon } from "../icons.js";
import { nav, setState, state } from "../state.js";
import { ba, esc } from "../ui.js";

/** created_at (unix seconds) → "DD.MM.YYYY". */
function fmtDate(sec) {
  const d = new Date((sec || 0) * 1000);
  const pad = (n) => String(n).padStart(2, "0");
  return `${pad(d.getDate())}.${pad(d.getMonth() + 1)}.${d.getFullYear()}`;
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
    return `<h1>${t("gallery.title")}</h1>
      <div class="card" style="text-align:center;padding:32px 20px">
        <div style="color:var(--muted2);display:grid;place-items:center;margin-bottom:12px">
          ${icon("gallery", 40, 1.4)}</div>
        <p class="mut" style="margin:0">${t("gallery.empty")}</p>
      </div>`;
  }
  return `<h1>${t("gallery.title")}</h1>
    <div class="galgrid">${state.gallery.map(card).join("")}</div>`;
}

/** Full-screen before/after of the tapped render, with delete. */
export function overlay() {
  const item = state.galleryView;
  if (!item) return "";
  const del = state.galleryConfirmDelete
    ? `<button class="btn" data-act="doDelete"
         style="color:var(--red);border-color:rgba(239,68,68,.4)">
         ${icon("trash", 16)} ${t("gallery.confirm_delete")}</button>`
    : `<button class="btn" data-act="confirmDelete">
         ${icon("trash", 16)} ${t("gallery.delete")}</button>`;
  return `
    <div class="zoom">
      <button class="iconbtn zoom-close" data-act="closeItem">${icon("close", 22)}</button>
      <div class="zoom-inner" style="gap:14px">
        <div style="text-align:center">
          <div style="font-weight:650;font-size:15px">${esc(item.product_name)}</div>
          <div class="mut2" style="font-size:12.5px">${esc(item.car_label || item.category_label)}</div>
        </div>
        ${ba({
          key: "gallerySlider",
          value: state.gallerySlider,
          height: 420,
          before: item.before_url,
          after: item.after_url,
          beforeCap: t("result.cap_before"),
          afterCap: t("result.cap_after"),
        })}
        <div style="width:100%;max-width:360px">${del}</div>
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
    if (item) setState({ galleryView: item, gallerySlider: 50, galleryConfirmDelete: false });
  },
  closeItem: () => setState({ galleryView: null, galleryConfirmDelete: false }),
  confirmDelete: () => setState({ galleryConfirmDelete: true }),
  toPick: () => nav("pick"),

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
