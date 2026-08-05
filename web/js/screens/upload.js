import { track } from "../analytics.js";
import { api } from "../api.js";
import { t } from "../i18n.js";
import { icon } from "../icons.js";
import { currentCategory, nav, setState, state } from "../state.js";
import { esc } from "../ui.js";

// [id, icon, i18n label, primary?] — the camera is the primary path, drawn with
// a filled lime tile; gallery and demo are secondary.
const SOURCES = [
  ["camera", "camera", "upload.src_camera", true],
  ["gallery", "gallery", "upload.src_gallery", false],
  ["demo", "demo", "upload.src_demo", false],
];

export const title = () => currentCategory()?.noun_cap || currentCategory()?.label || "";

export function body() {
  const cat = currentCategory();

  const rows = SOURCES.map(
    ([id, ic, key, primary]) => `
    <button class="card" style="width:100%;text-align:left;cursor:pointer;display:flex;align-items:center;gap:13px;margin-bottom:10px"
      data-act="pickSource" data-src="${id}">
      <span style="width:40px;height:40px;border-radius:11px;flex:none;display:grid;place-items:center;
        ${primary ? "background:var(--accent);color:var(--accentInk)" : "background:var(--card2);color:var(--accent)"}">${icon(ic, 20)}</span>
      <span style="flex:1;font-size:15px;font-weight:500">${t(key)}</span>
      <span class="mut2">${icon("next", 17)}</span>
    </button>`
  ).join("");

  return `
    <h2>${esc(cat?.shoot_title || "")}</h2>
    <p>${t("upload.subtitle")}</p>
    ${rows}
    ${state.uploadError ? `<div class="note" style="color:var(--red)">${esc(state.uploadError)}</div>` : ""}
    <div class="micro" style="margin:22px 0 10px">${t("upload.tips_title")}</div>
    <div class="row" style="gap:10px;align-items:stretch">
      <div style="flex:1;border-radius:12px;overflow:hidden;position:relative;height:96px;background:center/cover url('/img/example/before.jpg')">
        <span style="position:absolute;left:8px;bottom:8px;background:var(--accent);color:var(--accentInk);font-size:10.5px;font-weight:700;padding:3px 8px;border-radius:6px">${t("upload.eg_ok")}</span>
      </div>
      <div style="flex:1;border-radius:12px;overflow:hidden;position:relative;height:96px;background:center/cover url('/img/example/before.jpg');filter:grayscale(1) brightness(.55)">
        <span style="position:absolute;left:8px;bottom:8px;background:var(--card2);color:var(--muted);font-size:10.5px;font-weight:700;padding:3px 8px;border-radius:6px">${t("upload.eg_bad")}</span>
      </div>
    </div>
    <input type="file" id="filepick" accept="image/*" hidden>`;
}

/** Move on to the car-selection screen once a photo exists. */
function advance() {
  setState({ carField: null });
  nav("car");
}

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
        advance();
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
      advance();
    } catch (e) {
      setState({ uploadError: e.message });
    }
  });
}
