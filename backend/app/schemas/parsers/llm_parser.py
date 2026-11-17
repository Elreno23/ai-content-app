from pydantic import BaseModel, Field, ConfigDict, field_validator

class VisualMetadataContext(BaseModel):
    character:str
    visual_action:str
    expression_gaze:str
    props_hand:str | None = None
    environment:str
    camera_lighting:str

    @field_validator("props_hand", mode="before")
    @classmethod
    def clean_null_string(cls,v:object) -> object:
        if isinstance(v, str) and v.strip().lower() in ("none","null","n/a","na"):
            return None
        return v


class LlmResponse(BaseModel):
    narrative:str
    detected_actions: list[str] = Field(default_factory=list)
    visual_metadata: VisualMetadataContext