import re


def normalize(text):
    return re.sub(r"[^a-z0-9]", "", text.lower())


# ── Brand / model query expansion ─────────────────────────────────────────────

_QUERY_EXPANSIONS = [
    (re.compile(r'\bue\b'), 'ultimate ears'),
    (re.compile(r'\bsennheizer\b'), 'sennheiser'),
    (re.compile(r'\bsennhizer\b'), 'sennheiser'),
    (re.compile(r'\bqc45\b'), 'quietcomfort 45'),
    (re.compile(r'\bqcultra\b'), 'quietcomfort ultra'),
]


def _expand_query(query: str) -> str:
    """Expand brand abbreviations and model aliases before scoring."""
    q = query.lower()
    for pattern, replacement in _QUERY_EXPANSIONS:
        q = pattern.sub(replacement, q)
    return q


# ── Variant-identifier tokens (storage, generation, mark) ────────────────────
# Tested with exact set equality in test_matching.py — do not add tier/color here.

_VARIANT_ID_RE = re.compile(
    r"\d+(?:gb|tb|mb)"           # storage: 256gb, 512gb, 1tb
    r"|\d+(?:st|nd|rd|th)gen"    # ordinal generation: 2ndgen, 3rdgen
    r"|gen\d+"                   # generation prefix: gen2, gen3
    r"|mk\d+"                    # mark revision: mk2, mk3
)


def _variant_tokens(text: str) -> set:
    """Extract variant-identifier tokens from normalized text."""
    return set(_VARIANT_ID_RE.findall(normalize(text)))


# ── Context tokens (tier, color, connectivity) ────────────────────────────────
# Kept separate from _variant_tokens: tests assert exact set equality on _variant_tokens
# and adding tier/color tokens there would break them.

_CTX_TOKEN_RE = re.compile(
    r'\b(pro|max|ultra|mini|plus|se|lite|air'
    r'|black|white|silver|gold|blue|red|green|pink|navy|midnight|starlight|graphite|platinum'
    r'|wifi|cellular|lte|5g)\b'
)


def _ctx_tokens(text: str) -> set:
    """Extract tier/color/connectivity tokens from raw (not normalized) text."""
    return set(_CTX_TOKEN_RE.findall(text.lower()))


# ── Edit distance ─────────────────────────────────────────────────────────────

def _edit_distance(a: str, b: str) -> int:
    """Levenshtein distance between two strings."""
    if len(a) < len(b):
        a, b = b, a
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for c in a:
        curr = [prev[0] + 1]
        for j, d in enumerate(b):
            curr.append(min(prev[j] + (c != d), prev[j + 1] + 1, curr[-1] + 1))
        prev = curr
    return prev[-1]


def _fragment_in_model(part: str, model: str, model_parts: list) -> bool:
    """True if part is a substring of model, or within edit distance 1 of a model token (≥6 chars only)."""
    if part in model:
        return True
    if len(part) >= 6:
        return any(len(mp) >= 6 and _edit_distance(part, mp) <= 1 for mp in model_parts)
    return False


# ── Veto ──────────────────────────────────────────────────────────────────────

def _apply_variant_veto(score: int, query: str, product: dict) -> int:
    """Cap score at 84 when the query names a variant/context token absent from the product."""
    product_text = product.get("model", "") + " " + product.get("name", "")

    # Storage / generation / mark veto
    q_var = _variant_tokens(query)
    if q_var:
        p_var = _variant_tokens(product_text)
        if not q_var.issubset(p_var):
            score = min(score, 84)

    # Tier / color / connectivity veto
    q_ctx = _ctx_tokens(query)
    if q_ctx:
        p_ctx = _ctx_tokens(product_text)
        if not q_ctx.issubset(p_ctx):
            score = min(score, 84)

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
    expanded = _expand_query(query)
    query_clean = normalize(expanded)

    brand = normalize(product["brand"])
    model = normalize(product["model"])
    name = normalize(product["name"])
    model_parts = re.findall(r"[a-z]+\d+|\d+[a-z]+|[a-z]+|\d+", model)

    score = 0
    query_parts = re.findall(r"[a-z]+\d+|\d+[a-z]+|[a-z]+|\d+", expanded)

    # Brand match
    if brand in query_clean:
        score += 30

    if model in query_clean:
        # Full model match — strongest signal
        score += 60
        score = min(score + 10, 100)
    else:
        # Model fragment matches: exact substring or fuzzy (edit ≤ 1) for ≥6-char fragments
        model_matched_parts = set()
        for part in query_parts:
            if len(part) >= 3 and _fragment_in_model(part, model, model_parts):
                score += 50
                model_matched_parts.add(part)

        # Query words in product name — skip parts already scored via model
        for part in query_parts:
            if part in model_matched_parts:
                continue
            if len(part) >= 2 and part in name:
                score += 5

        # Brand + model fragment combo bonus
        if brand in query_clean:
            for part in query_parts:
                if len(part) >= 3 and _fragment_in_model(part, model, model_parts):
                    score += 20
                    break

        score = min(score, 100)

    # Veto uses expanded query so synonym/alias expansion is consistent
    return _apply_variant_veto(score, expanded, product)
