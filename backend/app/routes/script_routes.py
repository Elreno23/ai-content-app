from fastapi import APIRouter,Depends
from app.schemas.script_schema import ScriptRequest
from app.services.ai.script_service import ScriptService
from app.dependencies import get_script_service

router = APIRouter()

@router.post("/generate-script")
async def generate_script_endpoint(
    data: ScriptRequest,
    service: ScriptService = Depends(get_script_service)
    ):
    
    result = await service.generate_script(data.topic)
  
    return {"msg":result}

