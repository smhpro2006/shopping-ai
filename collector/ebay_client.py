"""eBay Browse API client with OAuth 2.0 client-credentials token management."""

import base64
import time
import httpx

_SANDBOX_TOKEN_URL = "https://api.sandbox.ebay.com/identity/v1/oauth2/token"
_PRODUCTION_TOKEN_URL = "https://api.ebay.com/identity/v1/oauth2/token"

_SANDBOX_SEARCH_URL = "https://api.sandbox.ebay.com/buy/browse/v1/item_summary/search"
_PRODUCTION_SEARCH_URL = "https://api.ebay.com/buy/browse/v1/item_summary/search"

_SCOPE = "https://api.ebay.com/oauth/api_scope"
_MARKETPLACE = "EBAY-US"


class EbayAuthError(Exception):
    pass


class EbayClient:
    def __init__(self, app_id: str, cert_id: str, environment: str = "sandbox"):
        if not app_id or not cert_id:
            raise EbayAuthError("EBAY_APP_ID and EBAY_CERT_ID must be set")
        self._app_id = app_id
        self._cert_id = cert_id
        self._sandbox = environment.lower() == "sandbox"
        self._token: str | None = None
        self._token_expires_at: float = 0.0
        self._http = httpx.Client(timeout=15.0)

    # ── token management ─────────────────────────────────────────────────────

    def _token_url(self) -> str:
        return _SANDBOX_TOKEN_URL if self._sandbox else _PRODUCTION_TOKEN_URL

    def _search_url(self) -> str:
        return _SANDBOX_SEARCH_URL if self._sandbox else _PRODUCTION_SEARCH_URL

    def _credentials_b64(self) -> str:
        raw = f"{self._app_id}:{self._cert_id}"
        return base64.b64encode(raw.encode()).decode()

    def _fetch_token(self) -> None:
        resp = self._http.post(
            self._token_url(),
            headers={
                "Authorization": f"Basic {self._credentials_b64()}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={"grant_type": "client_credentials", "scope": _SCOPE},
        )
        if resp.status_code != 200:
            raise EbayAuthError(
                f"Token request failed {resp.status_code}: {resp.text[:200]}"
            )
        body = resp.json()
        self._token = body["access_token"]
        # Expire 60 s early to avoid using a stale token at the boundary
        self._token_expires_at = time.monotonic() + body["expires_in"] - 60

    def _ensure_token(self) -> str:
        if self._token is None or time.monotonic() >= self._token_expires_at:
            self._fetch_token()
        return self._token  # type: ignore[return-value]

    # ── public API ───────────────────────────────────────────────────────────

    def search(self, query: str, limit: int = 20) -> dict:
        """Call Browse API item_summary/search and return the raw response dict."""
        token = self._ensure_token()
        resp = self._http.get(
            self._search_url(),
            headers={
                "Authorization": f"Bearer {token}",
                "X-EBAY-C-MARKETPLACE-ID": _MARKETPLACE,
                "X-EBAY-C-ENDUSERCTX": "affiliateCampaignId=0",
            },
            params={
                "q": query,
                "limit": limit,
                "filter": "buyingOptions:{FIXED_PRICE}",
            },
        )
        resp.raise_for_status()
        return resp.json()

    def close(self) -> None:
        self._http.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
