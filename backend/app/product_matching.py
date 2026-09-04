import re


def normalize(text):
    return re.sub(r"[^a-z0-9]", "", text.lower())


# Variant-identifier patterns — tokens that distinguish one SKU from another.
# If the query names a variant token that is absent from the product, the match
# cannot be Exact or Very Similar regardless of title similarity.
_VARIANT_ID_RE = re.compile(
    r"\d+(?:gb|tb|mb)"           # storage: 256gb, 512gb, 1tb
    r"|\d+(?:st|nd|rd|th)gen"    # ordinal generation: 2ndgen, 3rdgen
    r"|gen\d+"                   # generation prefix: gen2, gen3
    r"|mk\d+"                    # mark revision: mk2, mk3
)


def _variant_tokens(text: str) -> set:
    """Extract variant-identifier tokens from normalized text."""
    return set(_VARIANT_ID_RE.findall(normalize(text)))


def _apply_variant_veto(score: int, query: str, product: dict) -> int:
    """Cap score at 84 (Similar) if the query names a variant token absent from the product.

    Only fires when the query specifies a variant value (e.g. 512GB) that
    the product does not confirm.  Queries without variant tokens are unaffected.
    """
    q_tokens = _variant_tokens(query)
    if not q_tokens:
        return score
    p_tokens = _variant_tokens(product.get("model", "") + " " + product.get("name", ""))
    if not q_tokens.issubset(p_tokens):
        return min(score, 84)
    return score


def classify_score(score: int) -> str:
    """Return the §12 match classification label for a score."""
    if score >= 95:
        return "Exact Match"
    if score >= 85:
        return "Very Similar"
    if score >= 70:
        return "Similar"
    return "Alternative"


def calculate_match_score(query, product):
    query_clean = normalize(query)

    brand = normalize(product["brand"])
    model = normalize(product["model"])
    name = normalize(product["name"])

    score = 0
    query_parts = re.findall(r"[a-z]+\d+|\d+[a-z]+|[a-z]+|\d+", query.lower())

    # Brand match
    if brand in query_clean:
        score += 30

    if model in query_clean:
        # Full model match — strongest signal
        score += 60
        score = min(score + 10, 100)
    else:
        # Model fragment matches (e.g. "xm5" inside "wh1000xm5")
        model_matched_parts = set()
        for part in query_parts:
            if len(part) >= 3 and part in model:
                score += 50
                model_matched_parts.add(part)

        # Query words in product name — skip parts that already scored via model
        for part in query_parts:
            if part in model_matched_parts:
                continue
            if len(part) >= 2 and part in name:
                score += 5

        # Brand + model fragment combo bonus
        if brand in query_clean:
            for part in query_parts:
                if len(part) >= 3 and part in model:
                    score += 20
                    break

        score = min(score, 100)

    # Single exit point — veto always applied regardless of scoring path taken
    return _apply_variant_veto(score, query, product)
