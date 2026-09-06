"""Tests for admin coupon endpoints."""
import pytest

_EMAIL = "coupon_test@example.com"
_PASSWORD = "testpass123"
_COUPON_CODE = "SAVE20TEST"


@pytest.fixture(scope="module")
def auth_token(client):
    """Register a user and return a valid Bearer token."""
    client.post("/api/v1/auth/register", json={"email": _EMAIL, "password": _PASSWORD})
    resp = client.post("/api/v1/auth/login", json={"email": _EMAIL, "password": _PASSWORD})
    assert resp.status_code == 200
    return resp.json()["access_token"]


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    return {"Authorization": f"Bearer {auth_token}"}


class TestCoupons:
    def test_unauthenticated_create_returns_401(self, client):
        resp = client.post("/api/v1/admin/coupons", json={
            "code": "NOAUTH",
            "discount_type": "percentage",
            "discount_value": 10.0,
        })
        assert resp.status_code == 401

    def test_create_coupon_returns_201(self, client, auth_headers):
        resp = client.post("/api/v1/admin/coupons", headers=auth_headers, json={
            "code": _COUPON_CODE,
            "discount_type": "percentage",
            "discount_value": 20.0,
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["code"] == _COUPON_CODE
        assert data["discount_type"] == "percentage"
        assert data["discount_value"] == 20.0
        assert data["is_active"] is True

    def test_list_coupons_returns_created(self, client, auth_headers):
        resp = client.get("/api/v1/admin/coupons", headers=auth_headers)
        assert resp.status_code == 200
        codes = [c["code"] for c in resp.json()]
        assert _COUPON_CODE in codes

    def test_delete_coupon_soft_deletes(self, client, auth_headers):
        # Get the coupon id
        list_resp = client.get("/api/v1/admin/coupons", headers=auth_headers)
        coupon = next(c for c in list_resp.json() if c["code"] == _COUPON_CODE)
        coupon_id = coupon["id"]

        # Delete (soft)
        del_resp = client.delete(f"/api/v1/admin/coupons/{coupon_id}", headers=auth_headers)
        assert del_resp.status_code == 204

        # Must not appear in list anymore
        list_resp2 = client.get("/api/v1/admin/coupons", headers=auth_headers)
        codes = [c["code"] for c in list_resp2.json()]
        assert _COUPON_CODE not in codes

    def test_unauthenticated_list_returns_401(self, client):
        resp = client.get("/api/v1/admin/coupons")
        assert resp.status_code == 401
