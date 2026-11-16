from abc import ABC, abstractmethod

class BaseNarrativeRepository(ABC):

    @abstractmethod
    async def save_narrative_with_actions(self, episode_number:int, payload:dict):
        raise NotImplementedError

    @abstractmethod
    async def get_latest_episode_number(self) -> int:
        raise NotImplementedError
    
    @abstractmethod
    async def get_next_episode_number(self) -> int:
        raise NotImplementedError
    
    @abstractmethod
    async def get_recent_episode(self, limit:int) -> list:
        raise NotImplementedError


