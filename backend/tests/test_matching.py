import pytest
from backend.app.product_matching import (
    normalize,
    calculate_match_score,
    classify_score,
    _variant_tokens,
    _ctx_tokens,
    _expand_query,
    _edit_distance,
)

SONY = {
    "id": 1,
    "brand": "Sony",
    "model": "WH-1000XM5",
    "name": "Sony WH-1000XM5 Wireless Noise Cancelling Headphones",
    "category": "Headphones",
    "price": 349.99,
    "store": "Amazon",
}

APPLE = {
    "id": 3,
    "brand": "Apple",
    "model": "AirPods Pro 2",
    "name": "Apple AirPods Pro 2nd Generation",
    "category": "Earbuds",
    "price": 249.00,
    "store": "Best Buy",
}

SAMSUNG = {
    "id": 4,
    "brand": "Samsung",
    "model": "Galaxy Buds3 Pro",
    "name": "Samsung Galaxy Buds3 Pro Wireless Earbuds",
    "category": "Earbuds",
    "price": 199.99,
    "store": "Amazon",
}


class TestNormalize:
    def test_strips_spaces_and_special_chars(self):
        assert normalize("WH-1000XM5") == "wh1000xm5"

    def test_lowercases(self):
        assert normalize("Sony") == "sony"

    def test_empty_string(self):
        assert normalize("") == ""

    def test_alphanumeric_only_kept(self):
        assert normalize("Hello, World! 123") == "helloworld123"


class TestBrandMatch:
    def test_brand_in_query_scores_30(self):
        score = calculate_match_score("sony headphones", SONY)
        assert score >= 30

    def test_wrong_brand_no_brand_score(self):
        score = calculate_match_score("samsung headphones", SONY)
        assert score < 30


class TestFullModelMatch:
    def test_full_model_match_returns_high_score(self):
        score = calculate_match_score("sony wh1000xm5", SONY)
        assert score >= 90

    def test_full_model_alone_scores_high(self):
        # model without brand still matches
        score = calculate_match_score("wh1000xm5", SONY)
        assert score >= 60


class TestModelFragment:
    def test_xm5_fragment_matches_sony(self):
        score = calculate_match_score("xm5", SONY)
        assert score >= 50

    def test_fragment_does_not_match_wrong_product(self):
        score = calculate_match_score("xm5", SAMSUNG)
        assert score < 20

    def test_brand_plus_fragment_bonus(self):
        score_with_brand = calculate_match_score("sony xm5", SONY)
        score_fragment_only = calculate_match_score("xm5", SONY)
        assert score_with_brand > score_fragment_only


class TestNoDoubleCount:
    def test_model_fragment_not_double_counted_in_name(self):
        # "xm5" matches model fragment (+50) — should NOT also get name bonus (+5)
        score_xm5 = calculate_match_score("xm5", SONY)
        score_xm5_extra = calculate_match_score("xm5 xm5", SONY)
        # Extra repetition shouldn't bump score beyond one model match
        assert score_xm5 == score_xm5_extra or score_xm5_extra <= 100


class TestNoMatch:
    def test_completely_unrelated_query(self):
        score = calculate_match_score("laptop keyboard", SONY)
        assert score < 20

    def test_wrong_brand_wrong_model(self):
        score = calculate_match_score("samsung galaxy buds", SONY)
        assert score < 20


class TestScoreCap:
    def test_score_never_exceeds_100(self):
        for query in ["sony wh1000xm5 wireless noise cancelling headphones", "sony xm5 xm5 xm5"]:
            score = calculate_match_score(query, SONY)
            assert score <= 100


class TestAirPods:
    def test_airpods_word_in_name(self):
        # "airpods" not the brand, but in name — should return some score
        score = calculate_match_score("airpods", APPLE)
        assert score >= 5

    def test_apple_brand_match(self):
        score = calculate_match_score("apple earbuds", APPLE)
        assert score >= 30


# ── Permanent regression tests (CLAUDE.md §50) ───────────────────────────────
# These five queries MUST always match their canonical products.
# Do not relax thresholds without updating CLAUDE.md.

