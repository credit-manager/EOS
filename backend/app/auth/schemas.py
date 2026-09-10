from uuid import UUID

from pydantic import BaseModel, Field

_EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


class RegisterRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320, pattern=_EMAIL_PATTERN)
    password: str = Field(min_length=12, max_length=200)
    tenant_name: str = Field(min_length=1, max_length=200)


class TokenRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320, pattern=_EMAIL_PATTERN)
    password: str = Field(min_length=1, max_length=200)
    tenant_id: UUID | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    tenant_id: UUID
    role: str
    expires_in: int


class MeResponse(BaseModel):
    user_id: UUID
    email: str
    tenant_id: UUID
    role: str
