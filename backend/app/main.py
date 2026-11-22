from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.exceptions import (
    ComfyUIConnectionError,
    ComfyUIResponseError,
    ComfyUITimeoutError,
    ComfyUIWorkflowError,
    LLMConnectionError,
    LLMResponseError,
    LLMTimeoutError,
    NarrativeStateError,
)
from app.routes.script_routes import router

app = FastAPI()
app.include_router(router)


@app.get("/")
async def home():
    return {"msg": "APP funcionando"}


@app.exception_handler(LLMConnectionError)
async def llm_connection_error_handler(request: Request, exc: LLMConnectionError):
    return JSONResponse(status_code=503, content={"detail": str(exc)})


@app.exception_handler(LLMTimeoutError)
async def llm_timeout_error_handler(request: Request, exc: LLMTimeoutError):
    return JSONResponse(status_code=504, content={"detail": str(exc)})


@app.exception_handler(LLMResponseError)
async def llm_response_error_handler(request: Request, exc: LLMResponseError):
    return JSONResponse(status_code=502, content={"detail": str(exc)})


@app.exception_handler(NarrativeStateError)
async def narrative_state_error_handler(request: Request, exc: NarrativeStateError):
    return JSONResponse(status_code=422, content={"detail": str(exc)})


@app.exception_handler(ComfyUIConnectionError)
async def comfy_connection_error_handler(request: Request, exc: ComfyUIConnectionError):
    return JSONResponse(status_code=503, content={"detail": str(exc)})


@app.exception_handler(ComfyUITimeoutError)
async def comfy_timeout_error_handler(request: Request, exc: ComfyUITimeoutError):
    return JSONResponse(status_code=504, content={"detail": str(exc)})


@app.exception_handler(ComfyUIResponseError)
async def comfy_response_error_handler(request: Request, exc: ComfyUIResponseError):
    return JSONResponse(status_code=502, content={"detail": str(exc)})


@app.exception_handler(ComfyUIWorkflowError)
async def comfy_workflow_error_handler(request: Request, exc: ComfyUIWorkflowError):
    return JSONResponse(status_code=500, content={"detail": str(exc)})
