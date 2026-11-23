from abc import ABC, abstractmethod

from app.schemas.parsers.chapter_parser import ChapterStructure


class BaseAIProvider(ABC):
    @abstractmethod
    async def generate_chapter_structure(self, prompt: str) -> ChapterStructure:
        """Genera la estructura completa de un capítulo (escenas + beats).

        Contrato: en éxito retorna ``ChapterStructure`` validada contra
        CHAPTER_SCHEMA (límites 4-6 escenas, 2-5 beats, numeración
        consecutiva). En fallo lanza ``LLMProviderError`` o una subclase de
        la jerarquía en ``app.core.exceptions``. Nunca retorna valores de
        error.
        """
        raise NotImplementedError
