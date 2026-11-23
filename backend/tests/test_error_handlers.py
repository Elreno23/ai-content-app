import pytest
from fastapi import Request

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
from app.main import (
    comfy_connection_error_handler,
    comfy_response_error_handler,
    comfy_timeout_error_handler,
    comfy_workflow_error_handler,
    llm_connection_error_handler,
    llm_response_error_handler,
    llm_timeout_error_handler,
    narrative_state_error_handler,
)

EXPECTED = [
    (llm_connection_error_handler, LLMConnectionError, 503),
    (llm_timeout_error_handler, LLMTimeoutError, 504),
    (llm_response_error_handler, LLMResponseError, 502),
    (comfy_connection_error_handler, ComfyUIConnectionError, 503),
    (comfy_timeout_error_handler, ComfyUITimeoutError, 504),
    (comfy_response_error_handler, ComfyUIResponseError, 502),
    (comfy_workflow_error_handler, ComfyUIWorkflowError, 500),
    (narrative_state_error_handler, NarrativeStateError, 422),
]


def make_request():
    scope = {"type": "http", "method": "POST", "path": "/x", "headers": []}
    return Request(scope)


@pytest.mark.parametrize("handler,exc,expected_status", EXPECTED)
def test_error_handler_translation(handler, exc, expected_status):
    import asyncio
    import json

    response = asyncio.run(handler(make_request(), exc("fallo simulado")))
    assert response.status_code == expected_status
    body = json.loads(response.body)
    assert body["detail"] == "fallo simulado"
    assert "raw_detail" not in body
