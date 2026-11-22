from abc import ABC, abstractmethod

from app.schemas.parsers.llm_parser import LlmResponse


class BaseAIProvider(ABC):
    @abstractmethod
    async def generate_script(self, prompt: str) -> LlmResponse:
        """Genera un guion narrativo a partir de un prompt.

        Contrato: en éxito retorna ``LlmResponse``. En fallo lanza
        ``LLMProviderError`` o una subclase de la jerarquía en
        ``app.core.exceptions``. Nunca retorna valores de error.
        """
        raise NotImplementedError
