import { nav } from "../state.js";

const NODES = [
  ["Выберите раздел", "Руль, магнитола, бампер, камера или парктроники."],
  ["Сфотографируйте зону", "Камера, галерея или демонстрационное фото."],
  ["AI определяет автомобиль", "Марка, модель и год — с возможностью поправить."],
  ["Подбираем совместимые товары", "Только то, что подходит вашей машине."],
  ["Настройте товар", "Цвет кожи, строчка, вставки, подсветка."],
  ["AI создаёт визуализацию", "Меняем только выбранную зону на вашем фото."],
  ["Сравните до и после", "Ползунок показывает результат на вашей машине."],
  ["Оформите заявку", "Менеджер подтвердит совместимость и время установки."],
];

export function body() {
  const nodes = NODES.map(
    ([title, sub], i) => `
    <div class="row" style="align-items:flex-start;gap:13px;padding:11px 0">
      <div class="stepdot ${i === 0 ? "on" : ""}" style="margin-top:2px">${i + 1}</div>
      <div style="flex:1">
        <h3>${title}</h3>
        <div class="mut" style="font-size:13px;margin-top:3px;line-height:1.4">${sub}</div>
      </div>
    </div>
    ${i < NODES.length - 1 ? '<div style="height:1px;background:var(--line);margin-left:33px"></div>' : ""}`
  ).join("");

  return `
    <span class="eyebrow">Как это работает</span>
    <h1>Путь от фото до апгрейда</h1>
    <p>Восемь шагов — от снимка салона до заявки на установку.</p>
    <div class="card" style="padding:4px 14px">${nodes}</div>
    <div class="note">Каждую зону автомобиля фотографируйте отдельно — так AI точнее определит перспективу.</div>`;
}

export const bar = () =>
  `<button class="cta" data-act="start">Начать примерку</button>`;

export const actions = {
  start: () => nav("home"),
};
