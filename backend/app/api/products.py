from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.config import ANTHROPIC_API_KEY
from backend.app.core.security import get_current_user
from backend.app.models.product import Product
from backend.app.models.user import User
from backend.app.product_matching import calculate_match_score
from backend.app.services.ai_search import parse_search_intent, enhance_score_with_intent, generate_summary
from backend.app.schemas import (
    SearchResponse, AIIntent, ProductCreate, ProductUpdate, ProductRead, ProductsResponse
)

router = APIRouter(tags=["products"])


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

    products = db.query(Product).all()
    results = []

    for product in products:
        p_dict = product.to_dict()
        score = calculate_match_score(q, p_dict)

        if intent_raw:
            score = enhance_score_with_intent(score, p_dict, intent_raw)

        # Explicit params take priority; AI-detected values fill the gaps
        eff_category = category or (intent_raw.get("category") if intent_raw else None)
        eff_min = min_price if min_price is not None else (intent_raw.get("min_price") if intent_raw else None)
        eff_max = max_price if max_price is not None else (intent_raw.get("max_price") if intent_raw else None)

        if score < 20:
            continue
        if eff_category and p_dict["category"].lower() != eff_category.lower():
            continue
        if eff_min is not None and p_dict["price"] < eff_min:
            continue
        if eff_max is not None and p_dict["price"] > eff_max:
            continue

        p_dict["match_score"] = score
        results.append(p_dict)

    results.sort(key=lambda p: p["match_score"], reverse=True)
    total = len(results)

    ai_summary = generate_summary(q, total, intent_raw) if intent_raw else ""
    ai_intent = AIIntent(**intent_raw) if intent_raw else None

    start = (page - 1) * limit
    paginated = results[start : start + limit]

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
    products = db.query(Product).all()
    return {"total": len(products), "products": products}


@router.post("/products", response_model=ProductRead, status_code=201)
def create_product(
    product: ProductCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    db_product = Product(**product.model_dump())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
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
