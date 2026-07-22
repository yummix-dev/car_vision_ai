import { t } from "../i18n.js";
import { nav } from "../state.js";

const STEP_KEYS = ["s1", "s2", "s3", "s4", "s5", "s6", "s7", "s8"];

export function body() {
  const nodes = STEP_KEYS.map(
    (k, i) => `
    <div class="row" style="align-items:flex-start;gap:13px;padding:11px 0">
      <div class="stepdot ${i === 0 ? "on" : ""}" style="margin-top:2px">${i + 1}</div>
      <div style="flex:1">
        <h3>${t(`flow.${k}.t`)}</h3>
        <div class="mut" style="font-size:13px;margin-top:3px;line-height:1.4">${t(`flow.${k}.d`)}</div>
      </div>
    </div>
    ${i < STEP_KEYS.length - 1 ? '<div style="height:1px;background:var(--line);margin-left:33px"></div>' : ""}`
  ).join("");

  return `
    <span class="eyebrow">${t("flow.eyebrow")}</span>
    <h1>${t("flow.title")}</h1>
    <p>${t("flow.lede")}</p>
    <div class="card" style="padding:4px 14px">${nodes}</div>
    <div class="note">${t("flow.note")}</div>`;
}

export const bar = () =>
  `<button class="cta" data-act="start">${t("flow.start")}</button>`;

export const actions = {
  start: () => nav("home"),
};
