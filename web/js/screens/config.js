import { track } from "../analytics.js";
import { api } from "../api.js";
import { t } from "../i18n.js";
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
import { tg } from "../tg.js";
import { esc, genericPreview, optionGroup, priceBlock, wheelPreview } from "../ui.js";
import { fmt } from "../money.js";

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

/** Load the category's paid services and pre-select the default ones. */
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

/** The services section — a toggle per paid service, priced. */
function serviceSection() {
  const services = state.services || [];
  if (!services.length) return "";
  const rows = services
    .map((s) => {
      const on = (state.selectedServices || []).includes(s.id);
      return `<div class="optrow">
        <div>
          <div style="font-size:14px">${esc(s.name)}</div>
          ${s.price ? `<div class="mut2" style="font-size:12px">+${fmt(s.price)} ${t("ui.currency")}</div>`
                    : `<div class="mut2" style="font-size:12px">${t("config.free")}</div>`}
        </div>
        <button class="sw-track ${on ? "on" : ""}" data-act="toggleService"
          data-id="${s.id}"><b></b></button>
      </div>`;
    })
    .join("");
  return `<div class="card" style="padding:2px 14px 12px;margin-top:12px">
    <div class="micro" style="margin:11px 0 4px">${t("config.services")}</div>${rows}</div>`;
}

export function body() {
  const cat = currentCategory();
  const product = currentProduct();
  if (!cat || !product) return `<p>${t("config.no_product")}</p>`;

  // A real photo of the part beats the CSS mock-up of one; the wheel preview
  // stays as the fallback for products the shop has not photographed yet.
  const preview = product.photo
    ? `<div style="height:200px;background:center/cover url('/img/products/${esc(product.photo)}')"></div>`
    : cat.is_wheel
      ? wheelPreview(cat, state.selections)
      : genericPreview(product.name);

  const groups = cat.option_groups
    .map((g) => optionGroup(g, state.selections))
    .join("");
  // Ready-made products (wheels) have no options — skip the empty card entirely
  // rather than showing a blank bar where the configurator used to be.
  const optionsCard = groups
    ? `<div class="card" style="padding:2px 14px 12px">${groups}</div>`
    : "";

  return `
    <div class="card" style="padding:0;overflow:hidden">${preview}</div>
    <h2 style="margin-top:14px">${esc(product.name)}</h2>
    <div class="mut2" style="font-size:12.5px;margin-bottom:12px">
      ${esc(product.material || "")} · ${t("config.for")} ${esc(carLabelShort())}
    </div>
    ${optionsCard}
    ${serviceSection()}
    <div class="card">${priceBlock(state.breakdown)}</div>
    ${balanceChip(cat.label)}
    ${invitedNote()}`;
}

export const bar = () => `
  <button class="cta" data-act="generate">${t("config.cta_generate")}${buttonSuffix()}</button>
  <button class="cta sec" data-act="another">${t("config.cta_another")}</button>`;

export const overlay = () =>
  balanceSheet() + exhaustedSheet() + bonusConfirmSheet() + codeSheet();

export function onEnter() {
  const cat = currentCategory();
  refreshBalance(cat?.id);
  loadServices(cat?.id);
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

  toggleService: (_ev, el) => {
    const id = Number(el.dataset.id);
    const current = state.selectedServices || [];
    const next = current.includes(id)
      ? current.filter((x) => x !== id)
      : [...current, id];
    setState({ selectedServices: next });
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

  submitCode: () => activateCode((state.codeInput || "").trim()),

  scanCode: async () => {
    const scanned = await tg.scanQr(t("quota.scan_hint"));
    if (!scanned) return;
    // The QR may hold the bare code or a URL ending in it; take the last chunk.
    const code = scanned.trim().split(/[/?=\s]/).filter(Boolean).pop() || "";
    setState({ codeInput: code.toUpperCase() });
    activateCode(code);
  },
  cancelBonus: () => setState({ bonusConfirmOpen: false }),
  confirmBonus: () => {
    setState({ bonusConfirmOpen: false });
    startGeneration();
  },
};

async function activateCode(code) {
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
}

function startGeneration() {
  setState({
    jobId: null, job: null, saved: false, shared: false, sharing: false,
    resultError: "", zoomOpen: false, resultSlider: 50, zoomSlider: 50,
    // A normal generation is not a compare run — clear any stale compare state.
    comparing: false, compareBase: null,
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
