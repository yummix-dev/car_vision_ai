# MyCar Vision AI

Telegram-styled mini-app for a car-tuning shop: photograph a zone of your car →
AI identifies the vehicle → pick and configure an aftermarket part → AI renders a
before/after on your own photo → cart → installation booking.

FastAPI backend + a no-build vanilla-JS SPA. All UI copy is Russian; prices in сум.

## Run

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

Open http://127.0.0.1:8000 — the app renders in a 392×844 phone frame (it goes
full-bleed below 440px wide).

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest
```

## The two AI seams

Each is an ABC with a mock and a real implementation, selected by env var.
Both mocks stay the default so the funnel is walkable with no keys and no spend.

| Seam | Interface | Mock | Real |
|---|---|---|---|
| Vehicle recognition | `app/services/ai/vehicle_base.py` | fixed guess after 1.7s | `vehicle_claude.py` — Claude vision, `claude-opus-4-8` |
| Before/after image | `app/services/ai/imagegen_base.py` | highlights the region on your real photo | `imagegen_provider.py` — OpenAI `gpt-image-2` |

**Claude cannot do the before/after visualization** — that needs an image-generation
model, which is why seam 2 is a different vendor and stays provider-agnostic in
its naming (`IMAGEGEN_PROVIDER=provider`, not `=openai`).

```dotenv
AI_PROVIDER=mock          # mock | claude
IMAGEGEN_PROVIDER=mock    # mock | provider
IMAGEGEN_QUALITY=medium   # low | medium | high | auto — the cost dial
IMAGEGEN_MAX_EDGE=1024    # bigger costs more
GENERATION_FORCE_ERROR=0  # 1 makes generation always fail, to exercise the retry path
```

`AI_PROVIDER=claude` needs `ANTHROPIC_API_KEY` (or an `ant auth login` profile);
`IMAGEGEN_PROVIDER=provider` needs `OPENAI_API_KEY`. The manual chip-editor
correction on the `car` screen is the recovery path for wrong guesses and never
calls the model.

**Seam 2 sends no mask.** gpt-image-2 accepts one, but we have no per-pixel
segmentation of the zone and a crude rectangle would wipe out real interior
detail around the part. Instead the prompt names the zone and the model's
automatic high input fidelity holds the rest of the photo. If drift shows up in
practice, adding a mask is a change to that one file. Costs run ~$0.04–0.05 per
generation at `medium`/1024 — roughly 10× that at `high`.

## Telegram

The SPA loads the WebApp SDK and sends `Telegram.WebApp.initData` on every API
call as `X-Telegram-Init-Data`. The backend verifies it (HMAC-SHA256 against the
bot token, plus an `auth_date` freshness window) in `app/services/telegram.py` —
the only module that knows the Bot API exists. `web/js/tg.js` is its counterpart
on the client and the only place that touches `window.Telegram`.

### Running it inside Telegram

Telegram needs a public HTTPS URL — it will not load a mini-app from localhost.

```powershell
.\.venv\Scripts\python.exe main.py          # terminal 1
cloudflared tunnel --url http://127.0.0.1:8000   # terminal 2, prints an https URL
```

Then in [@BotFather](https://t.me/BotFather): `/newapp` → pick the bot → paste
the tunnel URL. Open the resulting `t.me/<bot>/<app>` link from a phone.

Two settings matter for the real run:

- `TELEGRAM_REQUIRE_INIT_DATA=1` — only while serving through Telegram. It makes
  `/api/booking` reject unsigned callers, which also breaks the browser demo.
- `TELEGRAM_MANAGER_CHAT_ID` — send the bot any message, then read the id from
  `https://api.telegram.org/bot<TOKEN>/getUpdates`. Until it is set, bookings are
  logged with a warning instead of delivered.

The tunnel URL changes every restart, so `/newapp` has to be re-pointed each
time (`/editapp` in BotFather). A named tunnel avoids that once it matters.

Inside Telegram the app drops its showcase chrome: `body.in-telegram` (set in
`web/js/app.js`) hides the drawn status bar and phone frame, sizes to
`--tg-viewport-stable-height` so the keyboard does not cover the booking form,
pads for safe areas, and turns ✕ into a real `close()`. In a browser the 392×844
frame stays exactly as before.

**Sharing a result** (`POST /api/generation/share`) has the bot send the render
into the user's own chat: a `/media/` link would not open for anyone else. The
client asks for permission via `requestWriteAccess()` first — without it the bot
cannot message the user at all — and the photo goes up as multipart bytes,
because Telegram fetches a `photo` URL from its own servers and cannot reach
`127.0.0.1`. The request names a `job_id`, never a file: a client-supplied path
would let any caller have the bot mail them somebody else's upload. This
endpoint always requires valid initData, even when `TELEGRAM_REQUIRE_INIT_DATA`
is off, because the user id *is* the destination.

