from sqlalchemy import select, func
from app.models.narrative import Narrative
from app.repositories.base_repository import BaseNarrativeRepository


class NarrativeRepository(BaseNarrativeRepository):
    def __init__(self, db):
        self.db = db


    async def save_narrative_with_actions(self, episode_number:int, payload:dict):
        narrative=Narrative(
            episode_number=episode_number,
            payload=payload)
    
        self.db.add(narrative)
        await self.db.commit()
       
        return narrative

    async def get_latest_episode_number(self):
        latest_episode = select(func.max(Narrative.episode_number))
        result = await self.db.scalar(latest_episode)
        return result or 0

    async def get_next_episode_number(self):
        last = await self.get_latest_episode_number()
        return last + 1

    async def get_recent_episode(self, limit):
        recents_episodes = select(Narrative).order_by(Narrative.episode_number.desc()).limit(limit)
        result = (await self.db.scalars(recents_episodes)).all()
        return result


        