"""Tests for collection health monitoring endpoints and stale-threshold logic."""
import pytest
from datetime import datetime, timezone, timedelta

from backend.app.core.database import get_db
from backend.app.models.collection_run import CollectionRun


# ── helpers ────────────────────────────────────────────────────────────────────

def _db():
    """Return a raw session for direct DB manipulation in tests. Caller must close."""
    return next(get_db())


def _clear(db):
    db.query(CollectionRun).delete()
    db.commit()


def _insert(db, status: str, hours_ago: float, **kwargs):
    when = datetime.now(timezone.utc) - timedelta(hours=hours_ago)
    db.add(CollectionRun(
        started_at=when,
        finished_at=when,
        status=status,
        products_processed=kwargs.get("products_processed", 20),
        offers_stored=kwargs.get("offers_stored", 118),
        calls_made=kwargs.get("calls_made", 20),
        error_count=kwargs.get("error_count", 0),
        error_detail=kwargs.get("error_detail", None),
    ))
    db.commit()


# ── GET /api/v1/health/collection ─────────────────────────────────────────────

class TestCollectionHealthEndpoint:
    def test_empty_table_returns_unknown(self, client):
        """Table exists but has no rows — must return unknown, not 500."""
        db = _db()
        _clear(db)
        db.close()
        resp = client.get("/api/v1/health/collection")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "unknown"
        assert body["last_successful_run_at"] is None
        assert body["hours_since_last_run"] is None
        assert body["offers_in_last_run"] is None

    def test_healthy_after_recent_success(self, client):
        db = _db()
        _clear(db)
        _insert(db, "success", hours_ago=5, offers_stored=118)
        db.close()
        resp = client.get("/api/v1/health/collection")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "healthy"
        assert body["hours_since_last_run"] <= 6
        assert body["offers_in_last_run"] == 118
        assert body["last_successful_run_at"] is not None

    def test_stale_when_last_success_over_26h_ago(self, client):
        db = _db()
        _clear(db)
        _insert(db, "success", hours_ago=27)
        db.close()
        resp = client.get("/api/v1/health/collection")
        assert resp.json()["status"] == "stale"

    def test_healthy_at_25_9_hours(self, client):
        """Just inside the 26-hour window must remain healthy."""
        db = _db()
        _clear(db)
        _insert(db, "success", hours_ago=25.9)
        db.close()
        resp = client.get("/api/v1/health/collection")
        assert resp.json()["status"] == "healthy"

    def test_stale_at_26_1_hours(self, client):
        """Just past the 26-hour window must be stale."""
        db = _db()
        _clear(db)
        _insert(db, "success", hours_ago=26.1)
        db.close()
        resp = client.get("/api/v1/health/collection")
        assert resp.json()["status"] == "stale"

    def test_failed_when_last_run_failed_after_success(self, client):
        """Recent success followed by a later failure → failed."""
        db = _db()
        _clear(db)
        _insert(db, "success", hours_ago=10)
        _insert(db, "failed", hours_ago=3, error_detail="EbayAuthError: invalid_client")
        db.close()
        resp = client.get("/api/v1/health/collection")
        body = resp.json()
        assert body["status"] == "failed"
        assert "EbayAuthError" in (body["last_run_error"] or "")

    def test_healthy_after_recovery(self, client):
        """Old failure followed by a later success → healthy (failure is resolved)."""
        db = _db()
        _clear(db)
        _insert(db, "failed", hours_ago=15)
        _insert(db, "success", hours_ago=5)
        db.close()
        resp = client.get("/api/v1/health/collection")
        assert resp.json()["status"] == "healthy"

    def test_only_failed_runs_returns_unknown(self, client):
        """If no successful run exists at all, status is unknown regardless of failures."""
        db = _db()
        _clear(db)
        _insert(db, "failed", hours_ago=2)
        db.close()
        resp = client.get("/api/v1/health/collection")
        # last_success is None → unknown (we haven't even had a good run yet)
        assert resp.json()["status"] == "unknown"

    def test_multiple_successes_uses_most_recent(self, client):
        """hours_since is measured against the most recent success, not the first."""
        db = _db()
        _clear(db)
        _insert(db, "success", hours_ago=30)   # old, would be stale alone
        _insert(db, "success", hours_ago=3)    # recent — should win
        db.close()
        resp = client.get("/api/v1/health/collection")
        assert resp.json()["status"] == "healthy"


