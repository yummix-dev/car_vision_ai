"""Test-wide isolation from the developer's local .env.

`get_settings()` reads .env, so without this the suite's behaviour depends on
whatever happens to be configured on the machine running it. That is not a
hypothetical: flipping TELEGRAM_REQUIRE_INIT_DATA=1 for a live run turned ten
tests red, and a real TELEGRAM_BOT_TOKEN plus a real manager chat id would let
a test message an actual person.

Individual tests still override these with monkeypatch where they need to —
this only fixes the starting point.
"""

import pytest

from app.config import get_settings

# Obviously fake, and shaped like a real token so signature helpers work.
TEST_BOT_TOKEN = "123456:TEST-TOKEN"


@pytest.fixture(autouse=True)
def isolated_settings(monkeypatch):
    settings = get_settings()

    # Nothing may reach the real Telegram: no manager chat means delivery is
    # "not configured" rather than "sent to a live human".
    monkeypatch.setattr(settings, "telegram_bot_token", TEST_BOT_TOKEN)
    monkeypatch.setattr(settings, "telegram_manager_chat_id", "")
    monkeypatch.setattr(settings, "telegram_require_init_data", False)
    monkeypatch.setattr(settings, "telegram_bot_username", "Test_Umid_bot")
    monkeypatch.setattr(settings, "telegram_app_name", "")

    # Feature flags at their documented defaults, whatever .env says.
    monkeypatch.setattr(settings, "quota_enabled", True)
    monkeypatch.setattr(settings, "referrals_enabled", True)
    monkeypatch.setattr(settings, "analytics_enabled", True)
    monkeypatch.setattr(settings, "free_tries_per_category", 3)

    # The admin page is unregistered by default; tests that want it set it.
    monkeypatch.setattr(settings, "admin_password", "")

    # A real key here would mean tests could spend money.
    monkeypatch.setattr(settings, "openai_api_key", None)
    monkeypatch.setattr(settings, "ai_provider", "mock")
    monkeypatch.setattr(settings, "imagegen_provider", "mock")
    monkeypatch.setattr(settings, "generation_force_error", False)

    yield
