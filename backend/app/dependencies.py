from fastapi import Depends
from services.ai.providers.ollama_provider import OllamaProvider
from services.ai.script_service import ScriptService
from repositories.narrative_repository import NarrativeRepository
from db.connection import get_db

def get_script_service(db = Depends(get_db)):
    provider = OllamaProvider()
    repo = NarrativeRepository(db)
    return ScriptService(provider, repo)