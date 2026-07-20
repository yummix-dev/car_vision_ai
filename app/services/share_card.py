"""Composes the image a customer actually posts.

The render alone says nothing about where it came from. The card adds the car,
the part, the price and the shop — so a screenshot forwarded to a group chat
still carries the offer. The referral link travels in the message caption, not
burned into the picture, because a link in pixels cannot be tapped.

PIL only, like the rest of the image work in this project.
"""

import io

from PIL import Image, ImageDraw, ImageFont

from app.money import fmt

WIDTH = 1080
PAD = 56
BG = "#0c0f14"
CARD = "#131922"
TEXT = "#e8edf4"
MUTED = "#9aa7b8"
ACCENT = "#3b82f6"


def _font(size: int, bold: bool = False):
    """Windows ships Arial; elsewhere fall back to PIL's built-in.

    A missing font must degrade to something readable rather than crash a share.
    """
    for name in (["arialbd.ttf", "DejaVuSans-Bold.ttf"] if bold
                 else ["arial.ttf", "DejaVuSans.ttf"]):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default(size)


def _fit(draw, text: str, font, max_width: int) -> str:
    if draw.textlength(text, font=font) <= max_width:
        return text
    while text and draw.textlength(text + "…", font=font) > max_width:
        text = text[:-1]
    return text + "…"


def build(
    after_image: bytes,
    *,
    product_name: str,
    car_label: str = "",
    category_label: str = "",
    price: int | None = None,
    shop_name: str = "MyCar Vision AI",
) -> bytes:
    """Render the share card as JPEG bytes."""
    photo = Image.open(io.BytesIO(after_image)).convert("RGB")

    # Photo on top at its own aspect, details below — cropping someone's car to
    # a fixed square is the one thing that would make the card worse than the
    # bare render.
    photo_h = round(WIDTH * photo.height / photo.width)
    photo_h = min(photo_h, round(WIDTH * 1.15))
    photo = photo.resize((WIDTH, photo_h), Image.LANCZOS)

    panel_h = 300
    card = Image.new("RGB", (WIDTH, photo_h + panel_h), BG)
    card.paste(photo.crop((0, 0, WIDTH, photo_h)), (0, 0))

    draw = ImageDraw.Draw(card)
    y = photo_h

    draw.rectangle([0, y, WIDTH, y + panel_h], fill=CARD)
    draw.rectangle([0, y, WIDTH, y + 4], fill=ACCENT)

    y += 40
    if category_label:
        f = _font(30)
        draw.text((PAD, y), category_label.upper(), font=f, fill=MUTED)
        y += 44

    f = _font(58, bold=True)
    draw.text((PAD, y), _fit(draw, product_name, f, WIDTH - 2 * PAD), font=f, fill=TEXT)
    y += 76

    if car_label:
        f = _font(34)
        draw.text((PAD, y), _fit(draw, f"для {car_label}", f, WIDTH - 2 * PAD),
                  font=f, fill=MUTED)
        y += 52

    if price is not None:
        f = _font(46, bold=True)
        draw.text((PAD, y), f"{fmt(price)} сум", font=f, fill=ACCENT)

    f = _font(30)
    label = _fit(draw, shop_name, f, WIDTH - 2 * PAD)
    draw.text((WIDTH - PAD - draw.textlength(label, font=f),
               photo_h + panel_h - 56), label, font=f, fill=MUTED)

    out = io.BytesIO()
    card.save(out, "JPEG", quality=90, optimize=True)
    return out.getvalue()
