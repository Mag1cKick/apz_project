from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime
from enum import Enum
from uuid import UUID


class MissionStatus(str, Enum):
    PENDING = "pending"
    QUEUED = "queued"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"


class MissionCreate(BaseModel):
    title: str
    description: Optional[str] = None
    robot_id: Optional[str] = None
    priority: int = 1


class MissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    description: Optional[str]
    robot_id: Optional[str]
    status: MissionStatus
    priority: int
    created_by: str
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
