import { track } from "../analytics.js";
import { api } from "../api.js";
import { t } from "../i18n.js";
import { icon } from "../icons.js";
import {
  currentCategory,
  currentProduct,
  nav,
  selectionList,
  setState,
  state,
} from "../state.js";
import { esc, genericPreview, optionGroup, stockPill, wheelPreview } from "../ui.js";
import { fmt } from "../money.js";

export const title = () => currentCategory()?.noun_cap || currentCategory()?.label || "";

/** Ask the server for the authoritative price. The client never invents totals. */
export async function refreshQuote() {
  if (!state.productId) return;
  try {
    const breakdown = await api.quote(
      state.productId,
      selectionList(),
      state.selectedServices || []
    );
    setState({ breakdown });
  } catch (e) {
    console.error("quote failed", e);
  }
}

/** Load the category's services and keep the default-on ones. Installation is
 *  folded into the price and shown as an "included" line, not a toggle. */
async function loadServices(categoryId) {
  try {
    const services = await api.services(categoryId);
    setState({
      services,
      selectedServices: services.filter((s) => s.default_on).map((s) => s.id),
    });
  } catch {
    setState({ services: [], selectedServices: [] });
  }
  refreshQuote();
}

export function body() {
  const cat = currentCategory();
  const product = currentProduct();
  if (!cat || !product) return `<p>${t("config.no_product")}</p>`;

  const preview = product.photo
    ? `<div style="height:190px;background:center/cover url('/img/products/${esc(product.photo)}')"></div>`
    : cat.is_wheel
      ? wheelPreview(cat, state.selections)
      : genericPreview(product.name);

  const sub = [product.material, product.time]
    .filter(Boolean)
    .concat(product.stock === "in" ? t("catalog.in_stock").toLowerCase() : t("catalog.on_order").toLowerCase())
    .join(" · ");

  const groups = cat.option_groups
    .map((g) => optionGroup(g, state.selections))
    .join("");
  const optionsCard = groups
    ? `<div class="card" style="padding:2px 14px 12px;margin-top:12px">${groups}</div>`
    : "";

  return `
    <div class="card" style="padding:0;overflow:hidden">${preview}</div>
    <h2 style="margin-top:14px">${esc(product.name)}</h2>
    <div class="mut2" style="font-size:13.5px;margin-bottom:2px">${esc(sub)}</div>
    ${optionsCard}
    <div class="included" style="margin-top:14px">${icon("check", 15, 2.2)}${t("config.install_included")}</div>`;
}

export const bar = () => `
  <div class="barsplit">
    <div class="bartotal">
      <span class="micro">${t("cart.total")}</span>
      <span class="num">${state.breakdown ? esc(state.breakdown.total_formatted) : "—"}</span>
    </div>
    <button class="cta" data-act="generate">${t("config.cta_generate")}</button>
  </div>`;

export function onEnter() {
  loadServices(currentCategory()?.id);
}

export const actions = {
  setOption: (_ev, el) => {
    setState({
      selections: { ...state.selections, [el.dataset.group]: el.dataset.id },
    });
    trackOption(el.dataset.group, el.dataset.id);
    refreshQuote();
  },

  toggleOption: (_ev, el) => {
    const g = el.dataset.group;
    const next = state.selections[g] === "on" ? "off" : "on";
    setState({ selections: { ...state.selections, [g]: next } });
    trackOption(g, next);
    refreshQuote();
  },

  generate: () => startGeneration(),
};

function startGeneration() {
  setState({
    jobId: null, job: null, saved: false, shared: false, sharing: false,
    resultError: "", zoomOpen: false, resultSlider: 50, zoomSlider: 50,
    // One key per attempt: a double tap reuses it and is charged once.
    generationKey: `${state.productId}-${Date.now()}`,
  });
  track("generation_started", {
    category_id: currentCategory()?.id,
    product_id: state.productId,
  });
  nav("generating");
}

/** Which options get tried tells the shop what to stock and what to price. */
function trackOption(group_id, choice_id) {
  track("option_changed", {
    category_id: currentCategory()?.id,
    product_id: state.productId,
    payload: { group_id, choice_id },
  });
}
