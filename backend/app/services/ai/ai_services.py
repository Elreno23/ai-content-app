from backend.app.services.ai.providers.ollama_provider import OllamaProvider
from backend.app.services.ai.providers.openai_provider import OpenIAProvider
import os

provider_name = os.getenv("AI_PROVIDER","ollama")

if provider_name == "ollama":
    provider = OllamaProvider()
elif provider_name == "openai":
    provider = OpenIAProvider()
else:
    raise ValueError(f"Proveedor de IA no soportado: {provider_name}")

async def generate_script(topic:str):
    return await provider.generate_script(topic)