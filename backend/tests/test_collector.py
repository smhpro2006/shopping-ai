"""Unit tests for the collector package — no eBay credentials required."""
import pytest
from unittest.mock import patch, MagicMock

from collector.ebay_search import normalize_condition, parse_listings, build_search_query
from collector.runner import _bidirectional_variant_check, _score_listing
from collector.ebay_client import EbayAuthError, EbayClient


# ── normalize_condition ───────────────────────────────────────────────────────

class TestNormalizeCondition:
    def test_new(self):
        assert normalize_condition("New") == "new"

    def test_brand_new(self):
        assert normalize_condition("Brand New") == "new"

    def test_new_with_tags(self):
        assert normalize_condition("New with tags") == "new"

    def test_certified_refurbished(self):
        assert normalize_condition("Certified Refurbished") == "refurbished"

    def test_seller_refurbished(self):
        assert normalize_condition("Seller Refurbished") == "refurbished"

    def test_like_new(self):
        assert normalize_condition("Like New") == "refurbished"

    def test_used(self):
        assert normalize_condition("Used") == "used"

    def test_very_good(self):
        assert normalize_condition("Very Good") == "used"

    def test_good(self):
        assert normalize_condition("Good") == "used"

    def test_acceptable(self):
        assert normalize_condition("Acceptable") == "used"

    def test_for_parts(self):
        assert normalize_condition("For Parts or Not Working") == "used"

    def test_unknown_passthrough(self):
        assert normalize_condition("Mysterious Condition") == "unknown"

    def test_strips_whitespace(self):
        assert normalize_condition("  New  ") == "new"

    def test_case_insensitive(self):
        assert normalize_condition("CERTIFIED REFURBISHED") == "refurbished"


# ── parse_listings ────────────────────────────────────────────────────────────

_SAMPLE_RESPONSE = {
    "itemSummaries": [
        {
            "itemId": "v1|123456|0",
            "title": "Sony WH-1000XM5 Wireless Noise Cancelling Headphones",
            "price": {"value": "329.99", "currency": "USD"},
            "condition": "New",
            "itemWebUrl": "https://www.ebay.com/itm/123456",
            "seller": {"username": "top_audio_shop"},
            "itemLocation": {"country": "US"},
        },
        {
            "itemId": "v1|789012|0",
            "title": "Sony WH-1000XM5 Used Great Condition",
            "price": {"value": "200.00", "currency": "USD"},
            "condition": "Used",
            "itemWebUrl": "https://www.ebay.com/itm/789012",
            "seller": {"username": "reseller99"},
        },
        {
            "itemId": "v1|bad|0",
            "title": "Bad listing no price",
            "price": {},
            "condition": "New",
            "itemWebUrl": "",
            "seller": {"username": "nobody"},
        },
    ]
}


class TestParseListings:
    def test_returns_list(self):
        listings = parse_listings(_SAMPLE_RESPONSE)
        assert isinstance(listings, list)

    def test_skips_zero_price(self):
        listings = parse_listings(_SAMPLE_RESPONSE)
        assert all(l.price > 0 for l in listings)

    def test_parses_two_valid_listings(self):
        listings = parse_listings(_SAMPLE_RESPONSE)
        assert len(listings) == 2

    def test_first_listing_fields(self):
        listing = parse_listings(_SAMPLE_RESPONSE)[0]
        assert listing.title == "Sony WH-1000XM5 Wireless Noise Cancelling Headphones"
        assert listing.price == pytest.approx(329.99)
        assert listing.currency == "USD"
        assert listing.condition == "new"
        assert listing.retailer_name == "top_audio_shop"

    def test_second_listing_condition_used(self):
        listing = parse_listings(_SAMPLE_RESPONSE)[1]
        assert listing.condition == "used"

    def test_empty_response(self):
        assert parse_listings({}) == []

    def test_empty_summaries(self):
        assert parse_listings({"itemSummaries": []}) == []


# ── build_search_query ────────────────────────────────────────────────────────

class TestBuildSearchQuery:
    def test_basic(self):
        assert build_search_query("Sony", "WH-1000XM5") == "Sony WH-1000XM5"

    def test_multiword_brand(self):
        assert build_search_query("Ultimate Ears", "Hyperboom") == "Ultimate Ears Hyperboom"


# ── _bidirectional_variant_check ─────────────────────────────────────────────

