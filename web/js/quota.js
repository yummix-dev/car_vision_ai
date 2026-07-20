// AI try-on balance: fetching, wording, and the sheets that explain it.
//
// The vocabulary is fixed by the product: "AI-примерки" and "бонусные примерки".
// No tokens, credits, limits or requests anywhere a customer can see.

import { api } from "./api.js";
import { icon } from "./icons.js";
import { setState, state } from "./state.js";
import { esc } from "./ui.js";

/** Refresh the balance for a category. Never blocks the screen it is on. */
export async function refreshBalance(categoryId) {
  try {
    setState({ balance: await api.balance(categoryId) });
  } catch {
    // A balance we cannot read must not stop anyone browsing; the server
    // enforces the quota regardless of what the client shows.
    setState({ balance: null });
  }
}

export const metered = () => Boolean(state.balance?.metered);

export const freeLeft = () => state.balance?.current?.free_remaining ?? 0;
export const bonusLeft = () => state.balance?.bonus_remaining ?? 0;
export const nextCharge = () => state.balance?.next_charge ?? "free";
export const exhausted = () => metered() && nextCharge() === "none";

/** Suffix for the generate button: "Примерить · осталось 2". */
export function buttonSuffix() {
  if (!metered()) return "";
  if (freeLeft() > 0) return ` · осталось ${freeLeft()}`;
  if (bonusLeft() > 0) return ` · бонусных ${bonusLeft()}`;
  return "";
}

/** The compact strip above the generate button. */
export function balanceChip(categoryLabel) {
  if (!metered()) return "";
  const left = freeLeft();
  const bonus = bonusLeft();
  const line =
    left > 0
      ? `Осталось ${left} из ${state.balance.current.free_limit} примерок`
      : bonus > 0
        ? "Бесплатные примерки закончились"
        : "Примерки в этой категории закончились";

  return `
    <button class="card quota-chip" data-act="openBalance"
            style="width:100%;text-align:left;cursor:pointer">
      <div style="flex:1">
        <div style="font-size:13.5px">${esc(categoryLabel)}</div>
        <div class="mut2" style="font-size:12px;margin-top:2px">${esc(line)}</div>
      </div>
      ${bonus ? `<span class="pill in">Бонусные: ${bonus}</span>` : ""}
      <span class="mut2">${icon("next", 16)}</span>
    </button>`;
}

/** Details sheet. The main screen stays uncluttered; this holds the rest. */
export function balanceSheet() {
  if (!state.balanceOpen || !metered()) return "";

  const cats = state.catalog?.categories || [];
  const limit = state.balance.current?.free_limit ?? 3;
  const rows = cats
    .map((c) => {
      const entry = state.balance.categories[c.id];
      const left = entry ? entry.free_remaining : limit;
      const max = entry ? entry.free_limit : limit;
      return `<div class="pl"><span>${esc(c.label)}</span>
        <span class="num">${left} из ${max}</span></div>`;
    })
    .join("");

  const history = (state.balanceHistory || [])
    .slice(0, 6)
    .map((h) => {
      const sign = h.amount > 0 ? "+" : "";
      return `<div class="pl"><span>${esc(describe(h))}</span>
        <span class="num">${sign}${h.amount}</span></div>`;
    })
    .join("");

  return `
    <div class="sheet-back" data-act="closeBalance"></div>
    <div class="sheet">
      <div class="sheet-grip"></div>
      <h3 style="margin:0 0 4px">AI-примерки</h3>
      <div class="mut2" style="font-size:12.5px;margin-bottom:12px">
        Бесплатные примерки считаются отдельно для каждого раздела.
      </div>
      <div class="price">${rows}
        <div class="total"><span class="micro">Бонусные примерки</span>
          <span class="num">${bonusLeft()}</span></div>
      </div>
      ${history ? `<div class="micro" style="margin:14px 0 6px">Последние операции</div>
        <div class="price">${history}</div>` : ""}
      <button class="cta" data-act="openReferral" style="margin-top:14px">Получить примерки</button>
      <button class="cta sec" data-act="closeBalance" style="margin-top:9px">Понятно</button>
    </div>`;
}