# ── GET /health and GET /api/v1/health ────────────────────────────────────────

class TestMainHealthEndpoint:
    def test_ok_when_no_runs(self, client):
        """Empty collection_runs table must NOT cause degraded — fresh deployment."""
        db = _db()
        _clear(db)
        db.close()
        for path in ["/health", "/api/v1/health"]:
            resp = client.get(path)
            assert resp.status_code == 200, f"{path} returned {resp.status_code}"
            assert resp.json()["status"] == "ok"

    def test_ok_and_collection_unknown_when_no_runs(self, client):
        db = _db()
        _clear(db)
        db.close()
        resp = client.get("/health")
        assert resp.json()["collection"] == "unknown"

    def test_ok_when_collection_healthy(self, client):
        db = _db()
        _clear(db)
        _insert(db, "success", hours_ago=5)
        db.close()
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
        assert resp.json()["collection"] == "healthy"

    def test_503_when_collection_stale(self, client):
        """Uptime monitors pointing at /health get a 503 when collection is stale."""
        db = _db()
        _clear(db)
        _insert(db, "success", hours_ago=30)
        db.close()
        resp = client.get("/health")
        assert resp.status_code == 503
        body = resp.json()
        assert body["status"] == "degraded"
        assert body["collection"] == "stale"

    def test_503_when_collection_failed(self, client):
        db = _db()
        _clear(db)
        _insert(db, "success", hours_ago=10)
        _insert(db, "failed", hours_ago=2)
        db.close()
        resp = client.get("/health")
        assert resp.status_code == 503
        body = resp.json()
        assert body["status"] == "degraded"
        assert body["collection"] == "failed"

    def test_versioned_health_path_same_behaviour(self, client):
        db = _db()
        _clear(db)
        _insert(db, "success", hours_ago=30)
        db.close()
        resp = client.get("/api/v1/health")
        assert resp.status_code == 503

    def test_health_ok_after_recovery(self, client):
        db = _db()
        _clear(db)
        _insert(db, "failed", hours_ago=15)
        _insert(db, "success", hours_ago=4)
        db.close()
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


# ── GET /api/v1/admin/collection/runs ─────────────────────────────────────────

class TestAdminCollectionRuns:
    _TOKEN: str | None = None

    def _get_token(self, client) -> str:
        if TestAdminCollectionRuns._TOKEN:
            return TestAdminCollectionRuns._TOKEN
        import uuid
        email = f"healthadmin-{uuid.uuid4().hex[:8]}@test.com"
        client.post("/api/v1/auth/register", json={
            "email": email, "password": "testpass123"
        })
        resp = client.post("/api/v1/auth/login", json={
            "email": email, "password": "testpass123"
        })
        TestAdminCollectionRuns._TOKEN = resp.json()["access_token"]
        return TestAdminCollectionRuns._TOKEN

    def test_unauthenticated_returns_401(self, client):
        resp = client.get("/api/v1/admin/collection/runs")
        assert resp.status_code == 401

    def test_authenticated_returns_list(self, client):
        db = _db()
        _clear(db)
        _insert(db, "success", hours_ago=5, offers_stored=118, calls_made=20)
        db.close()
        token = self._get_token(client)
        resp = client.get(
            "/api/v1/admin/collection/runs",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        runs = resp.json()
        assert isinstance(runs, list)
        assert len(runs) >= 1
        run = runs[0]
        assert run["status"] == "success"
        assert run["offers_stored"] == 118
        assert run["duration_seconds"] is not None

    def test_capped_at_20_runs(self, client):
        db = _db()
        _clear(db)
        for i in range(25):
            _insert(db, "success", hours_ago=i + 1)
        db.close()
        token = self._get_token(client)
        resp = client.get(
            "/api/v1/admin/collection/runs",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 20

    def test_empty_table_returns_empty_list(self, client):
        db = _db()
        _clear(db)
        db.close()
        token = self._get_token(client)
        resp = client.get(
            "/api/v1/admin/collection/runs",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json() == []
