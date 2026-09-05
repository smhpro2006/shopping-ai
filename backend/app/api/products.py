from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from backend.app.core.database import get_db
from backend.app.core.config import ANTHROPIC_API_KEY
from backend.app.core.security import get_current_user
from backend.app.models.product import Product
from backend.app.models.retailer import Retailer
from backend.app.models.offer import Offer
from backend.app.models.user import User
from backend.app.product_matching import calculate_match_score, classify_score
from backend.app.services.ai_search import parse_search_intent, enhance_score_with_intent, generate_summary
from backend.app.schemas import (
    SearchResponse, AIIntent, ProductCreate, ProductUpdate, ProductRead,
    ProductsResponse, OfferRead,
)

router = APIRouter(tags=["products"])


def _product_to_result_dict(product: Product, score: int) -> dict:
    """Build a search result dict from a canonical Product + its offers."""
    d = product.to_dict()
    low = product.lowest_offer()
    d["price"] = low.price if low else None
    d["store"] = low.retailer.name if low else None
    d["lowest_price"] = d["price"]
    d["retailer_count"] = len(product.live_offers())
    d["offers"] = product.offers
    d["match_score"] = score
    d["match_label"] = classify_score(score)
    return d


@router.get("/search", response_model=SearchResponse)
def search(
    q: str = Query(min_length=2),
    category: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    ai_enabled = bool(ANTHROPIC_API_KEY)
    intent_raw = parse_search_intent(q) if ai_enabled else None

    products = (
        db.query(Product)
        .options(joinedload(Product.offers).joinedload(Offer.retailer))
        .order_by(Product.id)
        .all()
    )
    results = []

    for product in products:
        p_dict = product.to_dict()
        score = calculate_match_score(q, p_dict)

        if intent_raw:
            score = enhance_score_with_intent(score, p_dict, intent_raw)

        eff_category = category or (intent_raw.get("category") if intent_raw else None)
        eff_min = min_price if min_price is not None else (intent_raw.get("min_price") if intent_raw else None)
        eff_max = max_price if max_price is not None else (intent_raw.get("max_price") if intent_raw else None)

        if score < 20:
            continue
        if eff_category and product.category.lower() != eff_category.lower():
            continue

        low = product.lowest_offer()
        effective_price = low.price if low else None
        if eff_min is not None and (effective_price is None or effective_price < eff_min):
            continue
        if eff_max is not None and (effective_price is None or effective_price > eff_max):
            continue

        results.append(_product_to_result_dict(product, score))

    results.sort(key=lambda p: p["match_score"], reverse=True)

    # Two-pass category cap: if the top result scores >= 85, infer the query
    # category from it and cap any cross-category result above 84 to 84.
    # Below 85 at the top, the query is too ambiguous to infer category.
    if results:
        top_score = results[0]["match_score"]
        if top_score >= 85:
            query_category = results[0]["category"]
            for r in results:
                if r["category"] != query_category and r["match_score"] > 84:
                    r["match_score"] = 84
                    r["match_label"] = classify_score(84)

    total = len(results)

    ai_summary = generate_summary(q, total, intent_raw) if intent_raw else ""
    ai_intent = AIIntent(**intent_raw) if intent_raw else None

    start = (page - 1) * limit
    paginated = results[start: start + limit]

    return {
        "query": q,
        "total": total,
        "page": page,
        "limit": limit,
        "results": paginated,
        "ai_intent": ai_intent,
        "ai_summary": ai_summary,
        "ai_enabled": ai_enabled,
    }


@router.get("/products", response_model=ProductsResponse)
def list_products(db: Session = Depends(get_db)):
    products = (
        db.query(Product)
        .options(joinedload(Product.offers).joinedload(Offer.retailer))
        .order_by(Product.id)
        .all()
    )
    for p in products:
        low = p.lowest_offer()
        p.lowest_price = low.price if low else None
        p.retailer_count = len(p.live_offers())
    return {"total": len(products), "products": products}


@router.get("/products/{product_id}", response_model=ProductRead)
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = (
        db.query(Product)
        .options(joinedload(Product.offers).joinedload(Offer.retailer))
        .filter(Product.id == product_id)
        .first()
    )
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    product.lowest_price = product.lowest_offer().price if product.lowest_offer() else None
    product.retailer_count = len(product.live_offers())
    return product


@router.get("/products/{product_id}/offers", response_model=list[OfferRead])
def get_product_offers(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    offers = (
        db.query(Offer)
        .options(joinedload(Offer.retailer))
        .filter(Offer.product_id == product_id)
        .order_by(Offer.price)
        .all()
    )
    return offers


@router.post("/products", response_model=ProductRead, status_code=201)
def create_product(
    product: ProductCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    product_data = product.model_dump(exclude={"price", "store"})
    db_product = Product(**product_data)
    db.add(db_product)
    db.flush()  # get db_product.id before commit

    if product.price is not None and product.store:
        retailer = db.query(Retailer).filter(Retailer.name == product.store).first()
        if not retailer:
            retailer = Retailer(name=product.store)
            db.add(retailer)
            db.flush()
        offer = Offer(
            product_id=db_product.id,
            retailer_id=retailer.id,
            price=product.price,
        )
        db.add(offer)

    db.commit()
    db.refresh(db_product)
    db_product.lowest_price = db_product.lowest_offer().price if db_product.lowest_offer() else None
    db_product.retailer_count = len(db_product.live_offers())
    return db_product


@router.patch("/products/{product_id}", response_model=ProductRead)
def update_product(
    product_id: int,
    updates: ProductUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    for field, value in updates.model_dump(exclude_none=True).items():
        setattr(product, field, value)
    db.commit()
    db.refresh(product)
    product.lowest_price = product.lowest_offer().price if product.lowest_offer() else None
    product.retailer_count = len(product.live_offers())
    return product


@router.delete("/products/{product_id}", status_code=204)
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    db.delete(product)
    db.commit()
