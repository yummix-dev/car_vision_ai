from typing import Literal

from pydantic import BaseModel, Field


class OptionChoice(BaseModel):
    id: str
    label: str
    label_uz: str | None = None
    price_delta: int = 0
    # Optional swatch colour, used by leather/stitch groups for the live CSS preview.
    hex: str | None = None


class OptionGroup(BaseModel):
    """A configurable dimension of a product.

    ``segment`` = pick exactly one choice. ``toggle`` = on/off, where the single
    choice carries the price applied when enabled.
    """

    id: str
    label: str
    label_uz: str | None = None
    type: Literal["segment", "toggle"]
    # For segments: the choice selected by default. For toggles: "on" or "off".
    default: str
    choices: list[OptionChoice]
    # Rendering hint for the frontend: swatch_square (leather), swatch_round (stitch),
    # chip (text choices), switch (toggles).
    ui: Literal["chip", "swatch_square", "swatch_round", "switch"] = "chip"

    def choice(self, choice_id: str) -> OptionChoice | None:
        return next((c for c in self.choices if c.id == choice_id), None)


class Product(BaseModel):
    id: str
    category: str
    name: str
    base_price: int
    # Filename under web/img/products/. Shown on the catalog card AND handed to
    # the image model as a reference, so the customer sees the part the shop
    # actually stocks rather than the model's idea of one. Optional: without it
    # the render falls back to a description in words.
    photo: str | None = None
    material: str | None = None
    material_uz: str | None = None
    tags: list[str] = Field(default_factory=list)
    time: str
    time_uz: str | None = None
    stock: Literal["in", "order"]
    popular: bool = False
    # Filter flags used by the wheels filter row: carbon, has_led, has_paddles.
    flags: dict[str, bool] = Field(default_factory=dict)
    # Preset applied when the product is opened (the prototype's `d{}`).
    default_config: dict[str, str] = Field(default_factory=dict)


class Category(BaseModel):
    id: str
    label: str
    label_uz: str | None = None
    # Filename under web/img/categories/, shown on the section card.
    photo: str | None = None
    noun: str
    noun_cap: str
    noun_cap_uz: str | None = None
    # Accusative form, used in "Мы изменим только {acc}".
    acc: str
    title: str
    title_uz: str | None = None
    sub: str
    sub_uz: str | None = None
    # Instruction shown on the upload screen for this zone.
    shoot_title: str
    shoot_title_uz: str | None = None
    # Subtitle on the category card.
    pick_sub: str
    pick_sub_uz: str | None = None
    is_wheel: bool = False
    gen_steps: list[str]
    gen_steps_uz: list[str] | None = None
    option_groups: list[OptionGroup] = Field(default_factory=list)
    products: list[Product] = Field(default_factory=list)

    def group(self, group_id: str) -> OptionGroup | None:
        return next((g for g in self.option_groups if g.id == group_id), None)

    def product(self, product_id: str) -> Product | None:
        return next((p for p in self.products if p.id == product_id), None)


class CarOptions(BaseModel):
    brands: list[str]
    models: list[str]
    years: list[int]


class Catalog(BaseModel):
    categories: list[Category]
    car_options: CarOptions

    def category(self, category_id: str) -> Category | None:
        return next((c for c in self.categories if c.id == category_id), None)

    def find_product(self, product_id: str) -> tuple[Category, Product] | None:
        for cat in self.categories:
            p = cat.product(product_id)
            if p is not None:
                return cat, p
        return None
