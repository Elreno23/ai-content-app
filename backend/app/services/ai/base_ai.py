from abc import ABC, abstractmethod
from app.schemas.parsers.llm_parser import LlmResponse

class BaseAIProvider(ABC):

    @abstractmethod
    async def generate_script(self, prompt:str) -> LlmResponse:
        raise NotImplementedError