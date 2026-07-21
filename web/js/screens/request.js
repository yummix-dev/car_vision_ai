import { api } from "../api.js";
import { cartTotal, nav, setQuiet, setState, state } from "../state.js";
import { tg } from "../tg.js";
import { esc } from "../ui.js";
import { fmt } from "../money.js";

const FIELDS = [
  ["name", "Имя", "text", "Как к вам обращаться"],
  ["phone", "Номер телефона", "tel", "+998 __ ___ __ __"],
  ["telegram", "Telegram", "text", "@username"],
  ["date", "Желаемая дата", "text", "например, 24 июля"],
];

export function body() {
  const fields = FIELDS.map(
    ([key, label, type, ph]) => `
    <div class="field">
      <label class="micro">${label}</label>
      <input type="${type}" data-field="${key}" placeholder="${esc(ph)}"
        value="${esc(state.form[key])}">
    </div>`
  ).join("");

  return `
    <h2>Заявка на установку</h2>
    <p>Менеджер свяжется с вами, подтвердит совместимость, стоимость и удобное время установки.</p>

    <div class="card" style="margin-bottom:14px">
      <div class="price">
        <div class="pl"><span>Автомобиль</span><span>${esc(state.carLabel)}</span></div>
        <div class="pl"><span>Позиций</span><span>${state.cart.length}</span></div>
        <div class="total"><span class="micro">Итого</span>
          <span class="num">${fmt(cartTotal())} сум</span></div>
      </div>
    </div>

    ${fields}
    <div class="field">
      <label class="micro">Комментарий</label>
      <textarea data-field="comment" placeholder="Пожелания к установке">${esc(state.form.comment)}</textarea>
    </div>
    ${state.formError ? `<div class="note" style="color:var(--red)">${esc(state.formError)}</div>` : ""}
    ${
      tg.user
        ? `<div class="note blue">Имя и Telegram подставлены из вашего профиля — их можно изменить.</div>`
        : `<div class="note">Откройте приложение в Telegram, чтобы имя и контакт подставились автоматически.</div>`
    }`;
}

export const bar = () =>
  `<button class="cta" data-act="submit">Отправить заявку</button>`;

export const actions = {
  submit: async () => {
    if (!state.form.phone.trim()) {
      setState({ formError: "Укажите номер телефона" });
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
