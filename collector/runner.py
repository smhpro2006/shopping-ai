"""Core collection loop: fetch eBay listings, score them, persist top offers."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from backend.app.core.config import (
    DATABASE_URL,
    EBAY_APP_ID,
    EBAY_CERT_ID,
    EBAY_ENVIRONMENT,
    COLLECTOR_OFFERS_PER_PRODUCT,
    COLLECTOR_MIN_MATCH_SCORE,
    COLLECTOR_WRITES_ENABLED,
)
from backend.app.core.database import Base, engine
from backend.app.models.product import Product
from backend.app.models.retailer import Retailer
from backend.app.models.offer import Offer
from backend.app.product_matching import calculate_match_score, _variant_tokens, normalize
from collector.ebay_client import EbayClient, EbayAuthError
from collector.ebay_search import EbayListing, parse_listings, build_search_query

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import create_engine as _create_engine

logger = logging.getLogger("collector")

# ── Accessory / junk listing filters ──────────────────────────────────────────
# Pre-normalized (spaces and punctuation removed, lowercased) so they can be
# checked against the already-normalized listing title in O(1) per keyword.
# Multi-word phrases like "for parts" become "forparts" after normalize().
ACCESSORY_KEYWORDS: frozenset[str] = frozenset({
    # Physical accessories
    "case", "cover", "pouch", "sleeve", "earpad", "cushion",
    "replacement", "cable", "cord", "charger", "adapter",
    "stand", "mount", "skin", "decal", "sticker",
    # Broken / incomplete units
    "forparts", "notworking", "broken", "faulty",
    "emptybox", "boxonly", "manualonly",
})

# Minimum price per category below which a listing is almost certainly an
# accessory, parts unit, or bundle bait. Covers the categories in the current
# 20-product catalog; extend as new categories are added.
CATEGORY_PRICE_FLOORS: dict[str, float] = {
    "headphones": 80.0,
    "earbuds": 40.0,
    "speakers": 30.0,
}


def _is_accessory(title: str) -> bool:
    """True if the normalized listing title contains any accessory keyword."""
    norm = normalize(title)
    return any(kw in norm for kw in ACCESSORY_KEYWORDS)


def _below_price_floor(price: float, category: str) -> bool:
    """True if price is below the per-category minimum. Unknown categories pass."""
    floor = CATEGORY_PRICE_FLOORS.get(category.lower())
    return floor is not None and price < floor


@dataclass
class RunStats:
    products_processed: int = 0
    offers_stored: int = 0
    no_match_count: int = 0
    error_count: int = 0
    skipped_products: list[str] = field(default_factory=list)


def _bidirectional_variant_check(query: str, listing_title: str, product: dict) -> bool:
    """Return True only if variant tokens are consistent in both directions.

    User-search veto is one-directional (query tokens ⊆ product tokens).
    For the collector we also require that the canonical product's variant
    tokens appear in the listing title, preventing e.g. storing a 256 GB
    listing against a canonical 512 GB product.
    """
    q_tokens = _variant_tokens(query)
    p_tokens = _variant_tokens(product.get("model", "") + " " + product.get("name", ""))
    l_tokens = _variant_tokens(listing_title)

    all_canonical_tokens = q_tokens | p_tokens

    # Listing must not introduce variant tokens absent from the canonical product
    if l_tokens - all_canonical_tokens:
        return False

    # All canonical variant tokens must appear in the listing
    if all_canonical_tokens - l_tokens:
        return False

    return True


def _score_listing(listing: EbayListing, product: dict) -> int:
    """Score a listing title against a canonical product dict."""
    return calculate_match_score(listing.title, product)


def _get_or_create_retailer(db: Session, name: str) -> Retailer:
    retailer = db.query(Retailer).filter(Retailer.name == name).first()
    if not retailer:
        retailer = Retailer(name=name)
        db.add(retailer)
        db.flush()
    return retailer


def _store_offers(
    db: Session,
    product: Product,
    listings: list[EbayListing],
    dry_run: bool,
) -> int:
    """Persist the top N offers for a product. Returns count stored."""
    if not listings:
        return 0

    now = datetime.now(timezone.utc)
    stored = 0
    for listing in listings:
        retailer = _get_or_create_retailer(db, listing.retailer_name)
        offer = Offer(
            product_id=product.id,
            retailer_id=retailer.id,
            price=listing.price,
            currency=listing.currency,
            url=listing.url,
            availability=listing.availability,
            condition=listing.condition,
            source="ebay",
            scraped_at=now,
        )
        if not dry_run:
            db.add(offer)
        stored += 1
    if not dry_run:
        db.commit()
    return stored


def run_once(
    product_id: Optional[int] = None,
    dry_run: bool = False,
    verbose: bool = False,
) -> RunStats:
    """Fetch eBay offers for all (or one) canonical products and persist them.

    Args:
        product_id: If set, only collect offers for this product.
        dry_run: Fetch and score but do not write to the database.
        verbose: Log individual listing details.
    """
    stats = RunStats()

    # Guard 1: writes must be explicitly opted in via env var.
    if not COLLECTOR_WRITES_ENABLED and not dry_run:
        logger.warning(
            "COLLECTOR_WRITES_ENABLED is false — forcing dry_run=True. "
            "Set COLLECTOR_WRITES_ENABLED=true in backend/.env to enable writes."
        )
        dry_run = True

    # Guard 2: sandbox listings are synthetic and must never reach the DB.
    if EBAY_ENVIRONMENT.lower() == "sandbox" and not dry_run:
        logger.warning(
            "EBAY_ENVIRONMENT=sandbox — forcing dry_run=True. "
            "Sandbox listings are synthetic and must never be written to the database."
        )
        dry_run = True

    db_engine = _create_engine(DATABASE_URL)
    Base.metadata.create_all(bind=db_engine)

    with Session(db_engine) as db:
        query_obj = db.query(Product).options(
            joinedload(Product.offers)
        )
        if product_id is not None:
            query_obj = query_obj.filter(Product.id == product_id)
        products = query_obj.all()

    ebay_base = (
        "https://api.sandbox.ebay.com"
        if EBAY_ENVIRONMENT.lower() == "sandbox"
        else "https://api.ebay.com"
    )
    logger.info(
        "Starting collection — environment: %s | base: %s | products: %d | dry_run: %s",
        EBAY_ENVIRONMENT, ebay_base, len(products), dry_run,
    )

    with EbayClient(EBAY_APP_ID, EBAY_CERT_ID, EBAY_ENVIRONMENT) as ebay:
        for product in products:
            stats.products_processed += 1
            p_dict = {
                "brand": product.brand,
                "model": product.model,
                "name": product.name,
                "category": product.category,
            }
            search_query = build_search_query(product.brand, product.model)

            try:
                raw = ebay.search(search_query, limit=50)
            except EbayAuthError:
                # Not transient — invalid_client will fail for every subsequent
                # product with identical credentials. Abort immediately.
                logger.error(
                    "AUTH FAILURE on eBay %s (%s) — credentials rejected. "
                    "Check that EBAY_APP_ID / EBAY_CERT_ID match "
                    "EBAY_ENVIRONMENT='%s'. Aborting.",
                    EBAY_ENVIRONMENT, ebay_base, EBAY_ENVIRONMENT,
                )
                raise
            except Exception as exc:
                logger.error("eBay search failed for %s %s: %s", product.brand, product.model, exc)
                stats.error_count += 1
                stats.skipped_products.append(f"{product.brand} {product.model}")
                continue

            listings = parse_listings(raw)
            candidates: list[EbayListing] = []

            for listing in listings:
                score = _score_listing(listing, p_dict)
                if score < COLLECTOR_MIN_MATCH_SCORE:
                    stats.no_match_count += 1
                    continue

                # Reject listings whose normalized title contains an accessory keyword.
                if _is_accessory(listing.title):
                    logger.info("REJECT [accessory] %s", listing.title[:80])
                    stats.no_match_count += 1
                    continue

                # Reject listings priced below the per-category floor.
                if _below_price_floor(listing.price, product.category):
                    floor = CATEGORY_PRICE_FLOORS.get(product.category.lower(), 0.0)
                    logger.info(
                        "REJECT [price_floor] $%.2f < $%.2f (%s): %s",
                        listing.price, floor, product.category, listing.title[:60],
                    )
                    stats.no_match_count += 1
                    continue

                # Canonical model must appear literally in the listing title.
                if normalize(product.model) not in normalize(listing.title):
                    logger.info("REJECT [model_not_in_title] %s", listing.title[:80])
                    stats.no_match_count += 1
                    continue

                # Bidirectional variant-token consistency check.
                if not _bidirectional_variant_check(search_query, listing.title, p_dict):
                    logger.info("REJECT [variant_mismatch] %s", listing.title[:80])
                    stats.no_match_count += 1
                    continue

                listing.match_score = score
                candidates.append(listing)

                if verbose:
                    logger.info(
                        "  [%d] %s — $%.2f (%s)",
                        score, listing.title[:60], listing.price, listing.condition,
                    )

            # Sort: score desc, price asc; keep top N
            candidates.sort(key=lambda l: (-l.match_score, l.price))
            top = candidates[:COLLECTOR_OFFERS_PER_PRODUCT]

            with Session(db_engine) as db:
                db_product = db.query(Product).filter(Product.id == product.id).first()
                stored = _store_offers(db, db_product, top, dry_run)

            stats.offers_stored += stored
            logger.info(
                "%s %s — %d candidates, %d stored%s",
                product.brand, product.model,
                len(candidates), stored,
                " (dry-run)" if dry_run else "",
            )

    return stats
