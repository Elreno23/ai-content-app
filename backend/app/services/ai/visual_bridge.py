import copy
import json
import logging
from pathlib import Path

import httpx

from app.core.exceptions import (
    ComfyUIConnectionError,
    ComfyUIResponseError,
    ComfyUITimeoutError,
    ComfyUIWorkflowError,
)

logger = logging.getLogger(__name__)

DEFAULT_WORKFLOW_PATH = (
    Path(__file__).resolve().parents[1] / "comfy" / "workflows" / "prueba_1.json"
)
DEFAULT_BASE_URL = "http://127.0.0.1:8188/prompt"


class ComfyUIBridge:
    """Envía workflows a ComfyUI mediante su API HTTP (/prompt).

    Contrato: en éxito retorna el ``prompt_id`` asignado por ComfyUI.
    En fallo lanza una subclase de ``ComfyUIBridgeError``. Nunca retorna
    valores de error.
    """

    PROMPT_NODE_ID = "88"

    def __init__(
        self,
        workflow_path: Path = DEFAULT_WORKFLOW_PATH,
        base_url: str = DEFAULT_BASE_URL,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.workflow_template: dict = self._load_workflow(workflow_path)

    def _load_workflow(self, workflow_path: Path) -> dict:
        try:
            with open(workflow_path, "r", encoding="utf-8") as file:
                workflow = json.load(file)
        except FileNotFoundError as e:
            raise ComfyUIWorkflowError(
                f"No se encontró el workflow de ComfyUI: {workflow_path}"
            ) from e
        except ValueError as e:
            raise ComfyUIWorkflowError(
                f"El workflow de ComfyUI no es un JSON válido: {workflow_path}"
            ) from e

        node = workflow.get(self.PROMPT_NODE_ID)
        if not isinstance(node, dict) or node.get("class_type") != "CLIPTextEncode":
            raise ComfyUIWorkflowError(
                f"El workflow no contiene el nodo '{self.PROMPT_NODE_ID}' "
                "(CLIPTextEncode) para inyectar el prompt positivo"
            )
        return workflow

    def _format_visual_metadata(self, visual_metadata: dict) -> str:
        if not visual_metadata:
            return ""
        return ", ".join(
            str(value).strip()
            for value in visual_metadata.values()
            if value is not None
        )

    def _build_payload(self, prompt_text: str) -> dict:
        workflow = copy.deepcopy(self.workflow_template)
        workflow[self.PROMPT_NODE_ID]["inputs"]["text"] = prompt_text
        return {"prompt": workflow}

    async def submit_prompt(self, visual_metadata: dict) -> str:
        prompt_text = self._format_visual_metadata(visual_metadata)
        payload = self._build_payload(prompt_text)
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(self.base_url, json=payload)
        except httpx.TimeoutException as e:
            raise ComfyUITimeoutError(
                "ComfyUI tardó demasiado en aceptar el prompt."
            ) from e
        except httpx.ConnectError as e:
            raise ComfyUIConnectionError(
                "No se pudo conectar con ComfyUI. ¿Está el servidor levantado?"
            ) from e
        except httpx.HTTPError as e:
            raise ComfyUIConnectionError(f"Fallo de red contra ComfyUI: {e}") from e

        if response.status_code != 200:
            raise ComfyUIResponseError(
                f"ComfyUI rechazó el prompt (status {response.status_code}): "
                f"{response.text[:200]}"
            )

        try:
            data = response.json()
        except ValueError as e:
            raise ComfyUIResponseError(
                "La respuesta de ComfyUI no es un JSON válido"
            ) from e

        prompt_id = data.get("prompt_id")
        if not isinstance(prompt_id, str) or not prompt_id:
            raise ComfyUIResponseError(
                f"ComfyUI no devolvió prompt_id: {str(data)[:200]}"
            )

        node_errors = data.get("node_errors") or {}
        if node_errors:
            raise ComfyUIResponseError(
                f"ComfyUI reportó errores de nodos: {str(node_errors)[:200]}"
            )

        return prompt_id
