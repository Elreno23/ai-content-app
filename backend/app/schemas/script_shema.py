from pydantic import BaseModel

class ScriptRequest(BaseModel):
    topic:str