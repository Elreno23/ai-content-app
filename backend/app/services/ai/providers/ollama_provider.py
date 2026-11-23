import logging

import httpx
from pydantic import ValidationError

from app.core.exceptions import (
    LLMConnectionError,
    LLMResponseError,
    LLMTimeoutError,
)
from app.schemas.parsers.chapter_parser import ChapterOutput, ChapterStructure
from app.services.ai.base_ai import BaseAIProvider

logger = logging.getLogger(__name__)

MODEL_NAME = "qwen-local"
OLLAMA_CHAT_URL = "http://127.0.0.1:11434/api/chat"
# Valores respaldados por el experimento de evaluación (4/4 runs válidos).
GENERATION_OPTIONS = {
    "num_ctx": 8192,
    "num_predict": 4096,
    "temperature": 0.7,
}
TIMEOUT = 1800


class OllamaProvider(BaseAIProvider):
    async def generate_chapter_structure(self, prompt: str) -> ChapterStructure:
        """Prepara la petición, llama a Ollama y valida la respuesta con Pydantic.

        Contrato: en éxito retorna ``ChapterStructure`` validada contra
        CHAPTER_SCHEMA. En fallo lanza ``LLMProviderError`` o una subclase.
        Nunca retorna valores de error.
        """
        payload = {
            "model": MODEL_NAME,
            "messages": [{"role": "user", "content": prompt}],
            "format": "json",
            "stream": False,
            # qwen-local (Qwen3.5-9B) es un modelo "thinking" (capacidad
            # declarada en /api/show): sin este flag consume todo el
            # presupuesto de tokens en razonamiento y devuelve content vacío.
            "think": False,
            "options": dict(GENERATION_OPTIONS),
        }
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                response = await client.post(
                    OLLAMA_CHAT_URL,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                )
        except httpx.TimeoutException as e:
            raise LLMTimeoutError(
                "Ollama tardó demasiado en generar el capítulo."
            ) from e
        except httpx.ConnectError as e:
            raise LLMConnectionError(
                "No se pudo conectar con Ollama. ¿Está el servidor levantado?"
            ) from e
        except httpx.HTTPError as e:
            raise LLMConnectionError(f"Fallo de red contra Ollama: {e}") from e

        if response.status_code != 200:
            raise LLMResponseError(
                f"Error en Ollama (status {response.status_code}): "
                f"{response.text[:200]}"
            )

        try:
            data = response.json()
        except ValueError as e:
            raise LLMResponseError(
                "La respuesta de Ollama no es un JSON válido"
            ) from e

        if "message" not in data:
            raise LLMResponseError(
                f"Respuesta de Ollama inesperada: {str(data)[:200]}"
            )

        raw_json = data["message"].get("content")
        if not isinstance(raw_json, str) or not raw_json:
            raise LLMResponseError(
                f"Respuesta de Ollama sin contenido de texto: {str(data)[:200]}"
            )

        try:
            output = ChapterOutput.model_validate_json(raw_json)
            return output.chapter
        except ValidationError as e:
            logger.error("Pydantic falló al validar el capítulo del LLM: %s", e)
            logger.error("Texto crudo del LLM: %s", raw_json)
            raise LLMResponseError(
                "El LLM produjo un capítulo que no cumple CHAPTER_SCHEMA",
                raw_detail=raw_json,
            ) from e
