import re


def normalize(text):
    return re.sub(r"[^a-z0-9]", "", text.lower())


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

    # Full model match — early return, strongest signal
    if model in query_clean:
        score += 60
        return min(score + 10, 100)

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

    return min(score, 100)
