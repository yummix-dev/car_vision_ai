import { api } from "../api.js";
import { t } from "../i18n.js";
import { fmt } from "../money.js";
import { currentCategory, nav, selectionList, setState, state } from "../state.js";
import { esc } from "../ui.js";

// Side-by-side compare: two products rendered on the SAME photo. The "before" is
// identical, so the two "after" images are what the customer weighs. `compareBase`
// is the first result (A); the live state is the second (B), just generated.
function variant(label, productId, afterUrl, total, act) {
  const p = currentCategory()?.products.find((x) => x.id === productId);
  return `<div class="card" style="padding:0;overflow:hidden">
    <div style="height:150px;background:#131922 center/cover url('${esc(afterUrl || "")}')"></div>
    <div style="padding:12px">
      <div class="micro">${label}</div>
      <div style="font-weight:650;font-size:13.5px;margin-top:3px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${esc(p?.name || "")}</div>
      <div class="num" style="font-size:16px;margin-top:2px">${fmt(total)} ${t("ui.currency")}</div>
      <button class="cta" style="margin-top:10px;width:100%;padding:10px" data-act="${act}">${t("compare.choose")}</button>
    </div>
  </div>`;
}

export function body() {
  const base = state.compareBase;
  if (!base) return `<p>${t("compare.none")}</p>`;
  return `
    <h2>${t("compare.title")}</h2>
    <p>${t("compare.lede")}</p>
    <div class="grid2">
      ${variant(t("compare.a"), base.productId, base.job?.after_url, base.breakdown?.total ?? 0, "chooseA")}
      ${variant(t("compare.b"), state.productId, state.job?.after_url, state.breakdown?.total ?? 0, "chooseB")}
    </div>
    <div class="note">${t("compare.note")}</div>`;
}

export const actions = {
  // Restore the first variant (A) as the current result.
  chooseA: () => {
    const base = state.compareBase;
    setState({
      productId: base.productId,
      selections: base.selections,
      job: base.job,
      jobId: base.job?.job_id || null,
      breakdown: base.breakdown,
      compareBase: null,
      resultSlider: 50,
    });
    nav("result");
  },
  // B is already the live state — just drop the compare snapshot.
  chooseB: () => {
    setState({ compareBase: null, resultSlider: 50 });
    nav("result");
  },
};

export async function onEnter() {
  // B was generated without passing through the configurator, so quote it now
  // for its price. Clearing `comparing` so the next normal generation is normal.
  setState({ comparing: false });
  try {
    const breakdown = await api.quote(state.productId, selectionList(), []);
    setState({ breakdown });
  } catch {
    // Leave the price blank rather than blocking the comparison.
  }
}
