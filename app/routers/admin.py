"""The funnel page.

Server-rendered HTML, no build step — the same choice the rest of the frontend
makes. The route is only registered when ADMIN_PASSWORD is set: an empty
password must mean "no page", never "page without a password", or the shop's
numbers are public the moment it is deployed.
"""

import html
import secrets
import time

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from app.config import get_settings
from app.db import connect
from app.money import fmt
from app.services import (
    analytics,
    photos,
    quota,
    referrals,
    reward_codes,
    services_repo,
    showcase,
)
from app.services.catalog_service import get_catalog

router = APIRouter(tags=["admin"])
_basic = HTTPBasic()

# Shared by both admin pages. Plain string, not an f-string: no brace escaping
# to get wrong, and the CSS stays readable.
_STYLE = """<style>
:root{color-scheme:dark}
body{background:#0c0f14;color:#e8edf4;font:15px/1.5 system-ui,sans-serif;
     margin:0;padding:28px 20px;max-width:820px;margin-inline:auto}
h1{font-size:21px;margin:0 0 4px}
h2{font-size:15px;margin:30px 0 10px;color:#9aa7b8;font-weight:600}
.mut{color:#7c8798}
.mono{font-family:ui-monospace,Consolas,monospace}
.row{display:flex;align-items:center;flex-wrap:wrap}
.period{display:flex;gap:8px;margin:14px 0 24px;flex-wrap:wrap}
.period a{color:#9aa7b8;text-decoration:none;border:1px solid #232a34;
          border-radius:8px;padding:5px 11px;font-size:13px}
.period a.on{background:#3b82f6;border-color:#3b82f6;color:#fff}
.cards{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:8px}
.card{background:#131922;border:1px solid #232a34;border-radius:12px;
      padding:12px 14px;flex:1;min-width:130px}
.card b{display:block;font-size:22px;margin-top:2px}
.card span{font-size:12px;color:#7c8798}
.price{background:#131922;border:1px solid #232a34;border-radius:12px;padding:6px 14px}
.pl{display:flex;justify-content:space-between;padding:7px 0;font-size:14px}
.total{display:flex;justify-content:space-between;padding:10px 0 6px;
       border-top:1px solid #232a34;margin-top:4px}
.micro{font-size:12px;color:#7c8798}
.num{font-variant-numeric:tabular-nums}
table{width:100%;border-collapse:collapse}
th,td{text-align:left;padding:8px 10px;border-bottom:1px solid #1c232d;font-size:14px}
th{font-size:12px;color:#7c8798;font-weight:600}
td.n,th.n{text-align:right;white-space:nowrap}
td.drop{color:#e06666}
.barcell{width:34%}
input,select{background:#131922;border:1px solid #232a34;color:#e8edf4;
             border-radius:8px;padding:6px 10px;font-size:13px}
.btn{border:1px solid #232a34;background:#1c232d;color:#e8edf4;border-radius:8px;
     padding:6px 11px;font-size:12.5px;cursor:pointer;margin-left:6px}
.btn.ok{border-color:rgba(34,197,94,.45);color:#7ee2a0}
.btn.no{border-color:rgba(224,102,102,.45);color:#e06666}
.bar{display:block;height:8px;border-radius:4px;background:#3b82f6;min-width:2px}
@media(max-width:560px){.barcell{display:none}}
</style>"""


def _authorise(credentials: HTTPBasicCredentials = Depends(_basic)) -> None:
    expected = get_settings().admin_password
    # compare_digest, not ==: a plain comparison leaks the password's prefix
    # through response timing.
    if not expected or not secrets.compare_digest(credentials.password, expected):
        raise HTTPException(
            status_code=401,
            detail="Неверный пароль",
            headers={"WWW-Authenticate": "Basic"},
        )


def _label_for(field: str, key: str) -> str:
    """Turn a catalog id into the name the shop actually uses."""
    catalog = get_catalog()
    if field == "category_id":
        cat = catalog.category(key)
        return cat.label if cat else key
    found = catalog.find_product(key)
    return found[1].name if found else key


