from pydantic import BaseModel, Field
from typing import List
from enum import Enum

class ActionType(str,Enum):
    USER_ARRIVED_LATE="USER_ARRIVED_LATE",
    USER_LIED="USER_LIED",
    USER_HELPED="USER_HELPED",
    USER_IGNORED="USER_IGNORED"

class DetectedActions(BaseModel):
    type: ActionType
    target: str | None = None

class LlmResponse(BaseModel):
    narrative:str
    detected_actions: List[DetectedActions] = Field(default_factory=List)