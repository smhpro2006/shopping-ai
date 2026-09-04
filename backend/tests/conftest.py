import os
import pytest

# Set DATABASE_URL before any backend.app import — pydantic-settings reads env at instantiation.
# This ensures pytest NEVER connects to a remote Postgres instance regardless of .env contents.
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_shopping_ai.db")
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")

from fastapi.testclient import TestClient  # noqa: E402
from backend.app.main import app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _isolate_test_db():
    db_path = "./test_shopping_ai.db"
    try:
        os.remove(db_path)
    except FileNotFoundError:
        pass
    yield
    try:
        os.remove(db_path)
    except FileNotFoundError:
        pass


@pytest.fixture(scope="session")
def client():
    """Single TestClient for the session; triggers lifespan (init_db) once."""
    with TestClient(app) as c:
        yield c
