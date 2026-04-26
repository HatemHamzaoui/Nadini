"""JWT-Aussteller (RS256)."""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from pathlib import Path

from jose import jwt

from app.core.config import Settings


@dataclass(frozen=True)
class TokenPair:
    access_token: str
    refresh_token: str
    refresh_token_jti: str
    expires_in: int


class JWTIssuer:
    def __init__(self, settings: Settings) -> None:
        self._private_key = _read_pem(settings.jwt_private_key_path)
        self._public_key = _read_pem(settings.jwt_public_key_path)
        self._issuer = settings.jwt_issuer
        self._audience = settings.jwt_audience
        self._access_ttl = settings.access_token_ttl_seconds
        self._refresh_ttl = settings.refresh_token_ttl_seconds

    def issue_access_token(
        self,
        user_id: uuid.UUID,
        email: str,
        ui_language: str,
        role: str = "user",
        tenant_id: uuid.UUID | None = None,
    ) -> str:
        now = int(time.time())
        claims = {
            "iss": self._issuer,
            "aud": self._audience,
            "sub": str(user_id),
            "email": email,
            "ui_language": ui_language,
            "role": role,
            "tenant_id": str(tenant_id) if tenant_id else None,
            "iat": now,
            "nbf": now,
            "exp": now + self._access_ttl,
            "jti": str(uuid.uuid4()),
            "typ": "access",
        }
        return jwt.encode(claims, self._private_key, algorithm="RS256")

    def issue_refresh_token(self, user_id: uuid.UUID) -> tuple[str, str]:
        """Gibt (refresh_token, jti) zurück. jti wird in DB gehasht persistiert."""
        now = int(time.time())
        jti = str(uuid.uuid4())
        claims = {
            "iss": self._issuer,
            "aud": self._audience,
            "sub": str(user_id),
            "iat": now,
            "nbf": now,
            "exp": now + self._refresh_ttl,
            "jti": jti,
            "typ": "refresh",
        }
        return jwt.encode(claims, self._private_key, algorithm="RS256"), jti

    def decode(self, token: str) -> dict:
        return jwt.decode(
            token,
            self._public_key,
            algorithms=["RS256"],
            audience=self._audience,
            issuer=self._issuer,
        )

    @property
    def access_ttl_seconds(self) -> int:
        return self._access_ttl

    @property
    def public_key_pem(self) -> str:
        return self._public_key


def _read_pem(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(
            f"JWT-Schlüssel nicht gefunden: {path}. "
            "Führe scripts/generate_keys.sh aus."
        )
    return path.read_text()