class TestBidirectionalVariantCheck:
    _SONY = {"model": "WH-1000XM5", "name": "Sony WH-1000XM5 Wireless Noise Cancelling Headphones"}

    def test_no_variant_tokens_passes(self):
        # Neither the canonical product nor the listing has storage/gen tokens
        assert _bidirectional_variant_check(
            "Sony WH-1000XM5",
            "Sony WH-1000XM5 Wireless Headphones",
            self._SONY,
        )

    def test_listing_has_extra_token_blocked(self):
        # Listing claims 256GB but canonical product has no storage token
        assert not _bidirectional_variant_check(
            "Samsung Galaxy S25",
            "Samsung Galaxy S25 256GB Unlocked",
            {"model": "Galaxy S25", "name": "Samsung Galaxy S25"},
        )

    def test_canonical_token_missing_from_listing_blocked(self):
        # Canonical is S25 Ultra 512GB; listing is just "256GB"
        assert not _bidirectional_variant_check(
            "Samsung Galaxy S25 Ultra 512gb",
            "Samsung Galaxy S25 Ultra 256GB Unlocked",
            {"model": "Galaxy S25 Ultra 512GB", "name": "Samsung Galaxy S25 Ultra"},
        )

    def test_matching_tokens_passes(self):
        assert _bidirectional_variant_check(
            "Samsung Galaxy S25 Ultra 512gb",
            "Samsung Galaxy S25 Ultra 512GB Factory Unlocked",
            {"model": "Galaxy S25 Ultra 512GB", "name": "Samsung Galaxy S25 Ultra"},
        )

    def test_generation_mismatch_blocked(self):
        assert not _bidirectional_variant_check(
            "Apple AirPods Pro Gen2",
            "Apple AirPods Pro 1st Generation",
            {"model": "AirPods Pro 2", "name": "Apple AirPods Pro 2nd Generation"},
        )


# ── _score_listing ────────────────────────────────────────────────────────────

class TestScoreListing:
    _SONY_PRODUCT = {
        "brand": "Sony",
        "model": "WH-1000XM5",
        "name": "Sony WH-1000XM5 Wireless Noise Cancelling Headphones",
        "category": "Headphones",
    }

    def test_exact_match_high_score(self):
        from collector.ebay_search import EbayListing
        listing = EbayListing(
            item_id="1",
            title="Sony WH-1000XM5 Wireless Noise Cancelling Headphones",
            price=329.99,
            currency="USD",
            condition="new",
            url="",
            retailer_name="shop",
        )
        score = _score_listing(listing, self._SONY_PRODUCT)
        assert score >= 85, f"Expected ≥85 for exact title match, got {score}"

    def test_unrelated_product_low_score(self):
        from collector.ebay_search import EbayListing
        listing = EbayListing(
            item_id="2",
            title="JBL Charge 5 Bluetooth Speaker Waterproof",
            price=149.99,
            currency="USD",
            condition="new",
            url="",
            retailer_name="shop",
        )
        score = _score_listing(listing, self._SONY_PRODUCT)
        assert score < 20, f"Expected <20 for unrelated product, got {score}"


# ── EbayClient auth guard ─────────────────────────────────────────────────────

class TestEbayClientAuth:
    def test_empty_credentials_raise(self):
        with pytest.raises(EbayAuthError):
            EbayClient(app_id="", cert_id="")

    def test_missing_cert_raise(self):
        with pytest.raises(EbayAuthError):
            EbayClient(app_id="some-id", cert_id="")


# ── Collector hardening guards ────────────────────────────────────────────────

from collector.runner import (  # noqa: E402
    _is_accessory, _below_price_floor, _normalize_roman,
    CATEGORY_PRICE_FLOORS,
)


class TestWritesEnabledDefault:
    def test_writes_disabled_by_default(self):
        from backend.app.core.config import Settings
        assert Settings.model_fields["COLLECTOR_WRITES_ENABLED"].default is False


