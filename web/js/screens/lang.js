import { setLang } from "../i18n.js";
import { nav, setState, state } from "../state.js";

// First-open language choice, and reachable again from home to switch. The
// screen is inherently bilingual — a not-yet-chosen visitor may read either
// language — so its title, like the buttons, is shown in both scripts rather
// than through t().
export function body() {
  return `
    <div style="display:grid;place-items:center;gap:6px;padding:52px 0 26px;text-align:center">
      <h1 style="margin:0">Tilni tanlang</h1>
      <h1 style="margin:0;opacity:.7;font-weight:600">Выберите язык</h1>
    </div>`;
}

export const bar = () => `
  <button class="cta" data-act="chooseUz">Oʻzbekcha</button>
  <button class="cta sec" data-act="chooseRu">Русский</button>`;

function choose(lang) {
  setLang(lang);
  // Refetch the catalog so its labels come back in the chosen language, then
  // continue into the funnel (or back home if the user was just switching).
  const dest = state.langReturn || "flow";
  setState({ lang, langReturn: null });
  window.dispatchEvent(new CustomEvent("lang-changed", { detail: { dest } }));
}

export const actions = {
  chooseUz: () => choose("uz"),
  chooseRu: () => choose("ru"),
};
