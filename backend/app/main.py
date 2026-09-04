from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from backend.app.core.database import Base, engine, get_db
from backend.app.models.product import Product
from backend.app.models.user import User  # noqa: F401
from backend.app.products import PRODUCTS
from backend.app.api import auth, products


def init_db():
    Base.metadata.create_all(bind=engine)

    # Add image_url column if missing (safe migration for existing DBs)
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE products ADD COLUMN image_url TEXT"))
            conn.commit()
        except Exception:
            pass

    db = next(get_db())
    try:
        if db.query(Product).count() == 0:
            for p in PRODUCTS:
                db.add(Product(**p))
            db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Shopping AI",
    description="AI-powered shopping intelligence platform",
    version="0.4.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:4173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(products.router)


@app.get("/")
def home():
    return {
        "message": "Shopping AI API is running",
        "version": "0.4.0"
    }