**Bookings are delivered, not stored.** `POST /api/booking` sends the order to
the manager's chat and only then confirms it to the customer; a delivery failure
is a 502 and no confirmation. That chat is the system of record — the
`_bookings` dict in `app/routers/cart.py` is a session cache, which is why there
is still no database.

```dotenv
TELEGRAM_BOT_TOKEN=123456:AA...   # unset → bookings are logged, not delivered
TELEGRAM_MANAGER_CHAT_ID=         # user, group or channel id
TELEGRAM_BOT_USERNAME=            # empty → the manager button is hidden
TELEGRAM_REQUIRE_INIT_DATA=0      # 1 in production: unsigned callers get 401
```

`TELEGRAM_REQUIRE_INIT_DATA=0` is the default on purpose: a browser has no
`initData`, and the whole funnel is developed and demoed in one. Production
turns it on. Everything degrades outside Telegram rather than breaking — no
user prefill, no native back button, no manager button.

## Analytics

`/admin` (HTTP Basic, `ADMIN_PASSWORD`) shows the funnel: sessions reaching each
step, conversion to the previous one, drop-off, top categories and products, and
the generation failure rate.

**An empty `ADMIN_PASSWORD` means the route is never registered** — not that it
is reachable without one. The default deployment must not publish the shop's
numbers.

Events come from the client (`web/js/analytics.js`), because the most valuable
fact about a funnel is where people *stop*, and stopping produces no request.
The queue flushes on `pagehide`/`visibilitychange` via `sendBeacon`: a plain
`fetch` is cancelled as the page tears down, losing exactly the last event —
the one that marks the drop-off.

`POST /api/events` is the app's only unauthenticated write path, so it is
bounded on every axis: a closed vocabulary of event names
(`app/services/analytics.py`), a batch cap, a payload cap, a per-session rate
limit, and a **server-assigned timestamp** — a phone's clock is not evidence.

Storage is one SQLite table in `data/analytics.db`, no ORM and no migrations.
`booking_submitted` is recorded server-side, where the fact is certain, and
carries only the amount and the number of positions. **Names and phone numbers
never reach analytics** — they exist only in the manager's chat.

## AI try-ons (quotas)

Every Telegram user gets `FREE_TRIES_PER_CATEGORY` (3) free AI try-ons **per
category**, plus a shared balance of bonus try-ons spendable anywhere. Free is
spent first; bonus only once the category is empty. A bonus never raises a
category's limit — "Рули: 0 из 3" with bonuses held separately, never "7 из 7".

Balances live in `data/app.db`, **separate from `data/analytics.db`**: events
are purged on a schedule and cheap to lose, balances are neither.

**Reserving debits, failing refunds.** The obvious design — check at the start,
debit at the end — lets two concurrent requests both pass the check and spend
one try twice. So `app/services/quota.py` debits inside the reserving
transaction (`BEGIN IMMEDIATE`, conditional UPDATE) and refunds on failure,
expiry, or a result that turns out to be missing or empty. What the customer
observes is what the spec asks for — nothing is paid for a failed render — and
the race cannot happen.

Every balance change writes a `generation_transactions` row with before/after
for both balances. The balance is never edited without one, which is what makes
a disputed count answerable.

The client sends one `Idempotency-Key` per attempt, so a double tap, a reload or
a retry over a slow connection costs a single try.

**Quotas apply inside Telegram only.** A browser visitor has no durable
identity, and a session-keyed quota resets with localStorage — decoration, not a
limit. In production `TELEGRAM_REQUIRE_INIT_DATA=1` makes the distinction moot.

Categories are not enumerated anywhere: an allowance is created lazily at the
default the first time a category is used, so adding one to `catalog.yaml` needs
no migration and no admin action.

## Referrals

Every user has a permanent code and a link
(`t.me/<bot>/<app>?startapp=ref_CODE`). A shared result adds the result's own
code: `ref_CODE-s-SHARECODE`. Both arrive as Telegram's `start_param`, and
`POST /api/referral/attribute` binds the visitor to their inviter.

**A bonus is never paid for a click.** Attribution alone is worth nothing.
`app/services/referrals.py` pays out only when the invited person has confirmed
a car, used **their own** photograph (the demo image does not count) and
completed a try-on that produced a real file — and only for their *first* one.

Paying at most once per invited person is enforced twice by the database:
`referrals.invited_user_id` is UNIQUE, and the grant is written with the ledger's
UNIQUE `idempotency_key`. Arriving through a shared result rather than a plain
link is the same single bonus, not a second one.

Attribution is permanent — a second link never reassigns credit — self-invites
are refused, and somebody who has already generated is not a new user however
they arrive next.