class TestAccessoryKeywordBlocklist:
    def test_case_rejected(self):
        assert _is_accessory("Case for Sony WH-1000XM5 Headphones")

    def test_cover_rejected(self):
        assert _is_accessory("Sony WH-1000XM5 Silicone Cover Skin")

    def test_earpad_rejected(self):
        assert _is_accessory("Sony WH-1000XM5 Ear Pad Replacement Cushion")

    def test_earpad_nospace_rejected(self):
        assert _is_accessory("WH-1000XM5 Earpad Cushion Set")

    def test_cable_rejected(self):
        assert _is_accessory("Replacement Audio Cable for Sony WH-1000XM5")

    def test_charger_rejected(self):
        assert _is_accessory("USB-C Charger for WH-1000XM5")

    def test_for_parts_rejected(self):
        assert _is_accessory("Sony WH-1000XM5 For Parts Not Working")

    def test_not_working_rejected(self):
        assert _is_accessory("Sony WH-1000XM5 Not Working As Is")

    def test_broken_rejected(self):
        assert _is_accessory("Sony WH-1000XM5 Broken Hinge")

    def test_empty_box_rejected(self):
        assert _is_accessory("Sony WH-1000XM5 Empty Box Only")

    def test_legitimate_listing_passes(self):
        assert not _is_accessory("Sony WH-1000XM5 Wireless Noise Cancelling Headphones")

    def test_legitimate_used_passes(self):
        assert not _is_accessory("Sony WH-1000XM5 Wireless Headphones Used Good Condition")

    def test_legitimate_refurb_passes(self):
        assert not _is_accessory("Sony WH-1000XM5 Certified Refurbished")

    # Problem 1 — accessories that were scoring 100 and passing
    def test_power_supply_rejected(self):
        assert _is_accessory("Ultimate Ears Switching Power Supply DSA-90PFE-192")

    def test_bottom_part_rejected(self):
        assert _is_accessory("SALE! Ultimate Ears HYPERBOOM Bottom Part Only")

    def test_repair_service_rejected(self):
        assert _is_accessory("UE Hyperboom REPAIR SERVICE for Power button switch")

    def test_lot_of_rejected(self):
        assert _is_accessory("[LOT OF 5] JBL Charge 5 PARTS ONLY")

    def test_oem_single_earbud_rejected(self):
        assert _is_accessory("Apple AirPods Pro 2nd Gen A3047 Right - A Grade - OEM")

    # Problem 3 — damaged units that were accepted at 100
    def test_defective_rejected(self):
        assert _is_accessory("DEFECTIVE Ultimate Ears HYPERBOOM")

    def test_doesnt_click_rejected(self):
        assert _is_accessory("Sony WH-1000XM5 POWER BUTTON DOESN'T CLICK")

    def test_needs_replacement_rejected(self):
        assert _is_accessory("Sony WH-1000XM5 BATTERY NEEDS REPLACEMENT")

    def test_damaged_rejected(self):
        assert _is_accessory("Sony WH-1000XM5 Damaged Unit Sold As-Is")

    def test_cracked_rejected(self):
        assert _is_accessory("Sony WH-1000XM5 Cracked Headband")

    # Problem 4 — false rejection due to substring match inside "Over-Ear"
    def test_over_ear_not_rejected(self):
        assert not _is_accessory(
            "Sennheiser MOMENTUM 4 Wireless Bluetooth ANC Over-Ear Headphones - Brown New!"
        )

    def test_apple_airpods_max_not_rejected(self):
        assert not _is_accessory("Apple AirPods Max Wireless Over-Ear Headphones Space Gray")


class TestCategoryPriceFloor:
    def test_headphones_below_floor_rejected(self):
        assert _below_price_floor(50.0, "Headphones")

    def test_headphones_at_floor_passes(self):
        assert not _below_price_floor(80.0, "Headphones")

    def test_headphones_above_floor_passes(self):
        assert not _below_price_floor(329.99, "Headphones")

    def test_earbuds_below_floor_rejected(self):
        assert _below_price_floor(25.0, "Earbuds")

    def test_earbuds_at_floor_passes(self):
        assert not _below_price_floor(40.0, "Earbuds")

    def test_speakers_below_floor_rejected(self):
        assert _below_price_floor(15.0, "Speakers")

    def test_speakers_at_floor_passes(self):
        assert not _below_price_floor(30.0, "Speakers")

    def test_unknown_category_always_passes(self):
        assert not _below_price_floor(1.0, "Phones")
        assert not _below_price_floor(0.01, "Unknown")

    def test_floor_lookup_case_insensitive(self):
        assert _below_price_floor(50.0, "headphones")
        assert _below_price_floor(50.0, "HEADPHONES")
        assert _below_price_floor(20.0, "earbuds")

    def test_all_category_floors_defined(self):
        assert "headphones" in CATEGORY_PRICE_FLOORS
        assert "earbuds" in CATEGORY_PRICE_FLOORS
        assert "speakers" in CATEGORY_PRICE_FLOORS


# ── Fail-fast on auth errors ──────────────────────────────────────────────────

