from services.ai.base_ai import BaseAIProvider
import requests

MODEL_NAME = ""

class OpenIAProvider(BaseAIProvider):
    def generate_script(self, topic):
        return f"Estamos trabajando en ello..."