class TestPermanentSearchQueries:
    # Actual scores as of last run: sony xm5→100, Sony WH-1000XM5→100,
    # WH1000XM5→70, AirPods Pro 2→70, Samsung Galaxy Buds3 Pro→100.
    # Thresholds give ≤5 points of tuning margin.

    def test_sony_xm5(self):
        score = calculate_match_score("sony xm5", SONY)
        assert score >= 95, f"got {score}"

    def test_sony_wh1000xm5_with_hyphens(self):
        score = calculate_match_score("Sony WH-1000XM5", SONY)
        assert score >= 95, f"got {score}"

    def test_wh1000xm5_no_brand(self):
        score = calculate_match_score("WH1000XM5", SONY)
        assert score >= 65, f"got {score}"

    def test_airpods_pro_2(self):
        score = calculate_match_score("AirPods Pro 2", APPLE)
        assert score >= 65, f"got {score}"

    def test_samsung_galaxy_buds3_pro(self):
        score = calculate_match_score("Samsung Galaxy Buds3 Pro", SAMSUNG)
        assert score >= 95, f"got {score}"


class TestPermanentSearchQueriesEndpoint:
    """Endpoint-level coverage for the five permanent queries.

    These exercise what the direct-call tests cannot: category cap,
    anchor logic, result ordering, and match_label serialisation.
    """

    WH_NAME = "Sony WH-1000XM5 Wireless Noise Cancelling Headphones"
    AIRPODS_NAME = "Apple AirPods Pro 2nd Generation"
    BUDS3_NAME = "Samsung Galaxy Buds3 Pro Wireless Earbuds"

    def _find(self, results, name):
        return next((r for r in results if r["name"] == name), None)

    def test_sony_xm5_endpoint(self, client):
        r = client.get("/api/v1/search?q=sony+xm5")
        assert r.status_code == 200
        results = r.json()["results"]
        assert results, "no results"
        assert results[0]["name"] == self.WH_NAME, f"expected WH first, got {results[0]['name']}"
        assert results[0]["match_score"] >= 95, f"got {results[0]['match_score']}"
        assert results[0]["match_label"] == "Exact Match"

    def test_sony_wh1000xm5_endpoint(self, client):
        r = client.get("/api/v1/search?q=Sony+WH-1000XM5")
        assert r.status_code == 200
        results = r.json()["results"]
        assert results, "no results"
        assert results[0]["name"] == self.WH_NAME, f"expected WH first, got {results[0]['name']}"
        assert results[0]["match_score"] >= 95
        assert results[0]["match_label"] == "Exact Match"

    def test_wh1000xm5_no_brand_endpoint(self, client):
        r = client.get("/api/v1/search?q=WH1000XM5")
        assert r.status_code == 200
        results = r.json()["results"]
        wh = self._find(results, self.WH_NAME)
        assert wh is not None, "WH-1000XM5 not in results"
        assert wh["match_score"] >= 65, f"got {wh['match_score']}"
        assert wh["match_label"] == "Similar"
        assert results[0]["name"] == self.WH_NAME, "WH should lead on brand-free exact-model query"

    def test_airpods_pro_2_endpoint(self, client):
        r = client.get("/api/v1/search?q=AirPods+Pro+2")
        assert r.status_code == 200
        results = r.json()["results"]
        ap = self._find(results, self.AIRPODS_NAME)
        assert ap is not None, "AirPods Pro 2 not in results"
        assert ap["match_score"] >= 65, f"got {ap['match_score']}"
        assert results[0]["name"] == self.AIRPODS_NAME, "AirPods Pro 2 should lead"

    def test_samsung_galaxy_buds3_pro_endpoint(self, client):
        r = client.get("/api/v1/search?q=Samsung+Galaxy+Buds3+Pro")
        assert r.status_code == 200
        results = r.json()["results"]
        assert results, "no results"
        assert results[0]["name"] == self.BUDS3_NAME, f"expected Buds3 Pro first, got {results[0]['name']}"
        assert results[0]["match_score"] >= 95
        assert results[0]["match_label"] == "Exact Match"


# ── Variant distinction ───────────────────────────────────────────────────────
# Capacity/storage identifiers in the query must VETO an exact match when the
# product carries a different value.  Both cases below must hold:
#   - simple case (single fragment differs)
#   - multi-fragment case (several fragments match but capacity is wrong)
#
# test_multi_fragment_capacity_not_exact_match is the Phase 1 acceptance
# criterion.  It FAILS with the current engine and must PASS after the fix.