const LABELS = {
  spend: "Примерка",
  refund: "Возврат за неудачную примерку",
  grant: "Начислены бонусные примерки",
};

function describe(entry) {
  return LABELS[entry.transaction_type] || entry.transaction_type;
}

/** Shown instead of starting a generation when nothing is left to spend. */
export function exhaustedSheet() {
  if (!state.exhaustedOpen) return "";
  return `
    <div class="sheet-back" data-act="closeExhausted"></div>
    <div class="sheet">
      <div class="sheet-grip"></div>
      <h3 style="margin:0 0 6px">Примерки закончились</h3>
      <p style="margin:0 0 14px">
        Вы использовали все бесплатные примерки в этом разделе.
        Каталог, сохранённые результаты и заявка на установку остаются доступны.
      </p>
      <div class="price">
        <div class="pl"><span>Бонусные примерки</span><span class="num">${bonusLeft()}</span></div>
      </div>
      <button class="cta" data-act="openReferral" style="margin-top:14px">Пригласить друзей</button>
      <button class="cta sec" data-act="openCode" style="margin-top:9px">Активировать код</button>
      <button class="cta sec" data-act="closeExhausted" style="margin-top:9px">Вернуться к каталогу</button>
    </div>`;
}

/** Redeeming a code from a visit or a purchase. */
export function codeSheet() {
  if (!state.codeOpen) return "";
  const ok = state.codeResult;
  return `
    <div class="sheet-back" data-act="closeCode"></div>
    <div class="sheet">
      <div class="sheet-grip"></div>
      ${
        ok
          ? `<h3 style="margin:0 0 6px">Код активирован</h3>
             <p style="margin:0 0 14px">${esc(describeReward(ok))}</p>
             <button class="cta" data-act="closeCode">Отлично</button>`
          : `<h3 style="margin:0 0 6px">Активировать бонус</h3>
             <p style="margin:0 0 12px">Код выдаётся после визита в мастерскую
                или установки. Введите его, чтобы получить примерки.</p>
             <div class="field">
               <input type="text" data-field="code" placeholder="Например, K7QX2M4P"
                      value="${esc(state.codeInput || "")}"
                      style="text-transform:uppercase">
             </div>
             ${state.codeError ? `<div class="note" style="color:var(--red)">${esc(state.codeError)}</div>` : ""}
             <button class="cta" data-act="submitCode" style="margin-top:10px"
                     ${state.codeBusy ? "disabled" : ""}>
               ${state.codeBusy ? "Проверяем…" : "Активировать"}</button>
             <button class="cta sec" data-act="closeCode" style="margin-top:9px">Отмена</button>`
      }
    </div>`;
}

function describeReward(r) {
  const parts = [];
  if (r.restored_free) parts.push("бесплатные примерки восстановлены во всех разделах");
  if (r.bonus_amount) parts.push(`начислено бонусных примерок: ${r.bonus_amount}`);
  return parts.length ? parts.join(", ") : "Бонус применён.";
}

/** Shown to somebody who arrived by invitation and has not generated yet.
 *  Says nothing about who invited them — §8 forbids exposing that. */
export function invitedNote() {
  if (!state.invitedPending) return "";
  return `<div class="note blue">Вы пришли по приглашению.
    Создайте свою первую примерку, чтобы друг получил бонус.</div>`;
}

/** Confirmation before a bonus try is spent — the customer should know. */
export function bonusConfirmSheet() {
  if (!state.bonusConfirmOpen) return "";
  return `
    <div class="sheet-back" data-act="cancelBonus"></div>
    <div class="sheet">
      <div class="sheet-grip"></div>
      <h3 style="margin:0 0 6px">Использовать бонусную примерку?</h3>
      <p style="margin:0 0 14px">
        Бесплатные примерки в этом разделе закончились.
        Будет использована 1 бонусная примерка. Осталось: ${bonusLeft()}.
      </p>
      <button class="cta" data-act="confirmBonus">Продолжить</button>
      <button class="cta sec" data-act="cancelBonus" style="margin-top:9px">Отмена</button>
    </div>`;
}
