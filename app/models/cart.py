from typing import Literal

from pydantic import BaseModel, Field

from app.models.pricing import Selection


class CartItemIn(BaseModel):
    product_id: str
    selections: list[Selection] = Field(default_factory=list)
    service_ids: list[int] = Field(default_factory=list)


class Contact(BaseModel):
    name: str = ""
    phone: str = ""
    telegram: str = ""
    date: str = ""
    comment: str = ""


class BookingRequest(BaseModel):
    cart: list[CartItemIn] = Field(default_factory=list)
    contact: Contact = Field(default_factory=Contact)
    car_label: str = ""
    # How the customer wants to pay: cash on site, card via Telegram, or Uzum
    # installments. The server validates and prices; the client never charges.
    payment_method: Literal["cash", "telegram", "uzum"] = "cash"


class PaymentAction(BaseModel):
    # What the client should do next. "manager" = nothing to open, the manager
    # will arrange payment; "invoice"/"redirect" carry a URL (Phase 2).
    kind: Literal["manager", "invoice", "redirect"] = "manager"
    url: str = ""


class BookingResponse(BaseModel):
    booking_id: str
    status: str
    positions: int
    total: int
    total_formatted: str
    car_label: str
    payment_method: str = "cash"
    payment: PaymentAction = Field(default_factory=PaymentAction)