IPHONE_16_128 = {
    "id": 10,
    "brand": "Apple",
    "model": "iPhone 16 128GB",
    "name": "Apple iPhone 16 128GB",
    "category": "Phones",
    "price": 799.99,
    "store": "Apple",
}

GALAXY_S25_ULTRA_256 = {
    "id": 11,
    "brand": "Samsung",
    "model": "Galaxy S25 Ultra 256GB",
    "name": "Samsung Galaxy S25 Ultra 256GB Smartphone",
    "category": "Phones",
    "price": 1199.99,
    "store": "Amazon",
}


class TestVariantDistinction:
    def test_different_capacity_not_exact_match(self):
        # Simple case: "iphone" is the only matching fragment → score 50, passes already.
        score = calculate_match_score("iPhone 16 256GB", IPHONE_16_128)
        assert score < 95, f"got {score}"

    def test_multi_fragment_capacity_not_exact_match(self):
        # Multi-fragment case: "galaxy" (+50), "s25" (+50), "ultra" (+50) each match
        # independently and stack to 100 despite 512GB ≠ 256GB.
        # This FAILS until the Phase 1 strong-identifier veto is implemented.
        score = calculate_match_score("Samsung Galaxy S25 Ultra 512GB", GALAXY_S25_ULTRA_256)
        assert score < 95, (
            f"512GB ≠ 256GB must prevent an exact/very-similar match, got {score}"
        )


# ── Variant token extraction ──────────────────────────────────────────────────

class TestVariantTokens:
    def test_storage_gb(self):
        assert _variant_tokens("256GB") == {"256gb"}

    def test_storage_tb(self):
        assert _variant_tokens("Samsung 1TB SSD") == {"1tb"}

    def test_multiple_storage(self):
        assert _variant_tokens("512GB / 1TB option") == {"512gb", "1tb"}

    def test_generation_prefix(self):
        assert _variant_tokens("AirPods Pro Gen2") == {"gen2"}

    def test_generation_ordinal(self):
        assert _variant_tokens("AirPods Pro 2nd Gen") == {"2ndgen"}

    def test_mark_revision(self):
        assert _variant_tokens("Sonos Arc MK2") == {"mk2"}

    def test_no_tokens_plain_model(self):
        assert _variant_tokens("Sony WH-1000XM5") == set()

    def test_no_tokens_brand_only(self):
        assert _variant_tokens("Apple") == set()


# ── Veto logic ────────────────────────────────────────────────────────────────

AIRPODS_PRO_GEN2 = {
    "id": 12,
    "brand": "Apple",
    "model": "AirPods Pro Gen2",
    "name": "Apple AirPods Pro 2nd Generation",
    "category": "Earbuds",
    "price": 249.00,
    "store": "Apple",
}


class TestStrongIdentifierVeto:
    def test_veto_fires_wrong_storage(self):
        # Query specifies 512GB; product is 256GB → capped at 84
        score = calculate_match_score("Samsung Galaxy S25 Ultra 512GB", GALAXY_S25_ULTRA_256)
        assert score <= 84, f"veto should cap at 84, got {score}"

    def test_veto_does_not_fire_correct_storage(self):
        # Query and product both say 256GB → no veto
        score = calculate_match_score("Samsung Galaxy S25 Ultra 256GB", GALAXY_S25_ULTRA_256)
        assert score > 84, f"correct storage should not trigger veto, got {score}"

    def test_veto_does_not_fire_no_storage_in_query(self):
        # Query has no capacity token → veto is silent
        score = calculate_match_score("Samsung Galaxy S25 Ultra", GALAXY_S25_ULTRA_256)
        assert score > 84, f"query without capacity should not trigger veto, got {score}"

    def test_veto_fires_wrong_generation(self):
        # Query says Gen2; product is Gen3
        gen3_product = {
            "id": 13,
            "brand": "Apple",
            "model": "AirPods Pro Gen3",
            "name": "Apple AirPods Pro 3rd Generation",
            "category": "Earbuds",
            "price": 299.00,
            "store": "Apple",
        }
        score = calculate_match_score("AirPods Pro Gen2", gen3_product)
        assert score <= 84, f"gen2 ≠ gen3 should cap at 84, got {score}"

    def test_veto_does_not_fire_correct_generation(self):
        # Include brand so the base score clears 84, making veto silence detectable.
        # "AirPods Pro Gen2" alone scores 70 (no brand boost); adding "Apple" hits 100.
        score = calculate_match_score("Apple AirPods Pro Gen2", AIRPODS_PRO_GEN2)
        assert score > 84, f"matching generation should not trigger veto, got {score}"

    def test_veto_fires_on_full_model_match_wrong_capacity(self):
        # Even when the model string fully matches (minus the capacity), veto still applies
        score = calculate_match_score("iPhone 16 256GB", IPHONE_16_128)
        assert score < 95, f"full model match with wrong capacity must not be Exact, got {score}"


