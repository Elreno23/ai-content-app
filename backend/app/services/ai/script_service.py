from app.services.ai.providers.ollama_provider import OllamaProvider
from app.repositories.narrative_repository import NarrativeRepository
from app.models.narrative import Narrative



class ScriptService:
    def __init__(self, llm_provider: OllamaProvider, narrative_repo: NarrativeRepository):
        self.llm_provider = llm_provider
        self.narrative_repo = narrative_repo
        
    async def generate_script(self, topic:str | None = None) -> Narrative:
        last_episode = await self.narrative_repo.get_latest_episode_number()

        if last_episode == 0 and not topic:
            raise ValueError("Se requiere un tema (topic) para iniciar el primer episodio de la serie.")

        if topic == "string":
            topic = None

        context_episodes =  await self.get_prompt_context()
        prompt = self.build_prompt(context_episodes, topic)
        parsed = await self.llm_provider.generate_script(prompt)
        print(f"QUE PASA AQUI????????{parsed}")
        next_episode = await self.narrative_repo.get_next_episode_number()
        payload_data = parsed.model_dump()
        print(f"QUE COÑO ES {payload_data}")
        narrative = await self.narrative_repo.save_narrative_with_actions(
            episode_number=next_episode,
            payload=payload_data
        )
        return narrative

    async def get_prompt_context(self):
        history_text = ""
        last_visual = None
        recent_episodes = await self.narrative_repo.get_recent_episode(limit=3)
        if recent_episodes:
            chronological_episodes = recent_episodes[::-1]
            history_summary = "\n".join(
                f"[Episodio: {ep.episode_number}]\n"
                f"Acciones previas: {', '.join(a for a in ep.payload['detected_actions'])}"
                for ep in chronological_episodes
            )   
            print(f"HOLAAAA {history_summary}")
            history_text = f"\n---\n###HISTORIAL DE EPISODIOS ANTERIORES:\n{history_summary}\n---"
            last_ep = recent_episodes[0]

            if last_ep and last_ep.payload:
                payload_data = last_ep.payload
                last_visual = payload_data.get("visual_metadata")
        
        if last_visual:
            visual_anchor_text = f"""
        ---
        ESTADO VISUAL EN EL QUE TERMINÓ LA ESCENA ANTERIOR:
        - character: {last_visual.get("character")}
        - visual_action: {last_visual.get("visual_action")}
        - expression_gaze: {last_visual.get("expression_gaze")}
        - props_hand: {last_visual.get("props_hand")}
        - environment: {last_visual.get("environment")}
        - camera_lighting: {last_visual.get("camera_lighting")}
        ---
        """
        else:
            visual_anchor_text = ("\n---\nESTADO VISUAL: Inicio de la serie (Primer fotograma).\n---\n")
        print(f"QLQQQQQQ: {visual_anchor_text}")
        return {"history_text": history_text,
                "visual_anchor_text": visual_anchor_text}

    def build_prompt(self, context_episodes: dict, topic: str | None) -> str:
        history_text = context_episodes.get("history_text","")
        visual_anchor_text = context_episodes.get("visual_anchor_text", "")
        prompt_topic = f"\n---\nSITUACIÓN ACTUAL \ ENTRADA ACTUAL:\n{topic}\n---\n" if topic else ""

        return f"""Eres el Guionista Técnico y Director de Fotografía de un motor narrativo audiovisual. 
Tu única tarea es producir una salida en formato JSON ESTRICTO que describa UNA SOLA MICRO-ESCENA (un instante concreto en el tiempo, no un resumen del capítulo).

{history_text}

{visual_anchor_text}

{prompt_topic}

REGLAS DE NARRATIVA Y CONTINUIDAD:
- Si hay historial de episodios anteriores, la nueva "narrative" DEBE continuar la acción exactamente donde se quedó. Si es la primera escena, introduce la situación inicial con gancho.
- Cada nuevo episodio debe introducir un cambio de tornas, una escalada real, un silencio incómodo o una reacción física nueva. Prohibido repetir el mismo conflicto emocional o los mismos argumentos de los episodios anteriores; la escena tiene que evolucionar o moverse hacia un punto de ruptura.
- Escribe en tiempo presente y describe acciones físicas inmediatas y concretas (qué pasa AHORA), evitando resúmenes literarios o elipsis temporales.

REGLAS DE DIRECCIÓN DE ARTE (VISUAL METADATA):
- "character": Descripción del personaje presente en la escena y su estado físico.
- "visual_action": La acción física exacta congelada en este fotograma.
- "expression_gaze": Hacia dónde mira el personaje y la expresión exacta de su rostro.
- "props_hand": Qué sostiene en la mano u objetos interactivos inmediatos en la escena (o ESTRICTAMENTE None si no hay nada).
- "environment": El escenario inmediato y detalles de fondo del plano.
- "camera_lighting": Encuadre del plano (ej. plano medio, primer plano) e iluminación exacta.

REGLAS DE FORMATO:
- Devuelve SOLO JSON. Nada de texto fuera del JSON.
- El JSON debe cumplir exactamente esta estructura:
{{
    "narrative": "string",
    "detected_actions": [
        "Descripción corta de la acción 1 en texto plano",
        "Descripción corta de la acción 2 en texto plano",
        "Descripción corta de la acción 3 en texto plano",
        "etc..."
    ],
    "visual_metadata": {{
        "character": "string",
        "visual_action": "string",
        "expression_gaze": "string",
        "props_hand": "string o None",
        "environment": "string",
        "camera_lighting": "string"
    }}
}}

Ahora genera la salida JSON siguiendo estas reglas."""
    
   

