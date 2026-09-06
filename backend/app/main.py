from contextlib import asynccontextmanager
from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware

from backend.app.core.config import settings
from backend.app.core.database import Base, engine, get_db
from backend.app.core.logging import configure_logging, logger
from backend.app.models.product import Product
from backend.app.models.retailer import Retailer
from backend.app.models.offer import Offer
from backend.app.models.user import User  # noqa: F401
from backend.app.products import PRODUCTS, RETAILERS, OFFERS
from backend.app.api import auth, products, deals

configure_logging()


def init_db():
    Base.metadata.create_all(bind=engine)

    db = next(get_db())
    try:
        if db.query(Product).count() > 0:
            return

        # Seed retailers
        retailer_map = {}
        for r in RETAILERS:
            retailer = Retailer(**r)
            db.add(retailer)
            db.flush()
            retailer_map[r["name"]] = retailer.id

        # Seed canonical products
        product_ids = []
        for p in PRODUCTS:
            product = Product(**p)
            db.add(product)
            db.flush()
            product_ids.append(product.id)

        # Seed offers
        for product_idx, retailer_name, price in OFFERS:
            offer = Offer(
                product_id=product_ids[product_idx],
                retailer_id=retailer_map[retailer_name],
                price=price,
                source="seed",
            )
            db.add(offer)

        db.commit()
        logger.info("Database seeded: %d products, %d retailers, %d offers",
                    len(PRODUCTS), len(RETAILERS), len(OFFERS))
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Shopping AI starting up")
    init_db()
    yield
    logger.info("Shopping AI shutting down")


app = FastAPI(
    title="Shopping AI",
    description="AI-powered shopping intelligence platform",
    version="0.5.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:4173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Versioned router
_v1 = APIRouter(prefix="/api/v1")
_v1.include_router(auth.router)
_v1.include_router(products.router)
_v1.include_router(deals.router)
app.include_router(_v1)

# Unversioned routes kept for backward compatibility
app.include_router(auth.router)
app.include_router(products.router)


@app.get("/")
def home():
    return {
        "message": "Shopping AI API is running",
        "version": app.version,
    }


@app.get("/health", tags=["health"])
@app.get("/api/v1/health", tags=["health"])
def health():
    return {"status": "ok"}