Beyond a monthly cap (`REFERRAL_MONTHLY_LIMIT`), weak fraud signals are *scored*
rather than acted on individually: qualifying implausibly fast, one photograph
appearing under several accounts, many invitations from one address. Over the
threshold the referral is **frozen for review**, not rejected — a weak signal is
not proof, and a wrongly refused bonus is invisible to everyone.

Frozen referrals are listed on `/admin` with their score and reasons, and can be
approved (the bonus is paid) or rejected. Approval deliberately ignores the
monthly cap — a person has examined this specific case — and is recorded in the
ledger as `referral_approved` so manual decisions stay distinguishable from
automatic ones. Approving twice cannot pay twice: manual and automatic payment
share one `idempotency_key`.

The admin actions are POST-only, so no state changes on a link. They are *not*
CSRF-protected beyond that: HTTP Basic credentials are attached by the browser
to a cross-site form submission too. For a single-operator internal page that is
an accepted trade, not an oversight — but it is the reason not to reuse this
pattern for anything wider. Device
fingerprinting is deliberately not implemented: invasive, trivially defeated,
and worthless next to a Telegram id that cannot be forged without breaking the
initData HMAC.

Sharing a result sends a composed **share card** (`app/services/share_card.py`)
carrying the render, the car, the part and the price, with the referral link in
the message caption — a link burned into pixels cannot be tapped.

## Reward codes

One-time codes (`app/services/reward_codes.py`) carry a visit, a purchase or a
manual make-good. A **visit** grants bonus try-ons. A **purchase** additionally
tops every category the customer has used back to its free limit — tops up,
never adds, so "3 из 3" stays "3 из 3" rather than becoming "6 из 3". Bonuses
stay in their own balance, which is the entire reason free and bonus are
different columns.

Activation is the only place a customer can increase their own balance, so both
guarantees come from the database rather than from the order of checks:
`reward_code_activations.idempotency_key` is UNIQUE per (code, user), and the
activation count is incremented conditionally inside the same transaction — two
simultaneous requests cannot both take the last slot.

A purchase by somebody who arrived through a referral also pays their inviter
`REFERRED_CLIENT_BONUS`, once, on top of the single bonus already paid for that
person's first try-on. A second purchase is not a second bonus.

`/admin` mints and cancels codes, and `/admin/users/<telegram_id>` shows one
customer's balances and every movement behind them, including manual
adjustments — where the comment is **required**, because an unexplained balance
change is indistinguishable from a bug six months later.

## Limits and cleanup

Nothing grows without a bound. A background sweep (`app/services/cleanup.py`,
started from the app lifespan) deletes `media/` files past `MEDIA_TTL_DAYS`,
evicts finished generation jobs, and purges events past `ANALYTICS_TTL_DAYS`.
The demo photo is exempt: it is only seeded at startup, so deleting it under a
running app would dead-end the zero-input funnel.

`GENERATION_LIMIT_PER_HOUR` caps generation per Telegram user (falling back to
the session id). It is the only thing between the endpoint and a real bill —
about $0.05 a call against `gpt-image-2`.

## Editing the catalog

Everything the shop sells lives in `app/data/catalog.yaml` — categories, products,
option groups and price deltas. It is validated against Pydantic models at startup,
so a bad price or a dangling option reference fails immediately rather than at
checkout. No database.

**Pricing is server-authoritative** (`app/services/pricing_service.py`). The client
may display an estimate, but every total entering the cart or a booking is
recomputed server-side. Installation is always bundled.

## Layout

```
app/       FastAPI: models, routers, services (AI seams, Telegram, analytics), catalog.yaml
web/       the SPA — index.html, css/, js/{state,api,ui,icons,tg,analytics}.js, js/screens/*.js
data/      the analytics SQLite file (gitignored)
media/     uploads + generated images (gitignored)
tests/     pricing golden cases, catalog validation, AI-seam contracts
```

The SPA is a state machine: `state.screen` plus a `history[]` stack, no router and
no build step. Events are delegated on `[data-act]` attributes.

## Not built yet

A QR scanner for reward codes (they are typed by hand today), and an admin view
of the whole referral chain. Telegram theme params are
deliberately not adopted — the app ships its own fixed dark palette, and
`setColors()` pushes that palette out to the client chrome instead.

There is no booking store, deliberately: the manager's chat is the system of
record and a second copy of customers' phone numbers would earn nothing.

The cart, the contact form and the confirmed car survive a reload via
`localStorage` (`web/js/state.js`). Deliberately excluded: the photo, the
generation job and the balance — a balance read from the browser would be a
balance the customer can edit. Saved lines are checked against the catalog on
restore, so a product the shop has dropped cannot reach checkout.
