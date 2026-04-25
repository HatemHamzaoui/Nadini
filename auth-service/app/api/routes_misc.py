"""Hilfs-Endpunkte: /health, /.well-known/jwks.json."""
from __future__ import annotations

import base64
from typing import Annotated

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
from fastapi import APIRouter, Depends

from app.api.deps import get_jwt_issuer
from app.core.jwt import JWTIssuer

router = APIRouter(tags=["meta"])


@router.get("/health", summary="Liveness probe")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/.well-known/jwks.json", summary="JSON Web Key Set für JWT-Verifikation")
async def jwks(jwt: Annotated[JWTIssuer, Depends(get_jwt_issuer)]) -> dict:
    pem = jwt.public_key_pem.encode()
    public_key = serialization.load_pem_public_key(pem)
    if not isinstance(public_key, RSAPublicKey):
        return {"keys": []}

    numbers = public_key.public_numbers()
    n = _int_to_b64url(numbers.n)
    e = _int_to_b64url(numbers.e)

    return {
        "keys": [
            {
                "kty": "RSA",
                "use": "sig",
                "alg": "RS256",
                "kid": "auth-service-key-1",
                "n": n,
                "e": e,
            }
        ]
    }


def _int_to_b64url(value: int) -> str:
    byte_length = (value.bit_length() + 7) // 8
    return (
        base64.urlsafe_b64encode(value.to_bytes(byte_length, "big"))
        .rstrip(b"=")
        .decode("ascii")
    )
