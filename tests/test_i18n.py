"""Localization: the catalog, services, error strings and stored user language.

The client sends X-Lang; the server answers in that language and remembers it for
out-of-request notifications. Uzbek falls back to Russian wherever a translation
is missing, so a half-translated catalog is never a broken one.
"""

import re

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.db import connect, reset_for_tests
from app.i18n import lang_of, t, tries
from app.models.telegram import TelegramUser
from app.server import create_app
from app.services import services_repo, users

CYRILLIC = re.compile("[А-Яа-яЁё]")


@pytest.fixture(autouse=True)
def app_db(tmp_path, monkeypatch):
    monkeypatch.setattr(get_settings(), "app_db", str(tmp_path / "app.db"))
    reset_for_tests()
    yield


# ── lang_of ───────────────────────────────────────────────────


def test_lang_of_normalises_header():
    assert lang_of("uz") == "uz"
    assert lang_of("uz-UZ") == "uz"
    assert lang_of("ru") == "ru"
    assert lang_of(None) == "ru"
    assert lang_of("en") == "ru"  # anything unknown → Russian


# ── the catalog ───────────────────────────────────────────────


def test_catalog_default_is_russian():
    client = TestClient(create_app())
    cats = client.get("/api/catalog").json()["categories"]
    rul = next(c for c in cats if c["id"] == "rul")
    assert rul["label"] == "Руль"


def test_catalog_uz_translates_labels_options_and_steps():
    client = TestClient(create_app())
    cats = client.get("/api/catalog", headers={"X-Lang": "uz"}).json()["categories"]
    rul = next(c for c in cats if c["id"] == "rul")

    assert rul["label"] == "Rul"
    assert rul["gen_steps"][0] == "Eski rul holatini aniqlaymiz"
    leather = next(g for g in rul["option_groups"] if g["id"] == "leather")
    assert leather["label"] == "Teri rangi"
    assert leather["choices"][0]["label"] == "Qora"


def test_catalog_uz_leaves_product_names_and_translates_material_tags():
    client = TestClient(create_app())
    cats = client.get("/api/catalog", headers={"X-Lang": "uz"}).json()["categories"]
    rul = next(c for c in cats if c["id"] == "rul")
    amg = next(p for p in rul["products"] if p["id"] == "amg")

    assert amg["name"] == "Mercedes-AMG Performance"  # brand, untranslated
    assert amg["material"] == "Teri + perforatsiya"
    assert amg["tags"] == ["AMG", "LED", "Kurakchalar"]  # AMG/LED pass through, Лепестки→Kurakchalar


def test_catalog_uz_has_no_cyrillic_in_rendered_fields():
    """Every field the client renders must be Cyrillic-free under uz.

    noun/acc are Russian grammar helpers the client never renders, so they are
    excluded — see app/models/catalog.py.
    """
    client = TestClient(create_app())
    cats = client.get("/api/catalog", headers={"X-Lang": "uz"}).json()["categories"]

    leaks = []

    def walk(node, path=""):
        if isinstance(node, dict):
            for k, v in node.items():
                if k in ("noun", "acc"):
                    continue
                walk(v, f"{path}/{k}")
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, f"{path}[{i}]")
        elif isinstance(node, str) and CYRILLIC.search(node):
            leaks.append((path, node))

    walk(cats)
    assert leaks == [], f"untranslated Cyrillic in uz catalog: {leaks}"


# ── services ──────────────────────────────────────────────────


def test_services_endpoint_uses_name_uz_when_present():
    services_repo.create("rul", "Установка руля", 500_000, name_uz="Rul oʻrnatish")
    client = TestClient(create_app())

    ru = client.get("/api/catalog/rul/services").json()
    uz = client.get("/api/catalog/rul/services", headers={"X-Lang": "uz"}).json()

    assert any(s["name"] == "Установка руля" for s in ru)
    assert any(s["name"] == "Rul oʻrnatish" for s in uz)


def test_services_endpoint_falls_back_to_russian_name():
    services_repo.create("rul", "Перепайка", 150_000)  # no name_uz
    client = TestClient(create_app())
    uz = client.get("/api/catalog/rul/services", headers={"X-Lang": "uz"}).json()
    assert any(s["name"] == "Перепайка" for s in uz), "missing name_uz falls back to ru"


# ── error strings ─────────────────────────────────────────────


def test_booking_error_is_localized(monkeypatch):
    monkeypatch.setattr(get_settings(), "telegram_bot_token", "")
    client = TestClient(create_app())

    ru = client.post("/api/booking", json={"cart": [], "contact": {"phone": "x"}})
    uz = client.post(
        "/api/booking",
        json={"cart": [], "contact": {"phone": "x"}},
        headers={"X-Lang": "uz"},
    )
    assert ru.json()["detail"] == "Корзина пуста"
    assert uz.json()["detail"] == "Savat boʻsh"


# ── stored user language ──────────────────────────────────────


def test_user_language_is_stored_and_updated():
    tg = TelegramUser(id=42, first_name="Test")
    user = users.get_or_create(tg, lang="uz")
    assert user["lang"] == "uz"

    # A later request in another language updates the stored preference.
    user = users.get_or_create(tg, lang="ru")
    assert user["lang"] == "ru"

    with connect() as conn:
        row = conn.execute("SELECT lang FROM users WHERE telegram_id=42").fetchone()
    assert row["lang"] == "ru"


def test_user_language_defaults_to_russian():
    tg = TelegramUser(id=7, first_name="Nolang")
    user = users.get_or_create(tg)  # no lang given
    assert user["lang"] == "ru"


# ── pluralisation helper ──────────────────────────────────────


def test_tries_pluralisation():
    assert tries(1, "ru") == "1 примерка"
    assert tries(2, "ru") == "2 примерки"
    assert tries(5, "ru") == "5 примерок"
    assert tries(1, "uz") == "1 primerka"
    assert tries(5, "uz") == "5 ta primerka"


def test_t_falls_back_to_russian_for_unknown_lang():
    assert t("err.cart_empty", "en") == "Корзина пуста"
