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


# ── Alphanum suffix conflict ──────────────────────────────────────────────────

def _alphanum_suffix_conflict(qp: str, model: str, model_parts: list) -> bool:
    """True if qp is [letters≥2][digits] absent from model, and a model token ends with same letters+different digits.

    Catches xm4 vs xm5, buds2 vs buds3 — series-code digit mismatches invisible to the veto regex.
    """
    m = re.match(r'^([a-z]+)(\d+)$', qp)
    if not m or len(m.group(1)) < 2 or qp in model:
        return False
    qletter, qdigit = m.group(1), m.group(2)
    for mp in model_parts:
        sm = re.search(r'([a-z]+)(\d+)$', mp)
        if sm and sm.group(1).endswith(qletter) and sm.group(2) != qdigit:
            return True
    return False


# ── Veto ──────────────────────────────────────────────────────────────────────

def _apply_variant_veto(score: int, query: str, product: dict,
                        query_parts: list = None, model: str = "") -> int:
    """Cap score at 84 (or 70) when the query names an identifier absent from the product."""
    product_text = product.get("model", "") + " " + product.get("name", "")

    # Storage / generation / mark veto → cap at 84
    q_var = _variant_tokens(query)
    if q_var:
        p_var = _variant_tokens(product_text)
        if not q_var.issubset(p_var):
            score = min(score, 84)

    # Tier / color / connectivity veto → cap at 84
    q_ctx = _ctx_tokens(query)
    if q_ctx:
        p_ctx = _ctx_tokens(product_text)
        if not q_ctx.issubset(p_ctx):
            score = min(score, 84)

    if query_parts and model:
        model_parts = re.findall(r"[a-z]+\d+|\d+[a-z]+|[a-z]+|\d+", model)

        # Rule 2a: alphanum suffix conflict (xm4/xm5, buds2/buds3) → cap at 70
        for qp in query_parts:
            if _alphanum_suffix_conflict(qp, model, model_parts):
                score = min(score, 70)
                break

        # Rule 2b: digit adjacency conflict (Era 300 vs 100, QC45 vs Ultra) → cap at 70
        # A pure-digit token is a discriminator only when adjacent (within 1 position)
        # to a letter token (≥3 chars) that is a substring of the normalized model.
        for i, qp in enumerate(query_parts):
            if re.match(r'^\d+$', qp) and qp not in model:
                neighbors = []
                if i > 0:
                    neighbors.append(query_parts[i - 1])
                if i < len(query_parts) - 1:
                    neighbors.append(query_parts[i + 1])
                for neighbor in neighbors:
                    if (len(neighbor) >= 3
                            and re.match(r'^[a-z]+$', neighbor)
                            and neighbor in model):
                        score = min(score, 70)
                        break

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

    # Brand gate: cap at 70 when query contains no brand signal
    if brand not in query_clean:
        score = min(score, 70)

    # Veto uses expanded query so synonym/alias expansion is consistent
    return _apply_variant_veto(score, expanded, product, query_parts, model)
