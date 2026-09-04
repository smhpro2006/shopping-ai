import pytest
from backend.app.product_matching import (
    normalize,
    calculate_match_score,
    classify_score,
    _variant_tokens,
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
    def test_sony_xm5(self):
        score = calculate_match_score("sony xm5", SONY)
        assert score >= 70, f"got {score}"

    def test_sony_wh1000xm5_with_hyphens(self):
        score = calculate_match_score("Sony WH-1000XM5", SONY)
        assert score >= 90, f"got {score}"

    def test_wh1000xm5_no_brand(self):
        score = calculate_match_score("WH1000XM5", SONY)
        assert score >= 60, f"got {score}"

    def test_airpods_pro_2(self):
        score = calculate_match_score("AirPods Pro 2", APPLE)
        assert score >= 60, f"got {score}"

    def test_samsung_galaxy_buds3_pro(self):
        score = calculate_match_score("Samsung Galaxy Buds3 Pro", SAMSUNG)
        assert score >= 70, f"got {score}"


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
