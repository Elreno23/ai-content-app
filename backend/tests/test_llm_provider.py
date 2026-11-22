import asyncio
import json

import httpx
import pytest

from app.core.exceptions import (
    LLMConnectionError,
    LLMResponseError,
    LLMTimeoutError,
)
from app.schemas.parsers.llm_parser import LlmResponse
from app.services.ai.providers.ollama_provider import OllamaProvider

VALID_LLM_OUTPUT = {
    "narrative": "Juan corre por el pasillo.",
    "detected_actions": ["Juan corre"],
    "visual_metadata": {
        "character": "Juan",
        "visual_action": "corre",
        "expression_gaze": "mira al frente",
        "props_hand": None,
        "environment": "pasillo",
        "camera_lighting": "plano medio, luz natural",
    },
}


def mock_client(monkeypatch, handler):
    transport = httpx.MockTransport(handler)
    real_async_client = httpx.AsyncClient

    def factory(*args, **kwargs):
        kwargs.pop("timeout", None)
        kwargs["transport"] = transport
        return real_async_client(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", factory)
    return OllamaProvider()


def run(coro):
    return asyncio.run(coro)


def test_success_returns_llm_response(monkeypatch):
    def handler(request):
        return httpx.Response(
            200, json={"message": {"content": json.dumps(VALID_LLM_OUTPUT)}}
        )

    provider = mock_client(monkeypatch, handler)
    result = run(provider.generate_script("prompt de prueba"))
    assert isinstance(result, LlmResponse)
    assert result.narrative == VALID_LLM_OUTPUT["narrative"]
    assert result.visual_metadata.character == "Juan"


def test_status_error_raises_response_error(monkeypatch):
    def handler(request):
        return httpx.Response(500, text="internal ollama failure")

    provider = mock_client(monkeypatch, handler)
    with pytest.raises(LLMResponseError, match="status 500"):
        run(provider.generate_script("p"))


def test_invalid_json_raises_response_error(monkeypatch):
    def handler(request):
        return httpx.Response(200, text="esto no es json")

    provider = mock_client(monkeypatch, handler)
    with pytest.raises(LLMResponseError, match="no es un JSON válido"):
        run(provider.generate_script("p"))


def test_missing_message_raises_response_error(monkeypatch):
    def handler(request):
        return httpx.Response(200, json={"otra": "estructura"})

    provider = mock_client(monkeypatch, handler)
    with pytest.raises(LLMResponseError, match="inesperada"):
        run(provider.generate_script("p"))


def test_non_string_content_raises_response_error(monkeypatch):
    def handler(request):
        return httpx.Response(200, json={"message": {"role": "user"}})

    provider = mock_client(monkeypatch, handler)
    with pytest.raises(LLMResponseError, match="sin contenido de texto"):
        run(provider.generate_script("p"))


def test_schema_violation_carries_raw_detail_truncated(monkeypatch):
    long_output = json.dumps({"narrative": "x" * 2000})
    assert len(long_output) > 500

    def handler(request):
        return httpx.Response(200, json={"message": {"content": long_output}})

    provider = mock_client(monkeypatch, handler)
    with pytest.raises(LLMResponseError) as exc_info:
        run(provider.generate_script("p"))
    assert len(exc_info.value.raw_detail) == 500
    assert exc_info.value.raw_detail == long_output[:500]


def test_timeout_raises_timeout_error(monkeypatch):
    def handler(request):
        raise httpx.ReadTimeout("simulated timeout")

    provider = mock_client(monkeypatch, handler)
    with pytest.raises(LLMTimeoutError):
        run(provider.generate_script("p"))


def test_connect_error_raises_connection_error(monkeypatch):
    def handler(request):
        raise httpx.ConnectError("simulated connection refused")

    provider = mock_client(monkeypatch, handler)
    with pytest.raises(LLMConnectionError):
        run(provider.generate_script("p"))


def test_error_hierarchy():
    from app.core.exceptions import AppError, LLMProviderError

    for exc in (LLMConnectionError, LLMTimeoutError, LLMResponseError):
        assert issubclass(exc, LLMProviderError)
        assert issubclass(exc, AppError)
    assert not issubclass(LLMTimeoutError, LLMConnectionError)
    assert not issubclass(LLMConnectionError, LLMTimeoutError)
