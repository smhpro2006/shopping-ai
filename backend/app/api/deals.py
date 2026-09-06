"""GET /api/v1/deals — products ranked by price spread across retailers."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload
from typing import Optional

from backend.app.core.database import get_db
from backend.app.models.product import Product
from backend.app.models.offer import Offer

router = APIRouter(tags=["deals"])


class DealItem(BaseModel):
    id: int
    name: str
    brand: str
    category: str
    lowest_price: float
    highest_price: float
    price_spread_pct: float
    retailer_count: int
    image_url: Optional[str] = None


@router.get("/deals", response_model=list[DealItem])
def get_deals(db: Session = Depends(get_db)):
    """Return up to 20 products with ≥2 active offers, ranked by price spread (desc)."""
    products = (
        db.query(Product)
        .options(joinedload(Product.offers).joinedload(Offer.retailer))
        .order_by(Product.id)
        .all()
    )

    deal_items = []
    for product in products:
        live = product.live_offers()
        if len(live) < 2:
            continue

        prices = [o.price for o in live]
        min_price = min(prices)
        max_price = max(prices)
        spread_pct = round((max_price - min_price) / max_price * 100, 1)

        deal_items.append(DealItem(
            id=product.id,
            name=product.name,
            brand=product.brand,
            category=product.category,
            lowest_price=min_price,
            highest_price=max_price,
            price_spread_pct=spread_pct,
            retailer_count=len(live),
            image_url=product.image_url,
        ))

    deal_items.sort(key=lambda d: d.price_spread_pct, reverse=True)
    return deal_items[:20]
