import { t } from "../i18n.js";
import { nav, state } from "../state.js";
import { ba, stockPill } from "../ui.js";

// Read-only demo. Deliberately hardcoded — it illustrates a finished result and
// is not derived from the live catalog.
export function body() {
  return `
    <span class="eyebrow">${t("example.eyebrow")}</span>
    <h2>${t("example.title")}</h2>
    ${ba({
      key: "exSlider",
      value: state.exSlider,
      height: 230,
      before: "/img/example/before.jpg",
      after: "/img/example/after.jpg",
      beforeCap: t("example.cap_before"),
      afterCap: t("example.cap_after"),
    })}
    <div class="card" style="margin-top:14px">
      <div class="row" style="align-items:flex-start">
        <div style="flex:1"><h3>Mercedes-AMG Performance</h3>
          <div class="mut2" style="font-size:12px;margin-top:2px">${t("example.for")}</div>
        </div>${stockPill("in")}
      </div>
      <div class="chips" style="margin:10px 0 12px">
        <span class="tag">${t("example.tag_carbon")}</span><span class="tag">${t("example.tag_led")}</span><span class="tag">${t("example.tag_paddles")}</span>
      </div>
      <div class="price">
        <div class="pl"><span>Mercedes-AMG Performance</span><span>6 200 000</span></div>
        <div class="pl"><span>${t("config.services")}</span><span>600 000</span></div>
        <div class="pl"><span>${t("example.install")}</span><span>${t("example.install_incl")}</span></div>
        <div class="total"><span class="micro">${t("example.total")}</span><span class="num">6 800 000 ${t("ui.currency")}</span></div>
      </div>
    </div>
    <div class="note">${t("example.note")}</div>`;
}

export const bar = () =>
  `<button class="cta" data-act="toPick">${t("example.cta")}</button>`;

export const actions = {
  toPick: () => nav("pick"),
};
