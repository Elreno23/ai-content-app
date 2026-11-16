from pydantic import BaseModel, Field, ConfigDict

class VisualMetadataContext(BaseModel):
    character:str
    visual_action:str
    expression_gaze:str
    props_hand:str | None = None
    environment:str
    camera_lighting:str

class LlmResponse(BaseModel):
    narrative:str
    detected_actions: list[str] = Field(default_factory=list)
    visual_metadata: VisualMetadataContext