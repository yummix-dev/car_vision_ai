// AI try-on balance: fetching, wording, and the sheets that explain it.
//
// The vocabulary is fixed by the product: "AI-примерки" and "бонусные примерки".
// No tokens, credits, limits or requests anywhere a customer can see.

import { api } from "./api.js";
import { t } from "./i18n.js";
import { icon } from "./icons.js";
import { setState, state } from "./state.js";
import { tg } from "./tg.js";
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
  if (freeLeft() > 0) return t("config.suffix_left", { n: freeLeft() });
  if (bonusLeft() > 0) return t("config.suffix_bonus", { n: bonusLeft() });
  return "";
}

/** The compact strip above the generate button. */
export function balanceChip(categoryLabel) {
  if (!metered()) return "";
  const left = freeLeft();
  const bonus = bonusLeft();
  const line =
    left > 0
      ? t("quota.left_of", { n: left, max: state.balance.current.free_limit })
      : bonus > 0
        ? t("quota.free_out")
        : t("quota.cat_out");

  return `
    <button class="card quota-chip" data-act="openBalance"
            style="width:100%;text-align:left;cursor:pointer">
      <div style="flex:1">
        <div style="font-size:13.5px">${esc(categoryLabel)}</div>
        <div class="mut2" style="font-size:12px;margin-top:2px">${esc(line)}</div>
      </div>
      ${bonus ? `<span class="pill in">${t("quota.bonus", { n: bonus })}</span>` : ""}
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
        <span class="num">${left} / ${max}</span></div>`;
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
      <h3 style="margin:0 0 4px">${t("quota.title")}</h3>
      <div class="mut2" style="font-size:12.5px;margin-bottom:12px">
        ${t("quota.by_section")}
      </div>
      <div class="price">${rows}
        <div class="total"><span class="micro">${t("quota.bonus_tries")}</span>
          <span class="num">${bonusLeft()}</span></div>
      </div>
      ${history ? `<div class="micro" style="margin:14px 0 6px">${t("quota.recent")}</div>
        <div class="price">${history}</div>` : ""}
      <button class="cta" data-act="openReferral" style="margin-top:14px">${t("quota.get_more")}</button>
      <button class="cta sec" data-act="closeBalance" style="margin-top:9px">${t("quota.ok")}</button>
    </div>`;
}

const LABEL_KEYS = {
  spend: "quota.op_spend",
  refund: "quota.op_refund",
  grant: "quota.op_grant",
};

function describe(entry) {
  const key = LABEL_KEYS[entry.transaction_type];
  return key ? t(key) : entry.transaction_type;
}

/** Shown instead of starting a generation when nothing is left to spend. */
export function exhaustedSheet() {
  if (!state.exhaustedOpen) return "";
  return `
    <div class="sheet-back" data-act="closeExhausted"></div>
    <div class="sheet">
      <div class="sheet-grip"></div>
      <h3 style="margin:0 0 6px">${t("quota.exhausted_title")}</h3>
      <p style="margin:0 0 14px">
        ${t("quota.exhausted_body")}
      </p>
      <div class="price">
        <div class="pl"><span>${t("quota.bonus_tries")}</span><span class="num">${bonusLeft()}</span></div>
      </div>
      <button class="cta" data-act="openReferral" style="margin-top:14px">${t("quota.invite_friends")}</button>
      <button class="cta sec" data-act="openCode" style="margin-top:9px">${t("quota.activate_code")}</button>
      <button class="cta sec" data-act="closeExhausted" style="margin-top:9px">${t("quota.back_to_catalog")}</button>
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
          ? `<h3 style="margin:0 0 6px">${t("quota.code_activated")}</h3>
             <p style="margin:0 0 14px">${esc(describeReward(ok))}</p>
             <button class="cta" data-act="closeCode">${t("quota.code_great")}</button>`
          : `<h3 style="margin:0 0 6px">${t("quota.code_title")}</h3>
             <p style="margin:0 0 12px">${t("quota.code_body")}</p>
             <div class="field">
               <input type="text" data-field="code" placeholder="${t("quota.code_ph")}"
                      value="${esc(state.codeInput || "")}"
                      style="text-transform:uppercase">
             </div>
             ${state.codeError ? `<div class="note" style="color:var(--red)">${esc(state.codeError)}</div>` : ""}
             <button class="cta" data-act="submitCode" style="margin-top:10px"
                     ${state.codeBusy ? "disabled" : ""}>
               ${state.codeBusy ? t("quota.code_checking") : t("quota.code_activate")}</button>
             ${tg.canScanQr ? `<button class="cta sec" data-act="scanCode" style="margin-top:9px">${t("quota.code_scan")}</button>` : ""}
             <button class="cta sec" data-act="closeCode" style="margin-top:9px">${t("quota.code_cancel")}</button>`
      }
    </div>`;
}

function describeReward(r) {
  const parts = [];
  if (r.restored_free) parts.push(t("quota.reward_restored"));
  if (r.bonus_amount) parts.push(t("quota.reward_bonus", { n: r.bonus_amount }));
  return parts.length ? parts.join(", ") : t("quota.reward_applied");
}

/** Shown to somebody who arrived by invitation and has not generated yet.
 *  Says nothing about who invited them — §8 forbids exposing that. */
export function invitedNote() {
  if (!state.invitedPending) return "";
  return `<div class="note blue">${t("ref.invited_note")}</div>`;
}

/** Confirmation before a bonus try is spent — the customer should know. */
export function bonusConfirmSheet() {
  if (!state.bonusConfirmOpen) return "";
  return `
    <div class="sheet-back" data-act="cancelBonus"></div>
    <div class="sheet">
      <div class="sheet-grip"></div>
      <h3 style="margin:0 0 6px">${t("quota.bonus_confirm_title")}</h3>
      <p style="margin:0 0 14px">
        ${t("quota.bonus_confirm_body", { n: bonusLeft() })}
      </p>
      <button class="cta" data-act="confirmBonus">${t("quota.bonus_continue")}</button>
      <button class="cta sec" data-act="cancelBonus" style="margin-top:9px">${t("quota.bonus_cancel")}</button>
    </div>`;
}
