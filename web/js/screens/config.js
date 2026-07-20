import { track } from "../analytics.js";
import { api } from "../api.js";
import {
  back,
  carLabelShort,
  currentCategory,
  currentProduct,
  nav,
  selectionList,
  setQuiet,
  setState,
  state,
} from "../state.js";
import {
  balanceChip,
  balanceSheet,
  bonusConfirmSheet,
  buttonSuffix,
  codeSheet,
  exhausted,
  exhaustedSheet,
  invitedNote,
  metered,
  nextCharge,
  refreshBalance,
} from "../quota.js";
import { esc, genericPreview, optionGroup, priceBlock, wheelPreview } from "../ui.js";

/** Ask the server for the authoritative price. The client never invents totals. */
export async function refreshQuote() {
  if (!state.productId) return;
  try {
    const breakdown = await api.quote(state.productId, selectionList());
    setState({ breakdown });
  } catch (e) {
    console.error("quote failed", e);
  }
}

export function body() {
  const cat = currentCategory();
  const product = currentProduct();
  if (!cat || !product) return `<p>Товар не выбран.</p>`;

  const preview = cat.is_wheel
    ? wheelPreview(cat, state.selections)
    : genericPreview(product.name);

  const groups = cat.option_groups
    .map((g) => optionGroup(g, state.selections))
    .join("");

  return `
    <div class="card" style="padding:0;overflow:hidden">${preview}</div>
    <h2 style="margin-top:14px">${esc(product.name)}</h2>
    <div class="mut2" style="font-size:12.5px;margin-bottom:12px">
      ${esc(product.material || "")} · для ${esc(carLabelShort())}
    </div>
    <div class="card" style="padding:2px 14px 12px">${groups}</div>
    <div class="card">${priceBlock(state.breakdown)}</div>
    ${balanceChip(cat.label)}
    ${invitedNote()}`;
}

export const bar = () => `
  <button class="cta" data-act="generate">Примерить на моей машине${buttonSuffix()}</button>
  <button class="cta sec" data-act="another">Выбрать другой товар</button>`;

export const overlay = () =>
  balanceSheet() + exhaustedSheet() + bonusConfirmSheet() + codeSheet();

export function onEnter() {
  refreshBalance(currentCategory()?.id);
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

  another: () => back(),

  generate: () => {
    // Nothing left to spend: explain, do not start a doomed generation.
    if (exhausted()) {
      setState({ exhaustedOpen: true });
      return;
    }
    // Spending a bonus is worth a confirmation — the customer earned those.
    if (metered() && nextCharge() === "bonus") {
      setState({ bonusConfirmOpen: true });
      return;
    }
    startGeneration();
  },

  openBalance: async () => {
    setState({ balanceOpen: true });
    try {
      setState({ balanceHistory: await api.transactions() });
    } catch {
      setState({ balanceHistory: [] });
    }
  },
  closeBalance: () => setState({ balanceOpen: false }),
  closeExhausted: () => setState({ exhaustedOpen: false }),

  openCode: () =>
    setState({ exhaustedOpen: false, balanceOpen: false, codeOpen: true,
               codeInput: "", codeError: "", codeResult: null }),
  closeCode: () => setState({ codeOpen: false, codeResult: null, codeError: "" }),

  submitCode: async () => {
    const code = (state.codeInput || "").trim();
    if (!code || state.codeBusy) return;
    setState({ codeBusy: true, codeError: "" });
    try {
      const result = await api.activateCode(code);
      // The balance moved on the server; re-read rather than guess by how much.
      await refreshBalance(currentCategory()?.id);
      setState({ codeBusy: false, codeResult: result });
    } catch (e) {
      setState({ codeBusy: false, codeError: e.message });
    }
  },
  cancelBonus: () => setState({ bonusConfirmOpen: false }),
  confirmBonus: () => {
    setState({ bonusConfirmOpen: false });
    startGeneration();
  },
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

/** setQuiet so re-rendering never steals focus while the code is being typed. */
export function onInput(el) {
  if (el.dataset.field === "code") {
    setQuiet({ codeInput: el.value.toUpperCase(), codeError: "" });
  }
}

/** Which options get tried tells the shop what to stock and what to price. */
function trackOption(group_id, choice_id) {
  track("option_changed", {
    category_id: currentCategory()?.id,
    product_id: state.productId,
    payload: { group_id, choice_id },
  });
}
