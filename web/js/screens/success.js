import { icon } from "../icons.js";
import { reset, setState, state } from "../state.js";
import { tg } from "../tg.js";
import { esc } from "../ui.js";

export function body() {
  const b = state.booking;
  return `
    <div style="display:grid;place-items:center;gap:14px;padding:44px 0 10px;text-align:center">
      <span style="width:66px;height:66px;border-radius:50%;background:var(--greenSoft);
        color:var(--green);display:grid;place-items:center">${icon("check", 32, 2.2)}</span>
      <h2 style="margin:0">Заявка отправлена</h2>
      <div class="mut" style="font-size:13.5px;max-width:280px">
        Менеджер свяжется с вами, подтвердит совместимость, стоимость и удобное время установки.
      </div>
    </div>
    <div class="card" style="margin-top:18px">
      <div class="price">
        <div class="pl"><span>Автомобиль</span><span>${esc(b?.car_label || state.carLabel)}</span></div>
        <div class="pl"><span>Позиций</span><span>${b?.positions ?? state.cart.length}</span></div>
        <div class="total"><span class="micro">Итого</span>
          <span class="num">${esc(b?.total_formatted || "0")} сум</span></div>
      </div>
    </div>
    ${b ? `<div class="mono" style="text-align:center;margin-top:12px">[ заявка № ${esc(b.booking_id)} ]</div>` : ""}`;
}

const botUsername = () => state.config?.telegram_bot_username || "";

export const bar = () => `
  ${botUsername() ? `<button class="cta" data-act="manager">Написать менеджеру</button>` : ""}
  <button class="cta ${botUsername() ? "sec" : ""}" data-act="toHome">На главную</button>`;

export const actions = {
  // Hidden entirely when no bot is configured — a button that opens nothing is
  // worse than no button.
  manager: () => {
    const username = botUsername();
    if (username) tg.openTelegramLink(`https://t.me/${username}`);
  },
  // The booking is done. Clear the finished order and start fresh at home
  // rather than walking back into a submitted funnel.
  toHome: () => {
    setState({
      cart: [],
      booking: null,
      form: { name: "", phone: "", telegram: "", date: "", comment: "" },
    });
    reset("home");
  },
};
