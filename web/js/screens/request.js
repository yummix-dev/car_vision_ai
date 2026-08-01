import { api } from "../api.js";
import { t } from "../i18n.js";
import { icon } from "../icons.js";
import { cartTotal, nav, setQuiet, setState, state } from "../state.js";
import { tg } from "../tg.js";
import { esc } from "../ui.js";
import { fmt } from "../money.js";

const FIELDS = [
  ["name", "request.f_name", "text", "request.f_name_ph"],
  ["phone", "request.f_phone", "tel", "+998 __ ___ __ __"],
  ["telegram", "request.f_tg", "text", "@username"],
  ["date", "request.f_date", "text", "request.f_date_ph"],
];

const PAY_METHODS = [
  ["cash", "wallet", "pay.cash"],
  ["telegram", "card", "pay.telegram"],
  ["uzum", "percent", "pay.uzum"],
];

export function body() {
  const fields = FIELDS.map(
    ([key, labelKey, type, ph]) => `
    <div class="field">
      <label class="micro">${t(labelKey)}</label>
      <input type="${type}" data-field="${key}" placeholder="${esc(ph.startsWith("request.") ? t(ph) : ph)}"
        value="${esc(state.form[key])}">
    </div>`
  ).join("");

  return `
    <h2>${t("request.title")}</h2>
    <p>${t("request.lede")}</p>

    <div class="card" style="margin-bottom:14px">
      <div class="price">
        <div class="pl"><span>${t("request.car")}</span><span>${esc(state.carLabel)}</span></div>
        <div class="pl"><span>${t("request.positions")}</span><span>${state.cart.length}</span></div>
        <div class="total"><span class="micro">${t("request.total")}</span>
          <span class="num">${fmt(cartTotal())} ${t("ui.currency")}</span></div>
      </div>
    </div>

    <label class="micro" style="display:block;margin-bottom:8px">${t("pay.title")}</label>
    <div class="payopts" style="margin-bottom:16px">
      ${PAY_METHODS.map(
        ([id, ic, label]) => `<button class="payopt ${state.paymentMethod === id ? "on" : ""}"
          data-act="setPay" data-id="${id}">${icon(ic, 18)}<span>${t(label)}</span></button>`
      ).join("")}
    </div>

    ${fields}
    <div class="field">
      <label class="micro">${t("request.f_comment")}</label>
      <textarea data-field="comment" placeholder="${t("request.f_comment_ph")}">${esc(state.form.comment)}</textarea>
    </div>
    ${state.formError ? `<div class="note" style="color:var(--red)">${esc(state.formError)}</div>` : ""}
    ${
      tg.user
        ? `<div class="note blue">${t("request.prefill")}</div>`
        : `<div class="note">${t("request.prefill_hint")}</div>`
    }`;
}

export const bar = () =>
  `<button class="cta" data-act="submit">${t("request.submit")}</button>`;

export const actions = {
  setPay: (_ev, el) => setState({ paymentMethod: el.dataset.id }),

  submit: async () => {
    if (!state.form.phone.trim()) {
      setState({ formError: t("request.need_phone") });
      return;
    }
    try {
      const booking = await api.booking({
        cart: state.cart.map((i) => ({
          product_id: i.productId,
          selections: Object.entries(i.selections).map(([group_id, choice_id]) => ({
            group_id,
            choice_id,
          })),
          service_ids: i.serviceIds || [],
        })),
        contact: state.form,
        car_label: state.carLabel,
        payment_method: state.paymentMethod,
      });
      setState({ booking, formError: "" });
      // A live provider (Phase 2) hands back an invoice/redirect to open; today
      // every method returns "manager", so we go straight to the confirmation.
      const action = booking.payment || { kind: "manager" };
      if ((action.kind === "invoice" || action.kind === "redirect") && action.url) {
        window.open(action.url, "_blank"); // Phase 2: tg.openInvoice for invoices
      }
      nav("success");
    } catch (e) {
      setState({ formError: e.message });
    }
  },
};

/** Field edits use setQuiet so re-rendering never steals focus mid-typing. */
export function onInput(el) {
  const key = el.dataset.field;
  if (!key) return;
  setQuiet({ form: { ...state.form, [key]: el.value } });
}
