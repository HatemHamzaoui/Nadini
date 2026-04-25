"""JWT-Verifikation über JWKS-Endpoint des Auth-Service."""
from __future__ import annotations

import httpx
from jose import jwt, JWTError

from app.core.logging import get_logger

log = get_logger(__name__)


class JWTVerifyError(Exception):
    pass


class JWTVerifier:
    """Verifiziert Access-Tokens anhand des Auth-Service JWKS."""

    def __init__(self, jwks_url: str, issuer: str, audience: str) -> None:
        self._jwks_url = jwks_url
        self._issuer = issuer
        self._audience = audience
        self._jwks: dict | None = None

    async def refresh_keys(self) -> None:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(self._jwks_url)
            resp.raise_for_status()
            self._jwks = resp.json()
            log.info("jwks_refreshed", url=self._jwks_url)

    def decode(self, token: str) -> dict:
        if not self._jwks:
            raise JWTVerifyError("JWKS not loaded")
        try:
            claims = jwt.decode(
                token,
                self._jwks,
                algorithms=["RS256"],
                audience=self._audience,
                issuer=self._issuer,
            )
        except JWTError as exc:
            raise JWTVerifyError(str(exc)) from exc

        if claims.get("typ") != "access":
            raise JWTVerifyError("Wrong token type, expected 'access'")

        return claims
