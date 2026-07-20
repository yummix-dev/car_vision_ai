import { track } from "../analytics.js";
import { nav, setState, state } from "../state.js";
import { categoryCard } from "../ui.js";

export function body() {
  const cards = (state.catalog?.categories || []).map(categoryCard).join("");
  return `
    <h2>Что примеряем?</h2>
    <p>Выберите зону автомобиля — для каждой нужна своя фотография.</p>
    <div class="grid2">${cards}</div>
    <div class="note">Один раздел за раз. После примерки можно вернуться и добавить ещё товар в сборку.</div>`;
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