def _e(value: object) -> str:
    return html.escape(str(value), quote=True)


def _frozen_section() -> str:
    """Referrals held by the fraud score, and the two buttons that end that.

    Without this the frozen status was a one-way door: written by the scorer,
    read by nothing, and the bonus quietly gone.
    """
    held = referrals.list_frozen()
    if not held:
        return (
            "<h2>Замороженные бонусы</h2>"
            "<p class='mut'>Нет рефералов, ожидающих проверки.</p>"
        )

    rows = []
    for r in held:
        reasons = "; ".join(_e(x) for x in r["reasons"]) or "—"
        when = time.strftime("%d.%m %H:%M", time.localtime(r["qualified_at"] or 0))
        rows.append(f"""
        <tr>
          <td>
            <div>Пригласил: <span class="mono">{r['inviter_telegram_id']}</span></div>
            <div class="mut" style="font-size:12px">Приглашён: {r['invited_telegram_id']} · {when}</div>
          </td>
          <td class="n">{r['fraud_score']}</td>
          <td style="font-size:12.5px;color:#c8a24a">{reasons}</td>
          <td class="n">
            <form method="post" action="/admin/referrals/{r['id']}/approve" style="display:inline">
              <input type="hidden" name="note" value="проверено вручную">
              <button class="btn ok" type="submit">Подтвердить</button>
            </form>
            <form method="post" action="/admin/referrals/{r['id']}/reject" style="display:inline">
              <input type="hidden" name="note" value="отклонено вручную">
              <button class="btn no" type="submit">Отклонить</button>
            </form>
          </td>
        </tr>""")

    return f"""<h2>Замороженные бонусы</h2>
<table><thead><tr><th>Кто и кого</th><th class="n">Риск</th>
<th>Признаки</th><th class="n">Решение</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table>
<p class="mut" style="font-size:12px;margin-top:8px">
Подтверждение выплачивает бонус и не ограничивается месячным потолком —
решение принимает человек. Повторное подтверждение второй раз не платит.</p>"""


@router.post("/admin/referrals/{referral_id}/approve")
def approve_referral(
    referral_id: int, note: str = Form(default=""), _: None = Depends(_authorise)
):
    referrals.approve(referral_id, note=note)
    # See-other so a refresh does not repeat the decision.
    return RedirectResponse("/admin", status_code=303)


@router.post("/admin/referrals/{referral_id}/reject")
def reject_referral(
    referral_id: int, note: str = Form(default=""), _: None = Depends(_authorise)
):
    referrals.reject(referral_id, note=note)
    return RedirectResponse("/admin", status_code=303)


def _codes_section() -> str:
    codes = reward_codes.recent(limit=12)
    rows = "".join(
        f"<tr><td class='mono'>{_e(c['code'])}</td>"
        f"<td>{_e(c['reward_type'])}</td>"
        f"<td class='n'>+{c['bonus_amount']}{' · восстановление' if c['restores_free'] else ''}</td>"
        f"<td class='n'>{c['activation_count']}/{c['max_activations']}</td>"
        f"<td>{_e(c['status'])}</td>"
        f"<td class='n'>" + (
            f"<form method='post' action='/admin/codes/{c['id']}/cancel' style='display:inline'>"
            "<button class='btn no' type='submit'>Отменить</button></form>"
            if c["status"] == reward_codes.ACTIVE else "—"
        ) + "</td></tr>"
        for c in codes
    )

    return f"""<h2>Одноразовые коды</h2>
<form method="post" action="/admin/codes" class="row" style="gap:8px;margin-bottom:12px">
  <select name="reward_type">
    <option value="visit">Визит</option>
    <option value="purchase">Покупка (восстановит разделы)</option>
    <option value="manual">Вручную</option>
  </select>
  <input name="note" placeholder="комментарий" style="flex:1">
  <button class="btn ok" type="submit">Создать код</button>
</form>
{'<table><thead><tr><th>Код</th><th>Тип</th><th class="n">Бонус</th>'
 '<th class="n">Активаций</th><th>Статус</th><th class="n"></th></tr></thead>'
 f'<tbody>{rows}</tbody></table>' if codes else "<p class='mut'>Кодов пока нет.</p>"}"""


