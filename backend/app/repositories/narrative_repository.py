from sqlalchemy import select, func
from app.models.narrative import Narrative
from app.models.detected_action import DetectedAction
from app.repositories.base_repository import BaseNarrativeRepository
from sqlalchemy.orm import selectinload

class NarrativeRepository(BaseNarrativeRepository):
    def __init__(self, db):
        self.db = db


    async def save_narrative_with_actions(self, episode_number,text, actions):
        narrative=Narrative(
            text=text,
            episode_number=episode_number)
        
        self.db.add(narrative)
        await self.db.flush()

        for a in actions:
            action = DetectedAction(
                type=a["type"],
                target=a.get("target"),
                narrative_id=narrative.id
            )
            self.db.add(action)
        await self.db.commit()
        await self.db.refresh(narrative)

        return narrative

    async def get_latest_episode_number(self):
        latest_episode = select(func.max(Narrative.episode_number))
        result = await self.db.scalar(latest_episode)
        return result or 0

    async def get_next_episode_number(self):
        last = await self.get_latest_episode_number()
        return last + 1

    async def get_recent_episode(self, limit):
        recents_episodes = select(Narrative).options(selectinload(Narrative.actions_relationship)).order_by(Narrative.episode_number.desc()).limit(limit)
        result = (await self.db.scalars(recents_episodes)).all()
        return result

        