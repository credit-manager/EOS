import re
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class _EmailModel(BaseModel):
    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        email = value.strip().lower()
        if not _EMAIL_RE.fullmatch(email):
            raise ValueError("invalid email address")
        return email


class RegisterRequest(_EmailModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=12, max_length=200)
    tenant_name: str = Field(min_length=1, max_length=200)


class TokenRequest(_EmailModel):
    email: str = Field(min_length=3, max_length=320)
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
