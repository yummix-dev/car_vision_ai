import { track } from "../analytics.js";
import { api } from "../api.js";
import { t } from "../i18n.js";
import { icon } from "../icons.js";
import { currentCategory, nav, setState, state } from "../state.js";
import { esc } from "../ui.js";

export const title = () => currentCategory()?.noun_cap || currentCategory()?.label || "";

// The three vehicle fields the customer sets by hand. `list` names the array in
// the catalog's car_options; `state` names the field they write.
const FIELDS = [
  { key: "brand", labelKey: "car.brand", list: "brands", wide: false },
  { key: "model", labelKey: "car.model", list: "models", wide: false },
  { key: "year", labelKey: "car.f_year", list: "years", wide: true },
];

const carOptions = () =>
  state.catalog?.car_options || { brands: [], models: [], years: [] };

function fieldCard(f) {
  const open = state.carField === f.key;
  return `
    <button class="carfield${open ? " on" : ""}${f.wide ? " wide" : ""}"
      data-act="openField" data-key="${f.key}">
      <span class="cf-lbl">${t(f.labelKey)}</span>
      <span class="cf-val">${esc(state[f.key])}</span>
    </button>`;
}

function picker() {
  const f = FIELDS.find((x) => x.key === state.carField);
  if (!f) return "";
  const list = carOptions()[f.list] || [];
  const chips = list
    .map(
      (v) => `<button class="chip ${String(state[f.key]) === String(v) ? "on" : ""}"
        data-act="setCar" data-key="${f.key}" data-v="${esc(v)}">${esc(v)}</button>`
    )
    .join("");
  return `<div class="card" style="margin-top:8px">
    <div class="micro" style="margin-bottom:10px">${t(f.labelKey)}</div>
    <div class="chips">${chips}</div>
  </div>`;
}

export function body() {
  const cat = currentCategory();

  return `
    <h2>${t("car.photo_title")}</h2>
    <div style="position:relative;height:190px;border-radius:var(--r-lg);overflow:hidden;
      background:#22252a center/cover url('${esc(state.photoUrl || "")}')">
      <span style="position:absolute;top:10px;left:10px;display:inline-flex;align-items:center;gap:7px;
        font-family:var(--disp);font-size:11.5px;letter-spacing:.6px;text-transform:uppercase;border-radius:20px;
        padding:5px 11px;background:rgba(16,17,19,.7);color:var(--accent)">
        <span style="width:6px;height:6px;border-radius:50%;background:currentColor"></span>${esc(cat?.noun_cap || "")} ${t("upload.in_frame")}</span>
      <button class="iconbtn" data-act="replace"
        style="position:absolute;bottom:8px;right:8px;min-height:44px;background:rgba(16,17,19,.75);color:var(--txt);
        border-radius:12px;padding:0 14px;font-size:13px;font-weight:500;display:inline-flex;align-items:center;gap:7px;font-family:var(--body)">
        ${icon("refresh", 15)}${t("upload.replace")}</button>
    </div>

    <div class="micro" style="margin:16px 0 9px">${t("car.your_car")}</div>
    <div class="carfields">
      ${FIELDS.map(fieldCard).join("")}
    </div>
    ${picker()}
    <div class="note accent">${t("car.match_hint", { plural: esc(cat?.title || cat?.label || "") })}</div>`;
}

export const bar = () =>
  `<button class="cta" data-act="acceptCar">${t("car.show", { plural: esc(currentCategory()?.title || "") })}</button>`;

export const actions = {
  // Re-pick the photo: back to the source screen.
  replace: () => {
    setState({ carField: null, photoId: null, photoUrl: null, photoSource: "" });
    nav("upload");
  },

  // Tapping a field opens (or closes) its chip picker; only one is open at a time.
  openField: (_ev, el) => {
    const key = el.dataset.key;
    setState({ carField: state.carField === key ? null : key });
  },

  setCar: (_ev, el) => {
    const { key, v } = el.dataset;
    setState({ [key]: key === "year" ? Number(v) : v, carField: null });
  },

  acceptCar: async () => {
    track("vehicle_confirmed");
    // The car is entirely user-chosen now — canonicalise the label on the server
    // (also records the vehicle), falling back to a local label if it is offline.
    try {
      const res = await api.correct(state.brand, state.model, state.year);
      setState({ carLabel: res.label });
    } catch {
      setState({ carLabel: `${state.brand} ${state.model} ${state.year}` });
    }
    api.confirmCar(state.brand, state.model, state.year).catch(() => {});
    nav("catalog");
  },
};
