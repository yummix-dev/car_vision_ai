from pydantic import BaseModel, Field


class Selection(BaseModel):
    group_id: str
    choice_id: str


class PriceLine(BaseModel):
    label: str
    amount: int
    amount_formatted: str


class PriceBreakdown(BaseModel):
    product_id: str
    product_name: str
    lines: list[PriceLine] = Field(default_factory=list)
    total: int
    total_formatted: str


class QuoteRequest(BaseModel):
    product_id: str
    selections: list[Selection] = Field(default_factory=list)
    service_ids: list[int] = Field(default_factory=list)
