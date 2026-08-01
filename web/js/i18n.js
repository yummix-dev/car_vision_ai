// Client-side translations. Every user-facing string lives here keyed; screens
// call t("key"). Uzbek is Latin script (Oʻzbek lotin).
//
// NOTE: the Uzbek strings were produced by a non-native translator and should be
// proof-read before launch. Anything still reading in Russian under `uz` is a
// missing key — the leak test in scratchpad catches those.

const STORE_KEY = "mcv_lang";

export const LANGS = ["ru", "uz"];

const MESSAGES = {
  ru: {
    // The language screen (screens/lang.js) is inherently bilingual, so it
    // hardcodes its own title and buttons in both scripts rather than via t().

    // ── flow (intro) ──
    "flow.eyebrow": "Как это работает",
    "flow.title": "Путь от фото до апгрейда",
    "flow.lede": "Восемь шагов — от снимка салона до заявки на установку.",
    "flow.note": "Каждую зону автомобиля фотографируйте отдельно — так AI точнее определит перспективу.",
    "flow.start": "Начать примерку",
    "flow.s1.t": "Выберите раздел",
    "flow.s1.d": "Руль, магнитола, бампер, камера или парктроники.",
    "flow.s2.t": "Сфотографируйте зону",
    "flow.s2.d": "Камера, галерея или демонстрационное фото.",
    "flow.s3.t": "AI определяет автомобиль",
    "flow.s3.d": "Марка, модель и год — с возможностью поправить.",
    "flow.s4.t": "Подбираем совместимые товары",
    "flow.s4.d": "Только то, что подходит вашей машине.",
    "flow.s5.t": "Настройте товар",
    "flow.s5.d": "Размер, покраска и доп-опции — там, где они есть.",
    "flow.s6.t": "AI создаёт визуализацию",
    "flow.s6.d": "Меняем только выбранную зону на вашем фото.",
    "flow.s7.t": "Сравните до и после",
    "flow.s7.d": "Ползунок показывает результат на вашей машине.",
    "flow.s8.t": "Оформите заявку",
    "flow.s8.d": "Менеджер подтвердит совместимость и время установки.",

    // ── home ──
    "home.title": "Примерь апгрейд на свою машину",
    "home.lede": "Загрузи фото салона, выбери руль, магнитолу или другой апгрейд и посмотри результат до установки.",
    "home.slider_hint": "Потяни ползунок «До / После»",
    "home.adv1": "Примерка на вашей собственной фотографии",
    "home.adv2": "Совместимость подбирается под вашу машину",
    "home.adv3": "Установка включена в стоимость",
    "home.cap_before": "[ салон · штатный руль ]",
    "home.cap_after": "[ салон · новый руль ]",
    "home.cta_pick": "Выбрать, что примерить",
    "home.cta_example": "Посмотреть пример",
    "home.gallery": "Мои примерки",
    "home.showcase": "Реальные сборки",

    // ── example ──
    "example.eyebrow": "Пример",
    "example.title": "Mercedes-AMG Performance на Chevrolet Malibu",
    "example.cap_before": "[ исходное фото ]",
    "example.cap_after": "[ AI-результат ]",
    "example.for": "Кожа + перфорация · для Chevrolet Malibu",
    "example.tag_carbon": "Карбон",
    "example.tag_led": "LED",
    "example.tag_paddles": "Лепестки",
    "example.install": "Установка",
    "example.install_incl": "включена",
    "example.total": "Итого",
    "example.note": "AI-визуализация является предварительной. Итоговый вид может немного отличаться из-за освещения, ракурса и особенностей автомобиля.",
    "example.cta": "Загрузить своё фото",

    // ── pick ──
    "pick.title": "Что примеряем?",
    "pick.lede": "Выберите зону автомобиля — для каждой нужна своя фотография.",
    "pick.note": "Один раздел за раз. После примерки можно вернуться и добавить ещё товар в сборку.",

    // ── upload ──
    "upload.subtitle": "Так AI точнее определит положение и перспективу.",
    "upload.in_frame": "в кадре",
    "upload.replace": "Заменить",
    "upload.rotate": "Повернуть",
    "upload.rotating": "Поворачиваем…",
    "upload.src_camera": "Сделать фотографию",
    "upload.src_gallery": "Выбрать из галереи",
    "upload.src_demo": "Демонстрационное фото",
    "upload.tips_title": "Рекомендации к фото",
    "upload.tip1": "Нужная зона должна полностью попадать в кадр",
    "upload.tip2": "Держите телефон ровно",
    "upload.tip3": "Используйте хорошее освещение",
    "upload.tip4": "Не закрывайте объект руками",
    "upload.continue": "Продолжить",

    // ── car ──
    "car.analyzing_title": "Определяем автомобиль",
    "car.analyzing_sub": "Анализируем фотографию…",
    "car.confirm_title": "Уточните автомобиль",
    "car.confirm_sub": "Выберите марку, модель и год — подберём совместимые товары.",
    "car.brand": "Марка",
    "car.model": "Модель",
    "car.year": "Год выпуска",
    "car.edit": "Изменить",
    "car.likely": "Похоже, это",
    "car.compatible_found": "Совместимые товары найдены",
    "car.wrong_hint": "Если модель определена неверно — поправьте вручную, каталог обновится.",
    "car.accept": "Всё верно",
    "car.confirm": "Подтвердить автомобиль",

    // ── catalog ──
    "catalog.change_section": "Сменить раздел",
    "catalog.configure": "Примерить",
    "catalog.in_stock": "В наличии",
    "catalog.on_order": "Под заказ",
    "catalog.filter_pop": "Популярные",
    "catalog.filter_price": "По цене",
    "catalog.filter_carbon": "Карбон",
    "catalog.filter_led": "LED",
    "catalog.filter_paddles": "Лепестки",
    "catalog.no_section": "Раздел не выбран.",
    "catalog.empty_filter": "В этом фильтре пока нет товаров.",

    // ── config ──
    "config.no_product": "Товар не выбран.",
    "config.for": "для",
    "config.services": "Услуги",
    "config.free": "бесплатно",
    "config.cta_generate": "Примерить на моей машине",
    "config.cta_another": "Выбрать другой товар",
    "config.suffix_left": " · осталось {n}",
    "config.suffix_bonus": " · бонусных {n}",

    // ── generating ──
    "gen.error_title": "Не удалось точно распознать фото",
    "gen.error_sub": "Попробуйте загрузить фотографию, где нужная зона полностью видна и хорошо освещена.",
    "gen.title": "Создаём визуализацию",
    "gen.progress": "Прогресс",
    "gen.retry": "Загрузить другое фото",

    // ── result ──
    "result.before": "До",
    "result.after": "После",
    "result.another": "Другой товар",
    "result.edit": "Изменить",
    "result.save": "Сохранить",
    "result.saved": "Сохранено",
    "result.share": "Поделиться",
    "result.sharing": "Отправляем…",
    "result.shared": "Отправлено",
    "result.cap_before": "[ фото пользователя ]",
    "result.cap_after": "[ AI-результат ]",
    "result.add_to_cart": "Добавить в корзину",
    "result.note": "AI-визуализация является предварительной. Итоговый вид может немного отличаться из-за освещения, ракурса и особенностей автомобиля.",
    "result.share_denied": "Без разрешения бот не сможет прислать изображение.",
    "result.compare": "Сравнить",

    // ── compare (side-by-side) ──
    "compare.title": "Сравнение",
    "compare.lede": "Оба варианта на вашей машине — выбирайте, что нравится.",
    "compare.pick_title": "С чем сравнить?",
    "compare.pick_sub": "Второй товар примерим на том же фото.",
    "compare.cancel": "Отмена",
    "compare.a": "Вариант A",
    "compare.b": "Вариант B",
    "compare.choose": "Выбрать этот",
    "compare.note": "Сравнение предварительное. Итоговый вид может немного отличаться.",
    "compare.none": "Нет данных для сравнения.",

    // ── gallery ("Мои примерки") ──
    "gallery.title": "Мои примерки",
    "gallery.empty": "Здесь появятся ваши AI-примерки. Загрузите фото и примерьте товар.",
    "gallery.empty_cta": "Примерить товар",
    "gallery.delete": "Удалить",
    "gallery.confirm_delete": "Удалить эту примерку?",
    "gallery.load_error": "Не удалось загрузить примерки.",

    // ── showcase ("Реальные сборки") ──
    "showcase.title": "Реальные сборки",
    "showcase.lede": "Настоящие установки на такие же машины, как ваша.",
    "showcase.all": "Все",
    "showcase.try": "Примерить как здесь",
    "showcase.empty": "Здесь появятся реальные работы магазина.",
    "showcase.load_error": "Не удалось загрузить сборки.",

    // ── cart ──
    "cart.title": "Ваша сборка",
    "cart.empty": "Корзина пуста. Выберите раздел и примерьте товар.",
    "cart.add_first": "Добавить товар",
    "cart.positions_for": "{n} поз. для {car}",
    "cart.price": "Стоимость",
    "cart.add_more": "Добавить ещё товар",
    "cart.positions": "Позиций",
    "cart.total": "Итого",
    "cart.checkout": "Оформить заявку",

    // ── request ──
    "request.title": "Заявка на установку",
    "request.lede": "Менеджер свяжется с вами, подтвердит совместимость, стоимость и удобное время установки.",
    "request.car": "Автомобиль",
    "request.positions": "Позиций",
    "request.total": "Итого",
    "request.f_name": "Имя",
    "request.f_name_ph": "Как к вам обращаться",
    "request.f_phone": "Номер телефона",
    "request.f_tg": "Telegram",
    "request.f_date": "Желаемая дата",
    "request.f_date_ph": "например, 24 июля",
    "request.f_comment": "Комментарий",
    "request.f_comment_ph": "Пожелания к установке",
    "request.prefill": "Имя и Telegram подставлены из вашего профиля — их можно изменить.",
    "request.prefill_hint": "Откройте приложение в Telegram, чтобы имя и контакт подставились автоматически.",
    "request.submit": "Отправить заявку",
    "request.need_phone": "Укажите номер телефона",

    // ── success ──
    "success.title": "Заявка отправлена",
    "success.sub": "Менеджер свяжется с вами, подтвердит совместимость, стоимость и удобное время установки.",
    "success.car": "Автомобиль",
    "success.positions": "Позиций",
    "success.total": "Итого",
    "success.booking_no": "заявка №",
    "success.manager": "Написать менеджеру",
    "success.home": "На главную",

    // ── referral ──
    "ref.title": "Получайте примерки за друзей",
    "ref.lede": "Поделитесь своей ссылкой. Когда новый пользователь создаст первую AI-примерку, вы получите одну бонусную примерку.",
    "ref.unavailable": "Персональная ссылка доступна в Telegram — откройте приложение через бота.",
    "ref.invited": "Приглашено",
    "ref.qualified": "Создали примерку",
    "ref.earned": "Получено бонусов",
    "ref.monthly": "Доступно в этом месяце",
    "ref.your_link": "Ваша ссылка",
    "ref.copied": "Ссылка скопирована",
    "ref.note": "Бонус начисляется только за первую успешную примерку приглашённого. За переход по ссылке или установку бонус не начисляется.",
    "ref.invite": "Пригласить друзей",
    "ref.copy": "Скопировать ссылку",
    "ref.back": "Назад",
    "ref.share_text": "Собери свою машину — примерь тюнинг на своём фото.",
    "ref.invited_note": "Вы пришли по приглашению. Создайте свою первую примерку, чтобы друг получил бонус.",

    // ── quota / balance ──
    "quota.left_of": "Осталось {n} из {max} примерок",
    "quota.free_out": "Бесплатные примерки закончились",
    "quota.cat_out": "Примерки в этой категории закончились",
    "quota.bonus": "Бонусные: {n}",
    "quota.title": "AI-примерки",
    "quota.by_section": "Бесплатные примерки считаются отдельно для каждого раздела.",
    "quota.bonus_tries": "Бонусные примерки",
    "quota.recent": "Последние операции",
    "quota.ok": "Понятно",
    "quota.get_more": "Получить примерки",
    "quota.op_spend": "Примерка",
    "quota.op_refund": "Возврат за неудачную примерку",
    "quota.op_grant": "Начислены бонусные примерки",
    "quota.exhausted_title": "Примерки закончились",
    "quota.exhausted_body": "Вы использовали все бесплатные примерки в этом разделе. Каталог, сохранённые результаты и заявка на установку остаются доступны.",
    "quota.invite_friends": "Пригласить друзей",
    "quota.activate_code": "Активировать код",
    "quota.back_to_catalog": "Вернуться к каталогу",
    "quota.code_activated": "Код активирован",
    "quota.code_title": "Активировать бонус",
    "quota.code_body": "Код выдаётся после визита в мастерскую или установки. Введите его, чтобы получить примерки.",
    "quota.code_ph": "Например, K7QX2M4P",
    "quota.code_checking": "Проверяем…",
    "quota.code_activate": "Активировать",
    "quota.code_scan": "Сканировать QR-код",
    "quota.code_cancel": "Отмена",
    "quota.code_great": "Отлично",
    "quota.reward_restored": "бесплатные примерки восстановлены во всех разделах",
    "quota.reward_bonus": "начислено бонусных примерок: {n}",
    "quota.reward_applied": "Бонус применён.",
    "quota.bonus_confirm_title": "Использовать бонусную примерку?",
    "quota.bonus_confirm_body": "Бесплатные примерки в этом разделе закончились. Будет использована 1 бонусная примерка. Осталось: {n}.",
    "quota.bonus_continue": "Продолжить",
    "quota.bonus_cancel": "Отмена",
    "quota.scan_hint": "Наведите на QR-код",

    // ── shared ui ──
    "ui.app_sub": "мини-приложение",
    "ui.step_section": "Раздел",
    "ui.step_photo": "Фото",
    "ui.step_car": "Авто",
    "ui.step_choice": "Выбор",
    "ui.currency": "сум",
    "ui.catalog_error": "Не удалось загрузить каталог: {msg}",
  },

  uz: {

    "flow.eyebrow": "Bu qanday ishlaydi",
    "flow.title": "Suratdan apgreydgacha yoʻl",
    "flow.lede": "Sakkiz qadam — salon suratidan oʻrnatish arizasigacha.",
    "flow.note": "Avtomobilning har bir qismini alohida suratga oling — shunda AI istiqbolni aniqroq belgilaydi.",
    "flow.start": "Primerkani boshlash",
    "flow.s1.t": "Boʻlimni tanlang",
    "flow.s1.d": "Rul, magnitola, bamper, kamera yoki parktronik.",
    "flow.s2.t": "Qismni suratga oling",
    "flow.s2.d": "Kamera, galereya yoki namunaviy surat.",
    "flow.s3.t": "AI avtomobilni aniqlaydi",
    "flow.s3.d": "Marka, model va yil — tuzatish imkoni bilan.",
    "flow.s4.t": "Mos mahsulotlarni tanlaymiz",
    "flow.s4.d": "Faqat mashinangizga mos keladiganlar.",
    "flow.s5.t": "Mahsulotni sozlang",
    "flow.s5.d": "Oʻlcham, boʻyash va qoʻshimcha optsiyalar — bor joyda.",
    "flow.s6.t": "AI vizualizatsiya yaratadi",
    "flow.s6.d": "Suratingizda faqat tanlangan qismni oʻzgartiramiz.",
    "flow.s7.t": "Avval va keyinni solishtiring",
    "flow.s7.d": "Slayder mashinangizdagi natijani koʻrsatadi.",
    "flow.s8.t": "Ariza qoldiring",
    "flow.s8.d": "Menejer moslik va oʻrnatish vaqtini tasdiqlaydi.",

    "home.title": "Apgreydni oʻz mashinangizga primerka qiling",
    "home.lede": "Salon suratini yuklang, rul, magnitola yoki boshqa apgreyd tanlang va natijani oʻrnatishdan oldin koʻring.",
    "home.slider_hint": "«Avval / Keyin» slayderini torting",
    "home.adv1": "Oʻzingizning suratingizda primerka",
    "home.adv2": "Moslik mashinangizga qarab tanlanadi",
    "home.adv3": "Oʻrnatish narxga kiritilgan",
    "home.cap_before": "[ salon · standart rul ]",
    "home.cap_after": "[ salon · yangi rul ]",
    "home.cta_pick": "Nimani primerka qilishni tanlash",
    "home.cta_example": "Namunani koʻrish",
    "home.gallery": "Mening primerkalarim",
    "home.showcase": "Haqiqiy ishlar",

    "example.eyebrow": "Namuna",
    "example.title": "Chevrolet Malibu uchun Mercedes-AMG Performance",
    "example.cap_before": "[ asl surat ]",
    "example.cap_after": "[ AI natija ]",
    "example.for": "Teri + perforatsiya · Chevrolet Malibu uchun",
    "example.tag_carbon": "Karbon",
    "example.tag_led": "LED",
    "example.tag_paddles": "Kurakchalar",
    "example.install": "Oʻrnatish",
    "example.install_incl": "kiritilgan",
    "example.total": "Jami",
    "example.note": "AI vizualizatsiya taxminiy. Yakuniy koʻrinish yoritish, rakurs va avtomobil xususiyatlariga qarab biroz farq qilishi mumkin.",
    "example.cta": "Oʻz suratingizni yuklash",

    "pick.title": "Nimani primerka qilamiz?",
    "pick.lede": "Avtomobil qismini tanlang — har biri uchun alohida surat kerak.",
    "pick.note": "Bir vaqtda bitta boʻlim. Primerkadan soʻng qaytib, yigʻmaga yana mahsulot qoʻshish mumkin.",

    "upload.subtitle": "Shunda AI joylashuv va istiqbolni aniqroq belgilaydi.",
    "upload.in_frame": "kadrda",
    "upload.replace": "Almashtirish",
    "upload.rotate": "Aylantirish",
    "upload.rotating": "Aylantiryapmiz…",
    "upload.src_camera": "Surat olish",
    "upload.src_gallery": "Galereyadan tanlash",
    "upload.src_demo": "Namunaviy surat",
    "upload.tips_title": "Suratga tavsiyalar",
    "upload.tip1": "Kerakli qism kadrga toʻliq tushishi kerak",
    "upload.tip2": "Telefonni tekis ushlang",
    "upload.tip3": "Yaxshi yoritishdan foydalaning",
    "upload.tip4": "Obyektni qoʻl bilan toʻsmang",
    "upload.continue": "Davom etish",

    "car.analyzing_title": "Avtomobilni aniqlayapmiz",
    "car.analyzing_sub": "Suratni tahlil qilyapmiz…",
    "car.confirm_title": "Avtomobilni aniqlashtiring",
    "car.confirm_sub": "Marka, model va yilni tanlang — mos mahsulotlarni tanlaymiz.",
    "car.brand": "Marka",
    "car.model": "Model",
    "car.year": "Ishlab chiqarilgan yil",
    "car.edit": "Oʻzgartirish",
    "car.likely": "Ehtimol, bu",
    "car.compatible_found": "Mos mahsulotlar topildi",
    "car.wrong_hint": "Agar model notoʻgʻri aniqlangan boʻlsa — qoʻlda tuzating, katalog yangilanadi.",
    "car.accept": "Hammasi toʻgʻri",
    "car.confirm": "Avtomobilni tasdiqlash",

    "catalog.change_section": "Boʻlimni almashtirish",
    "catalog.configure": "Primerka qilish",
    "catalog.in_stock": "Mavjud",
    "catalog.on_order": "Buyurtma asosida",
    "catalog.filter_pop": "Ommabop",
    "catalog.filter_price": "Narx boʻyicha",
    "catalog.filter_carbon": "Karbon",
    "catalog.filter_led": "LED",
    "catalog.filter_paddles": "Kurakchalar",
    "catalog.no_section": "Boʻlim tanlanmagan.",
    "catalog.empty_filter": "Bu filtrda hozircha mahsulot yoʻq.",

    "config.no_product": "Mahsulot tanlanmagan.",
    "config.for": "uchun",
    "config.services": "Xizmatlar",
    "config.free": "bepul",
    "config.cta_generate": "Mashinamda primerka qilish",
    "config.cta_another": "Boshqa mahsulot tanlash",
    "config.suffix_left": " · qoldi {n}",
    "config.suffix_bonus": " · bonus {n}",

    "gen.error_title": "Suratni aniq tanib boʻlmadi",
    "gen.error_sub": "Kerakli qism toʻliq koʻrinadigan va yaxshi yoritilgan suratni yuklab koʻring.",
    "gen.title": "Vizualizatsiya yaratyapmiz",
    "gen.progress": "Jarayon",
    "gen.retry": "Boshqa surat yuklash",

    "result.before": "Avval",
    "result.after": "Keyin",
    "result.another": "Boshqa mahsulot",
    "result.edit": "Oʻzgartirish",
    "result.save": "Saqlash",
    "result.saved": "Saqlandi",
    "result.share": "Ulashish",
    "result.sharing": "Yuboryapmiz…",
    "result.shared": "Yuborildi",
    "result.cap_before": "[ foydalanuvchi surati ]",
    "result.cap_after": "[ AI natija ]",
    "result.add_to_cart": "Savatga qoʻshish",
    "result.note": "AI vizualizatsiya taxminiy. Yakuniy koʻrinish yoritish, rakurs va avtomobil xususiyatlariga qarab biroz farq qilishi mumkin.",
    "result.share_denied": "Ruxsatsiz bot rasmni yubora olmaydi.",
    "result.compare": "Solishtirish",

    // ── compare (side-by-side) ──
    "compare.title": "Solishtirish",
    "compare.lede": "Ikkala variant sizning mashinangizda — qaysi biri yoqsa, tanlang.",
    "compare.pick_title": "Nima bilan solishtiramiz?",
    "compare.pick_sub": "Ikkinchi mahsulotni xuddi shu suratda primerka qilamiz.",
    "compare.cancel": "Bekor qilish",
    "compare.a": "A variant",
    "compare.b": "B variant",
    "compare.choose": "Shuni tanlash",
    "compare.note": "Solishtirish taxminiy. Yakuniy koʻrinish biroz farq qilishi mumkin.",
    "compare.none": "Solishtirish uchun maʼlumot yoʻq.",

    // ── gallery ("Mening primerkalarim") ──
    "gallery.title": "Mening primerkalarim",
    "gallery.empty": "Bu yerda AI-primerkalaringiz paydo boʻladi. Surat yuklang va mahsulotni primerka qiling.",
    "gallery.empty_cta": "Mahsulotni primerka qilish",
    "gallery.delete": "Oʻchirish",
    "gallery.confirm_delete": "Bu primerkani oʻchirilsinmi?",
    "gallery.load_error": "Primerkalarni yuklab boʻlmadi.",

    // ── showcase ("Haqiqiy ishlar") ──
    "showcase.title": "Haqiqiy ishlar",
    "showcase.lede": "Xuddi sizniki kabi mashinalarga haqiqiy oʻrnatishlar.",
    "showcase.all": "Barchasi",
    "showcase.try": "Xuddi shunday primerka qilish",
    "showcase.empty": "Bu yerda magazinning haqiqiy ishlari paydo boʻladi.",
    "showcase.load_error": "Ishlarni yuklab boʻlmadi.",

    "cart.title": "Sizning yigʻmangiz",
    "cart.empty": "Savat boʻsh. Boʻlim tanlang va mahsulotni primerka qiling.",
    "cart.add_first": "Mahsulot qoʻshish",
    "cart.positions_for": "{car} uchun {n} ta pozitsiya",
    "cart.price": "Narxi",
    "cart.add_more": "Yana mahsulot qoʻshish",
    "cart.positions": "Pozitsiyalar",
    "cart.total": "Jami",
    "cart.checkout": "Ariza rasmiylashtirish",

    "request.title": "Oʻrnatishga ariza",
    "request.lede": "Menejer siz bilan bogʻlanadi, moslik, narx va qulay oʻrnatish vaqtini tasdiqlaydi.",
    "request.car": "Avtomobil",
    "request.positions": "Pozitsiyalar",
    "request.total": "Jami",
    "request.f_name": "Ism",
    "request.f_name_ph": "Sizga qanday murojaat qilaylik",
    "request.f_phone": "Telefon raqami",
    "request.f_tg": "Telegram",
    "request.f_date": "Istalgan sana",
    "request.f_date_ph": "masalan, 24-iyul",
    "request.f_comment": "Izoh",
    "request.f_comment_ph": "Oʻrnatishga oid istaklar",
    "request.prefill": "Ism va Telegram profilingizdan olindi — ularni oʻzgartirish mumkin.",
    "request.prefill_hint": "Ism va kontakt avtomatik toʻlishi uchun ilovani Telegramda oching.",
    "request.submit": "Arizani yuborish",
    "request.need_phone": "Telefon raqamini kiriting",

    "success.title": "Ariza yuborildi",
    "success.sub": "Menejer siz bilan bogʻlanadi, moslik, narx va qulay oʻrnatish vaqtini tasdiqlaydi.",
    "success.car": "Avtomobil",
    "success.positions": "Pozitsiyalar",
    "success.total": "Jami",
    "success.booking_no": "ariza №",
    "success.manager": "Menejerga yozish",
    "success.home": "Bosh sahifaga",

    "ref.title": "Doʻstlaringiz uchun primerka oling",
    "ref.lede": "Havolangizni ulashing. Yangi foydalanuvchi birinchi AI-primerkasini yaratganda, siz bitta bonus primerka olasiz.",
    "ref.unavailable": "Shaxsiy havola Telegramda mavjud — ilovani bot orqali oching.",
    "ref.invited": "Taklif qilingan",
    "ref.qualified": "Primerka yaratgan",
    "ref.earned": "Olingan bonuslar",
    "ref.monthly": "Shu oyda mavjud",
    "ref.your_link": "Sizning havolangiz",
    "ref.copied": "Havola nusxalandi",
    "ref.note": "Bonus faqat taklif qilingan foydalanuvchining birinchi muvaffaqiyatli primerkasi uchun beriladi. Havolaga oʻtish yoki oʻrnatish uchun bonus berilmaydi.",
    "ref.invite": "Doʻstlarni taklif qilish",
    "ref.copy": "Havolani nusxalash",
    "ref.back": "Orqaga",
    "ref.share_text": "Mashinangizni yigʻing — tuningni oʻz suratingizda primerka qiling.",
    "ref.invited_note": "Siz taklif orqali keldingiz. Doʻstingiz bonus olishi uchun birinchi primerkangizni yarating.",

    "quota.left_of": "{max} tadan {n} ta primerka qoldi",
    "quota.free_out": "Bepul primerkalar tugadi",
    "quota.cat_out": "Bu boʻlimda primerkalar tugadi",
    "quota.bonus": "Bonus: {n}",
    "quota.title": "AI-primerkalar",
    "quota.by_section": "Bepul primerkalar har bir boʻlim uchun alohida hisoblanadi.",
    "quota.bonus_tries": "Bonus primerkalar",
    "quota.recent": "Soʻnggi amallar",
    "quota.ok": "Tushunarli",
    "quota.get_more": "Primerka olish",
    "quota.op_spend": "Primerka",
    "quota.op_refund": "Muvaffaqiyatsiz primerka uchun qaytarish",
    "quota.op_grant": "Bonus primerkalar berildi",
    "quota.exhausted_title": "Primerkalar tugadi",
    "quota.exhausted_body": "Siz bu boʻlimdagi barcha bepul primerkalarni ishlatdingiz. Katalog, saqlangan natijalar va oʻrnatish arizasi mavjud boʻlib qoladi.",
    "quota.invite_friends": "Doʻstlarni taklif qilish",
    "quota.activate_code": "Kodni faollashtirish",
    "quota.back_to_catalog": "Katalogga qaytish",
    "quota.code_activated": "Kod faollashtirildi",
    "quota.code_title": "Bonusni faollashtirish",
    "quota.code_body": "Kod ustaxonaga tashrif yoki oʻrnatishdan soʻng beriladi. Primerka olish uchun uni kiriting.",
    "quota.code_ph": "Masalan, K7QX2M4P",
    "quota.code_checking": "Tekshiryapmiz…",
    "quota.code_activate": "Faollashtirish",
    "quota.code_scan": "QR-kodni skanerlash",
    "quota.code_cancel": "Bekor qilish",
    "quota.code_great": "Zoʻr",
    "quota.reward_restored": "barcha boʻlimlarda bepul primerkalar tiklandi",
    "quota.reward_bonus": "berilgan bonus primerkalar: {n}",
    "quota.reward_applied": "Bonus qoʻllandi.",
    "quota.bonus_confirm_title": "Bonus primerkadan foydalanilsinmi?",
    "quota.bonus_confirm_body": "Bu boʻlimda bepul primerkalar tugadi. 1 ta bonus primerka ishlatiladi. Qoldi: {n}.",
    "quota.bonus_continue": "Davom etish",
    "quota.bonus_cancel": "Bekor qilish",
    "quota.scan_hint": "QR-kodga qarating",

    "ui.app_sub": "mini-ilova",
    "ui.step_section": "Boʻlim",
    "ui.step_photo": "Surat",
    "ui.step_car": "Avto",
    "ui.step_choice": "Tanlash",
    "ui.currency": "soʻm",
    "ui.catalog_error": "Katalogni yuklab boʻlmadi: {msg}",
  },
};

let current = read();

function read() {
  try {
    const stored = localStorage.getItem(STORE_KEY);
    if (LANGS.includes(stored)) return stored;
  } catch {
    // Blocked storage: fall through to unset.
  }
  return null;
}

/** The active language, or null if none has been chosen yet (→ language screen). */
export function getLang() {
  return current;
}

export function hasLang() {
  return current !== null;
}

export function setLang(lang) {
  if (!LANGS.includes(lang)) return;
  current = lang;
  try {
    localStorage.setItem(STORE_KEY, lang);
  } catch {
    // Not persisting is acceptable; the choice still holds for this session.
  }
}

/** Translate a key, interpolating {name} params. Falls back to ru, then the key. */
export function t(key, params) {
  const lang = current || "ru";
  const table = MESSAGES[lang] || MESSAGES.ru;
  let str = table[key];
  if (str === undefined) str = MESSAGES.ru[key];
  if (str === undefined) return key;
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      str = str.replaceAll(`{${k}}`, String(v));
    }
  }
  return str;
}
