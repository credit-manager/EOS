from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    message: str
    notification_type: str
    category: str
    is_read: bool
    action_url: str | None = None
    created_at: datetime
    read_at: datetime | None = None


class NotificationListResponse(BaseModel):
    items: list[NotificationResponse]
    total: int
    unread_count: int
    limit: int
    offset: int


class NotificationCreate(BaseModel):
    user_id: UUID
    title: str = Field(max_length=500)
    message: str
    notification_type: str = Field(default="info", pattern="^(info|warning|error|success)$")
    category: str = Field(default="system", pattern="^(system|approval|payment|project|workflow)$")
    action_url: str | None = Field(default=None, max_length=1000)


class BulkNotificationCreate(BaseModel):
    user_ids: list[UUID]
    title: str = Field(max_length=500)
    message: str
    notification_type: str = Field(default="info")
    category: str = Field(default="system")
    action_url: str | None = None


class MarkReadRequest(BaseModel):
    notification_ids: list[UUID]


class NotificationStats(BaseModel):
    total: int
    unread: int
    by_type: dict[str, int]
    by_category: dict[str, int]