@router.post("/admin/codes")
def create_code(
    reward_type: str = Form(...),
    note: str = Form(default=""),
    _: None = Depends(_authorise),
):
    if reward_type not in (reward_codes.VISIT, reward_codes.PURCHASE, reward_codes.MANUAL):
        raise HTTPException(status_code=400, detail="Неизвестный тип кода")
    reward_codes.create(reward_type, note=note)
    return RedirectResponse("/admin", status_code=303)


@router.post("/admin/codes/{code_id}/cancel")
def cancel_code(code_id: int, _: None = Depends(_authorise)):
    reward_codes.cancel(code_id)
    return RedirectResponse("/admin", status_code=303)


def _services_section() -> str:
    """Paid services per category — installation, rework and the like — with the
    prices the customer is charged. This is the money the shop actually makes on
    top of the parts, so it lives where the shop can change it without a deploy."""
    catalog = get_catalog()
    grouped = services_repo.all_grouped()

    blocks = []
    for cat in catalog.categories:
        rows = ""
        for s in grouped.get(cat.id, []):
            dim = "" if s["active"] else " style='opacity:.5'"
            rows += f"""<tr{dim}>
              <td>{_e(s['name'])}</td>
              <td class='n'>{fmt(s['price'])}</td>
              <td>{'по умолчанию' if s['default_on'] else '—'}</td>
              <td>{'активна' if s['active'] else 'выключена'}</td>
              <td class='n'>
                <details><summary class='btn'>Изменить</summary>
                <form method='post' action='/admin/services/{s['id']}' class='row'
                      style='gap:6px;margin-top:6px;flex-wrap:wrap'>
                  <input name='name' value="{_e(s['name'])}" style='flex:1'>
                  <input name='name_uz' value="{_e(s['name_uz'] or '')}"
                    placeholder='ozʻbekcha (ixtiyoriy)' style='flex:1'>
                  <input name='price' type='number' value='{s['price']}' style='width:110px'>
                  <label style='font-size:12px'><input type='checkbox' name='default_on'
                    {'checked' if s['default_on'] else ''}> умолч.</label>
                  <label style='font-size:12px'><input type='checkbox' name='active'
                    {'checked' if s['active'] else ''}> активна</label>
                  <button class='btn ok' type='submit'>Сохранить</button>
                </form></details>
              </td></tr>"""
        table = (
            f"<table><thead><tr><th>Услуга</th><th class='n'>Цена</th>"
            f"<th>Предвыбор</th><th>Статус</th><th class='n'></th></tr></thead>"
            f"<tbody>{rows}</tbody></table>"
            if rows else "<p class='mut'>Услуг пока нет.</p>"
        )
        blocks.append(f"""<div style='margin-bottom:18px'>
          <div class='mono' style='color:#9aa7b8;margin-bottom:6px'>{_e(cat.label)}</div>
          {table}
          <form method='post' action='/admin/services' class='row'
                style='gap:6px;margin-top:6px;flex-wrap:wrap'>
            <input type='hidden' name='category_id' value='{_e(cat.id)}'>
            <input name='name' placeholder='Новая услуга' style='flex:1'>
            <input name='name_uz' placeholder='ozʻbekcha (ixtiyoriy)' style='flex:1'>
            <input name='price' type='number' placeholder='цена' value='0' style='width:110px'>
            <button class='btn ok' type='submit'>Добавить</button>
          </form>
        </div>""")

    return "<h2>Услуги по категориям</h2>" + "".join(blocks)


