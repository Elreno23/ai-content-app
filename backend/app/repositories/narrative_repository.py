from sqlalchemy.orm import Session
from models.narrative import Narrative
from models.detected_action import DetectedAction

class NarrativeRepository:
    def __init__(self,db):
        self.db = db

    async def save_narrative_with_actions(self, text:str, actions: list[dict]):
        #1. Creamos narrativa
        narrative = Narrative(text=text)
        self.db.add(narrative)

        #2. Validamos que la narrativa exista
        await self.db.flush()

        #3. Le asignamos la accion del json que devuelve el LLM a nuestra tabla
        for a in actions:
            action = DetectedAction(
                type=a["type"],
                target=a.get("target"),
                narrative_id=narrative.id
            )
            self.db.add(action)
            
        await self.db.commit()
        await self.db.refresh(narrative)

        return  narrative