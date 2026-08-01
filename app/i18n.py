"""Server-side translations for the strings that reach a customer: booking and
generation errors, and the bot notifications.

The admin page, the manager's booking message and internal prompts stay Russian.
"""

LANGS = ("ru", "uz")


def lang_of(x_lang: str | None) -> str:
    """Normalise an X-Lang header (or Telegram language_code) to ru/uz."""
    return "uz" if (x_lang or "ru").lower().startswith("uz") else "ru"


MESSAGES = {
    "ru": {
        "err.cart_empty": "Корзина пуста",
        "err.need_phone": "Укажите номер телефона",
        "err.booking_failed": "Не удалось отправить заявку. Попробуйте ещё раз.",
        "err.rate_limited": "Слишком много генераций за час. Попробуйте позже.",
        "err.quota_exhausted": "Примерки в этой категории закончились.",
        "err.no_telegram": "Откройте приложение в Telegram.",
        "err.bad_init_data": "Не удалось подтвердить вход через Telegram.",
        "err.job_not_found": "Задача не найдена",
        "err.result_not_found": "Результат не найден",
        "err.write_denied": "Разрешите боту писать вам, чтобы получить изображение.",
        "err.image_failed": "Не удалось отправить изображение.",
        "err.code_not_found": "Код не найден",
        "err.code_used": "Код уже использован",
        "err.code_expired": "Срок действия кода истёк",
        "err.code_wrong_user": "Этот код предназначен для другого пользователя",
        "err.code_generic": "Не удалось активировать код. Попробуйте позже",
        # code activation (reward_codes surfaces these; ru originals kept there)
        "notif.referral": "Ваш друг создал первую AI-примерку. Вам начислено: {tries}.",
        "notif.referred_client": "Приглашённый вами клиент оформил установку. Вам начислено: {tries}.",
        "notif.code_visit": "Код активирован: начислили {tries}.",
        "notif.code_restore": "Код активирован: мы восстановили бесплатные примерки во всех разделах",
        "notif.code_both": "Код активирован: мы восстановили бесплатные примерки во всех разделах и начислили {tries}.",
        "notif.low_balance": "Осталась {tries} в разделе «{cat}».",
        "notif.cat_exhausted_bonus": "Бесплатные примерки в разделе «{cat}» закончились. У вас есть {tries} бонусных.",
        "notif.cat_exhausted_none": "Бесплатные примерки в разделе «{cat}» закончились. Пригласите друга, чтобы получить бонусные примерки.",
        "notif.referral_frozen": "Бонус за приглашённого друга временно на проверке. Мы сообщим, когда она завершится.",
        # share card + caption sent into the customer's own Telegram chat
        "share.cta": "Попробуй собрать свою машину:",
        "share.for": "для {car}",
        "share.currency": "сум",
        "share.product_fallback": "Визуализация",
        "share.card_fallback": "AI-визуализация",
        "tries.one": "{n} примерка",
        "tries.few": "{n} примерки",
        "tries.many": "{n} примерок",
    },
    "uz": {
        "err.cart_empty": "Savat boʻsh",
        "err.need_phone": "Telefon raqamini kiriting",
        "err.booking_failed": "Arizani yuborib boʻlmadi. Qayta urinib koʻring.",
        "err.rate_limited": "Bir soatda juda koʻp primerka. Keyinroq urinib koʻring.",
        "err.quota_exhausted": "Bu boʻlimda primerkalar tugadi.",
        "err.no_telegram": "Ilovani Telegramda oching.",
        "err.bad_init_data": "Telegram orqali kirishni tasdiqlab boʻlmadi.",
        "err.job_not_found": "Vazifa topilmadi",
        "err.result_not_found": "Natija topilmadi",
        "err.write_denied": "Rasmni olish uchun botga sizga yozishga ruxsat bering.",
        "err.image_failed": "Rasmni yuborib boʻlmadi.",
        "err.code_not_found": "Kod topilmadi",
        "err.code_used": "Kod allaqachon ishlatilgan",
        "err.code_expired": "Kod muddati tugagan",
        "err.code_wrong_user": "Bu kod boshqa foydalanuvchi uchun",
        "err.code_generic": "Kodni faollashtirib boʻlmadi. Keyinroq urinib koʻring",
        "notif.referral": "Doʻstingiz birinchi AI-primerkasini yaratdi. Sizga berildi: {tries}.",
        "notif.referred_client": "Siz taklif qilgan mijoz oʻrnatishni rasmiylashtirdi. Sizga berildi: {tries}.",
        "notif.code_visit": "Kod faollashtirildi: {tries} berildi.",
        "notif.code_restore": "Kod faollashtirildi: barcha boʻlimlarda bepul primerkalar tiklandi",
        "notif.code_both": "Kod faollashtirildi: barcha boʻlimlarda bepul primerkalar tiklandi va {tries} berildi.",
        "notif.low_balance": "«{cat}» boʻlimida {tries} qoldi.",
        "notif.cat_exhausted_bonus": "«{cat}» boʻlimida bepul primerkalar tugadi. Sizda {tries} bonus bor.",
        "notif.cat_exhausted_none": "«{cat}» boʻlimida bepul primerkalar tugadi. Bonus primerka olish uchun doʻstingizni taklif qiling.",
        "notif.referral_frozen": "Taklif qilingan doʻst uchun bonus vaqtincha tekshiruvda. Yakunlangach xabar beramiz.",
        "share.cta": "Oʻz mashinangni yigʻib koʻr:",
        "share.for": "{car} uchun",
        "share.currency": "soʻm",
        "share.product_fallback": "Vizualizatsiya",
        "share.card_fallback": "AI-vizualizatsiya",
        "tries.one": "{n} primerka",
        "tries.few": "{n} ta primerka",
        "tries.many": "{n} ta primerka",
    },
}


def t(key: str, lang: str = "ru", **params) -> str:
    table = MESSAGES.get(lang, MESSAGES["ru"])
    text = table.get(key) or MESSAGES["ru"].get(key) or key
    for k, v in params.items():
        text = text.replace(f"{{{k}}}", str(v))
    return text


def tries(n: int, lang: str = "ru") -> str:
    """Localized 'N try-ons'. Russian pluralises; Uzbek keeps a counter form."""
    if lang == "ru":
        if n % 10 == 1 and n % 100 != 11:
            key = "tries.one"
        elif n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14):
            key = "tries.few"
        else:
            key = "tries.many"
    else:
        key = "tries.one" if n == 1 else "tries.few"
    return t(key, lang, n=n)
