from app.schemas.parsers.llm_parser import LlmResponse
from app.services.ai.base_ai import BaseAIProvider

MODEL_NAME = ""


class OpenIAProvider(BaseAIProvider):
    async def generate_script(self, prompt: str) -> LlmResponse:
        raise NotImplementedError
