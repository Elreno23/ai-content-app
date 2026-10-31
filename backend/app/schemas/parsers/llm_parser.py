from pydantic import BaseModel, Field, ConfigDict
from enum import Enum

class ActionType(str,Enum):
    USER_ARRIVED_LATE="USER_ARRIVED_LATE",
    USER_LIED="USER_LIED",
    USER_HELPED="USER_HELPED",
    USER_IGNORED="USER_IGNORED"

class DetectedActions(BaseModel):
    type: ActionType
    target: str | None = None

    model_config = ConfigDict(from_attributes=True)

class LlmResponse(BaseModel):
    narrative:str
    detected_actions: list[DetectedActions] = Field(default_factory=list)

class NarrativeContext(BaseModel):
    episode_number:int
    text:str
    actions_relationship: list[DetectedActions] = Field(default_factory=list)
    
    model_config = ConfigDict(from_attributes=True)