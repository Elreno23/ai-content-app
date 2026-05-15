from backend.app.services.ai.base_ai import BaseAIProvider
import httpx
from backend.app.schemas.parsers.llm_parser import LlmResponse 

MODEL_NAME = "llama3"

class OllamaProvider(BaseAIProvider):
    async def generate_script(self, topic):

        url = "http://127.0.0.1:11434/api/chat"
        prompt = """
Eres un generador narrativo. Tu única tarea es producir una salida en formato JSON ESTRICTO.

REGLAS:
- Devuelve SOLO JSON. Nada de texto fuera del JSON.
- No añadas explicaciones, comentarios ni texto antes o después.
- El JSON debe tener exactamente estos campos:

{
  "narrative": "string",
  "detected_actions": [
    {
      "type": "USER_ARRIVED_LATE" | "USER_LIED" | "USER_HELPED" | "USER_IGNORED",
      "target": "string o null"
    }
  ]
}

- La narrativa debe ser texto libre.
- Las acciones deben pertenecer SOLO a la taxonomía permitida.
- Si no puedes generar un JSON válido, devuelve exactamente:
  {"error":"UNABLE_TO_GENERATE_JSON"}

EJEMPLO VÁLIDO:
{
  "narrative": "María llegó tarde a la reunión y todos la miraron en silencio.",
  "detected_actions": [
    {
      "type": "USER_ARRIVED_LATE",
      "target": "María"
    }
  ]
}

EJEMPLO DE ERROR:
{"error":"UNABLE_TO_GENERATE_JSON"}

Ahora genera la salida JSON siguiendo estas reglas.
"""

        payload = {
            "model": MODEL_NAME,
             "messages": [
                {"role": "user", "content": prompt}
            ],
            "stream": False
        }
    
        try:
            async with httpx.AsyncClient(timeout=900) as client:
                response = await client.post(url,
                                             json=payload,
                                             headers={"Content-Type": "application/json"})
            if response.status_code != 200:
                return f"Error en Ollama (status {response.status_code}): {response.text}"
            try:
                data = response.json()
                print(data)
            except ValueError:
                return "Error Ollama devolvió una respuesta que no es JSON válido"
            
            if "message" not in data:
                return f"Error: la respuesta de Ollama: {data}"
            
            raw_json =  data["message"]["content"]
        
            try:
                parsed = LlmResponse.model_validate_json(raw_json)
                return parsed
            except Exception as e:
                return {
                    "error": "INVALID_JSON_FROM_LLM",
                    "details": str(e),
                    "raw": raw_json
                }

        except httpx.ConnectError:
                return "Error: No se pudo conectar con Ollama. ¿Está el servidor levantado?"
        
        except httpx.ReadTimeout:
            return "Error: Ollama tardó demasiado en responder."
        
        except httpx.Timeout:
             return "Error: Ollama tardó demasiado en responder."
        
        except Exception as e:
            return f"Error inesperado en el proveedor Ollama: {str(e)}"
        