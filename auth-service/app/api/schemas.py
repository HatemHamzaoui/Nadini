"""Pydantic-Schemas für Auth-API."""
from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class MagicLinkRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    email: EmailStr = Field(..., max_length=254)
    ui_language: str = Field(default="en", min_length=2, max_length=10)


class MagicLinkResponse(BaseModel):
    """Bewusst minimal — keine Auskunft, ob die E-Mail existiert."""

    message: str = "If the email exists, a sign-in link has been sent."


class MagicLinkVerifyRequest(BaseModel):
    token: str = Field(..., min_length=40, max_length=50)


class ComplianceInfo(BaseModel):
    """AI-Act-Compliance-Hinweis: Muss der User die Disclosure noch bestätigen?"""

    ai_disclosure_required: bool
    ai_disclosure_version: str | None = None
    acknowledge_endpoint: str | None = None


class UserOut(BaseModel):
    user_id: uuid.UUID
    email: EmailStr
    ui_language: str
    tenant_id: uuid.UUID | None = None
    tenant_risk_tier: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int
    user: UserOut
    compliance: ComplianceInfo


class RefreshRequest(BaseModel):
    refresh_token: str = Field(..., min_length=20, max_length=4096)


class RefreshResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int


class MeResponse(BaseModel):
    user: UserOut
    compliance: ComplianceInfo
    email_verified: bool
    last_login_at: str | None


class DisclosureTextOut(BaseModel):
    version: str
    locale: str
    title: str
    body: str
    short_label: str
    acknowledge_button: str


class DisclosureAcknowledgeRequest(BaseModel):
    version: str = Field(..., min_length=1, max_length=20)
    locale: str | None = Field(default=None, max_length=10)


class DisclosureAcknowledgeResponse(BaseModel):
    acknowledged: bool = True
    version: str


class ErrorResponse(BaseModel):
    error: str
    detail: str | None = None
