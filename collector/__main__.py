"""Entry point for: python -m collector"""

import argparse
import logging
import sys

from backend.app.core.logging import configure_logging


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m collector",
        description="Fetch eBay offers for canonical products and store top matches.",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch and score listings but do not write to the database.",
    )
    p.add_argument(
        "--product-id",
        type=int,
        metavar="ID",
        help="Collect offers for a single product ID only.",
    )
    p.add_argument(
        "--verbose",
        action="store_true",
        help="Log individual listing details.",
    )
    return p


def main() -> None:
    args = _build_parser().parse_args()
    configure_logging(level="DEBUG" if args.verbose else "INFO")
    logger = logging.getLogger("collector")

    from collector.ebay_client import EbayAuthError
    from collector.runner import run_once

    logger.info(
        "Collector starting — dry_run=%s product_id=%s",
        args.dry_run, args.product_id,
    )

    try:
        stats = run_once(
            product_id=args.product_id,
            dry_run=args.dry_run,
            verbose=args.verbose,
        )
    except EbayAuthError as exc:
        logger.error("eBay authentication failed: %s", exc)
        logger.error("Set EBAY_APP_ID and EBAY_CERT_ID in backend/.env")
        sys.exit(1)
    except Exception as exc:
        logger.exception("Unexpected error: %s", exc)
        sys.exit(1)

    logger.info(
        "Done — products=%d offers_stored=%d no_match=%d errors=%d",
        stats.products_processed,
        stats.offers_stored,
        stats.no_match_count,
        stats.error_count,
    )
    if stats.skipped_products:
        logger.warning("Skipped: %s", ", ".join(stats.skipped_products))

    sys.exit(1 if stats.error_count else 0)


if __name__ == "__main__":
    main()
