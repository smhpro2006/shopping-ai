"""Admin coupon CRUD endpoints — requires Bearer auth."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.security import get_current_user
from backend.app.models.coupon import Coupon
from backend.app.models.user import User

router = APIRouter(prefix="/admin/coupons", tags=["coupons"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class CouponCreate(BaseModel):
    code: str
    discount_type: str  # "percentage" | "fixed"
    discount_value: float
    retailer_id: Optional[int] = None
    product_id: Optional[int] = None
    min_order_value: Optional[float] = None
    expires_at: Optional[datetime] = None


class CouponOut(BaseModel):
    id: int
    code: str
    discount_type: str
    discount_value: float
    retailer_id: Optional[int] = None
    product_id: Optional[int] = None
    min_order_value: Optional[float] = None
    expires_at: Optional[datetime] = None
    is_active: bool
    source: str
    verified_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("", response_model=CouponOut, status_code=201)
def create_coupon(
    data: CouponCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    existing = db.query(Coupon).filter(Coupon.code == data.code).first()
    if existing:
        raise HTTPException(status_code=409, detail="Coupon code already exists")
    coupon = Coupon(**data.model_dump())
    db.add(coupon)
    db.commit()
    db.refresh(coupon)
    return coupon


@router.get("", response_model=list[CouponOut])
def list_coupons(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return db.query(Coupon).filter(Coupon.is_active.is_(True)).order_by(Coupon.id).all()


@router.delete("/{coupon_id}", status_code=204)
def delete_coupon(
    coupon_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    coupon = db.query(Coupon).filter(Coupon.id == coupon_id).first()
    if not coupon:
        raise HTTPException(status_code=404, detail="Coupon not found")
    coupon.is_active = False
    db.commit()
