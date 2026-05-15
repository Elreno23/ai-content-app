from fastapi import APIRouter, status
from backend.app.schemas.script_shema import ScriptRequest
from backend.app.services.ai.ai_services import generate_script

router = APIRouter()

@router.post("/generate-script")
async def generate_script_endpoint(data: ScriptRequest):
    print(data.topic)
    result = await generate_script(data.topic)
    return {"msg":result}