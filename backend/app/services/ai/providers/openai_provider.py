from app.schemas.parsers.chapter_parser import ChapterStructure
from app.services.ai.base_ai import BaseAIProvider


class OpenIAProvider(BaseAIProvider):
    async def generate_chapter_structure(self, prompt: str) -> ChapterStructure:
        raise NotImplementedError
