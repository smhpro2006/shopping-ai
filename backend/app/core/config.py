import os
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY: str = os.getenv("SECRET_KEY", "insecure-default-change-me")
DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./shopping_ai.db")
ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
TOKEN_EXPIRE_HOURS: int = 24
ALGORITHM: str = "HS256"
