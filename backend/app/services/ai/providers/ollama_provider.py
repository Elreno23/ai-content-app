import logging

import httpx
from pydantic import ValidationError

from app.core.exceptions import (
    LLMConnectionError,
    LLMResponseError,
    LLMTimeoutError,
)
from app.schemas.parsers.llm_parser import LlmResponse
from app.services.ai.base_ai import BaseAIProvider

logger = logging.getLogger(__name__)

MODEL_NAME = "dolphin-llama3"
OLLAMA_CHAT_URL = "http://127.0.0.1:11434/api/chat"


class OllamaProvider(BaseAIProvider):
    async def generate_script(self, prompt: str) -> LlmResponse:
        payload = {
            "model": MODEL_NAME,
            "messages": [{"role": "user", "content": prompt}],
            "format": "json",
            "stream": False,
        }
        try:
            async with httpx.AsyncClient(timeout=500) as client:
                response = await client.post(
                    OLLAMA_CHAT_URL,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                )
        except httpx.TimeoutException as e:
            raise LLMTimeoutError("Ollama tardó demasiado en responder.") from e
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
        if not isinstance(raw_json, str):
            raise LLMResponseError(
                f"Respuesta de Ollama sin contenido de texto: {str(data)[:200]}"
            )

        try:
            return LlmResponse.model_validate_json(raw_json)
        except ValidationError as e:
            logger.error("Pydantic falló al validar el JSON de Ollama: %s", e)
            logger.error("Texto crudo del LLM: %s", raw_json)
            raise LLMResponseError(
                "El LLM produjo una salida que no cumple el schema esperado",
                raw_detail=raw_json,
            ) from e
