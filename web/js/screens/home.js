import { track } from "../analytics.js";
import { getLang, setLang, t } from "../i18n.js";
import { nav, setState, state } from "../state.js";
import { icon } from "../icons.js";
import { zoneCard } from "../ui.js";

export const title = () => "MyCar Vision AI";

export function body() {
  const cats = state.catalog?.categories || [];
  // The design gives the odd-one-out card the full width so the grid never ends
  // on a lone half-row.
  const cards = cats
    .map((c, i) => zoneCard(c, cats.length % 2 === 1 && i === cats.length - 1))
    .join("");

  const lang = getLang() || "ru";

  return `
    <div style="display:flex;justify-content:flex-end;margin-bottom:10px">
      <div class="langseg">
        <button data-act="setLangRu" class="${lang === "ru" ? "on" : ""}">RU</button>
        <button data-act="setLangUz" class="${lang === "uz" ? "on" : ""}">UZ</button>
      </div>
    </div>
    <h1>${t("home.title")}</h1>
    <p>${t("home.lede")}</p>
    <div class="zonegrid">${cards}</div>
    <div class="softrow" style="margin-top:14px">
      <button class="softbtn" data-act="openShowcase">${icon("grid", 15)}${t("home.showcase")}</button>
      <button class="softbtn" data-act="openGallery">${icon("bookmark", 15)}${t("home.gallery")}</button>
    </div>`;
}

function switchTo(lang) {
  if ((getLang() || "ru") === lang) return;
  setLang(lang);
  window.dispatchEvent(new CustomEvent("lang-changed", { detail: { dest: "home" } }));
}

export const actions = {
  // Picking a zone starts a fresh try-on: the previous photo and product
  // configuration no longer apply.
  pickZone: (_ev, el) => {
    const id = el.dataset.id;
    setState({
      category: id,
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
    track("category_picked", { category_id: id });
    nav("upload");
  },
  openGallery: () => nav("gallery"),
  openShowcase: () => nav("showcase"),
  setLangRu: () => switchTo("ru"),
  setLangUz: () => switchTo("uz"),
};
