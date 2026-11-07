import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone

import jwt

from api.config import Settings
from api.errors import UnauthorizedError


class PasswordHasher:
    """scrypt with a random salt per password."""

    N, R, P = 2**14, 8, 1

    def hash(self, password: str) -> str:
        salt = os.urandom(16)
        digest = hashlib.scrypt(password.encode(), salt=salt, n=self.N, r=self.R, p=self.P)
        return f"{salt.hex()}${digest.hex()}"

    def verify(self, password: str, stored: str) -> bool:
        try:
            salt_hex, digest_hex = stored.split("$")
            digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt_hex), n=self.N, r=self.R, p=self.P)
        except ValueError:
            return False
        return hmac.compare_digest(digest.hex(), digest_hex)


class TokenService:
    ALGORITHM = "HS256"

    def __init__(self, settings: Settings):
        self._secret = settings.secret_key
        self._hours = settings.token_hours

    def issue(self, user_id: int) -> str:
        payload = {"sub": str(user_id), "exp": datetime.now(timezone.utc) + timedelta(hours=self._hours)}
        return jwt.encode(payload, self._secret, algorithm=self.ALGORITHM)

    def read_user_id(self, token: str) -> int:
        try:
            return int(jwt.decode(token, self._secret, algorithms=[self.ALGORITHM])["sub"])
        except (jwt.PyJWTError, KeyError, ValueError):
            raise UnauthorizedError("Sesión inválida o expirada")
