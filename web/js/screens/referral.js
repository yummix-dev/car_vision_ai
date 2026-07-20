import { api } from "../api.js";
import { back, setState, state } from "../state.js";
import { tg } from "../tg.js";
import { esc } from "../ui.js";

export function body() {
  const r = state.referral;

  if (r && r.available === false) {
    return `
      <h2>Получайте примерки за друзей</h2>
      <p>Персональная ссылка доступна в Telegram — откройте приложение через бота.</p>`;
  }
  if (!r) {
    return `<div style="display:grid;place-items:center;padding:60px 0"><div class="spinner"></div></div>`;
  }

  const stat = (label, value) => `
    <div class="card" style="flex:1;min-width:132px">
      <div class="micro">${label}</div>
      <div class="num" style="font-size:24px;margin-top:3px">${value}</div>
    </div>`;

  return `
    <h2>Получайте примерки за друзей</h2>
    <p>Поделитесь своей ссылкой. Когда новый пользователь создаст первую
       AI-примерку, вы получите одну бонусную примерку.</p>

    <div class="row" style="gap:9px;flex-wrap:wrap;margin-bottom:12px">
      ${stat("Приглашено", r.invited)}
      ${stat("Создали примерку", r.qualified)}
    </div>
    <div class="row" style="gap:9px;flex-wrap:wrap">
      ${stat("Получено бонусов", r.bonus_earned)}
      ${stat("Доступно в этом месяце", r.monthly_remaining)}
    </div>

    <div class="card" style="margin-top:14px">
      <div class="micro" style="margin-bottom:7px">Ваша ссылка</div>
      <div class="mono" style="word-break:break-all;font-size:12.5px">${esc(r.link || "—")}</div>
    </div>

    ${state.referralCopied ? `<div class="note blue">Ссылка скопирована</div>` : ""}
    <div class="note">Бонус начисляется только за первую успешную примерку
      приглашённого. За переход по ссылке или установку бонус не начисляется.</div>`;
}

export const bar = () => {
  const link = state.referral?.link;
  if (!link) return `<button class="cta sec" data-act="closeReferral">Назад</button>`;
  return `
    <button class="cta" data-act="shareLink">Пригласить друзей</button>
    <button class="cta sec" data-act="copyLink">Скопировать ссылку</button>`;
};

export const actions = {
  closeReferral: () => back(),

  copyLink: async () => {
    const link = state.referral?.link;
    if (!link) return;
    try {
      await navigator.clipboard.writeText(link);
    } catch {
      // Clipboard is blocked in some webviews; the link is on screen to select.
    }
    setState({ referralCopied: true });
  },

  shareLink: () => {
    const link = state.referral?.link;
    if (!link) return;
    const text = encodeURIComponent(
      "Собери свою машину — примерь тюнинг на своём фото."
    );
    tg.openTelegramLink(
      `https://t.me/share/url?url=${encodeURIComponent(link)}&text=${text}`
    );
  },
};

export async function onEnter() {
  setState({ referralCopied: false });
  try {
    setState({ referral: await api.referral() });
  } catch {
    setState({ referral: { available: false } });
  }
}
