import { track } from "../analytics.js";
import { api } from "../api.js";
import { t } from "../i18n.js";
import { nav, setState, state } from "../state.js";
import { esc } from "../ui.js";

export function body() {
  if (state.analyzing) {
    return `
      <div style="display:grid;place-items:center;gap:16px;padding:70px 0">
        <div class="spinner"></div>
        <h2 style="text-align:center;margin:0">${t("car.analyzing_title")}</h2>
        <div class="mut" style="text-align:center;font-size:13.5px">${t("car.analyzing_sub")}</div>
      </div>`;
  }

  if (state.carEditing) {
    const opts = state.catalog?.car_options || { brands: [], models: [], years: [] };
    const row = (label, list, key) => `
      <div style="padding:11px 0;border-top:1px solid var(--line)">
        <div class="micro" style="margin-bottom:9px">${label}</div>
        <div class="chips">${list
          .map(
            (v) => `<button class="chip ${String(state[key]) === String(v) ? "on" : ""}"
              data-act="setCar" data-key="${key}" data-v="${esc(v)}">${esc(v)}</button>`
          )
          .join("")}</div>
      </div>`;
    return `
      <h2>${t("car.confirm_title")}</h2>
      <p>${t("car.confirm_sub")}</p>
      <div class="card" style="padding:2px 14px 12px">
        ${row(t("car.brand"), opts.brands, "brand")}
        ${row(t("car.model"), opts.models, "model")}
        ${row(t("car.year"), opts.years, "year")}
      </div>`;
  }

  return `
    <h2>${t("car.likely")}</h2>
    <div style="height:200px;border-radius:var(--r-lg);overflow:hidden;margin-bottom:14px;
      background:#131922 center/cover url('${esc(state.photoUrl || "")}')"></div>
    <div class="card">
      <h3 style="font-size:22px">${esc(state.carLabel)}</h3>
      <div style="margin-top:10px"><span class="pill in">${t("car.compatible_found")}</span></div>
    </div>
    <div class="note">${t("car.wrong_hint")}</div>`;
}

export function bar() {
  if (state.analyzing) return "";
  if (state.carEditing)
    return `<button class="cta" data-act="confirmCar">${t("car.confirm")}</button>`;
  return `
    <button class="cta" data-act="acceptCar">${t("car.accept")}</button>
    <button class="cta sec" data-act="editCar">${t("car.edit")}</button>`;
}

export const actions = {
  editCar: () => setState({ carEditing: true }),

  setCar: (_ev, el) => {
    const { key, v } = el.dataset;
    setState({ [key]: key === "year" ? Number(v) : v });
  },

  confirmCar: async () => {
    // The manual correction path never calls the model — it is the recovery
    // route for when recognition gets it wrong. Tracked separately from
    // acceptance: a high correction rate means recognition is the weak link.
    track("vehicle_corrected");
    try {
      const res = await api.correct(state.brand, state.model, state.year);
      setState({ carLabel: res.label, carEditing: false });
    } catch {
      setState({ carEditing: false });
    }
  },

  acceptCar: () => {
    track("vehicle_confirmed");
    // Fire-and-forget: recording the car must not delay the funnel, and a
    // failure only costs a referral bonus, never the customer's progress.
    api.confirmCar(state.brand, state.model, state.year).catch(() => {});
    nav("catalog");
  },
};

/** Runs when the screen becomes active. */
export async function onEnter() {
  if (!state.analyzing || !state.photoId) return;
  try {
    const res = await api.recognize(state.photoId);
    setState({
      brand: res.make,
      model: res.model,
      year: res.year,
      carLabel: res.label,
      analyzing: false,
    });
  } catch {
    // Recognition failed — drop straight into manual correction rather than
    // dead-ending the funnel.
    setState({ analyzing: false, carEditing: true });
  }
}