def _referral_chain_section() -> str:
    chain = referrals.chain(limit=40)
    if not chain:
        return "<h2>Реферальная цепочка</h2><p class='mut'>Пока нет приглашений.</p>"
    rows = "".join(
        f"<tr><td class='mono'>{_e(r['inviter_telegram_id'])}</td>"
        f"<td class='mono'>{_e(r['invited_telegram_id'])}</td>"
        f"<td>{_e(r['status'])}</td>"
        f"<td>{_e(r['source_type'])}</td>"
        f"<td class='n'>{'да' if r['reward_issued_at'] else '—'}</td></tr>"
        for r in chain
    )
    return f"""<h2>Реферальная цепочка</h2>
<table><thead><tr><th>Пригласил</th><th>Приглашён</th><th>Статус</th>
<th>Источник</th><th class='n'>Бонус</th></tr></thead><tbody>{rows}</tbody></table>"""


def _showcase_section() -> str:
    """Curate the public 'Реальные сборки' feed — real installs with before/after
    photos, shown to customers as social proof."""
    catalog = get_catalog()
    rows = ""
    for b in showcase.all_admin():
        dim = "" if b["active"] else " style='opacity:.5'"
        car = _e(" ".join(str(p) for p in (b["car_brand"], b["car_model"], b["car_year"]) if p))
        rows += f"""<tr{dim}>
          <td>{car}</td><td>{_e(b['title'])}</td>
          <td>{'видна' if b['active'] else 'скрыта'}</td>
          <td class='n'>
            <form method='post' action='/admin/showcase/{b['id']}/delete'
                  onsubmit="return confirm('Удалить сборку?')" style='margin:0'>
              <button class='btn' type='submit'>Удалить</button></form>
          </td></tr>"""
    table = (
        f"<table><thead><tr><th>Машина</th><th>Что сделали</th><th>Статус</th>"
        f"<th class='n'></th></tr></thead><tbody>{rows}</tbody></table>"
        if rows else "<p class='mut'>Сборок пока нет.</p>"
    )
    brand_opts = "".join(f"<option>{_e(b)}</option>" for b in catalog.car_options.brands)
    model_opts = "".join(f"<option>{_e(m)}</option>" for m in catalog.car_options.models)
    year_opts = "<option value=''>—</option>" + "".join(
        f"<option>{y}</option>" for y in catalog.car_options.years)
    cat_opts = "<option value=''>—</option>" + "".join(
        f"<option value='{_e(c.id)}'>{_e(c.label)}</option>" for c in catalog.categories)
    form = f"""<form method='post' action='/admin/showcase' enctype='multipart/form-data'
      class='row' style='gap:8px;margin-top:10px;flex-wrap:wrap;align-items:flex-end'>
      <label style='font-size:12px'>Марка<br><select name='car_brand'>{brand_opts}</select></label>
      <label style='font-size:12px'>Модель<br><select name='car_model'>{model_opts}</select></label>
      <label style='font-size:12px'>Год<br><select name='car_year'>{year_opts}</select></label>
      <label style='font-size:12px'>Раздел<br><select name='category_id'>{cat_opts}</select></label>
      <label style='font-size:12px;flex:1;min-width:150px'>Что сделали<br>
        <input name='title' placeholder='Руль Mercedes-AMG' style='width:100%'></label>
      <label style='font-size:12px'>Фото «до»<br><input type='file' name='before' accept='image/*'></label>
      <label style='font-size:12px'>Фото «после»<br><input type='file' name='after' accept='image/*'></label>
      <button class='btn ok' type='submit'>Добавить</button>
    </form>"""
    return f"<h2>Реальные сборки (лента)</h2>{table}{form}"


@router.post("/admin/services")
def create_service(
    category_id: str = Form(...),
    name: str = Form(...),
    name_uz: str = Form(default=""),
    price: int = Form(default=0),
    _: None = Depends(_authorise),
):
    try:
        services_repo.create(category_id, name, price, name_uz=name_uz)
    except services_repo.ServiceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return RedirectResponse("/admin", status_code=303)


