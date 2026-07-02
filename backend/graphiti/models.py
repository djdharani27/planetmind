"""Pydantic models for Graphiti integration — episode inputs and entity types."""

from pydantic import BaseModel
from enum import Enum
from datetime import datetime


class PlanetMindEntityType(str, Enum):
    EQUIPMENT = "equipment"
    COMPONENT = "component"
    FAILURE = "failure"
    MAINTENANCE_ACTIVITY = "maintenance_activity"
    TECHNICIAN = "technician"
    DATE = "date"
    LOCATION = "location"
    REGULATION = "regulation"
    DOCUMENT = "document"
    PROCESS_PARAMETER = "process_parameter"


ENTITY_TYPE_GROUPS = {
    "equipment": "equipment",
    "component": "component",
    "failure": "failure",
    "maintenance_activity": "maintenanceactivity",
    "technician": "technician",
    "regulation": "regulation",
    "document": "document",
    "location": "location",
    "process_parameter": "processparameter",
    "date": "date",
}


class DocumentEpisodeInput(BaseModel):
    doc_id: str
    filename: str
    text: str
    chunks: list[dict] = []
    metadata: dict = {}


class ConversationEpisodeInput(BaseModel):
    session_id: str
    user_message: str
    assistant_response: str = ""
    timestamp: datetime | None = None
    metadata: dict = {}
