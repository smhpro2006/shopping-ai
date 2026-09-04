import json
from typing import Optional, List
import anthropic

from backend.app.core.config import ANTHROPIC_API_KEY
from backend.app.product_matching import normalize

_client: Optional[anthropic.Anthropic] = None

_INTENT_SYSTEM = (
    "You are a product search intent analyzer. "
    "Extract structured search intent from any language query. "
    "Always respond with valid JSON only — no explanation, no markdown."
)

_SUMMARY_SYSTEM = (
    "Write a single helpful search result summary sentence (max 15 words). "
    "Be friendly and specific. No quotes around the sentence."
)


def get_client() -> Optional[anthropic.Anthropic]:
    global _client
    if _client is None and ANTHROPIC_API_KEY:
        _client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    return _client


def parse_search_intent(query: str) -> Optional[dict]:
    """Use Claude Haiku to extract structured intent from a search query."""
    client = get_client()
    if not client:
        return None
    try:
        response = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=300,
            system=[{
                "type": "text",
                "text": _INTENT_SYSTEM,
                "cache_control": {"type": "ephemeral"},
            }],
            messages=[{
                "role": "user",
                "content": (
                    f'Extract intent from: "{query}"\n\n'
                    "Return ONLY this JSON (null for missing):\n"
                    '{"brand":null,"model":null,'
                    '"category":null,"max_price":null,"min_price":null,'
                    '"features":[],"language":"en"}\n\n'
                    "category must be one of: Headphones, Earbuds, Speakers, Keyboards, Mice, or null."
                ),
            }],
        )
        text = next((b.text for b in response.content if b.type == "text"), "")
        return json.loads(text.strip())
    except Exception:
        return None


def enhance_score_with_intent(base_score: int, product: dict, intent: dict) -> int:
    """Boost match score using AI-extracted intent fields."""
    score = base_score

    if intent.get("brand"):
        ai_brand = normalize(intent["brand"])
        prod_brand = normalize(product["brand"])
        if ai_brand and (ai_brand in prod_brand or prod_brand in ai_brand):
            score = max(score, 30)

    if intent.get("model"):
        ai_model = normalize(intent["model"])
        prod_model = normalize(product["model"])
        if ai_model and ai_model in prod_model:
            score = max(score, 60)

    prod_name = normalize(product["name"])
    for feature in intent.get("features", []):
        feat = normalize(feature)
        if feat and len(feat) >= 3 and feat in prod_name:
            score += 8

    return min(score, 100)


def generate_summary(query: str, total: int, intent: dict) -> str:
    """Generate a one-sentence summary of search results."""
    client = get_client()
    if not client or total == 0:
        return ""
    try:
        response = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=60,
            system=[{
                "type": "text",
                "text": _SUMMARY_SYSTEM,
                "cache_control": {"type": "ephemeral"},
            }],
            messages=[{
                "role": "user",
                "content": f'Query: "{query}" | {total} result(s) | Intent: {json.dumps(intent)}',
            }],
        )
        text = next((b.text for b in response.content if b.type == "text"), "")
        return text.strip().strip('"')
    except Exception:
        return ""
