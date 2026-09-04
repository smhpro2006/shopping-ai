"""Parse eBay Browse API item_summary responses into typed EbayListing objects."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class EbayListing:
    item_id: str
    title: str
    price: float
    currency: str
    condition: str          # normalised: "new" | "used" | "refurbished" | "unknown"
    url: str
    retailer_name: str      # seller username (used as retailer identifier)
    availability: Optional[str] = None
    raw_condition: str = ""
    match_score: int = 0    # filled in by runner after scoring


_CONDITION_MAP: dict[str, str] = {
    "new": "new",
    "brand new": "new",
    "new with tags": "new",
    "new without tags": "new",
    "new with defects": "new",
    "certified refurbished": "refurbished",
    "excellent - refurbished": "refurbished",
    "very good - refurbished": "refurbished",
    "good - refurbished": "refurbished",
    "seller refurbished": "refurbished",
    "like new": "refurbished",
    "used": "used",
    "very good": "used",
    "good": "used",
    "acceptable": "used",
    "for parts or not working": "used",
}


def normalize_condition(raw: str) -> str:
    """Map eBay condition strings to canonical values."""
    key = raw.strip().lower()
    return _CONDITION_MAP.get(key, "unknown")


def _parse_price(price_node: dict) -> tuple[float, str]:
    """Extract (amount, currency) from an eBay price dict."""
    try:
        return float(price_node["value"]), price_node.get("currency", "USD")
    except (KeyError, ValueError, TypeError):
        return 0.0, "USD"


def parse_listings(api_response: dict) -> list[EbayListing]:
    """Convert a Browse API search response into a list of EbayListing objects."""
    items = api_response.get("itemSummaries", [])
    listings: list[EbayListing] = []
    for item in items:
        price_node = item.get("price", {})
        price, currency = _parse_price(price_node)
        if price <= 0:
            continue

        raw_condition = item.get("condition", "")
        url = item.get("itemWebUrl", "")
        seller = item.get("seller", {}).get("username", "eBay Seller")

        listings.append(
            EbayListing(
                item_id=item.get("itemId", ""),
                title=item.get("title", ""),
                price=price,
                currency=currency,
                condition=normalize_condition(raw_condition),
                url=url,
                retailer_name=seller,
                availability=item.get("itemLocation", {}).get("country"),
                raw_condition=raw_condition,
            )
        )
    return listings


def build_search_query(brand: str, model: str) -> str:
    """Construct an eBay query string from canonical product fields."""
    return f"{brand} {model}"
