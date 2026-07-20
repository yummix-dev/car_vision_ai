import { track } from "../analytics.js";
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
  ["pop", "Популярные"],
  ["price", "По цене"],
  ["carbon", "Карбон"],
  ["led", "LED"],
  ["paddles", "Лепестки"],
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

export function body() {
  const cat = currentCategory();
  if (!cat) return `<p>Раздел не выбран.</p>`;

  const filters = cat.is_wheel
    ? `<div class="filters scrollx">${FILTERS.map(
        ([id, label]) => `<button class="chip ${state.filter === id ? "on" : ""}"
          data-act="setFilter" data-id="${id}">${label}</button>`
      ).join("")}</div>`
    : "";

  const items = visibleProducts(cat);
  const cards = items.length
    ? items.map((p) => productCard(p)).join("")
    : `<div class="note">В этом фильтре пока нет товаров.</div>`;

  return `
    <div class="row" style="justify-content:space-between;margin-bottom:10px">
      <span class="eyebrow" style="margin:0">${esc(cat.label)}</span>
      <a href="#" data-act="toPick">Сменить раздел</a>
    </div>
    <h2>${esc(cat.title)} ${esc(state.brand)} ${esc(state.model)}</h2>
    <p>${esc(cat.sub)}</p>
    ${filters}
    ${cards}`;
}

export const actions = {
  setFilter: (_ev, el) => setState({ filter: el.dataset.id }),

  toPick: (ev) => {
    ev.preventDefault();
    nav("pick");
  },

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
