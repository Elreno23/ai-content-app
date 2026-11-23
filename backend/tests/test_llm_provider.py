import asyncio
import json

import httpx
import pytest

from app.core.exceptions import (
    AppError,
    LLMConnectionError,
    LLMProviderError,
    LLMResponseError,
    LLMTimeoutError,
)
from app.services.ai.providers.ollama_provider import (
    GENERATION_OPTIONS,
    MODEL_NAME,
    OllamaProvider,
)


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


VALID_CHAPTER_PAYLOAD = {
    "chapter": {
        "title": "La Oferta",
        "summary": "Andres llega con una propuesta que Juan no puede rechazar.",
        "scenes": [
            {
                "number": i,
                "title": f"Escena {i}",
                "summary": f"Resumen concreto de la escena {i} del capitulo de prueba.",
                "beats": [
                    {
                        "number": 1,
                        "content": f"Primera accion concreta de la escena {i} del test.",
                    },
                    {
                        "number": 2,
                        "content": f"Segunda accion concreta de la escena {i} del test.",
                    },
                ],
            }
            for i in range(1, 5)
        ],
    }
}


def test_chapter_structure_success_returns_chapter(monkeypatch):
    def handler(request):
        body = json.loads(request.content)
        assert body["model"] == MODEL_NAME
        assert body["think"] is False
        assert body["options"]["num_ctx"] == GENERATION_OPTIONS["num_ctx"]
        return httpx.Response(
            200, json={"message": {"content": json.dumps(VALID_CHAPTER_PAYLOAD)}}
        )

    provider = mock_client(monkeypatch, handler)
    result = run(provider.generate_chapter_structure("prompt de capitulo"))
    assert result.title == "La Oferta"
    assert [s.number for s in result.scenes] == [1, 2, 3, 4]


def test_chapter_structure_schema_violation_raises_with_raw_detail(monkeypatch):
    broken = {"chapter": {"title": None, "summary": "ok", "scenes": [
        {"number": 2, "title": None, "summary": "x" * 20, "beats": []}
    ]}}

    def handler(request):
        return httpx.Response(200, json={"message": {"content": json.dumps(broken)}})

    provider = mock_client(monkeypatch, handler)
    with pytest.raises(LLMResponseError, match="CHAPTER_SCHEMA") as exc_info:
        run(provider.generate_chapter_structure("p"))
    assert exc_info.value.raw_detail == json.dumps(broken)


def test_chapter_structure_empty_content_raises(monkeypatch):
    def handler(request):
        return httpx.Response(200, json={"message": {"content": ""}})

    provider = mock_client(monkeypatch, handler)
    with pytest.raises(LLMResponseError, match="sin contenido"):
        run(provider.generate_chapter_structure("p"))


def test_chapter_structure_status_error_raises_response_error(monkeypatch):
    def handler(request):
        return httpx.Response(500, text="internal ollama failure")

    provider = mock_client(monkeypatch, handler)
    with pytest.raises(LLMResponseError, match="status 500"):
        run(provider.generate_chapter_structure("p"))


def test_chapter_structure_invalid_json_raises_response_error(monkeypatch):
    def handler(request):
        return httpx.Response(200, text="esto no es json")

    provider = mock_client(monkeypatch, handler)
    with pytest.raises(LLMResponseError, match="no es un JSON válido"):
        run(provider.generate_chapter_structure("p"))


def test_chapter_structure_timeout_raises_timeout_error(monkeypatch):
    def handler(request):
        raise httpx.ReadTimeout("simulated timeout")

    provider = mock_client(monkeypatch, handler)
    with pytest.raises(LLMTimeoutError):
        run(provider.generate_chapter_structure("p"))


def test_chapter_structure_connect_error_raises_connection_error(monkeypatch):
    def handler(request):
        raise httpx.ConnectError("simulated connection refused")

    provider = mock_client(monkeypatch, handler)
    with pytest.raises(LLMConnectionError):
        run(provider.generate_chapter_structure("p"))


def test_error_hierarchy():
    for exc in (LLMConnectionError, LLMTimeoutError, LLMResponseError):
        assert issubclass(exc, LLMProviderError)
        assert issubclass(exc, AppError)
    assert not issubclass(LLMTimeoutError, LLMConnectionError)
    assert not issubclass(LLMConnectionError, LLMTimeoutError)
