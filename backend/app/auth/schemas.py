from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=200)
    tenant_name: str = Field(min_length=1, max_length=200)


class TokenRequest(BaseModel):
    email: EmailStr
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
    email: EmailStr
    tenant_id: UUID
    role: str