class TestFailFastOnAuthError:
    """invalid_client is not transient — run_once must abort on the first failure
    rather than retrying the same rejected credentials for every product."""

    def _mock_ebay(self, search_side_effect):
        mock_ebay = MagicMock()
        mock_ebay.search.side_effect = search_side_effect
        mock_cls = MagicMock()
        mock_cls.return_value.__enter__.return_value = mock_ebay
        return mock_cls, mock_ebay

    def test_auth_error_aborts_run(self, client):
        from collector.runner import run_once
        mock_cls, mock_ebay = self._mock_ebay(
            EbayAuthError("invalid_client: credentials rejected")
        )
        with patch("collector.runner.EbayClient", mock_cls):
            with pytest.raises(EbayAuthError):
                run_once(dry_run=True)

        assert mock_ebay.search.call_count == 1, (
            f"Expected 1 search call before abort, got {mock_ebay.search.call_count}. "
            "Auth errors must not retry against subsequent products."
        )

    def test_transient_error_continues(self, client):
        from collector.runner import run_once
        calls = []

        def flaky(query, **kwargs):
            calls.append(query)
            if len(calls) == 1:
                raise RuntimeError("Connection timeout")
            return {"itemSummaries": []}

        mock_cls, mock_ebay = self._mock_ebay(flaky)
        with patch("collector.runner.EbayClient", mock_cls):
            stats = run_once(dry_run=True)

        assert stats.error_count == 1, "Expected exactly 1 transient error recorded"
        assert len(calls) > 1, "Run should have continued past the transient error"


# ── New-condition at retail price — regression for removed ceiling ────────────

class TestNewConditionAtRetailNotRejected:
    """The median-based price ceiling was removed because it mixed conditions and
    systematically excluded new-condition listings at retail price. These tests
    assert that the specific listings the ceiling falsely rejected still pass
    all remaining filters."""

    def test_sonos_era_100_retail_not_filtered(self):
        # $399.99 is the retail price for Sonos Era 100 — was rejected by the ceiling
        assert not _is_accessory("Sonos Era 100 Wireless Streaming Speaker")
        assert not _below_price_floor(399.99, "Speakers")

    def test_sony_wh1000xm4_retail_not_filtered(self):
        assert not _is_accessory("Sony WH-1000XM4 Wireless Noise Cancelling Headphones New")
        assert not _below_price_floor(279.19, "Headphones")

    def test_sennheiser_momentum4_retail_not_filtered(self):
        assert not _is_accessory("Sennheiser Momentum 4 Wireless Headphones New Sealed")
        assert not _below_price_floor(249.95, "Headphones")

    def test_airpods_max_retail_not_filtered(self):
        assert not _is_accessory("Apple AirPods Max Wireless Over-Ear Headphones USB-C New")
        assert not _below_price_floor(328.00, "Headphones")


# ── Roman numeral normalisation ───────────────────────────────────────────────

class TestNormalizeRoman:
    def test_ii_to_2(self):
        assert "2" in _normalize_roman("Bose QuietComfort Earbuds II")

    def test_iii_to_3(self):
        assert "3" in _normalize_roman("Galaxy Buds III Pro")

    def test_iv_to_4(self):
        assert "4" in _normalize_roman("Product Edition IV")

    def test_v_to_5(self):
        assert "5" in _normalize_roman("Series V Speaker")

    def test_vi_to_6(self):
        assert "6" in _normalize_roman("Flip VI Edition")

    def test_case_insensitive(self):
        assert "2" in _normalize_roman("Earbuds ii Wireless")

    def test_word_boundary_preserved(self):
        # "XM5" does not contain a standalone Roman numeral — must not be altered
        result = _normalize_roman("Sony WH-1000XM5 Wireless Headphones")
        assert "XM5" in result

    def test_anc_over_ear_not_altered(self):
        # "V" is not present as a standalone word in "ANC Over-Ear"
        result = _normalize_roman("Sennheiser ANC Over-Ear Headphones")
        assert "Over-Ear" in result

    def test_earbuds_ii_matches_model_2(self):
        # Integration: confirms the model_not_in_title check passes after expansion
        from backend.app.product_matching import normalize
        listing = "Bose QuietComfort Earbuds II True Wireless Noise Cancelling Earbuds"
        model = "QuietComfort Earbuds 2"
        assert normalize(model) in normalize(_normalize_roman(listing))

    def test_galaxy_buds2_pro_roman(self):
        from backend.app.product_matching import normalize
        listing = "Samsung Galaxy Buds II Pro True Wireless Earbuds"
        model = "Galaxy Buds2 Pro"
        # "Buds2" normalizes to "buds2", "Buds II" after expansion is "Buds 2" → "buds2"
        assert normalize(model) in normalize(_normalize_roman(listing))
