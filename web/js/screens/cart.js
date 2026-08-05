import { t } from "../i18n.js";
import { icon } from "../icons.js";
import { carLabelShort, cartTotal, nav, setState, state } from "../state.js";
import { esc } from "../ui.js";
import { fmt } from "../money.js";

export const title = () => t("cart.title");

export function body() {
  if (!state.cart.length) {
    return `
      <h2>${t("cart.title")}</h2>
      <div class="note">${t("cart.empty")}</div>
      <button class="cta dashed" style="margin-top:14px" data-act="addMore">${t("cart.add_first")}</button>`;
  }

  const rows = state.cart
    .map(
      (i) => `
    <div class="card" style="display:flex;align-items:center;gap:12px">
      ${
        i.image
          ? `<div class="thumb" style="background-image:url('${esc(i.image)}')"></div>`
          : `<div class="ph sm thumb"><span class="mono" style="font-size:9px">[ ${esc(i.categoryLabel)} ]</span></div>`
      }
      <div style="flex:1;min-width:0">
        <div class="micro" style="font-size:11px">${esc(i.categoryLabel)}</div>
        <div style="font-family:var(--disp);font-size:17px;font-weight:600;line-height:1.15;margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${esc(i.name)}</div>
        <div style="font-family:var(--disp);font-size:17px;font-weight:700;color:var(--accent);margin-top:3px">${fmt(i.total)}</div>
      </div>
      <button class="iconbtn mut2" data-act="removeItem" data-uid="${esc(i.uid)}" style="flex:none;align-self:flex-start">${icon("trash", 17)}</button>
    </div>`
    )
    .join("");

  return `
    <div style="display:flex;align-items:baseline;gap:8px;margin-bottom:4px">
      <h2 style="margin:0">${esc(carLabelShort())}</h2><span class="mut2" style="font-size:14px">${esc(state.year)}</span>
    </div>
    <p>${t("cart.build_sub")}</p>
    ${rows}
    <button class="cta dashed" style="margin-top:12px" data-act="addMore">
      ${icon("plus", 16)} ${t("cart.other_zone")}</button>
    <div style="margin-top:14px">
      <div class="row" style="justify-content:space-between;font-size:13.5px;padding:6px 0;color:var(--muted)">
        <span>${t("cart.work")}</span><span class="incl" style="color:var(--accent);font-family:var(--disp);font-weight:600">${t("cart.work_incl")}</span></div>
      <div class="row" style="justify-content:space-between;font-size:13.5px;padding:6px 0;color:var(--muted);border-top:1px solid var(--line)">
        <span>${t("cart.payment")}</span><span style="color:var(--txt)">${t("cart.payment_val")}</span></div>
    </div>`;
}

export const bar = () =>
  state.cart.length
    ? `<div class="barsplit">
        <div class="bartotal">
          <span class="micro">${t("cart.positions_n", { n: state.cart.length })}</span>
          <span class="num">${fmt(cartTotal())}</span>
        </div>
        <button class="cta" data-act="toRequest">${t("cart.checkout")}</button>
      </div>`
    : "";

export const actions = {
  addMore: () => nav("home"),
  removeItem: (_ev, el) =>
    setState({ cart: state.cart.filter((i) => i.uid !== el.dataset.uid) }),
  toRequest: () => nav("request"),
};
