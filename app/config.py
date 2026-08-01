from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Which implementation backs each AI seam.
    ai_provider: str = "mock"  # mock | claude
    imagegen_provider: str = "mock"  # mock | provider

    anthropic_api_key: str | None = None
    openai_api_key: str | None = None

    # Image generation knobs. Quality is the cost dial: at 1024px "low" is a
    # fraction of a cent and "high" is upwards of 20 — "medium" is the preview
    # that is worth showing a customer without paying for a print master.
    # Vehicle recognition (AI_PROVIDER=openai) reuses the OpenAI key. A vision
    # chat model, NOT gpt-image-2 — that generates images, it does not read them.
    vehicle_recognition_model: str = "gpt-4o-mini"

    imagegen_model: str = "gpt-image-2"
    imagegen_quality: str = "medium"  # low | medium | high | auto
    imagegen_max_edge: int = 1024
    imagegen_timeout_seconds: float = 180.0
    # Roughly how long a real generation takes, used only to pace the progress
    # bar. Bump it toward 120 when running IMAGEGEN_QUALITY=high, which is slower.
    generation_expected_seconds: float = 25.0

    # Telegram. `require_init_data` off by default so the funnel stays walkable
    # in a plain browser, exactly like the mock AI seams; production sets it to 1
    # and /api/booking then refuses unsigned callers.
    telegram_bot_token: str | None = None
    telegram_bot_username: str = ""
    telegram_manager_chat_id: str = ""
    telegram_require_init_data: bool = False
    telegram_auth_max_age_seconds: int = 86400
    telegram_timeout_seconds: float = 15.0

    # Payments. All empty by default: the customer's chosen method is captured on
    # the order and routed to the manager, and nothing is charged online until a
    # provider is configured. Then card pay (Telegram Payments) and Uzum Nasiya
    # installments go live without a client change — see app/services/payments.py.
    telegram_payment_provider_token: str = ""  # BotFather → connect Click/Payme
    payment_currency: str = "UZS"
    uzum_merchant_id: str = ""
    uzum_api_key: str = ""

    # Analytics. Empty ADMIN_PASSWORD does not mean "open" — it means the
    # /admin route is never registered at all.
    admin_password: str = ""
    analytics_db: str = "data/analytics.db"
    analytics_enabled: bool = True
    analytics_ttl_days: int = 180

    # AI try-ons. Quotas apply to Telegram users only: a browser has no durable
    # identity, and a session-keyed quota resets with localStorage — decoration,
    # not a limit.
    app_db: str = "data/app.db"
    quota_enabled: bool = True
    free_tries_per_category: int = 3
    reservation_ttl_minutes: int = 15

    # Referrals. A bonus is paid for a completed try-on by an invited person,
    # never for a click, a bot start or a registration.
    referrals_enabled: bool = True
    referral_bonus: int = 1
    referral_monthly_limit: int = 10
    # Below this, qualification is too fast to be a real person exploring.
    referral_min_seconds: int = 60
    referral_fraud_threshold: int = 4
    # Mini-app short name from BotFather, for t.me/<bot>/<app>?startapp=…
    telegram_app_name: str = ""

    # One-time codes. A purchase both tops every category back up to full and
    # grants bonuses; a visit only grants bonuses.
    visit_bonus: int = 3
    purchase_bonus: int = 3
    referred_client_bonus: int = 5
    reward_code_valid_days: int = 30
    # Warn when a category drops to this many free tries.
    low_balance_threshold: int = 1

    # Nothing may grow without a bound.
    media_ttl_days: int = 7
    job_ttl_minutes: int = 60
    cleanup_interval_minutes: int = 60

    # The only guard on real money: each generation is ~$0.05 against gpt-image-2.
    generation_limit_per_hour: int = 20

    media_dir: str = "media"
    max_upload_mb: int = 10

    # Makes the generation mock fail deterministically, so the retry path is testable.
    generation_force_error: bool = False

    @property
    def media_path(self) -> Path:
        p = BASE_DIR / self.media_dir
        p.mkdir(parents=True, exist_ok=True)
        (p / "demo").mkdir(parents=True, exist_ok=True)
        return p

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    @property
    def analytics_db_path(self) -> Path:
        p = BASE_DIR / self.analytics_db
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def app_db_path(self) -> Path:
        p = BASE_DIR / self.app_db
        p.parent.mkdir(parents=True, exist_ok=True)
        return p


@lru_cache
def get_settings() -> Settings:
    return Settings()
