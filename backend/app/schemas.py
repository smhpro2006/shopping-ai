from pydantic import BaseModel, EmailStr
from typing import List, Optional


# ── Retailers ─────────────────────────────────────────────

class RetailerRead(BaseModel):
    id: int
    name: str
    url: Optional[str] = None

    model_config = {"from_attributes": True}


# ── Offers ────────────────────────────────────────────────

class OfferRead(BaseModel):
    id: int
    retailer: RetailerRead
    price: float
    currency: str
    url: Optional[str] = None
    availability: Optional[str] = None
    condition: str
    source: Optional[str] = None

    model_config = {"from_attributes": True}


# ── Products ──────────────────────────────────────────────

class ProductBase(BaseModel):
    brand: str
    model: str
    name: str
    category: str
    image_url: Optional[str] = None


class ProductCreate(ProductBase):
    # price and store accepted for convenience — internally creates a default Offer
    price: Optional[float] = None
    store: Optional[str] = None


class ProductUpdate(BaseModel):
    brand: Optional[str] = None
    model: Optional[str] = None
    name: Optional[str] = None
    category: Optional[str] = None
    image_url: Optional[str] = None


class ProductRead(ProductBase):
    id: int
    offers: List[OfferRead] = []
    lowest_price: Optional[float] = None
    retailer_count: int = 0

    model_config = {"from_attributes": True}


class ProductResult(ProductRead):
    # price and store preserved for frontend backward compatibility (= lowest offer)
    price: Optional[float] = None
    store: Optional[str] = None
    match_score: int
    match_label: str  # Exact Match | Very Similar | Similar | Alternative (§12)


class AIIntent(BaseModel):
    brand: Optional[str] = None
    model: Optional[str] = None
    category: Optional[str] = None
    max_price: Optional[float] = None
    min_price: Optional[float] = None
    features: List[str] = []
    language: str = "en"


class SearchResponse(BaseModel):
    query: str
    total: int
    page: int
    limit: int
    results: List[ProductResult]
    ai_intent: Optional[AIIntent] = None
    ai_summary: Optional[str] = None
    ai_enabled: bool = False


class ProductsResponse(BaseModel):
    total: int
    products: List[ProductRead]


# ── Auth ──────────────────────────────────────────────────

class UserRegister(BaseModel):
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserRead(BaseModel):
    id: int
    email: str
    is_active: bool

    model_config = {"from_attributes": True}
