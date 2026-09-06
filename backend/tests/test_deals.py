"""Tests for GET /api/v1/deals."""
import pytest


class TestDealsEndpoint:
    def test_deals_endpoint_returns_200(self, client):
        resp = client.get("/api/v1/deals")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_deals_excludes_single_offer_products(self, client):
        """All returned deals must have retailer_count >= 2."""
        resp = client.get("/api/v1/deals")
        assert resp.status_code == 200
        for item in resp.json():
            assert item["retailer_count"] >= 2, (
                f"Deal item {item['name']} has only {item['retailer_count']} retailer(s)"
            )

    def test_deals_sorted_by_spread_descending(self, client):
        """Results must be sorted by price_spread_pct descending."""
        resp = client.get("/api/v1/deals")
        assert resp.status_code == 200
        items = resp.json()
        if len(items) >= 2:
            for i in range(len(items) - 1):
                assert items[i]["price_spread_pct"] >= items[i + 1]["price_spread_pct"], (
                    f"Items not sorted: index {i} spread {items[i]['price_spread_pct']} "
                    f"< index {i+1} spread {items[i+1]['price_spread_pct']}"
                )

    def test_deals_response_fields(self, client):
        """If any deals exist, verify all required fields are present."""
        resp = client.get("/api/v1/deals")
        assert resp.status_code == 200
        for item in resp.json():
            assert "id" in item
            assert "name" in item
            assert "brand" in item
            assert "category" in item
            assert "lowest_price" in item
            assert "highest_price" in item
            assert "price_spread_pct" in item
            assert "retailer_count" in item
            assert item["lowest_price"] <= item["highest_price"]

    def test_deals_returns_at_most_20(self, client):
        """Response must never exceed 20 items."""
        resp = client.get("/api/v1/deals")
        assert resp.status_code == 200
        assert len(resp.json()) <= 20
