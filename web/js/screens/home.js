import { nav, state } from "../state.js";
import { ba } from "../ui.js";
import { icon } from "../icons.js";

const ADVANTAGES = [
  "Примерка на вашей собственной фотографии",
  "Совместимость подбирается под вашу машину",
  "Установка включена в стоимость",
];

export function body() {
  const rows = ADVANTAGES.map(
    (t) => `<div class="row" style="padding:8px 0">
      <span style="color:var(--green);display:grid;place-items:center">${icon("check", 17, 2.4)}</span>
      <span style="font-size:14px">${t}</span></div>`
  ).join("");

  return `
    <h1>Примерь апгрейд на свою машину</h1>
    <p>Загрузи фото салона, выбери руль, магнитолу или другой апгрейд и посмотри результат до установки.</p>
    ${ba({
      key: "homeSlider",
      value: state.homeSlider,
      height: 224,
      before: "/img/example/before.jpg",
      after: "/img/example/after.jpg",
      beforeCap: "[ салон · штатный руль ]",
      afterCap: "[ салон · новый руль ]",
    })}
    <div class="mono" style="text-align:center;margin:9px 0 4px">Потяни ползунок «До / После»</div>
    <div class="card">${rows}</div>`;
}

export const bar = () => `
  <button class="cta" data-act="toPick">Выбрать, что примерить</button>
  <button class="cta sec" data-act="toExample">Посмотреть пример</button>`;

export const actions = {
  toPick: () => nav("pick"),
  toExample: () => nav("example"),
};
