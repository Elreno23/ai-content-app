from pydantic import BaseModel, Field
from typing import List, Optional, Literal

ActionType = Literal[
    "USER_ARRIVED-LATE",
    "USER_LIED",
    "USER_HELPED",
    "USER_IGNORED"
]

class DetectedAction(BaseModel):
    type: ActionType
    target:Optional[str] = None

class LlmResponse(BaseModel):
    narrative: str
    detected_actions: List[DetectedAction] = Field(default_factory=list)