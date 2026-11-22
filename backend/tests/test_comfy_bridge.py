import asyncio

import httpx
import pytest

from app.core.exceptions import (
    ComfyUIConnectionError,
    ComfyUIResponseError,
    ComfyUITimeoutError,
    ComfyUIWorkflowError,
)
from app.services.ai.visual_bridge import ComfyUIBridge

SUCCESS_RESPONSE = {
    "prompt_id": "11111111-2222-3333-4444-555555555555",
    "number": 0,
    "node_errors": {},
}


def mock_client(monkeypatch, handler):
    transport = httpx.MockTransport(handler)
    real_async_client = httpx.AsyncClient

    def factory(*args, **kwargs):
        kwargs.pop("timeout", None)
        kwargs["transport"] = transport
        return real_async_client(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", factory)
    return ComfyUIBridge()


def run(coro):
    return asyncio.run(coro)


def test_success_returns_prompt_id(monkeypatch):
    def handler(request):
        assert request.url.path == "/prompt"
        return httpx.Response(200, json=SUCCESS_RESPONSE)

    bridge = mock_client(monkeypatch, handler)
    prompt_id = run(bridge.submit_prompt({"character": "Juan"}))
    assert prompt_id == SUCCESS_RESPONSE["prompt_id"]


def test_node_errors_raises_response_error(monkeypatch):
    def handler(request):
        return httpx.Response(
            200,
            json={**SUCCESS_RESPONSE, "node_errors": {"82": {"errors": ["boom"]}}},
        )

    bridge = mock_client(monkeypatch, handler)
    with pytest.raises(ComfyUIResponseError, match="errores de nodos"):
        run(bridge.submit_prompt({"character": "Juan"}))


def test_rejection_raises_response_error(monkeypatch):
    def handler(request):
        return httpx.Response(400, json={"error": {"type": "missing_node_type"}})

    bridge = mock_client(monkeypatch, handler)
    with pytest.raises(ComfyUIResponseError, match="status 400"):
        run(bridge.submit_prompt({"character": "Juan"}))


def test_invalid_json_raises_response_error(monkeypatch):
    def handler(request):
        return httpx.Response(200, text="no-json")

    bridge = mock_client(monkeypatch, handler)
    with pytest.raises(ComfyUIResponseError, match="no es un JSON válido"):
        run(bridge.submit_prompt({"character": "Juan"}))


def test_missing_prompt_id_raises_response_error(monkeypatch):
    def handler(request):
        return httpx.Response(200, json={"number": 1, "node_errors": {}})

    bridge = mock_client(monkeypatch, handler)
    with pytest.raises(ComfyUIResponseError, match="prompt_id"):
        run(bridge.submit_prompt({"character": "Juan"}))


def test_timeout_raises_timeout_error(monkeypatch):
    def handler(request):
        raise httpx.ReadTimeout("simulated timeout")

    bridge = mock_client(monkeypatch, handler)
    with pytest.raises(ComfyUITimeoutError):
        run(bridge.submit_prompt({"character": "Juan"}))


def test_connect_error_raises_connection_error(monkeypatch):
    def handler(request):
        raise httpx.ConnectError("simulated connection refused")

    bridge = mock_client(monkeypatch, handler)
    with pytest.raises(ComfyUIConnectionError):
        run(bridge.submit_prompt({"character": "Juan"}))


def test_injection_targets_positive_node_and_keeps_negative():
    bridge = ComfyUIBridge()
    payload = bridge._build_payload("TEXTO-INJECT")
    assert payload["prompt"]["88"]["inputs"]["text"] == "TEXTO-INJECT"
    assert payload["prompt"]["77"]["inputs"]["text"].startswith("stick, wooden")


def test_visual_metadata_formatting_skips_none():
    bridge = ComfyUIBridge()
    text = bridge._format_visual_metadata(
        {"character": "Juan", "visual_action": "corre", "props_hand": None}
    )
    assert text == "Juan, corre"


def test_invalid_workflow_raises_workflow_error(tmp_path):
    bad_workflow = tmp_path / "bad.json"
    bad_workflow.write_text('{"88": {"class_type": "OtroNodo", "inputs": {}}}', encoding="utf-8")
    with pytest.raises(ComfyUIWorkflowError):
        ComfyUIBridge(workflow_path=bad_workflow)


def test_missing_workflow_file_raises_workflow_error(tmp_path):
    with pytest.raises(ComfyUIWorkflowError):
        ComfyUIBridge(workflow_path=tmp_path / "inexistente.json")
