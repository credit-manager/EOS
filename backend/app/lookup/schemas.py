from typing import Any
from uuid import UUID

from pydantic import BaseModel


class LookupItem(BaseModel):
    id: UUID
    label: str
    data: dict[str, Any]