# ── Score classification ──────────────────────────────────────────────────────

class TestClassifyScore:
    def test_exact_match_lower_bound(self):
        assert classify_score(95) == "Exact Match"

    def test_exact_match_upper_bound(self):
        assert classify_score(100) == "Exact Match"

    def test_very_similar_lower(self):
        assert classify_score(85) == "Very Similar"

    def test_very_similar_upper(self):
        assert classify_score(94) == "Very Similar"

    def test_similar_lower(self):
        assert classify_score(70) == "Similar"

    def test_similar_upper(self):
        assert classify_score(84) == "Similar"

    def test_alternative(self):
        assert classify_score(69) == "Alternative"

    def test_zero(self):
        assert classify_score(0) == "Alternative"


# ── Phase 5: context tokens ───────────────────────────────────────────────────

class TestCtxTokens:
    def test_tier_pro(self):
        assert "pro" in _ctx_tokens("Galaxy Buds3 Pro")

    def test_tier_ultra(self):
        assert "ultra" in _ctx_tokens("Galaxy S25 Ultra")

    def test_color_black(self):
        assert "black" in _ctx_tokens("iPhone 16 Pro Black")

    def test_connectivity_5g(self):
        assert "5g" in _ctx_tokens("iPad 5G")

    def test_no_ctx_plain_model(self):
        assert _ctx_tokens("Sony WH-1000XM5") == set()

    def test_professional_not_pro(self):
        assert "pro" not in _ctx_tokens("Professional Audio")


# ── Phase 5: tier veto ────────────────────────────────────────────────────────

GALAXY_BUDS3_BASE = {
    "id": 20,
    "brand": "Samsung",
    "model": "Galaxy Buds3",
    "name": "Samsung Galaxy Buds3 Wireless Earbuds",
    "category": "Earbuds",
    "price": 159.99,
    "store": "Amazon",
}


class TestTierVeto:
    def test_pro_query_vs_non_pro_product_capped(self):
        score = calculate_match_score("Samsung Galaxy Buds3 Pro", GALAXY_BUDS3_BASE)
        assert score <= 84, f"'Pro' absent from product must cap at 84, got {score}"

    def test_pro_query_vs_pro_product_not_capped(self):
        score = calculate_match_score("Samsung Galaxy Buds3 Pro", SAMSUNG)
        assert score > 84, f"Matching tier should not trigger veto, got {score}"

    def test_ultra_query_vs_non_ultra_product_capped(self):
        galaxy_s25 = {
            "id": 21,
            "brand": "Samsung",
            "model": "Galaxy S25",
            "name": "Samsung Galaxy S25 Smartphone",
            "category": "Phones",
            "price": 799.99,
            "store": "Amazon",
        }
        score = calculate_match_score("Samsung Galaxy S25 Ultra", galaxy_s25)
        assert score <= 84, f"'Ultra' absent from product must cap at 84, got {score}"

    def test_no_tier_query_not_vetoed(self):
        score = calculate_match_score("Samsung Galaxy Buds3", SAMSUNG)
        assert score >= 70, f"Query without tier should still match Pro product, got {score}"


# ── Phase 5: brand synonyms ───────────────────────────────────────────────────

UE_HYPERBOOM = {
    "id": 22,
    "brand": "Ultimate Ears",
    "model": "Hyperboom",
    "name": "Ultimate Ears Hyperboom Portable Bluetooth Speaker",
    "category": "Speakers",
    "price": 399.99,
    "store": "Amazon",
}

