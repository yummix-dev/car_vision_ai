from pydantic import BaseModel, Field

from app.models.pricing import Selection


class CartItemIn(BaseModel):
    product_id: str
    selections: list[Selection] = Field(default_factory=list)


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


class BookingResponse(BaseModel):
    booking_id: str
    status: str
    positions: int
    total: int
    total_formatted: str
    car_label: str
