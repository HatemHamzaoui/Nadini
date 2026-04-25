"""Kryptografische Helfer: Token-Generierung, Hashing."""
from __future__ import annotations

import base64
import hashlib
import secrets


def generate_token(byte_length: int = 32) -> str:
    """Erzeugt URL-sicheres Token (base64url ohne Padding).

    32 Bytes → 256 bit Entropie → ~43 Zeichen.
    """
    raw = secrets.token_bytes(byte_length)
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def hash_token(token: str) -> bytes:
    """SHA-256 Hash des Tokens. Wird in der DB gespeichert."""
    return hashlib.sha256(token.encode("ascii")).digest()


def constant_time_equals(a: str, b: str) -> bool:
    """Konstantzeit-Stringvergleich gegen Timing-Attacken."""
    return secrets.compare_digest(a.encode("utf-8"), b.encode("utf-8"))
