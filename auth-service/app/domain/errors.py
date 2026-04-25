"""Domänen-spezifische Exceptions."""
from __future__ import annotations


class DomainError(Exception):
    """Basisklasse aller fachlichen Fehler."""


class RateLimitExceeded(DomainError):
    pass


class TokenInvalid(DomainError):
    """Token-Format ungültig oder unbekannt."""


class TokenExpiredOrUsed(DomainError):
    """Token abgelaufen oder bereits verbraucht."""


class MailerError(DomainError):
    pass
