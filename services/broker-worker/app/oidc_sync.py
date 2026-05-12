import logging
import threading
import time
from typing import Optional
import jwt as pyjwt
import google.auth.transport.requests
from google.oauth2 import id_token as google_id_token

logger = logging.getLogger(__name__)
_OIDC_REFRESH_BUFFER = 30

class SyncOidcTokenProvider:
    def __init__(self, audience: str) -> None:
        self._audience = audience
        self._cached_token: Optional[str] = None
        self._token_expiry: float = 0.0
        self._lock = threading.Lock()

    def get_token(self) -> Optional[str]:
        with self._lock:
            now = time.time()
            if self._cached_token is not None and now < self._token_expiry - _OIDC_REFRESH_BUFFER:
                return self._cached_token
            token, exp = self._fetch_token()
            self._cached_token = token
            self._token_expiry = exp
            return token

    def _fetch_token(self) -> tuple[Optional[str], float]:
        try:
            request = google.auth.transport.requests.Request()
            token = google_id_token.fetch_id_token(request, self._audience)
            payload = pyjwt.decode(token, options={"verify_signature": False})
            return token, float(payload.get("exp", time.time() + 3600))
        except Exception:
            logger.debug("OIDC token fetch skipped (not running on GCP)")
            return None, 0.0

    def attach_to_headers(self, headers: dict) -> dict:
        token = self.get_token()
        if token is None:
            return headers
        return {**headers, "Authorization": f"Bearer {token}"}
