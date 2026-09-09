"""
EOS System — Users Router
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

from app.db.session import get_db
from app.core.security import get_current_user

router = APIRouter()


# Schemas
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    first_name: str
    last_name: str
    first_name_ar: Optional[str] = None
    last_name_ar: Optional[str] = None
    phone: Optional[str] = None
    role: str = "user"


class UserResponse(BaseModel):
    id: str
    email: str
    first_name: str
    last_name: str
    phone: Optional[str]
    role: str
    is_active: bool
    created_at: datetime


class UserList(BaseModel):
    users: List[UserResponse]
    total: int
    page: int
    page_size: int


# Endpoints
@router.get("/", response_model=UserList)
async def list_users(
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """List all users in tenant."""
    return UserList(
        users=[],
        total=0,
        page=page,
        page_size=page_size,
    )


@router.post("/", response_model=UserResponse)
async def create_user(
    user: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Create a new user."""
    return UserResponse(
        id="new_user",
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        phone=user.phone,
        role=user.role,
        is_active=True,
        created_at=datetime.now(),
    )


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get user by ID."""
    return UserResponse(
        id=user_id,
        email="user@example.com",
        first_name="John",
        last_name="Doe",
        phone="+201234567890",
        role="user",
        is_active=True,
        created_at=datetime.now(),
    )


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    user: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Update user details."""
    return UserResponse(
        id=user_id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        phone=user.phone,
        role=user.role,
        is_active=True,
        created_at=datetime.now(),
    )


@router.delete("/{user_id}")
async def delete_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Delete user (soft delete)."""
    return {"message": "User deleted successfully"}