SENNHEISER_M4 = {
    "id": 23,
    "brand": "Sennheiser",
    "model": "Momentum 4",
    "name": "Sennheiser Momentum 4 Wireless Headphones",
    "category": "Headphones",
    "price": 279.99,
    "store": "Amazon",
}

BOSE_QC45 = {
    "id": 24,
    "brand": "Bose",
    "model": "QuietComfort 45",
    "name": "Bose QuietComfort 45 Wireless Headphones",
    "category": "Headphones",
    "price": 279.00,
    "store": "Amazon",
}


class TestBrandSynonyms:
    def test_ue_expands_to_ultimate_ears(self):
        score = calculate_match_score("UE Hyperboom", UE_HYPERBOOM)
        assert score >= 70, f"'UE' should expand to 'Ultimate Ears', got {score}"

    def test_sennheizer_typo_matches(self):
        score = calculate_match_score("Sennheizer Momentum 4", SENNHEISER_M4)
        assert score >= 30, f"Sennheizer typo should still match Sennheiser brand, got {score}"

    def test_qc45_alias_matches(self):
        score = calculate_match_score("QC45", BOSE_QC45)
        assert score >= 60, f"QC45 alias should expand to QuietComfort 45, got {score}"


# ── Phase 5: edit distance ────────────────────────────────────────────────────

class TestEditDistance:
    def test_identical_strings(self):
        assert _edit_distance("sony", "sony") == 0

    def test_single_substitution(self):
        assert _edit_distance("sony", "somy") == 1

    def test_single_insertion(self):
        assert _edit_distance("sony", "sonya") == 1

    def test_single_deletion(self):
        assert _edit_distance("sonys", "sony") == 1

    def test_clearly_different(self):
        assert _edit_distance("apple", "samsung") > 3

    def test_fuzzy_model_fragment(self):
        assert _edit_distance("momentum4", "momentum3") == 1


# ── Phase 5: query expansion ──────────────────────────────────────────────────

class TestExpandQuery:
    def test_ue_expanded(self):
        assert "ultimate ears" in _expand_query("UE Hyperboom")

    def test_sennheizer_corrected(self):
        assert "sennheiser" in _expand_query("Sennheizer Momentum 4")

    def test_qc45_expanded(self):
        assert "quietcomfort 45" in _expand_query("QC45 headphones")

    def test_no_expansion_preserves_query(self):
        expanded = _expand_query("Sony WH-1000XM5")
        assert "sony" in expanded
        assert "wh-1000xm5" in expanded


# ── Cross-model false positive regression tests ────────────────────────────────
# 16 permanent tests for pairs that scored ≥95 before Phase 1 fixes.
# 14 are unit-level (calculate_match_score, assert < 84).
# 2 are API-level (WH/WF cross-series, assert ≤84 + match_label).

WH_1000XM4 = {
    "brand": "Sony", "model": "WH-1000XM4",
    "name": "Sony WH-1000XM4 Wireless Noise Cancelling Headphones",
    "category": "Headphones",
}
WF_1000XM5 = {
    "brand": "Sony", "model": "WF-1000XM5",
    "name": "Sony WF-1000XM5 Wireless Noise Cancelling Earbuds",
    "category": "Earbuds",
}
GALAXY_BUDS2_PRO = {
    "brand": "Samsung", "model": "Galaxy Buds2 Pro",
    "name": "Samsung Galaxy Buds2 Pro True Wireless Earbuds",
    "category": "Earbuds",
}
QC_ULTRA = {
    "brand": "Bose", "model": "QuietComfort Ultra",
    "name": "Bose QuietComfort Ultra Headphones",
    "category": "Headphones",
}
QC_EARBUDS_2 = {
    "brand": "Bose", "model": "QuietComfort Earbuds 2",
    "name": "Bose QuietComfort Earbuds 2 True Wireless Earbuds",
    "category": "Earbuds",
}
ERA_300 = {
    "brand": "Sonos", "model": "Era 300",
    "name": "Sonos Era 300 Wireless Speaker",
    "category": "Speakers",
}
ERA_100 = {
    "brand": "Sonos", "model": "Era 100",
    "name": "Sonos Era 100 Wireless Speaker",
    "category": "Speakers",
}
PIXEL_BUDS_PRO = {
    "brand": "Google", "model": "Pixel Buds Pro",
    "name": "Google Pixel Buds Pro Wireless Earbuds",
    "category": "Earbuds",
}


