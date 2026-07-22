import { track } from "../analytics.js";
import { t } from "../i18n.js";
import { nav, setState, state } from "../state.js";
import { categoryCard } from "../ui.js";

export function body() {
  const cards = (state.catalog?.categories || []).map(categoryCard).join("");
  return `
    <h2>${t("pick.title")}</h2>
    <p>${t("pick.lede")}</p>
    <div class="grid2">${cards}</div>
    <div class="note">${t("pick.note")}</div>`;
}

export const actions = {
  pickCategory: (_ev, el) => {
    const id = el.dataset.id;
    // Switching category invalidates the photo and any product configuration.
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
};
