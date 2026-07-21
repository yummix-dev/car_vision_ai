import { nav, state } from "../state.js";
import { ba, stockPill } from "../ui.js";

// Read-only demo. Deliberately hardcoded — it illustrates a finished result and
// is not derived from the live catalog.
export function body() {
  return `
    <span class="eyebrow">Пример</span>
    <h2>AMG Carbon LED на Chevrolet Malibu</h2>
    ${ba({
      key: "exSlider",
      value: state.exSlider,
      height: 230,
      before: "/img/example/before.jpg",
      after: "/img/example/after.jpg",
      beforeCap: "[ исходное фото ]",
      afterCap: "[ AI-результат ]",
    })}
    <div class="card" style="margin-top:14px">
      <div class="row" style="align-items:flex-start">
        <div style="flex:1"><h3>AMG Carbon LED</h3>
          <div class="mut2" style="font-size:12px;margin-top:2px">Кожа + карбон · для Chevrolet Malibu</div>
        </div>${stockPill("in")}
      </div>
      <div class="chips" style="margin:10px 0 12px">
        <span class="tag">Карбон</span><span class="tag">LED</span><span class="tag">Лепестки</span>
      </div>
      <div class="price">
        <div class="pl"><span>AMG Carbon LED</span><span>6 200 000</span></div>
        <div class="pl"><span>Опции</span><span>600 000</span></div>
        <div class="pl"><span>Установка</span><span>включена</span></div>
        <div class="total"><span class="micro">Итого</span><span class="num">6 800 000 сум</span></div>
      </div>
    </div>
    <div class="note">AI-визуализация является предварительной. Итоговый вид может немного отличаться из-за освещения, ракурса и особенностей автомобиля.</div>`;
}

export const bar = () =>
  `<button class="cta" data-act="toPick">Загрузить своё фото</button>`;

export const actions = {
  toPick: () => nav("pick"),
};
