from services.ai.base_ai import BaseAIProvider
import httpx

MODEL_NAME = "llama3"

class OllamaProvider(BaseAIProvider):
    async def generate_script(self, topic):

        url = "http://127.0.0.1:11434/api/chat"
        prompt = f"Genera un guion cinematográfico en 3 escenas sobre {topic}"
        payload = {
            "model": MODEL_NAME,
             "messages": [
                {"role": "user", "content": prompt}
            ],
            "stream": False
        }
    
        try:
            async with httpx.AsyncClient(timeout=500) as client:
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
            
            return data["message"]["content"]
            
        except httpx.ConnectError:
                return "Error: No se pudo conectar con Ollama. ¿Está el servidor levantado?"
        
        except httpx.ReadTimeout:
            return "Error: Ollama tardó demasiado en responder."
        
        except httpx.Timeout:
             return "Error: Ollama tardó demasiado en responder."
        
        except Exception as e:
            return f"Error inesperado en el proveedor Ollama: {str(e)}"
        