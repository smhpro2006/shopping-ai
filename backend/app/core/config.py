from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = Path(__file__).resolve().parent.parent.parent / ".env"


class Settings(BaseSettings):
    # Required — no default. App raises ValidationError at startup if unset.
    SECRET_KEY: str

    DATABASE_URL: str = "sqlite:///./shopping_ai.db"
    ANTHROPIC_API_KEY: str = ""
    TOKEN_EXPIRE_HOURS: int = 24
    ALGORITHM: str = "HS256"

    # eBay Browse API
    EBAY_APP_ID: str = ""
    EBAY_CERT_ID: str = ""
    EBAY_ENVIRONMENT: str = "sandbox"  # "sandbox" or "production"

    # Collector tuning
    COLLECTOR_OFFERS_PER_PRODUCT: int = 5
    COLLECTOR_MIN_MATCH_SCORE: int = 85

    model_config = SettingsConfigDict(env_file=str(_ENV_FILE), extra="ignore")


settings = Settings()

# Module-level re-exports for backward compatibility with existing imports
SECRET_KEY = settings.SECRET_KEY
DATABASE_URL = settings.DATABASE_URL
ANTHROPIC_API_KEY = settings.ANTHROPIC_API_KEY
TOKEN_EXPIRE_HOURS = settings.TOKEN_EXPIRE_HOURS
ALGORITHM = settings.ALGORITHM
EBAY_APP_ID = settings.EBAY_APP_ID
EBAY_CERT_ID = settings.EBAY_CERT_ID
EBAY_ENVIRONMENT = settings.EBAY_ENVIRONMENT
COLLECTOR_OFFERS_PER_PRODUCT = settings.COLLECTOR_OFFERS_PER_PRODUCT
COLLECTOR_MIN_MATCH_SCORE = settings.COLLECTOR_MIN_MATCH_SCORE
