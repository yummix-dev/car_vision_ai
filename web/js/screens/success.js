import { t } from "../i18n.js";
import { icon } from "../icons.js";
import { cartTotal, nav, reset, setState, state } from "../state.js";
import { esc } from "../ui.js";
import { fmt } from "../money.js";

export const title = () => "";

export function body() {
  const b = state.booking;

  const lines = state.cart
    .map(
      (i) => `<div class="row" style="justify-content:space-between;font-size:13.5px;padding:6px 0;color:var(--muted)">
        <span>${esc(i.name)}</span>
        <span style="font-family:var(--disp);color:var(--txt);font-weight:600">${fmt(i.total)}</span></div>`
    )
    .join("");

  return `
    <div style="padding-top:6px">
      <div style="width:66px;height:66px;border-radius:50%;background:var(--accent);
        color:var(--accentInk);display:grid;place-items:center;margin-bottom:20px">${icon("check", 32, 2.4)}</div>
      <h2 style="font-size:32px">${t("success.title", { n: b?.booking_id ?? "" })}</h2>
      <p style="font-size:14px">${t("success.sub")}</p>
    </div>
    <div class="card" style="margin-top:6px">
      ${lines}
      <div class="row" style="justify-content:space-between;font-size:13.5px;padding:6px 0;color:var(--muted)">
        <span>${t("cart.work")}</span><span style="color:var(--accent);font-family:var(--disp);font-weight:600">${t("cart.work_incl")}</span></div>
      <div class="row" style="justify-content:space-between;align-items:baseline;padding-top:10px;border-top:1px solid var(--line);margin-top:6px">
        <span class="micro">${t("success.total")}</span>
        <span class="num" style="font-size:25px">${esc(b?.total_formatted || fmt(cartTotal()))} ${t("ui.currency")}</span></div>
    </div>
    <div class="note">${t("success.route_note")}</div>`;
}

export const bar = () => `
  <button class="cta" data-act="again">${t("success.again")}</button>
  <button class="cta sec" data-act="orders">${t("success.orders")}</button>`;

export const actions = {
  // The booking is done. Clear the finished order and start fresh at home.
  again: () => {
    setState({
      cart: [],
      booking: null,
      reqExtra: false,
      form: { name: "", phone: "", telegram: "", date: "", comment: "" },
    });
    reset("home");
  },
  orders: () => {
    setState({
      cart: [],
      booking: null,
      reqExtra: false,
      form: { name: "", phone: "", telegram: "", date: "", comment: "" },
    });
    reset("gallery");
  },
};
