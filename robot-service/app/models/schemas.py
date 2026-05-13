from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from enum import Enum


class RobotStatus(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    BUSY = "busy"
    MAINTENANCE = "maintenance"


class RobotType(str, Enum):
    INDUSTRIAL = "industrial"
    MOBILE = "mobile"
    DRONE = "drone"
    MANIPULATOR = "manipulator"


class Location(BaseModel):
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0


class RobotCreate(BaseModel):
    name: str
    type: RobotType
    model: str
    capabilities: List[str] = []
    location: Optional[Location] = None


class RobotUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[RobotStatus] = None
    location: Optional[Location] = None
    assigned_mission_id: Optional[str] = None


class RobotResponse(BaseModel):
    id: str
    name: str
    type: str
    model: str
    status: RobotStatus
    capabilities: List[str]
    location: Location
    assigned_mission_id: Optional[str]
    owner_id: str
    created_at: datetime
    updated_at: datetime
