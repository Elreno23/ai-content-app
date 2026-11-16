from app.schemas.parsers.llm_parser import LlmResponse
from app.services.ai.base_ai import BaseAIProvider
import httpx

MODEL_NAME = "dolphin-llama3"
class OllamaProvider(BaseAIProvider):
    async def generate_script(self,prompt):
        url = "http://127.0.0.1:11434/api/chat"

        playload = {"model":MODEL_NAME,
                    "messages":[{"role":"user","content":prompt}],
                    "format": "json",
                    "stream": False}
        try:
            async with httpx.AsyncClient(timeout=500) as client:
                response =  await client.post(url,
                                              json=playload,
                                              headers={"Content-Type":"application/json"})
                if response.status_code != 200:
                    return f"Error en Ollama (status {response.status_code}): {response.text}"

                try:
                    data = response.json()
                except ValueError:
                    return f"Error: La respuesta de Ollama no es un JSON válido"
                
                if "message" not in data:
                    return f"Error: Respuesta de Ollama {data}"

                raw_json = data["message"]["content"]
                try:
                    parsed = LlmResponse.model_validate_json(raw_json)
                    return parsed
                
                except Exception as e:
                    print("Pydantic falló al validar el JSON de Ollama:", e)
                    print("Texto crudo que mandó el LLM:", raw_json)
                    raise e
                
        except httpx.ConnectError:
            return "Error: No se pudo conectar con Ollama. ¿Está el servidor levantado?"
        except httpx.ReadTimeout:
            return "Error: Ollama tardó demasiado en responder."
        except httpx.Timeout:
            return "Error: Ollama tardó demasiado en responder."
        except Exception as e:
            return f"Error inesperado en el proveedor Ollama: {str(e)}"

