import { icon } from "../icons.js";
import { cartTotal, nav, setState, state } from "../state.js";
import { esc } from "../ui.js";
import { fmt } from "../money.js";

export function body() {
  if (!state.cart.length) {
    return `
      <h2>Ваша сборка</h2>
      <div class="note">Корзина пуста. Выберите раздел и примерьте товар.</div>
      <button class="cta dashed" style="margin-top:12px" data-act="addMore">Добавить товар</button>`;
  }

  const rows = state.cart
    .map(
      (i) => `
    <div class="card">
      <div class="row" style="align-items:flex-start">
        ${
          i.image
            ? `<div class="thumb" style="background-image:url('${esc(i.image)}')"></div>`
            : `<div class="ph sm thumb"><span class="mono" style="font-size:9px">[ ${esc(i.categoryLabel)} ]</span></div>`
        }
        <div style="flex:1">
          <div class="micro" style="margin-bottom:3px">${esc(i.categoryLabel)}</div>
          <h3>${esc(i.name)}</h3>
          <div class="mut2" style="font-size:12px;margin-top:3px">${esc(i.time)}</div>
        </div>
        <button class="iconbtn mut2" data-act="removeItem" data-uid="${esc(i.uid)}">${icon("trash", 17)}</button>
      </div>
      <div class="chips" style="margin:10px 0 0">
        ${i.chips.map((c) => `<span class="tag">${esc(c)}</span>`).join(" ")}
        ${(i.serviceLines || []).map((s) => `<span class="tag" style="color:var(--blue)">${esc(s)}</span>`).join(" ")}
      </div>
      <div class="row" style="justify-content:space-between;margin-top:11px;padding-top:10px;border-top:1px solid var(--line)">
        <span class="micro">Стоимость</span>
        <span class="num" style="font-size:18px">${fmt(i.total)} сум</span>
      </div>
    </div>`
    )
    .join("");

  return `
    <h2>Ваша сборка</h2>
    <p>${state.cart.length} поз. для ${esc(state.carLabel)}</p>
    ${rows}
    <button class="cta dashed" style="margin-top:12px" data-act="addMore">
      ${icon("plus", 16)} Добавить ещё товар</button>
    <div class="card" style="margin-top:12px">
      <div class="price">
        <div class="pl"><span>Позиций</span><span>${state.cart.length}</span></div>
        <div class="total"><span class="micro">Итого</span>
          <span class="num">${fmt(cartTotal())} сум</span></div>
      </div>
    </div>`;
}

export const bar = () =>
  state.cart.length
    ? `<button class="cta" data-act="toRequest">Оформить заявку</button>`
    : "";

export const actions = {
  addMore: () => nav("pick"),
  removeItem: (_ev, el) =>
    setState({ cart: state.cart.filter((i) => i.uid !== el.dataset.uid) }),
  toRequest: () => nav("request"),
};
