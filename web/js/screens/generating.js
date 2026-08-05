import { track } from "../analytics.js";
import { api } from "../api.js";
import { t } from "../i18n.js";
import { icon } from "../icons.js";
import {
  currentCategory,
  nav,
  replace,
  selectionList,
  setQuiet,
  setState,
  state,
} from "../state.js";
import { esc } from "../ui.js";

export const title = () => currentCategory()?.noun_cap || currentCategory()?.label || "";

export function body() {
  const job = state.job;

  if (job?.status === "error") {
    return `
      <div style="display:grid;place-items:center;gap:14px;padding:56px 0;text-align:center">
        <span style="color:var(--red)">${icon("warn", 40, 1.6)}</span>
        <h2 style="margin:0">${t("gen.error_title")}</h2>
        <div class="mut" style="font-size:13.5px;max-width:270px">
          ${t("gen.error_sub")}
        </div>
      </div>`;
  }

  // Prefer the localized catalog steps over the server's (which are Russian);
  // job.step_index still drives which one is active.
  const steps = (currentCategory()?.gen_steps || job?.steps || []).map((s, i) => {
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
    <h2 style="margin-top:16px">${t("gen.title")}</h2>
    <p data-gen="sub">${t("gen.sub")}</p>
    <div class="progress"><b data-gen="bar" style="width:${pct}%"></b></div>
    <div class="row" style="justify-content:space-between;margin-top:7px">
      <span class="micro">${t("gen.progress")}</span><span class="num" data-gen="pct">${pct}%</span>
    </div>
    <ul class="checklist" data-gen="steps">${steps}</ul>`;
}

/** Update the moving parts in place, without rebuilding the screen.
 *
 * A full re-render every poll (4×/sec) destroyed and recreated the spinner
 * element, restarting its CSS animation from zero each time — which is the
 * stutter. Patching the DOM instead lets the spinner and the photo stay put,
 * and the progress bar's width transition finally plays. */
export function patch() {
  const job = state.job;
  const root = document.getElementById("scr");
  if (!job || !root) return;

  const pct = job.progress ?? 0;
  const set = (sel, fn) => {
    const el = root.querySelector(`[data-gen="${sel}"]`);
    if (el) fn(el);
  };

  set("bar", (el) => (el.style.width = `${pct}%`));
  set("pct", (el) => (el.textContent = `${pct}%`));
  set("sub", (el) => (el.textContent = t("gen.sub")));
  set("steps", (list) => {
    const idx = job.step_index ?? 0;
    [...list.children].forEach((li, i) => {
      const done = i < idx || job.status === "done";
      li.className = done ? "done" : i === idx ? "on" : "";
      const ck = li.querySelector(".ck");
      if (ck) ck.innerHTML = done ? icon("check", 10, 3) : "";
    });
  });
}

export function bar() {
  if (state.job?.status === "error")
    return `<button class="cta" data-act="retry">${t("gen.retry")}</button>`;
  return "";
}

export const actions = {
  retry: () => {
    setState({
      photoSource: "", photoId: null, photoUrl: null, job: null, jobId: null,
    });
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
    // setQuiet, not setState: the screen is already drawn with the right steps,
    // so patch the initial job in place rather than rebuilding and restarting
    // the spinner.
    setQuiet({ jobId: job.job_id, job });
    patch();
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

    if (job.status === "done" || job.status === "error") {
      track(job.status === "done" ? "generation_done" : "generation_failed", {
        category_id: currentCategory()?.id,
        product_id: state.productId,
      });
    }

    if (job.status === "done") {
      setQuiet({ job }); // result reads state.job; no need to rebuild this screen
      // Replace rather than push, so Back from the result skips this screen.
      await new Promise((r) => setTimeout(r, 350));
      replace("result");
      return;
    }
    if (job.status === "error") {
      setState({ job }); // a full render here swaps in the error body
      return;
    }

    // Still running: patch in place so the spinner never restarts.
    setQuiet({ job });
    patch();
  }
}
