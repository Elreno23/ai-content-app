class AppError(Exception):
    """Base de todos los errores de dominio de la aplicación."""


class LLMProviderError(AppError):
    """Fallo de un proveedor LLM durante la generación."""


class LLMConnectionError(LLMProviderError):
    """No se pudo establecer conexión con el proveedor LLM."""


class LLMTimeoutError(LLMProviderError):
    """El proveedor LLM tardó demasiado en responder."""


class LLMResponseError(LLMProviderError):
    """El proveedor LLM respondió, pero con una salida inutilizable.

    ``raw_detail`` conserva un fragmento de la respuesta original
    (máx. 500 caracteres) exclusivamente para diagnóstico interno y
    logging. Nunca debe enviarse al cliente: la respuesta HTTP solo
    incluye ``str(exc)``.
    """

    RAW_DETAIL_MAX_CHARS = 500

    def __init__(self, message: str, raw_detail: str | None = None) -> None:
        super().__init__(message)
        if raw_detail:
            self.raw_detail = raw_detail[: self.RAW_DETAIL_MAX_CHARS]
        else:
            self.raw_detail = None


class NarrativeStateError(AppError):
    """El estado narrativo almacenado no permite ejecutar la operación."""


class ComfyUIBridgeError(AppError):
    """Fallo en la comunicación con ComfyUI."""


class ComfyUIConnectionError(ComfyUIBridgeError):
    """No se pudo establecer conexión con ComfyUI."""


class ComfyUITimeoutError(ComfyUIBridgeError):
    """ComfyUI tardó demasiado en responder."""


class ComfyUIResponseError(ComfyUIBridgeError):
    """ComfyUI respondió, pero la operación no se pudo completar."""


class ComfyUIWorkflowError(ComfyUIBridgeError):
    """El workflow de ComfyUI es inválido o no es compatible con el bridge."""
