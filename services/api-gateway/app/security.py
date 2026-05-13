import logging
import jwt
from jwt.exceptions import InvalidTokenError
from app.config import settings

logger = logging.getLogger(__name__)

class TokenService:
    def __init__(self) -> None:
        self._secret = settings.jwt_secret_key
        self._algorithm = settings.jwt_algorithm

    def decode_token(self, token: str) -> dict:
        try:
            return jwt.decode(
                token,
                self._secret,
                algorithms=[self._algorithm],
            )
        except InvalidTokenError as exc:
            raise ValueError(str(exc)) from exc

    def get_user_id(self, token: str) -> str:
        payload = self.decode_token(token)
        return payload["sub"]