import { t } from "../i18n.js";
import { nav, setState, state } from "../state.js";
import { ba } from "../ui.js";
import { icon } from "../icons.js";

export function body() {
  const rows = ["home.adv1", "home.adv2", "home.adv3"]
    .map(
      (key) => `<div class="row" style="padding:8px 0">
      <span style="color:var(--green);display:grid;place-items:center">${icon("check", 17, 2.4)}</span>
      <span style="font-size:14px">${t(key)}</span></div>`
    )
    .join("");

  return `
    <div class="row" style="justify-content:space-between;margin-bottom:2px;gap:6px">
      <div class="row" style="gap:6px">
        <button class="btn" style="font-size:12.5px;padding:5px 11px" data-act="openShowcase">
          ${icon("gallery", 14)} ${t("home.showcase")}</button>
        <button class="btn" style="font-size:12.5px;padding:5px 11px" data-act="openGallery">
          ${t("home.gallery")}</button>
      </div>
      <button class="btn" style="font-size:12.5px;padding:5px 11px" data-act="switchLang">
        ${icon("globe", 14)} ${t("home.lang_switch")}</button>
    </div>
    <h1>${t("home.title")}</h1>
    <p>${t("home.lede")}</p>
    ${ba({
      key: "homeSlider",
      value: state.homeSlider,
      height: 224,
      before: "/img/example/before.jpg",
      after: "/img/example/after.jpg",
      beforeCap: t("home.cap_before"),
      afterCap: t("home.cap_after"),
    })}
    <div class="mono" style="text-align:center;margin:9px 0 4px">${t("home.slider_hint")}</div>
    <div class="card">${rows}</div>`;
}

export const bar = () => `
  <button class="cta" data-act="toPick">${t("home.cta_pick")}</button>
  <button class="cta sec" data-act="toExample">${t("home.cta_example")}</button>`;

export const actions = {
  toPick: () => nav("pick"),
  toExample: () => nav("example"),
  openGallery: () => nav("gallery"),
  openShowcase: () => nav("showcase"),
  // Reopen the language screen; it returns here after a choice.
  switchLang: () => setState({ langReturn: "home", screen: "lang" }),
};
