import { api } from "../api.js";
import { t } from "../i18n.js";
import { icon } from "../icons.js";
import { nav, setState, state } from "../state.js";
import { ba, esc } from "../ui.js";

export const title = () => t("showcase.title");

// Public feed of the shop's real installs — social proof. Read-only; builds are
// curated in /admin. Each card can jump into the funnel for its zone.
function card(b) {
  const meta = [b.car_label, b.category_label].filter(Boolean).join(" · ");
  const tryBtn = b.category_id
    ? `<button class="btn" style="width:100%;margin-top:10px"
         data-act="tryBuild" data-cat="${esc(b.category_id)}">
         ${icon("camera", 15)} ${t("showcase.try")}</button>`
    : "";
  return `<div class="card" style="margin-bottom:12px">
    ${ba({
      key: `sc${b.id}`,
      value: 50,
      height: 220,
      before: b.before_url,
      after: b.after_url,
      beforeCap: t("result.cap_before"),
      afterCap: t("result.cap_after"),
    })}
    <div style="margin-top:11px">
      <div style="font-weight:650;font-size:14.5px">${esc(b.title)}</div>
      <div class="mut2" style="font-size:12px;margin-top:2px">${esc(meta)}</div>
    </div>
    ${tryBtn}
  </div>`;
}

export function body() {
  if (state.showcase === null) {
    return `<div style="display:grid;place-items:center;padding:64px 0"><div class="spinner"></div></div>`;
  }
  if (state.showcaseError) {
    return `<h1>${t("showcase.title")}</h1>
      <div class="note" style="color:var(--red)">${esc(state.showcaseError)}</div>`;
  }
  if (state.showcase.length === 0) {
    return `<h1>${t("showcase.title")}</h1>
      <div class="card" style="text-align:center;padding:32px 20px">
        <div style="color:var(--muted2);display:grid;place-items:center;margin-bottom:12px">
          ${icon("gallery", 40, 1.4)}</div>
        <p class="mut" style="margin:0">${t("showcase.empty")}</p>
      </div>`;
  }

  const all = state.showcase;
  const models = [...new Set(all.map((b) => b.car_model).filter(Boolean))];
  const filter = state.showcaseFilter || "";
  const shown = filter ? all.filter((b) => b.car_model === filter) : all;

  const chips = [["", t("showcase.all")], ...models.map((m) => [m, m])]
    .map(
      ([id, label]) => `<button class="chip ${filter === id ? "on" : ""}"
        data-act="scFilter" data-id="${esc(id)}">${esc(label)}</button>`
    )
    .join("");

  return `
    <h1>${t("showcase.title")}</h1>
    <p>${t("showcase.lede")}</p>
    ${models.length > 1 ? `<div class="filters scrollx">${chips}</div>` : ""}
    ${shown.map(card).join("")}`;
}

export const actions = {
  scFilter: (_ev, el) => setState({ showcaseFilter: el.dataset.id }),

  // "Примерить как здесь" — start the funnel for this build's zone.
  tryBuild: (_ev, el) => {
    setState({
      category: el.dataset.cat,
      filter: "pop",
      photoSource: "",
      photoId: null,
      photoUrl: null,
      uploadError: "",
      productId: null,
      selections: {},
      breakdown: null,
      jobId: null,
      job: null,
    });
    nav("upload");
  },
};

export async function onEnter() {
  setState({ showcase: null, showcaseError: "", showcaseFilter: "" });
  try {
    setState({ showcase: await api.showcase() });
  } catch {
    setState({ showcase: [], showcaseError: t("showcase.load_error") });
  }
}
