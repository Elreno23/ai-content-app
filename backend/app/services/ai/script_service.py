from app.services.ai.providers.ollama_provider import OllamaProvider
from app.repositories.narrative_repository import NarrativeRepository
from app.models.narrative import Narrative
from app.schemas.parsers.llm_parser import NarrativeContext


class ScriptService:
    def __init__(self, llm_provider: OllamaProvider, narrative_repo: NarrativeRepository):
        self.llm_provider = llm_provider
        self.narrative_repo = narrative_repo
        

    async def generate_script(self, topic:str | None = None) -> Narrative:
        last_episode = await self.narrative_repo.get_latest_episode_number()

        if last_episode == 0 and not topic:
            raise ValueError("Se requiere un tema (topic) para iniciar el primer episodio de la serie.")

        if last_episode == 0:
            prompt_topic = topic

        else:
            recent_episodes = await self.narrative_repo.get_recent_episode(limit=10)
            chronological_episodes = recent_episodes[::-1]
            context_episodes = self.format_context(chronological_episodes)
            prompt = f"""Eres un generador narrativo. Tu única tarea es producir una salida en formato JSON ESTRICTO.

REGLAS:
- Devuelve SOLO JSON. Nada de texto fuera del JSON.
- No añadas explicaciones, comentarios ni texto antes o después.
- El JSON debe tener exactamente estos campos:

{{
    "narrative": "string",
    "detected_actions": [
        {{
            "type": "USER_ARRIVED_LATE" | "USER_LIED" | "USER_HELPED" | "USER_IGNORED",
            "target": "string o null"
        }}
    ]
}}

- La narrativa debe ser texto libre.
- Las acciones deben pertenecer SOLO a la taxonomía permitida.
- Si no puedes generar un JSON válido, devuelve exactamente:
    {{"error":"UNABLE_TO_GENERATE_JSON"}}

EJEMPLO VÁLIDO:
{{
    "narrative": "María llegó tarde a la reunión y todos la miraron en silencio.",
    "detected_actions": [
        {{
            "type": "USER_ARRIVED_LATE",
            "target": "María"
        }}
    ]
}}

EJEMPLO DE ERROR:
{{"error":"UNABLE_TO_GENERATE_JSON"}}

{context_episodes}

TEMA O ENTRADA ACTUAL:
"{prompt_topic}"

Ahora genera la salida JSON siguiendo estas reglas."""
            
        parsed = await self.llm_provider.generate_script(prompt)
        actions = [a.model_dump() for a in parsed.detected_actions]
        next_episode = await self.narrative_repo.get_next_episode_number()

        narrative = await self.narrative_repo.save_narrative_with_actions(
            episode_number = next_episode,
            text=parsed.narrative,
            actions=actions
        )
        return narrative


    def format_context(self, episodes:list) -> str:
        if not episodes:
            return "--- Nota: Este es el inicio de la historia. No hay episodios anteriores. ---"
        
        narrative_context = [NarrativeContext.model_validate(ep) for ep in episodes]
        narrative_serialize = [narrative.model_dump() for narrative in narrative_context]

        history_summary = "\n".join(
        f"[Episodio: {ep['episode_number']}]\n"
        f"Narrativa: {ep['text']}\n"
        f"Acciones previas: {', '.join([a['target'] for a in ep['detected_actions'] if a['target']])}"
        for ep in narrative_serialize)

        return f"\n---\nHISTORIAL DE EPISODIOS ANTERIORES:\n{history_summary}\n---"

