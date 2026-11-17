from fastapi import Depends
from app.services.ai.providers.ollama_provider import OllamaProvider
from app.services.ai.script_service import ScriptService
from app.repositories.narrative_repository import NarrativeRepository
from app.services.ai.visual_bridge import VisualBridge
from app.db.connection import get_db

def get_script_service(db = Depends(get_db)):
    provider = OllamaProvider()
    repo = NarrativeRepository(db)
    bridge = VisualBridge()
    return ScriptService(provider, repo, bridge)