@router.post("/admin/services/{service_id}")
def edit_service(
    service_id: int,
    name: str = Form(...),
    name_uz: str = Form(default=""),
    price: int = Form(default=0),
    default_on: bool = Form(default=False),
    active: bool = Form(default=False),
    _: None = Depends(_authorise),
):
    # Unchecked checkboxes are simply absent from a form POST, so the defaults
    # above make "unchecked" mean False rather than "unchanged".
    try:
        services_repo.update(
            service_id, name=name, price=price, default_on=default_on,
            active=active, name_uz=name_uz,
        )
    except services_repo.ServiceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return RedirectResponse("/admin", status_code=303)


@router.post("/admin/showcase")
async def create_showcase(
    car_brand: str = Form(...),
    car_model: str = Form(...),
    car_year: str = Form(default=""),
    category_id: str = Form(default=""),
    title: str = Form(...),
    before: UploadFile = File(...),
    after: UploadFile = File(...),
    _: None = Depends(_authorise),
):
    try:
        before_saved = photos.save_upload(await before.read(), before.content_type or "")
        after_saved = photos.save_upload(await after.read(), after.content_type or "")
    except photos.PhotoError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    year = int(car_year) if car_year.strip().isdigit() else None
    try:
        showcase.create(
            car_brand=car_brand, car_model=car_model, car_year=year,
            category_id=category_id or None, title=title,
            before_photo_id=before_saved["photo_id"],
            after_photo_id=after_saved["photo_id"],
        )
    except showcase.ShowcaseError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return RedirectResponse("/admin", status_code=303)


@router.post("/admin/showcase/{build_id}/delete")
def delete_showcase(build_id: int, _: None = Depends(_authorise)):
    showcase.delete(build_id)
    return RedirectResponse("/admin", status_code=303)


