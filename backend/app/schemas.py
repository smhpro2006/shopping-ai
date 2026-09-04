from pydantic import BaseModel, EmailStr
from typing import List, Optional


# ── Products ──────────────────────────────────────────────

class ProductBase(BaseModel):
    brand: str
    model: str
    name: str
    category: str
    price: float
    store: str
    image_url: Optional[str] = None


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    brand: Optional[str] = None
    model: Optional[str] = None
    name: Optional[str] = None
    category: Optional[str] = None
    price: Optional[float] = None
    store: Optional[str] = None
    image_url: Optional[str] = None


class ProductRead(ProductBase):
    id: int

    model_config = {"from_attributes": True}


class ProductResult(ProductRead):
    match_score: int


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
