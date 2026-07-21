from fastapi import APIRouter, HTTPException

from app.models.pricing import PriceBreakdown, QuoteRequest
from app.services.pricing_service import PricingError, quote

router = APIRouter(prefix="/api/pricing", tags=["pricing"])


@router.post("/quote")
def post_quote(req: QuoteRequest) -> PriceBreakdown:
    """Server-authoritative price. The client may estimate; this is the truth."""
    try:
        return quote(req.product_id, req.selections, req.service_ids)
    except PricingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
