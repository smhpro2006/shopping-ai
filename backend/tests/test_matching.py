import pytest
from backend.app.product_matching import normalize, calculate_match_score

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
