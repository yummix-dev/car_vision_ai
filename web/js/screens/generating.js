import { track } from "../analytics.js";
import { api } from "../api.js";
import { icon } from "../icons.js";
import { refreshBalance } from "../quota.js";
import {
  currentCategory,
  nav,
  replace,
  selectionList,
  setState,
  state,
} from "../state.js";
import { esc } from "../ui.js";

export function body() {
  const job = state.job;

  if (job?.status === "error") {
    return `
      <div style="display:grid;place-items:center;gap:14px;padding:56px 0;text-align:center">
        <span style="color:var(--red)">${icon("warn", 40, 1.6)}</span>
        <h2 style="margin:0">Не удалось точно распознать фото</h2>
        <div class="mut" style="font-size:13.5px;max-width:270px">
          Попробуйте загрузить фотографию, где нужная зона полностью видна и хорошо освещена.
        </div>
      </div>`;
  }

  const steps = (job?.steps || currentCategory()?.gen_steps || []).map((s, i) => {
    const idx = job?.step_index ?? 0;
    const done = i < idx || job?.status === "done";
    const on = i === idx;
    return `<li class="${done ? "done" : on ? "on" : ""}">
      <span class="ck">${done ? icon("check", 10, 3) : ""}</span>${esc(s)}</li>`;
  }).join("");

  const pct = job?.progress ?? 0;

  return `
    <div style="position:relative;height:190px;border-radius:var(--r-lg);overflow:hidden;
      background:#131922 center/cover url('${esc(state.photoUrl || "")}')">
      <div style="position:absolute;inset:0;display:grid;place-items:center;background:rgba(8,11,15,.55)">
        <div class="spinner"></div>
      </div>
    </div>
    <h2 style="margin-top:16px">Создаём визуализацию</h2>
    <p>${esc(job?.sub || "")}</p>
    <div class="progress"><b style="width:${pct}%"></b></div>
    <div class="row" style="justify-content:space-between;margin-top:7px">
      <span class="micro">Прогресс</span><span class="num">${pct}%</span>
    </div>
    <ul class="checklist">${steps}</ul>`;
}

export function bar() {
  if (state.job?.status === "error")
    return `<button class="cta" data-act="retry">Загрузить другое фото</button>`;
  return "";
}

export const actions = {
  retry: () => {
    setState({ photoSource: "", photoId: null, photoUrl: null, job: null, jobId: null });
    nav("upload");
  },
};

export async function onEnter() {
  if (state.jobId) return;
  try {
    const job = await api.startGeneration(
      state.photoId,
      state.productId,
      selectionList(),
      state.generationKey
    );
    setState({ jobId: job.job_id, job });
    poll();
  } catch (e) {
    // A rejected start (rate limit, bad product) never becomes a job, so the
    // poller below will not see it — report the failure here.
    track("generation_failed", {
      category_id: currentCategory()?.id,
      product_id: state.productId,
    });
    setState({ job: { status: "error", error: e.message, steps: [], progress: 0 } });
  }
}

async function poll() {
  while (state.screen === "generating" && state.jobId) {
    await new Promise((r) => setTimeout(r, 250));
    if (state.screen !== "generating" || !state.jobId) return;
    let job;
    try {
      job = await api.pollGeneration(state.jobId);
    } catch {
      return;
    }
    setState({ job });
    if (job.status === "done" || job.status === "error") {
      // The server has settled the reservation by now — a failure refunded it,
      // so re-read rather than guessing what was charged.
      refreshBalance(currentCategory()?.id);
      track(job.status === "done" ? "generation_done" : "generation_failed", {
        category_id: currentCategory()?.id,
        product_id: state.productId,
      });
    }
    if (job.status === "done") {
      // Replace rather than push, so Back from the result skips this screen.
      await new Promise((r) => setTimeout(r, 350));
      replace("result");
      return;
    }
    if (job.status === "error") return;
  }
}
