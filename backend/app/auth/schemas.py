from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

_EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
Role = Literal["admin", "member"]


class RegisterRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "email": "user@example.com",
                    "password": "securepassword123",
                    "tenant_name": "Acme Corp",
                }
            ]
        }
    )

    email: str = Field(min_length=3, max_length=320, pattern=_EMAIL_PATTERN)
    password: str = Field(min_length=12, max_length=200)
    tenant_name: str = Field(min_length=1, max_length=200)


class TokenRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "email": "user@example.com",
                    "password": "securepassword123",
                }
            ]
        }
    )

    email: str = Field(min_length=3, max_length=320, pattern=_EMAIL_PATTERN)
    password: str = Field(min_length=1, max_length=200)
    tenant_id: UUID | None = None


class TokenResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                    "refresh_token": "dGhpcyBpcyBhIHJlZnJlc2ggdG9rZW4...",
                    "token_type": "bearer",
                    "user_id": "550e8400-e29b-41d4-a716-446655440000",
                    "tenant_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
                    "role": "admin",
                    "expires_in": 3600,
                    "refresh_expires_in": 2592000,
                }
            ]
        }
    )

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user_id: UUID
    tenant_id: UUID
    role: str
    expires_in: int
    refresh_expires_in: int


class RefreshTokenRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "refresh_token": "dGhpcyBpcyBhIHJlZnJlc2ggdG9rZW4...",
                }
            ]
        }
    )

    refresh_token: str


class MeResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "user_id": "550e8400-e29b-41d4-a716-446655440000",
                    "email": "user@example.com",
                    "tenant_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
                    "role": "admin",
                }
            ]
        }
    )

    user_id: UUID
    email: str
    tenant_id: UUID
    role: str


class MemberCreateRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "email": "member@example.com",
                    "role": "member",
                }
            ]
        }
    )

    email: str = Field(min_length=3, max_length=320, pattern=_EMAIL_PATTERN)
    role: Role = "member"


class MemberRoleUpdate(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "role": "admin",
                }
            ]
        }
    )

    role: Role


class MemberResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "user_id": "550e8400-e29b-41d4-a716-446655440000",
                    "email": "member@example.com",
                    "tenant_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
                    "role": "member",
                }
            ]
        }
    )

    user_id: UUID
    email: str
    tenant_id: UUID
    role: Role
