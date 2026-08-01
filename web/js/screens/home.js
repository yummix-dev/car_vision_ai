import { getLang, setLang, t } from "../i18n.js";
import { nav, state } from "../state.js";
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

  const lang = getLang() || "ru";

  return `
    <div class="htop">
      <div class="htop-l">
        <button class="hchip" data-act="openShowcase">${icon("grid", 15)}${t("home.showcase")}</button>
        <button class="hchip" data-act="openGallery">${icon("bookmark", 15)}${t("home.gallery")}</button>
      </div>
      <div class="langseg">
        <button data-act="setLangRu" class="${lang === "ru" ? "on" : ""}">RU</button>
        <button data-act="setLangUz" class="${lang === "uz" ? "on" : ""}">UZ</button>
      </div>
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

function switchTo(lang) {
  if ((getLang() || "ru") === lang) return;
  setLang(lang);
  // Refetch the catalog in the new language and re-render home, the same path
  // the first-open language screen uses.
  window.dispatchEvent(new CustomEvent("lang-changed", { detail: { dest: "home" } }));
}

export const actions = {
  toPick: () => nav("pick"),
  toExample: () => nav("example"),
  openGallery: () => nav("gallery"),
  openShowcase: () => nav("showcase"),
  setLangRu: () => switchTo("ru"),
  setLangUz: () => switchTo("uz"),
};
