from services.ai.providers.ollama_provider import OllamaProvider
from repositories.narrative_repository import NarrativeRepository

class ScriptService:
    def __init__(self, llm_provider: OllamaProvider, narrative_repo: NarrativeRepository):
        self.llm_provider = llm_provider
        self.narrative_repo = narrative_repo

    async def generate_script(self, topic:str):
        #1. Provider devuelve un LlmResponse
        parsed = await self.llm_provider.generate_script(topic)

        #2. Convertimos acciones a dict para recibirlo en nuestro repository
        actions = [a.model_dump() for a in parsed.detected_actions]

        #3. Guardamos narrativa + acciones en la BD
        narrative = await self.narrative_repo.save_narrative_with_actions(
            text=parsed.narrative,
            actions=actions
        )
        #4. Retornamos lo guardado
        return narrative