import { track } from "../analytics.js";
import { t } from "../i18n.js";
import {
  currentCategory,
  defaultSelections,
  nav,
  setState,
  state,
} from "../state.js";
import { esc, productCard } from "../ui.js";
import { refreshQuote } from "./config.js";

// Filter row only applies to wheels, as in the prototype.
const FILTERS = [
  ["pop", "catalog.filter_pop"],
  ["price", "catalog.filter_price"],
  ["carbon", "catalog.filter_carbon"],
  ["led", "catalog.filter_led"],
  ["paddles", "catalog.filter_paddles"],
];

function visibleProducts(cat) {
  let items = [...cat.products];
  if (!cat.is_wheel) return items;
  switch (state.filter) {
    case "price":
      return items.sort((a, b) => a.base_price - b.base_price);
    case "carbon":
      return items.filter((p) => p.flags?.carbon);
    case "led":
      return items.filter((p) => p.flags?.has_led);
    case "paddles":
      return items.filter((p) => p.flags?.has_paddles);
    default:
      return items.filter((p) => p.popular);
  }
}

export const title = () => currentCategory()?.label || "";

export function body() {
  const cat = currentCategory();
  if (!cat) return `<p>${t("catalog.no_section")}</p>`;

  const filters = cat.is_wheel
    ? `<div class="filters scrollx">${FILTERS.map(
        ([id, key]) => `<button class="chip ${state.filter === id ? "on" : ""}"
          data-act="setFilter" data-id="${id}">${t(key)}</button>`
      ).join("")}</div>`
    : "";

  const items = visibleProducts(cat);
  const cards = items.length
    ? items.map((p) => productCard(p)).join("")
    : `<div class="note">${t("catalog.empty_filter")}</div>`;

  return `
    <h2 style="margin-bottom:4px">${esc(cat.title)}</h2>
    <p style="font-size:13px">${esc(cat.sub)}</p>
    ${filters}
    ${cards}`;
}

export const actions = {
  setFilter: (_ev, el) => setState({ filter: el.dataset.id }),

  openProduct: async (_ev, el) => {
    const cat = currentCategory();
    const product = cat.products.find((p) => p.id === el.dataset.id);
    if (!product) return;
    track("product_opened", { category_id: cat.id, product_id: product.id });
    setState({
      productId: product.id,
      selections: defaultSelections(cat, product),
      breakdown: null,
    });
    nav("config");
    refreshQuote();
  },
};
