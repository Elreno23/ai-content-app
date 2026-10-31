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

        recent_episodes = await self.narrative_repo.get_recent_episode(limit=10)
        chronological_episodes = recent_episodes[::-1]
        context_episodes = self.format_context(chronological_episodes)

        if topic == "string":
            topic = None

        prompt_topic = f"\n---\nSITUACIÓN ACTUAL \ ENTRADA ACTUAL:\n{topic}\n---\n" if topic else ""
        prompt = f"""Eres un generador narrativo. Tu única tarea es producir una salida en formato JSON ESTRICTO.


{context_episodes}

{prompt_topic}

REGLAS DE CONTINUIDAD:
- La nueva "narrative" DEBE continuar la historia exactamente donde se quedó el último episodio del historial.
- No repitas eventos pasados, pero mantén la coherencia con lo que ya ocurrió y las acciones detectadas previamente.

REGLAS DE FORMATO:
- Devuelve SOLO JSON. Nada de texto fuera del JSON.
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

Ahora genera la salida JSON siguiendo estas reglas."""
        
        print(f"QUE ESTAMOS PASANDO EN EL PROMPT {prompt_topic}")
        print(f"QUE ESTAMOS PASANDO EN EL PROMPT {prompt}")
        parsed = await self.llm_provider.generate_script(prompt)
        actions = [a.model_dump() for a in parsed.detected_actions]
        next_episode = await self.narrative_repo.get_next_episode_number()

        print(f"que estamos pasando {parsed}")
        print(f"que acciones hay {actions}")
        print(f"siguiente episodio {next_episode}")
        narrative = await self.narrative_repo.save_narrative_with_actions(
            episode_number = next_episode,
            text=parsed.narrative,
            actions=actions
        )
        return narrative


    def format_context(self, episodes:list) -> str:
        if not episodes:
            return " "
        
        narrative_context = [NarrativeContext.model_validate(ep) for ep in episodes]
        print(f"ESTO QUE EEEEEH? {narrative_context}")
        narrative_serialize = [narrative.model_dump() for narrative in narrative_context]
        print(f"QUE HAY AQUIII? {narrative_serialize}")
        history_summary = "\n".join(
        f"[Episodio: {ep['episode_number']}]\n"
        f"Narrativa: {ep['text']}\n"
        f"Acciones previas: {', '.join((a['type'] + (' (' + a['target'] + ')' if a['target'] else '') for a in ep['actions_relationship']))}"
        for ep in narrative_serialize)

        return f"\n---\n###HISTORIAL DE EPISODIOS ANTERIORES (Usa esto para mantener una continuidad estricta):\n{history_summary}\n---"

