import pytest
from fastapi.testclient import TestClient

from app.core.exceptions import (
    ComfyUIConnectionError,
    ComfyUIResponseError,
    ComfyUITimeoutError,
    ComfyUIWorkflowError,
    LLMConnectionError,
    LLMResponseError,
    LLMTimeoutError,
    NarrativeStateError,
)
from app.dependencies import get_script_service

EXPECTED = [
    (LLMConnectionError, 503),
    (LLMTimeoutError, 504),
    (LLMResponseError, 502),
    (ComfyUIConnectionError, 503),
    (ComfyUITimeoutError, 504),
    (ComfyUIResponseError, 502),
    (ComfyUIWorkflowError, 500),
    (NarrativeStateError, 422),
]


class StubService:
    def __init__(self, exc):
        self.exc = exc

    async def generate_script(self, topic=None):
        raise self.exc("fallo simulado")


@pytest.mark.parametrize("exc,expected_status", EXPECTED)
def test_error_handlers(exc, expected_status):
    from app.main import app

    app.dependency_overrides[get_script_service] = lambda: StubService(exc)
    try:
        client = TestClient(app, raise_server_exceptions=False)
        response = client.post("/generate-script", json={"topic": "x"})
        assert response.status_code == expected_status
        body = response.json()
        assert body["detail"] == "fallo simulado"
        assert "raw_detail" not in body
    finally:
        app.dependency_overrides.clear()