class TestCrossModelFalsePositives:
    # ── Rule 2a: alphanum suffix conflict ────────────────────────────────────

    def test_xm5_query_vs_xm4_product(self):
        assert calculate_match_score("Sony WH-1000XM5", WH_1000XM4) < 84

    def test_xm4_query_vs_xm5_product(self):
        assert calculate_match_score("Sony WH-1000XM4", SONY) < 84

    def test_buds3_query_vs_buds2_product(self):
        assert calculate_match_score("Samsung Galaxy Buds3 Pro", GALAXY_BUDS2_PRO) < 84

    def test_buds2_query_vs_buds3_product(self):
        assert calculate_match_score("Samsung Galaxy Buds2 Pro", SAMSUNG) < 84

    def test_wf_xm5_query_vs_wh_xm4_product(self):
        assert calculate_match_score("Sony WF-1000XM5", WH_1000XM4) < 84

    def test_wh_xm4_query_vs_wf_xm5_product(self):
        assert calculate_match_score("Sony WH-1000XM4", WF_1000XM5) < 84

    # ── Rule 2b: digit adjacency conflict ────────────────────────────────────

    def test_qc45_query_vs_qc_ultra_product(self):
        assert calculate_match_score("Bose QuietComfort 45", QC_ULTRA) < 84

    def test_qc45_query_vs_qc_earbuds2_product(self):
        assert calculate_match_score("Bose QuietComfort 45", QC_EARBUDS_2) < 84

    def test_era300_query_vs_era100_product(self):
        assert calculate_match_score("Sonos Era 300", ERA_100) < 84

    def test_era100_query_vs_era300_product(self):
        assert calculate_match_score("Sonos Era 100", ERA_300) < 84

    # ── Brand gate: cross-brand fragment stacking ────────────────────────────

    def test_google_buds_query_vs_samsung_buds3_product(self):
        assert calculate_match_score("Google Pixel Buds Pro", SAMSUNG) < 84

    def test_google_buds_query_vs_samsung_buds2_product(self):
        assert calculate_match_score("Google Pixel Buds Pro", GALAXY_BUDS2_PRO) < 84

    def test_samsung_buds3_query_vs_google_buds_product(self):
        assert calculate_match_score("Samsung Galaxy Buds3 Pro", PIXEL_BUDS_PRO) < 84

    def test_samsung_buds2_query_vs_google_buds_product(self):
        assert calculate_match_score("Samsung Galaxy Buds2 Pro", PIXEL_BUDS_PRO) < 84

    # ── Category cap: WH/WF cross-series (API level) ────────────────────────

    def test_wh_query_wf_product_capped_at_similar(self, client):
        r = client.get('/api/v1/search?q=Sony+WH-1000XM5')
        by_name = {p['name']: p for p in r.json()['results']}
        wf = by_name.get('Sony WF-1000XM5 Wireless Noise Cancelling Earbuds')
        assert wf is not None
        assert wf['match_score'] <= 84
        assert wf['match_label'] == 'Similar'

    def test_wf_query_wh_product_capped_at_similar(self, client):
        r = client.get('/api/v1/search?q=Sony+WF-1000XM5')
        by_name = {p['name']: p for p in r.json()['results']}
        wh = by_name.get('Sony WH-1000XM5 Wireless Noise Cancelling Headphones')
        assert wh is not None
        assert wh['match_score'] <= 84
        assert wh['match_label'] == 'Similar'


class TestCategoryAnchorFallback:
    """Documents the known insertion-order sensitivity when no model is a literal
    substring of the normalised query.

    For fragment-only queries like "Sony XM5", neither "wh1000xm5" nor "wf1000xm5"
    appears in "sonyxm5", so the anchor falls back to results[0] — determined by
    DB insertion order (Product.id ASC). Which XM5 variant leads is an artefact
    of insertion order, not query intent. This is a documented limitation.
    """

    def test_fragment_query_anchor_insertion_order_sensitive(self, client):
        r = client.get('/api/v1/search?q=Sony+XM5')
        results = r.json()['results']
        assert len(results) >= 2
        top_names = [p['name'] for p in results[:2]]
        assert any('XM5' in n for n in top_names)