@router.post("/admin/users/{telegram_id}/grant")
def manual_grant(
    telegram_id: int,
    amount: int = Form(...),
    note: str = Form(...),
    _: None = Depends(_authorise),
):
    """Manual adjustment. The comment is required, not optional: an unexplained
    balance change is indistinguishable from a bug six months later."""
    if not note.strip():
        raise HTTPException(status_code=400, detail="Комментарий обязателен")
    with connect() as conn:
        row = conn.execute(
            "SELECT id FROM users WHERE telegram_id=?", (telegram_id,)
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    quota.grant(row["id"], amount, f"manual:{note.strip()}")
    return RedirectResponse(f"/admin/users/{telegram_id}", status_code=303)


@router.get("/admin/users/{telegram_id}", response_class=HTMLResponse)
def user_page(telegram_id: int, _: None = Depends(_authorise)) -> HTMLResponse:
    """One customer: balances and every movement behind them."""
    with connect() as conn:
        user = conn.execute(
            "SELECT * FROM users WHERE telegram_id=?", (telegram_id,)
        ).fetchone()
    if user is None:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    snap = quota.snapshot(user["id"])
    cats = "".join(
        f"<div class='pl'><span>{_e(c)}</span>"
        f"<span class='num'>{v['free_remaining']} из {v['free_limit']}</span></div>"
        for c, v in snap["categories"].items()
    ) or "<div class='pl'><span>Разделы не использовались</span><span>—</span></div>"

    history = "".join(
        f"<tr><td>{_e(h['transaction_type'])}</td><td>{_e(h['balance_type'] or '')}</td>"
        f"<td class='n'>{h['amount']:+d}</td><td>{_e(h['category_id'] or '')}</td>"
        f"<td>{_e(h['source'] or '')}</td>"
        f"<td class='n'>{time.strftime('%d.%m %H:%M', time.localtime(h['created_at']))}</td></tr>"
        for h in quota.history(user["id"], limit=40)
    )

    return HTMLResponse(f"""<!doctype html><html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Пользователь {telegram_id}</title>{_STYLE}</head><body>
<h1>Пользователь {telegram_id}</h1>
<div class="mut">код {_e(user['ref_code'])} ·
  {_e(' '.join(str(x) for x in (user['car_brand'], user['car_model'], user['car_year']) if x) or 'автомобиль не подтверждён')}</div>
<p><a href="/admin" style="color:#3b82f6">← к воронке</a></p>

<h2>Баланс</h2>
<div class="price">{cats}
  <div class="total"><span class="micro">Бонусные примерки</span>
    <span class="num">{snap['bonus_remaining']}</span></div></div>

<h2>Ручная корректировка</h2>
<form method="post" action="/admin/users/{telegram_id}/grant" class="row" style="gap:8px">
  <input name="amount" type="number" value="1" style="width:80px">
  <input name="note" placeholder="причина (обязательно)" required style="flex:1">
  <button class="btn ok" type="submit">Применить</button>
</form>

<h2>История</h2>
<table><thead><tr><th>Операция</th><th>Баланс</th><th class="n">Кол-во</th>
<th>Раздел</th><th>Источник</th><th class="n">Когда</th></tr></thead>
<tbody>{history}</tbody></table>
</body></html>""")


@router.get("/admin", response_class=HTMLResponse)
def funnel_page(
    days: int = Query(default=7, ge=1, le=365),
    _: None = Depends(_authorise),
) -> HTMLResponse:
    steps = analytics.funnel(days)
    stats = analytics.totals(days)

    rows = []
    for step in steps:
        conv = "—" if step["conversion"] is None else f"{step['conversion']}%"
        drop = "—" if step["dropped"] is None else f"−{step['dropped']}"
        width = 0
        if steps[0]["sessions"]:
            width = round(step["sessions"] / steps[0]["sessions"] * 100)
        rows.append(
            f"<tr><td>{_e(step['label'])}</td>"
            f"<td class='n'>{step['sessions']}</td>"
            f"<td class='n'>{conv}</td><td class='n drop'>{drop}</td>"
            f"<td class='barcell'><span class='bar' style='width:{width}%'></span></td></tr>"
        )

    def top_table(field: str, title: str) -> str:
        items = analytics.top(field, days)
        if not items:
            return f"<h2>{_e(title)}</h2><p class='mut'>Пока нет данных.</p>"
        body = "".join(
            f"<tr><td>{_e(_label_for(field, i['key']))}</td>"
            f"<td class='n'>{i['sessions']}</td></tr>"
            for i in items
        )
        return (
            f"<h2>{_e(title)}</h2><table><thead><tr><th>Название</th>"
            f"<th class='n'>Сессий</th></tr></thead><tbody>{body}</tbody></table>"
        )

    frozen_section = _frozen_section()

    period = "".join(
        "<a href='/admin?days={d}' class='{cls}'>{d} дн.</a>".format(
            d=d, cls="on" if d == days else ""
        )
        for d in (1, 7, 30, 90)
    )

    return HTMLResponse(f"""<!doctype html>
<html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Воронка · MyCar Vision AI</title>
{_STYLE}</head><body>
<h1>Воронка</h1>
<div class="mut">MyCar Vision AI · последние {days} дн.</div>
<div class="period">{period}</div>

<div class="cards">
  <div class="card"><span>Сессий</span><b>{stats['sessions']}</b></div>
  <div class="card"><span>Генераций</span><b>{stats['generations']}</b></div>
  <div class="card"><span>Ошибок генерации</span><b>{stats['failure_rate']}%</b></div>
  <div class="card"><span>Заявок</span><b>{stats['bookings']}</b></div>
</div>

<h2>Шаги</h2>
<table><thead><tr><th>Шаг</th><th class="n">Сессий</th>
<th class="n">Конверсия</th><th class="n">Отвал</th><th class="barcell"></th></tr></thead>
<tbody>{''.join(rows)}</tbody></table>

{_services_section()}

{_showcase_section()}

{_codes_section()}

{frozen_section}

{_referral_chain_section()}

{top_table("category_id", "Популярные разделы")}
{top_table("product_id", "Популярные товары")}

<p class="mut" style="margin-top:28px;font-size:12px">
Конверсия считается к предыдущему шагу, по уникальным сессиям.
Контакты клиентов здесь не хранятся — они только в чате менеджера.</p>
</body></html>""")
