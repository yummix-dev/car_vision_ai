import { api } from "../api.js";
import { t } from "../i18n.js";
import { icon } from "../icons.js";
import { cartTotal, nav, setQuiet, setState, state } from "../state.js";
import { tg } from "../tg.js";
import { esc } from "../ui.js";
import { fmt } from "../money.js";

// The optional details, revealed by the disclosure — everything but the phone.
const EXTRA_FIELDS = [
  ["name", "request.f_name", "text", "request.f_name_ph"],
  ["date", "request.f_date", "text", "request.f_date_ph"],
];

export const title = () => t("request.hdr");

function summaryLine() {
  const names = state.cart.map((i) => i.name);
  if (!names.length) return "";
  if (names.length === 1) return names[0];
  return t("request.plus_more", { first: names[0], n: names.length - 1 });
}

export function body() {
  const tgNote = tg.user
    ? `<div class="note accent">${icon("send", 16)}${esc(
        [tg.user.fullName, tg.user.username ? `@${tg.user.username}` : ""]
          .filter(Boolean)
          .join(", ")
      )} — ${t("request.from_tg")}</div>`
    : `<div class="note">${t("request.prefill_hint")}</div>`;

  const extra = state.reqExtra
    ? EXTRA_FIELDS.map(
        ([key, labelKey, type, ph]) => `
        <div class="field" style="margin-top:12px">
          <label class="micro">${t(labelKey)}</label>
          <input type="${type}" data-field="${key}" placeholder="${esc(t(ph))}" value="${esc(state.form[key])}">
        </div>`
      ).join("") +
      `<div class="field">
        <label class="micro">${t("request.f_comment")}</label>
        <textarea data-field="comment" placeholder="${t("request.f_comment_ph")}">${esc(state.form.comment)}</textarea>
      </div>`
    : "";

  return `
    <h2>${t("request.title")}</h2>
    <p>${t("request.lede")}</p>

    <div class="micro" style="margin-bottom:9px">${t("request.f_phone")}</div>
    <div class="field hero">
      <input type="tel" data-field="phone" placeholder="+998 __ ___ __ __" value="${esc(state.form.phone)}">
    </div>
    ${tgNote}

    <div class="card" style="margin-top:16px">
      <div class="row" style="align-items:center;gap:11px;margin-bottom:12px">
        ${
          state.cart[0]?.image
            ? `<div style="width:44px;height:44px;flex:none;border-radius:10px;overflow:hidden;background:center/cover url('${esc(state.cart[0].image)}')"></div>`
            : ""
        }
        <div style="flex:1;min-width:0">
          <div style="font-size:13.5px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${esc(summaryLine())}</div>
          <div style="font-size:12px;color:var(--muted);margin-top:2px">${esc(state.carLabel)}</div>
        </div>
      </div>
      <div class="row" style="justify-content:space-between;font-size:13px;padding:6px 0;color:var(--muted);border-top:1px solid var(--line)">
        <span>${t("cart.work")}</span><span style="color:var(--accent);font-family:var(--disp);font-weight:600">${t("cart.work_incl")}</span></div>
      <div class="row" style="justify-content:space-between;align-items:baseline;padding-top:9px;border-top:1px solid var(--line);margin-top:5px">
        <span class="micro">${t("request.total")}</span>
        <span class="num" style="font-size:23px">${fmt(cartTotal())}</span></div>
    </div>

    <button class="disclosure ${state.reqExtra ? "open" : ""}" data-act="toggleExtra">
      ${t("request.add_details")} ${icon("next", 15)}</button>
    ${extra}
    ${state.formError ? `<div class="note" style="color:var(--red)">${esc(state.formError)}</div>` : ""}`;
}

export const bar = () => `
  <button class="cta" data-act="submit">${t("request.submit")}</button>
  <div style="text-align:center;color:var(--muted);font-size:12px">${t("request.no_pay")}</div>`;

export const actions = {
  toggleExtra: () => setState({ reqExtra: !state.reqExtra }),

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
