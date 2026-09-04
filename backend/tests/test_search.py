"""API-level search tests — exercise the full request/response cycle."""
import pytest


class TestSearchEndpoint:
    def test_health(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}

    def test_versioned_health(self, client):
        r = client.get("/api/v1/health")
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}

    def test_search_requires_query(self, client):
        r = client.get("/search")
        assert r.status_code == 422

    def test_search_query_too_short(self, client):
        r = client.get("/search?q=s")
        assert r.status_code == 422

    def test_search_returns_results(self, client):
        r = client.get("/search?q=sony+xm5")
        assert r.status_code == 200
        body = r.json()
        assert body["total"] >= 1
        assert len(body["results"]) >= 1

    def test_search_result_has_expected_fields(self, client):
        r = client.get("/search?q=sony+xm5")
        result = r.json()["results"][0]
        for field in ("id", "brand", "model", "name", "category",
                      "match_score", "match_label", "price", "store",
                      "lowest_price", "retailer_count", "offers"):
            assert field in result, f"missing field: {field}"

    def test_search_result_score_label_consistent(self, client):
        r = client.get("/search?q=sony+wh1000xm5")
        result = r.json()["results"][0]
        score = result["match_score"]
        label = result["match_label"]
        if score >= 95:
            assert label == "Exact Match"
        elif score >= 85:
            assert label == "Very Similar"
        elif score >= 70:
            assert label == "Similar"
        else:
            assert label == "Alternative"

    def test_unrelated_query_returns_no_results(self, client):
        r = client.get("/search?q=refrigerator+washing+machine")
        assert r.status_code == 200
        assert r.json()["total"] == 0

    def test_versioned_search_matches_unversioned(self, client):
        r1 = client.get("/search?q=airpods")
        r2 = client.get("/api/v1/search?q=airpods")
        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r1.json()["total"] == r2.json()["total"]


class TestCanonicalProducts:
    def test_product_count_is_canonical(self, client):
        # 20 canonical products; Sony WH-1000XM5 appears at two retailers but must be ONE product
        r = client.get("/products")
        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 20, (
            f"Expected 20 canonical products, got {body['total']}. "
            "Sony WH-1000XM5 must not be duplicated."
        )

    def test_seed_offers_excluded_from_retailer_count(self, client):
        # source="seed" offers must not appear in retailer_count.
        # The test DB has only seed offers for Sony → count must be 0.
        r = client.get("/products")
        products = r.json()["products"]
        sony = next(p for p in products if p["brand"] == "Sony" and p["model"] == "WH-1000XM5")
        assert sony["retailer_count"] == 0, (
            f"retailer_count must exclude source='seed' offers; "
            f"got {sony['retailer_count']}"
        )

    def test_seed_offers_excluded_from_lowest_price(self, client):
        # source="seed" offers must not appear in lowest_price.
        # The test DB has only seed offers for Sony → lowest_price must be None.
        r = client.get("/products")
        products = r.json()["products"]
        sony = next(p for p in products if p["brand"] == "Sony" and p["model"] == "WH-1000XM5")
        assert sony["lowest_price"] is None, (
            f"lowest_price must exclude source='seed' offers; "
            f"got {sony['lowest_price']}"
        )

    def test_offers_endpoint_returns_offers_sorted_by_price(self, client):
        products = client.get("/products").json()["products"]
        sony_id = next(p["id"] for p in products if p["brand"] == "Sony" and p["model"] == "WH-1000XM5")

        r = client.get(f"/products/{sony_id}/offers")
        assert r.status_code == 200
        offers = r.json()
        assert len(offers) == 2
        prices = [o["price"] for o in offers]
        assert prices == sorted(prices)
        assert offers[0]["retailer"]["name"] == "Walmart"

    def test_offers_endpoint_404_for_unknown_product(self, client):
        r = client.get("/products/99999/offers")
        assert r.status_code == 404


class TestOfferSchema:
    def test_offer_has_retailer_name(self, client):
        products = client.get("/products").json()["products"]
        sony_id = next(p["id"] for p in products if p["brand"] == "Sony" and p["model"] == "WH-1000XM5")
        offers = client.get(f"/products/{sony_id}/offers").json()
        for offer in offers:
            assert "retailer" in offer
            assert "name" in offer["retailer"]
            assert offer["retailer"]["name"] in ("Amazon", "Walmart", "Best Buy")

    def test_search_result_offers_embedded(self, client):
        r = client.get("/search?q=sony+xm5")
        result = r.json()["results"][0]
        assert isinstance(result["offers"], list)
        assert len(result["offers"]) == 2
        retailer_names = {o["retailer"]["name"] for o in result["offers"]}
        assert retailer_names == {"Amazon", "Walmart"}
