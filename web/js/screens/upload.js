import { track } from "../analytics.js";
import { api } from "../api.js";
import { icon } from "../icons.js";
import { currentCategory, nav, setState, state } from "../state.js";
import { esc } from "../ui.js";

const SOURCES = [
  ["camera", "camera", "Сделать фотографию"],
  ["gallery", "gallery", "Выбрать из галереи"],
  ["demo", "demo", "Демонстрационное фото"],
];

const TIPS = [
  "Нужная зона должна полностью попадать в кадр",
  "Держите телефон ровно",
  "Используйте хорошее освещение",
  "Не закрывайте объект руками",
];

export function body() {
  const cat = currentCategory();
  const hasPreview = Boolean(state.photoId);

  if (hasPreview) {
    return `
      <h2>${esc(cat?.shoot_title || "Фото")}</h2>
      <p>Так AI точнее определит положение и перспективу.</p>
      <div style="position:relative;height:260px;border-radius:var(--r-lg);overflow:hidden;
        background:#131922 center/cover url('${esc(state.photoUrl)}')">
        <span class="pill in" style="position:absolute;top:10px;left:10px">${esc(cat?.noun_cap || "Зона")} в кадре</span>
      </div>
      <div class="row" style="margin-top:12px">
        <button class="btn" style="flex:1" data-act="clearPhoto">Заменить</button>
        <button class="btn" style="flex:1" data-act="rotate" ${state.rotating ? "disabled" : ""}>
          ${state.rotating ? "Поворачиваем…" : "Повернуть"}</button>
      </div>
      ${state.uploadError ? `<div class="note" style="color:var(--red)">${esc(state.uploadError)}</div>` : ""}`;
  }

  const rows = SOURCES.map(
    ([id, ic, label]) => `
    <button class="card" style="width:100%;text-align:left;cursor:pointer;display:flex;align-items:center;gap:12px"
      data-act="pickSource" data-src="${id}">
      <span style="width:38px;height:38px;border-radius:11px;background:var(--card2);
        display:grid;place-items:center;color:var(--blue);flex:none">${icon(ic, 19)}</span>
      <span style="flex:1;font-size:14.5px">${label}</span>
      <span class="mut2">${icon("next", 17)}</span>
    </button>`
  ).join("");

  const tips = TIPS.map(
    (t) => `<div class="row" style="padding:6px 0">
      <span style="color:var(--green);display:grid;place-items:center">${icon("check", 15, 2.4)}</span>
      <span style="font-size:13px;color:var(--muted)">${t}</span></div>`
  ).join("");

  return `
    <h2>${esc(cat?.shoot_title || "Фото")}</h2>
    <p>Так AI точнее определит положение и перспективу.</p>
    ${rows}
    ${state.uploadError ? `<div class="note" style="color:var(--red)">${esc(state.uploadError)}</div>` : ""}
    <div class="card" style="margin-top:14px">
      <div class="micro" style="margin-bottom:6px">Рекомендации к фото</div>${tips}
    </div>
    <input type="file" id="filepick" accept="image/*" hidden>`;
}

export const bar = () => `
  <button class="cta" data-act="goCar" ${state.photoId ? "" : "disabled"}>Продолжить</button>`;

export const actions = {
  pickSource: async (_ev, el) => {
    const src = el.dataset.src;
    if (src === "demo") {
      try {
        const photo = await api.demoPhoto();
        setState({
          photoSource: "demo",
          photoId: photo.photo_id,
          photoUrl: photo.url,
          uploadError: "",
        });
        track("photo_uploaded", {
          category_id: currentCategory()?.id,
          payload: { source: "demo" },
        });
      } catch (e) {
        setState({ uploadError: e.message });
      }
      return;
    }
    // Camera vs gallery is purely a capture-attribute difference; both upload
    // through the same endpoint.
    const input = document.getElementById("filepick");
    if (!input) return;
    if (src === "camera") input.setAttribute("capture", "environment");
    else input.removeAttribute("capture");
    input.dataset.src = src;
    input.click();
  },

  // Which source people actually use decides whether the camera path is worth
  // its complexity.
  clearPhoto: () =>
    setState({ photoSource: "", photoId: null, photoUrl: null, uploadError: "" }),

  rotate: async () => {
    if (!state.photoId || state.rotating) return;
    setState({ rotating: true, uploadError: "" });
    try {
      const photo = await api.rotatePhoto(state.photoId);
      setState({
        photoId: photo.photo_id,
        photoUrl: photo.url,
        rotating: false,
      });
    } catch (e) {
      setState({ rotating: false, uploadError: e.message });
    }
  },

  goCar: () => {
    if (!state.photoId) return;
    setState({ analyzing: true, carEditing: false });
    nav("car");
  },
};

/** Wired once by app.js after each render, since the input is recreated. */
export function afterRender() {
  const input = document.getElementById("filepick");
  if (!input || input.dataset.bound) return;
  input.dataset.bound = "1";
  input.addEventListener("change", async () => {
    const file = input.files?.[0];
    if (!file) return;
    try {
      const source = input.dataset.src || "gallery";
      const photo = await api.uploadPhoto(file);
      setState({
        photoSource: source,
        photoId: photo.photo_id,
        photoUrl: photo.url,
        uploadError: "",
      });
      track("photo_uploaded", {
        category_id: currentCategory()?.id,
        payload: { source },
      });
    } catch (e) {
      setState({ uploadError: e.message });
    }
  });
}
